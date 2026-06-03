# 纯 UYA 重构 VP8 编解码器详细设计

## 1. 目标与边界

本项目目标是用纯 UYA 重新实现一个可维护、可验证、可 SIMD 优化的 VP8 视频编解码器。这里的“纯 UYA”定义为：

- 运行时代码全部为 `.uya` 源文件，不依赖 libvpx、FFmpeg、C/C++ intrinsics 或外部汇编文件。
- 优先使用 UYA 内建 `@vector(T,N)` / `@mask(N)` 表达 SIMD 语义，让 C99 后端在 x86_64 SSE、ARM NEON 或标量回退之间生成等价代码。
- UYA `@asm` 只作为可选的、隔离的极热点微内核补充，不能成为正确性依赖；默认构建必须可在无 `@asm` 路径下通过。
- 外部工具只允许用于测试和差分验证，例如调用 `vpxdec`/`vpxenc` 生成 golden，不进入库的运行时依赖。

第一目标是 bit-exact VP8 decoder。第二目标是可用 encoder。第三目标是围绕 VP8 热点建立完整 SIMD 和并行流水线。

明确不做：

- 不实现 VP9、AV1、VP8L、WebP lossless。
- 不在第一阶段实现完整 Matroska/WebM muxer/demuxer；先支持 IVF 和裸 VP8 payload。
- 不为了追求局部性能破坏标量参考路径。所有 SIMD 路径都必须能和 scalar reference 做逐块对照。
- 不把“能解析 header”称为“支持 VP8 解码”；必须完成重建、环路滤波、参考帧更新并输出 YUV 才算 decoder 可用。

## 2. VP8 能力范围

### 2.1 Decoder 覆盖

必须支持 VP8 8-bit YUV 4:2:0 bitstream：

- Key frame 和 inter frame。
- Frame tag、key frame start code、width/height/scale。
- Boolean arithmetic decoder。
- Segmentation、quantizer delta、loop filter delta。
- Simple 和 normal loop filter。
- 1/2/4/8 token partitions。
- Intra 16x16、intra 4x4、chroma 8x8 prediction。
- Inter prediction、sub-pixel interpolation、motion vector 解码。
- Last、golden、alternate reference frame 管理。
- Coefficient entropy、probability update、EOB context。
- Y2 Walsh-Hadamard inverse transform、4x4 inverse DCT、dequant、reconstruction。

### 2.2 Encoder 覆盖

Encoder 分阶段支持：

- MVP：key-frame only intra encoder，输出合法 IVF/VP8，质量可控。
- Baseline：inter frame、last/golden/altref reference、整数像素与亚像素运动估计、skip、segmentation。
- Quality：RD mode decision、rate control、token probability adaptation、loop filter level decision。
- Performance：SIMD SAD/SSE/SATD、并行 motion search、row-level encode pipeline。

### 2.3 容器与 I/O

优先级：

1. IVF demux/mux：简单、适合测试和 CLI。
2. 裸 VP8 frame payload：适合库 API 和 RTP/WebRTC 上层集成。
3. WebM subset demux：后续实现最小 Matroska reader，只抽 VP8 track。
4. RTP payload：后续以无拷贝 packet assembler 形式实现。

## 3. 模块划分

建议目录结构：

```text
src/main.uya                         CLI 入口
src/vp8/api.uya                      公共 decoder/encoder API
src/vp8/errors.uya                   错误码、诊断上下文
src/vp8/common/types.uya             基础类型、枚举、常量
src/vp8/common/arena.uya             arena/scratch allocator
src/vp8/common/plane.uya             Y/U/V plane、stride、border
src/vp8/common/frame.uya             FrameBuffer、reference frame pool
src/vp8/common/cpu.uya               SIMD 能力和运行时选路

src/vp8/container/ivf.uya            IVF reader/writer
src/vp8/container/raw.uya            裸 VP8 frame reader/writer
src/vp8/container/webm_subset.uya    后续 WebM subset

src/vp8/bitstream/bool_reader.uya    VP8 boolean decoder
src/vp8/bitstream/bool_writer.uya    VP8 boolean encoder
src/vp8/bitstream/header.uya         frame tag 和 uncompressed header

src/vp8/entropy/probs.uya            默认概率表、更新逻辑
src/vp8/entropy/tokens.uya           coefficient token decode/encode
src/vp8/entropy/mv.uya               motion vector probability
src/vp8/entropy/stats.uya            encoder probability stats

src/vp8/decoder/context.uya          Decoder、FrameContext、row context
src/vp8/decoder/parse.uya            frame header、mode、token partition 解析
src/vp8/decoder/predict.uya          intra/inter predictor 调度
src/vp8/decoder/recon.uya            dequant、inverse transform、reconstruct
src/vp8/decoder/loopfilter.uya       loop filter 调度
src/vp8/decoder/refs.uya             reference frame refresh 和 border extension

src/vp8/encoder/context.uya          Encoder、RateControl、Lookahead
src/vp8/encoder/analysis.uya         macroblock 分析与 mode search
src/vp8/encoder/motion.uya           motion estimation
src/vp8/encoder/rd.uya               rate-distortion 模型
src/vp8/encoder/quant.uya            forward transform、quant、tokenize
src/vp8/encoder/pack.uya             header、partition、bool writer 打包

src/vp8/kernels/scalar.uya           标量参考 kernel
src/vp8/kernels/simd.uya             @vector/@mask SIMD kernel
src/vp8/kernels/dispatch.uya         函数表和运行时选路
src/vp8/kernels/asm_x86.uya          可选 @asm 微内核
src/vp8/kernels/asm_arm.uya          可选 @asm 微内核

tests/                              单元、golden、fuzz、性能测试
bench/                              benchmark harness
docs/                               设计、TODO、格式和性能记录
```

## 4. 核心数据结构

### 4.1 Plane 与 FrameBuffer

`Plane` 是所有像素操作的基础：

- `data`: 指向实际分配块。
- `origin`: 指向可见图像左上角，保留 border 后不一定等于 `data`。
- `width` / `height`: 可见区域。
- `stride`: 行跨度，按 32 或 64 字节对齐。
- `border`: 用于 inter prediction 的扩展边界，luma 至少覆盖 sub-pixel filter 访问范围，chroma 也要独立扩展。

`FrameBuffer` 包含 Y、U、V 三个 plane：

- VP8 固定 4:2:0，U/V 尺寸为 `(width+1)/2`、`(height+1)/2`。
- 内部尺寸向 macroblock 对齐，visible crop 由输出层处理。
- 分配时保证每个 plane 起始地址适合 `@vector.load` 快路径；若 UYA 后端对未对齐加载不稳定，使用安全 load helper。

### 4.2 Macroblock 数据

Macroblock 维度：

- `mb_cols = (width + 15) / 16`
- `mb_rows = (height + 15) / 16`

建议使用 SoA，而不是每个 macroblock 一个巨型 struct：

- `segment_id[mb_count]`
- `skip_coeff[mb_count]`
- `y_mode[mb_count]`
- `uv_mode[mb_count]`
- `ref_frame[mb_count]`
- `mv[mb_count]`
- `filter_level[mb_count]`
- `b_mode[mb_count * 16]`

原因：

- Decoder 解析 mode 时顺序写入，reconstruct/loopfilter 顺序读取。
- Encoder mode search 可以按字段批量访问。
- SIMD 和 cache 更友好。
- 避免 hot loop 复制大 struct。

### 4.3 Token 与系数暂存

Decoder 每个 macroblock 最多涉及：

- 16 个 Y 4x4 block。
- 4 个 U block。
- 4 个 V block。
- 可选 1 个 Y2 block。

推荐结构：

- `CoeffBlock`: 16 个 `i16` qcoeff 或 dequant coeff。
- `MbCoeffScratch`: 25 个 block，栈上或 row scratch 复用。
- `AboveContext` / `LeftContext`: 记录每个 block 是否 non-zero，用于 token context。

系数暂存策略：

- 默认单线程路径采用 token decode -> dequant/transform -> reconstruct 的融合流程。`MbCoeffScratch` 只保存当前 macroblock 或当前 row window，不做整帧 coefficient materialization。
- 并行 token partition 路径可以把 token decode 到 row-local `MbCoeffScratchRing`，但 ring 必须有固定深度和 backpressure，默认只保留少量 row，不允许无界缓存整帧系数。
- `EOB=0`、DC-only 等高频场景走 summary/fast-path，避免填充和搬运 25 个完整 `CoeffBlock`。
- performance stats 记录 coefficient scratch bytes written/read，用于发现“先写全帧再读全帧”的带宽退化。

单线程融合路径和并行 row-local ring 共享同一个 block kernel，避免两套正确性逻辑。

### 4.4 Probability State

`Vp8Probs` 保存 frame 内概率状态：

- coefficient token probabilities。
- Y/UV mode probabilities。
- MV probability。
- segmentation map probability。
- loop filter deltas。

Decoder 按 bitstream 更新；Encoder 每帧从 stats 决定是否写概率更新。概率更新逻辑必须和 bool coder 隔离，便于单独 golden 测试。

## 5. Decoder 流水线

### 5.1 Frame decode 总流程

```text
read frame payload
parse frame tag
if key frame:
    parse key frame header and reset decoder state
parse segmentation / loop filter / quant / token partitions
parse probability updates
parse macroblock modes from first partition
decode coefficient tokens from token partitions
for each macroblock row:
    predict intra/inter
    inverse transform + add residual
    update above/left contexts
    apply row-delayed loop filter
refresh reference frames
extend borders
emit visible YUV frame
```

### 5.2 Header 与 partitions

第一 partition 包含 frame header、probability update 和 macroblock mode syntax。Token partitions 存放 coefficient tokens。

实现要求：

- 所有 partition size 必须边界检查。
- Boolean reader 不能越过 partition。
- `num_token_partitions = 1 << token_partition_bits`。
- token partition 到 macroblock row 的映射要封装为函数，并用 small frame golden 验证。
- 任意 parse 错误都返回带 offset、partition id、frame number 的错误。

### 5.3 Mode parse

Key frame：

- 解析 `y_mode`：DC、V、H、TM、B_PRED。
- `B_PRED` 时解析 16 个 4x4 luma mode。
- 解析 `uv_mode`：DC、V、H、TM。
- 根据 segmentation、skip、coeff token presence 更新上下文。

Inter frame：

- 解析 skip、segment。
- 解析 intra/inter 标记。
- inter 时解析 ref frame、motion vector、sub-pixel offset。
- 处理 near/nearest/zero/new mv。
- 更新 above/left MV context。

### 5.4 Prediction

Intra predictor：

- Y 16x16：DC、V、H、TM。
- Y 4x4：B_DC、B_TM、B_VE、B_HE、B_LD、B_RD、B_VR、B_VL、B_HD、B_HU。
- UV 8x8：DC、V、H、TM。
- 边界缺失时按 VP8 规则使用默认 left/top/top-left。

Inter predictor：

- 整数像素 copy。
- 半/四分像素 sub-pixel interpolation。
- Luma 和 chroma 独立处理，motion vector 缩放和边界裁剪要封装。
- 临时 buffer 复用，先水平后垂直，避免每 block 分配。

### 5.5 Transform 与重建

Decoder reference kernel：

- Y2 inverse Walsh-Hadamard。
- 4x4 inverse DCT。
- DC-only 快路径。
- Dequant。
- Residual add with clamp to `0..255`。

设计原则：

- 标量 transform 作为 bit-exact 基准。
- SIMD transform 必须逐 block 与标量输出完全一致。
- 所有中间值类型显式使用 `i16`/`i32`，避免 UYA 默认整数类型导致溢出语义不清。
- DC-only、EOB=0 是高频路径，要单独优化。

### 5.6 Loop Filter

需要支持：

- simple filter。
- normal filter。
- macroblock edge 和 sub-block edge。
- segmentation/ref/mode delta 影响下的 per-MB filter level。
- high edge variance mask。

实现策略：

- 先写标量、逐边、逐像素 reference。
- 再写 row-level dispatcher：按 Y/UV、vertical/horizontal、MB edge/block edge 调度。
- 最后写 SIMD kernel：一次处理 8 或 16 个边缘像素，使用 vector compare/select 表达 mask。

Loop filter row 依赖：

- 当前 row 重建完成后，可以过滤上一 row 的 horizontal MB edge。
- 当前 macroblock 左邻已重建后，可以过滤 vertical edge。
- 并行实现中使用 row fence，避免读未完成像素。

### 5.7 Reference Frame 管理

VP8 decoder 需要维护：

- current frame。
- last frame。
- golden frame。
- altref frame。

刷新规则由 bitstream 标志控制。实现时使用 `FramePool`：

- 固定数量 buffer，避免每帧分配。
- refresh 时更新 logical reference 到 physical slot 的映射，优先 alias/ref-count，不做大拷贝。
- 多个 reference 指向同一 reconstructed current frame 时只增加引用计数；下一帧 current 必须从 free slot 取得，或在外部 `DecodedFrame` lease 仍占用时延迟复用。
- full-plane copy 只能作为明确的 fallback，并且必须计入 `bytes_copied_for_ref_refresh`；正常 decode 期望该指标为 0。
- 每个 plane 维护 border dirty flag，只在 frame 成为 reference 前扩展，避免重复 border extension。
- 每次作为 reference 前保证 border 已扩展。
- key frame 重置 reference 状态。

## 6. Encoder 流水线

### 6.1 Encoder 总流程

```text
accept YUV420 frame
decide frame type and reference refresh flags
choose segmentation / quantizer / loop filter level
for each macroblock:
    intra/inter mode search
    motion estimation
    transform + quantize
    reconstruct local frame
    collect token/mode/mv stats
decide probability updates
write first partition
write token partitions
run loop filter on reconstructed frame
refresh reference frames
```

Encoder 必须本地重建当前帧，并用重建帧刷新 reference，不能使用源图像作为参考。

### 6.2 Intra Encoder MVP

第一版 encoder 只做 key frame：

- 固定或简单自适应 quantizer。
- 16x16 intra mode search。
- 可选 4x4 intra mode search。
- UV mode search。
- forward DCT/WHT、quantize、tokenize。
- bool writer 写合法 bitstream。
- 输出 IVF。

验收：

- 自己的 decoder 能解。
- libvpx/vpxdec 能解。
- 小图像 roundtrip 的 PSNR 和 MD5 稳定。

### 6.3 Inter Encoder

逐步增加：

- last/golden/altref reference 选择。
- integer-pel diamond/hex search。
- half/quarter-pel refinement。
- SAD/SSE/SATD cost。
- MV rate cost。
- skip decision。
- segmentation for static/flat/noisy blocks。
- loop filter level decision。

### 6.4 Rate Control

分三层：

- CQP：固定 quantizer，最先实现。
- CRF-like：按复杂度调 macroblock quant/segment。
- CBR/VBR：buffer model、frame target bits、overshoot 修正。

VP8 bool writer 的实际 bit cost 要能回传给 rate control。Encoder 不应只依赖估算。

## 7. SIMD 设计

### 7.1 SIMD 抽象原则

SIMD 代码分三层：

1. `scalar.uya`：权威正确性实现。
2. `simd.uya`：使用 `@vector/@mask` 的 portable SIMD。
3. `asm_*.uya`：可选 `@asm` 极热点实现。

公共 dispatcher：

- 初始化时检测 CPU 和构建能力。
- 每个 kernel 有函数表入口。
- 支持环境变量或 CLI 强制 `scalar`，用于定位问题。
- benchmark 同时记录 scalar 与 SIMD 结果。

建议枚举：

```text
SimdLevel.scalar
SimdLevel.vector128
SimdLevel.vector256_tiled
SimdLevel.asm_x86
SimdLevel.asm_arm
```

`vector256_tiled` 不要求目标 CPU 真有 256-bit 指令，可以用多个 `@vector(u8,16)` 或 `@vector(i32,4)` tile 表达；后端能发 SSE/NEON 时自动收益，不能时仍正确。

`SimdLevel.vector128` 和 `SimdLevel.vector256_tiled` 只表示选择 portable vector kernel，不承诺一定产生真实硬件 SIMD。具体 kernel 是否进入默认 dispatcher，必须由编译验证、生成 C/汇编检查和 benchmark 决定。

### 7.2 UYA SIMD 使用约束

当前 UYA 支持的关键能力：

- `@vector(T,N)`、`@mask(N)`。
- `@vector.splat`。
- `@vector.load` / `@vector.store`。
- `@vector.select`。
- `@vector.reduce_add` / `reduce_mul` / `reduce_min` / `reduce_max`。
- `@vector.any` / `@vector.all`。

当前性能限制：

- `@vector.load` / `@vector.store` 语义允许 C99 后端用 `memcpy` 实现；热路径必须检查生成 C/汇编，不能假设一定是单条 load/store。
- `@vector.select`、`reduce_*` 和宽通道 tile 可能降级为逐 lane helper；只有 benchmark 证明有收益时才默认启用。
- `shuffle`、`widen/truncate/convert` 仍属于缺口。依赖这些能力的 SAD、sub-pixel、narrow-store kernel 必须保留 scalar tile fallback 或可选 `@asm` 微内核。
- portable SIMD 代码的第一目标是表达清晰和 bit-exact；性能合入由门禁决定，而不是由使用了 `@vector` 自动成立。

编码规范：

- `@mask(N)` 不能当普通 `bool`，分支使用 `@vector.any/all`。
- 热路径显式写类型别名，例如 `type U8x16 = @vector(u8, 16)`。
- 不在 kernel 中使用隐式默认整数，所有常量加后缀或显式转换。
- 对不确定的未对齐加载封装在 `load_u8x16` helper 中。
- SIMD 不能改变溢出和 rounding 语义；VP8 bit-exact kernel 优先使用整数。

### 7.3 SIMD 热点清单

Decoder 优先级：

1. Reconstruction add/clamp。
2. Intra prediction fill/copy/average。
3. Inter predictor copy 和 sub-pixel filter。
4. Loop filter masks 和边缘更新。
5. Inverse DCT/WHT DC-only 快路径。
6. Border extension。
7. YUV plane copy/pack。

Encoder 优先级：

1. SAD 16x16、8x8、4x4。
2. SSE/variance。
3. SATD/Hadamard cost。
4. Sub-pixel interpolation for search。
5. Forward DCT/WHT。
6. Quant/dequant/token scan。
7. Intra predictor cost evaluation。

### 7.4 典型 SIMD kernel 设计

SAD 16x16：

- 每行加载 16 个 `u8`。
- 扩展为 `u16` 或 `i16` 后求 abs diff。
- 以 `u32` 或 `i32` 累加。
- `@vector.reduce_add` 得到标量。
- 若 UYA 缺少直接 widening，先实现 tile helper，并把 vector widening 列为编译器增强任务。

Reconstruct add：

- 加载 predictor `u8x16`。
- 加载 residual `i16x16` 或拆成两个 `i16x8`。
- 转 `i16` 后相加。
- clamp 到 `0..255`。
- narrow/store。
- 若缺少 narrow/saturate，保留 `@vector.select` 组合或局部标量收尾。

Loop filter：

- 加载 p3 p2 p1 p0 q0 q1 q2 q3。
- vector compare 生成 mask：limit、blimit、thresh、hev。
- `@vector.select` 根据 mask 选择更新值。
- 写回 p1/p0/q0/q1 或更宽 normal filter 更新。

Sub-pixel filter：

- 水平 filter 一次处理 8 或 16 个输出像素。
- 需要相邻 6 tap；用连续 load + lane shift/shuffle。
- 若当前 UYA `@vector` shuffle 不足，先以 `@asm` 可选微内核或标量 tile fallback 实现，接口保持一致，等待 UYA shuffle/lane extract 增强。

### 7.5 SIMD 正确性制度

每个 SIMD kernel 必须有：

- 固定输入 golden。
- 随机输入 scalar-vs-simd 对照。
- 边界输入：0、255、最大 residual、负 residual、奇数 stride、未对齐 origin。
- Address sanitizer 类越界验证，至少用 guard bytes。
- benchmark，记录 cycles/px 或 ns/block。

SIMD 的合入标准：

- 默认测试同时跑 scalar 和 SIMD。
- SIMD 与 scalar bit-exact。
- 记录对应 kernel 的生成 C/汇编检查结论，确认热操作没有明显退化为多余拷贝或逐 lane 临时对象风暴。
- 对目标 workload 至少有可测收益；内存型 kernel 默认要求不慢于 scalar 且建议达到 1.10x，计算型 kernel 建议达到 1.25x。达不到阈值时保留代码但不默认启用。
- decoder 端到端 SIMD 路径不能比 scalar 慢超过 5%；否则 `--force-simd` 可用但默认 dispatcher 回退 scalar。
- 具体默认启用阈值以 `bench/kernel_thresholds.json` 为准，并由 `make check-kernel-thresholds` 校验。

## 8. 并行与调度

### 8.1 Decoder 并行

VP8 token partition 天然允许部分并行：

- token partitions 按 macroblock row 映射。
- 可先并行 decode coefficient tokens 到 row scratch。
- reconstruct 有上/左像素依赖，适合 row pipeline。
- loop filter 需要 row delay。

推荐阶段：

1. 单线程 bit-exact。
2. token decode 并行。
3. row reconstruct pipeline。
4. loopfilter row pipeline。

所有并行任务必须保持 deterministic output 和 deterministic error reporting。

### 8.2 Encoder 并行

Encoder 可并行区域：

- motion search across macroblocks with row dependency guard。
- intra/inter cost 计算。
- token stats 收集后 reduce。
- lookahead frame analysis。

不可随意并行：

- bool writer bit packing。
- probability update 决策。
- 依赖左/上 mode context 的最终 mode coding。

实现策略是“分析并行、最终打包串行或分 partition 串行”。

## 9. 内存与性能策略

### 9.1 分配原则

- 初始化时分配 decoder/encoder context。
- 每帧复用 frame buffers、row contexts、coefficient scratch。
- hot loop 禁止 heap allocation。
- stride 对齐到 32/64 字节。
- Plane border 一次分配，frame 完成后统一 extend。
- 所有临时 buffer 使用 arena，并在 frame end reset。

### 9.2 Cache 策略

- 按 macroblock row 顺序处理，提升 top/left context 局部性。
- Loop filter 和 reconstruct 尽量在同一 row window 内完成。
- Encoder motion search 对 reference frame 使用局部 search window，减少大范围随机访问。
- Token stats 使用 per-thread 局部数组，最后 reduce，避免 atomic。

### 9.3 性能指标

建议 benchmark：

- `decode_ivf_360p_scalar`
- `decode_ivf_720p_scalar`
- `decode_ivf_720p_simd`
- `decode_ivf_1080p_simd`
- `sad_16x16_scalar_vs_simd`
- `subpel_16x16_scalar_vs_simd`
- `loopfilter_row_scalar_vs_simd`
- `encode_keyframe_720p`
- `encode_inter_720p`

核心指标：

- fps。
- cycles/pixel。
- ns/macroblock。
- bytes allocated per frame。
- hot-loop heap allocation count。
- bytes copied per frame。
- bytes copied for reference refresh。
- coefficient scratch bytes written/read。
- border extension count。
- scalar-vs-simd speedup。
- decode output MD5。
- encoder bitrate/PSNR/SSIM。

### 9.4 性能回归门禁

硬性门禁：

- 完成 context 初始化后，decode hot loop heap allocation count 必须为 0。
- reference refresh 的整帧 copy 在正常样本中必须为 0 bytes；若 fallback 触发，stats 和 debug log 必须可见。
- coefficient scratch 不允许整帧无界缓存；并行路径的 scratch 峰值应与 `ring_depth * mb_cols` 成正比。
- SIMD 默认启用前必须有 scalar-vs-simd benchmark 和生成 C/汇编检查记录。
- SIMD kernel 默认启用阈值表由 `bench/kernel_thresholds.json` 记录，阈值表变更必须通过 `make check-kernel-thresholds`。

阶段性建议阈值：

- Phase 7 scalar decoder 建立 360p/720p baseline，后续同样样本 cycles/pixel 退化超过 5% 需说明。
- Phase 10 单个 SIMD kernel 未达到预期 speedup 时不进入默认 dispatcher。
- Phase 11 1080p 多线程结果必须报告 fps、cycles/pixel、线程数、bytes copied/frame、allocation count。

## 10. 错误处理与诊断

错误类型至少包括：

- `ErrShortInput`
- `ErrBadFrameTag`
- `ErrBadKeyframeStartCode`
- `ErrUnsupportedVersion`
- `ErrBadPartitionSize`
- `ErrBoolReaderOverread`
- `ErrBadProbabilityUpdate`
- `ErrInvalidMode`
- `ErrInvalidMotionVector`
- `ErrFrameSizeChangedUnsupported`
- `ErrOutOfMemory`
- `ErrInternalInvariant`

诊断上下文：

- frame index。
- partition id。
- byte offset。
- macroblock row/col。
- block index。
- current syntax stage。

CLI debug 开关：

- `--trace-header`
- `--trace-mb r,c`
- `--dump-probs`
- `--dump-yuv`
- `--force-scalar`
- `--force-simd`

## 11. 测试策略

### 11.1 Unit Tests

- bool reader/writer roundtrip。
- frame tag parser。
- partition boundary。
- probability update。
- token decode。
- inverse transforms。
- predictors。
- loop filter。
- reference refresh。
- IVF reader/writer。

### 11.2 Golden Tests

Golden 来源：

- 手写 tiny bitstream。
- libvpx 生成的小尺寸 IVF。
- 真实公开 VP8 样本的截短集合。

Golden 断言：

- header fields。
- frame count。
- visible width/height。
- 每帧 YUV MD5。
- 关键中间态可选：MB mode map、filter level map、token counts。

### 11.3 Differential Tests

- scalar decoder vs SIMD decoder。
- UYA decoder vs libvpx decode output。
- UYA encoder output 能被 libvpx decode。
- UYA encoder output 被 UYA decoder roundtrip。
- bool writer output 再经 bool reader 解析一致。

### 11.4 Fuzz Tests

重点 fuzz：

- frame tag。
- partition sizes。
- bool reader。
- probability updates。
- MV decode。
- coefficient token stream。
- IVF headers。

要求：

- 不崩溃。
- 不越界。
- 错误可诊断。
- fuzz 后 decoder context 可继续处理下一输入。

## 12. API 设计

### 12.1 Decoder API

概念接口：

```text
Decoder.init(options, allocator) -> !Decoder
Decoder.decode_frame(payload: &[const u8]) -> !DecodedFrame
Decoder.flush() -> void
Decoder.set_simd_level(level: SimdLevel) -> !void
Decoder.stats() -> DecoderStats
```

`DecodedFrame`：

- `y/u/v` plane view。
- visible width/height。
- stride。
- pts/duration optional。
- colorspace/clamping flags。

生命周期：

- `DecodedFrame` 默认是 borrowed view，指向 decoder-owned frame slot。
- API 必须提供 release/lease 语义，或明确规定下一次 `decode_frame` 会使前一个 borrowed view 失效。
- 如果调用方需要跨多帧保留输出，使用显式 owned copy API；decode 默认路径不能为规避生命周期问题隐式复制整帧。

### 12.2 Encoder API

概念接口：

```text
Encoder.init(config, allocator) -> !Encoder
Encoder.encode_frame(input: YuvFrameView, flags: EncodeFlags) -> !EncodedPacket
Encoder.flush() -> !EncodedPacket
Encoder.stats() -> EncoderStats
```

`EncoderConfig`：

- width/height。
- target bitrate 或 quantizer。
- fps。
- keyframe interval。
- speed preset。
- thread count。
- simd level。

### 12.3 CLI

建议命令：

```text
vp8uya info <input.ivf>
vp8uya decode <input.ivf> --yuv out.yuv
vp8uya decode-frame <input.ivf> --index N --dump out.yuv
vp8uya encode <input.yuv> --width W --height H --fps N --out out.ivf
vp8uya bench decode <input.ivf>
vp8uya bench kernels
vp8uya fuzz-smoke <seed>
vp8uya compare <input.ivf> --with-vpxdec /path/vpxdec
```

## 13. 迁移与实现顺序

推荐路线：

1. 建立项目 scaffold、文档、测试 harness。
2. 实现 IVF、frame tag、bool reader。
3. 实现 decoder header/mode/token parse。
4. 完成标量 transform、predict、reconstruct、loopfilter。
5. 用小 bitstream 达成 bit-exact decode。
6. 增加 reference frame、inter prediction、segmentation，跑真实 IVF。
7. 建立 SIMD kernel 框架，逐热点替换。
8. 做 decoder row pipeline 和 token partition 并行。
9. 实现 key-frame intra encoder。
10. 实现 inter encoder、motion search、rate control。
11. 完成 SIMD encoder 热点。
12. 加强 fuzz、benchmark、CI、release 工具。

## 14. 风险与应对

| 风险 | 影响 | 应对 |
|---|---|---|
| Boolean coder 1 bit 偏差 | 整帧失真或后续 parse 全错 | 独立 roundtrip、partition offset golden、逐 bit trace |
| Loop filter 细节偏差 | MD5 不一致，画面边缘异常 | 从标量 reference 开始，逐边 golden，延后 SIMD |
| Sub-pixel filter shuffle 难表达 | inter decoder/encoder 性能不足 | 接口隔离；先 scalar，再 `@vector` tile，必要时可选 `@asm` |
| SIMD 溢出语义不一致 | 只在高亮/强边缘出错 | 所有中间类型显式，随机极值对照 |
| UYA SIMD lowering 能力不足 | 性能收益低 | 记录编译器增强需求：widen/narrow/shuffle/saturating ops |
| Encoder RD 复杂度高 | 质量落后 | 分层 preset：fast first，RD 后补 |
| WebM 解析牵扯过大 | 拖慢 codec 核心 | IVF 优先，WebM subset 后置 |

## 15. 参考

- VP8 bitstream 规范：[RFC 6386, VP8 Data Format and Decoding Guide](https://datatracker.ietf.org/doc/html/rfc6386)。
- 行为对照：[WebM Project libvpx](https://chromium.googlesource.com/webm/libvpx/)。
- UYA SIMD 能力：`../uya/docs/uya_ai_prompt.md`、`../uya/docs/compiler_status.md`、`../uya/tests/test_simd_*.uya`。
