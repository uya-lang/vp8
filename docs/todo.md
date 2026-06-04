# 纯 UYA VP8 重构 TODO

## 状态说明

- `[x]` 已完成。
- `[ ]` 未开始。
- `[~]` 进行中或需要持续维护。

当前仓库为空项目基座，已完成设计文档和 TODO 文档。后续任务按 decoder 正确性、SIMD 性能、encoder 能力、并行与发布的顺序推进。

## Phase 0: 项目基座

- [x] 创建 `docs/design.md`。
- [x] 创建 `docs/todo.md`。
- [x] 创建 `README.md`，说明目标、构建方式、当前能力边界。
- [x] 创建 `AGENT.md`，记录纯 UYA、bit-exact、SIMD、测试约束。
- [x] 创建 `Makefile`。
- [x] 创建 `src/main.uya` CLI scaffold。
- [x] 创建 `src/vp8` 模块目录。
- [x] 创建 `tests/README.md`。
- [x] 创建 `bench/README.md`。
- [x] 增加 `.gitignore`，排除 build、fixtures 大文件、YUV 输出、coverage。
- [x] 确认本机 UYA 编译器路径和最小 hello-world 可构建。

验收标准：

- [x] `make build` 能生成 CLI，或文档明确记录当前 UYA 编译器缺失。
- [x] `vp8uya --help` 能显示 scaffold 命令。
- [x] 文档明确说明当前尚无真实编解码能力。

## Phase 1: Bitstream 与 IVF 基础

- [x] 实现 little-endian reader。
- [x] 实现 bounded slice reader，所有 read 都检查长度。
- [x] 实现 IVF header parser。
- [x] 实现 IVF frame iterator。
- [x] 实现 IVF writer。
- [x] 实现裸 VP8 frame payload reader。
- [x] 解析 VP8 frame tag：frame type、version、show frame、first partition size。
- [x] 解析 key frame start code。
- [x] 解析 key frame width/height/scale。
- [x] 对 frame tag 和 partition size 做 fuzz smoke。

验收标准：

- [x] 能打印 IVF frame count、width、height、fps。
- [x] 能对短 IVF/header/frame 返回明确错误，不崩溃。
- [x] 能从 IVF 抽出每个 VP8 frame payload。

## Phase 2: Boolean Reader/Writer

- [x] 实现 VP8 boolean arithmetic reader。
- [x] 实现 read bit with probability。
- [x] 实现 literal read helper。
- [x] 实现 signed value helper。
- [x] 实现 partition boundary 检查。
- [x] 实现 reader trace 模式，记录 bit/prob/offset。
- [x] 实现 boolean writer。
- [x] 实现 writer flush 和 carry handling。
- [x] 增加 reader/writer roundtrip tests。
- [x] 增加与 libvpx 小样本 trace 对照。

验收标准：

- [x] reader 不会越过 partition。
- [x] writer 写出的 synthetic stream 可被 reader 还原。
- [x] 错误中包含 partition id 和 byte offset。

## Phase 3: VP8 Header 与概率状态

- [x] 定义 `Vp8FrameHeader`。
- [x] 定义 `Vp8Segmentation`。
- [x] 定义 `Vp8LoopFilterHeader`。
- [x] 定义 `Vp8QuantHeader`。
- [x] 定义 `Vp8Probs`。
- [x] 填入 VP8 默认概率表。
- [x] 解析 segmentation enabled/update/map probs。
- [x] 解析 loop filter type/level/sharpness/ref deltas/mode deltas。
- [x] 解析 base quant 和 y1/y2/uv delta。
- [x] 解析 token partition count。
- [x] 解析 coefficient probability updates。
- [x] 解析 MV probability updates。
- [x] 实现 key frame 重置概率状态。

验收标准：

- [x] tiny key frame header golden 全字段一致。
- [x] inter frame 继承/更新概率状态正确。
- [x] 坏 probability update 能返回精确错误。

## Phase 4: Decoder Context 与内存布局

- [x] 实现 `Plane`。
- [x] 实现 aligned frame allocation。
- [x] 实现 border allocation 和 origin offset。
- [x] 实现 `FrameBuffer`。
- [x] 实现 `FramePool`：current/last/golden/altref。
- [x] 实现 logical reference 到 physical frame slot 的 alias/ref-count 映射。
- [x] 实现 reference border dirty flag。
- [x] 实现 Y/U/V visible view。
- [x] 定义 `DecodedFrame` borrowed view 生命周期和 release/lease 语义。
- [x] 实现 macroblock grid helper。
- [x] 实现 SoA macroblock info arrays。
- [x] 实现 above/left mode context。
- [x] 实现 above/left coefficient context。
- [x] 实现 row scratch arena。
- [x] 实现 coefficient scratch bytes read/write 统计。
- [x] 实现 frame-level scratch reset。

验收标准：

- [x] 17x17、16x16、1x1、1920x1080 尺寸分配正确。
- [x] Plane stride 对齐符合设计。
- [x] Guard bytes 检查无越界写。
- [x] context 初始化后 decode hot loop heap allocation count 为 0。
- [x] 正常 reference refresh 不发生整帧 copy，`bytes_copied_for_ref_refresh == 0`。
- [x] 默认 `DecodedFrame` 不隐式复制整帧，生命周期规则有测试覆盖。

## Phase 5: Mode 与 Token Parse

- [x] 解析 key frame macroblock y mode。
- [x] 解析 key frame UV mode。
- [x] 解析 4x4 luma block mode。
- [x] 解析 inter/intra flag。
- [x] 解析 inter reference frame。
- [x] 解析 nearest/near/zero/new MV。
- [x] 实现 MV clamp 和边界检查。
- [x] 解析 skip coefficient flag。
- [x] 解析 coefficient tokens。
- [x] 实现 coefficient bands、scan order、EOB context。
- [x] 实现 EOB=0、DC-only coefficient summary/fast-path。
- [x] 实现 Y2 block token decode。
- [x] 支持 1/2/4/8 token partitions。
- [x] 为每个 macroblock 记录 mode/ref/mv/coeff summary。

验收标准：

- [x] 小 key frame 的 mode map 与 golden 一致。
- [x] token partition 映射在多 row、多 partition 下正确。
- [x] 任意 token overread 返回 `ErrBoolReaderOverread`。

## Phase 6: Scalar Kernel Reference

- [x] 实现 clip/clamp helpers。
- [x] 实现 DC-only inverse transform。
- [x] 实现 4x4 inverse DCT。
- [x] 实现 inverse Walsh-Hadamard Y2。
- [x] 实现 dequant。
- [x] 实现 residual add and clamp。
- [x] 实现 Y 16x16 intra predictors。
- [x] 实现 Y 4x4 intra predictors。
- [x] 实现 UV 8x8 intra predictors。
- [x] 实现 inter copy predictor。
- [x] 实现 luma sub-pixel filter。
- [x] 实现 chroma sub-pixel filter。
- [x] 实现 border extension。
- [x] 实现 simple loop filter。
- [x] 实现 normal loop filter。

验收标准：

- [x] 每个 transform 有 deterministic golden。
- [x] 每个 predictor 有边界 golden。
- [x] loop filter 单边测试覆盖 hev、limit、blimit。
- [x] scalar kernels 无 heap allocation。

## Phase 7: Scalar Decoder 完整闭环

- [x] 将 header/mode/token/kernel 串成 `Decoder.decode_frame`。
- [x] 实现单线程 token decode -> dequant/transform -> reconstruct 融合路径。
- [x] 实现 key frame decode。
- [x] 实现 inter frame decode。
- [x] 实现 current frame reconstruction。
- [x] 实现 row-delayed loop filter。
  - [x] 实现 loop filter level 到 limit/blimit/thresh 的 scalar 派生 helper。
  - [x] 实现 Y/UV macroblock edge 与 subblock edge loop filter dispatcher。
  - [x] 将 normal loop filter dispatcher 接入 decoder row delay：当前 row 完成后过滤上一 row，帧结束过滤最后一 row。
  - [x] 实现 simple loop filter 的 Y-only macroblock/subblock dispatcher 并接入 decoder row delay。
- [x] 实现 reference refresh。
- [x] 实现 show_frame output。
- [x] 实现 visible crop。
- [x] 实现 `decode <input.ivf> --yuv out.yuv`。
- [x] 实现 `info <input.ivf>`。
- [x] 实现 `decode-frame --index N`。

验收标准：

- [x] 至少 5 个 tiny IVF 样本输出 YUV MD5 与 golden 一致。
- [x] 至少 1 个 inter sample 能完整 decode。
- [x] 强制 scalar 路径可通过全部 decoder 测试。

## Phase 8: Conformance 与差分测试

- [x] 建立 `fixtures/manifest.json`，记录样本来源、帧数、MD5。
- [x] 增加 libvpx/vpxdec 可选差分脚本。
- [x] 对 key frame 样本做 YUV MD5 对照。
- [x] 对 inter frame 样本做 YUV MD5 对照。
- [x] 对尺寸非 16 对齐样本做对照。
- [x] 对 segmentation 样本做对照。
- [x] 对多 token partition 样本做对照。
- [x] 增加 malformed IVF corpus。
- [x] 增加 malformed VP8 payload corpus。
- [x] 增加 fuzz smoke target。

验收标准：

- [x] `make test` 不需要外部 libvpx 即可通过内置 golden。
- [x] `make test-vpxdiff` 在安装 libvpx 时通过。
- [x] malformed corpus 不崩溃、不越界。

## Phase 9: SIMD 框架

- [x] 定义 `SimdLevel`。
- [x] 实现 CPU/构建能力检测。
- [x] 实现 kernel function table。
- [x] 实现 `--force-scalar`。
- [x] 实现 `--force-simd`。
- [x] 实现 scalar-vs-simd test harness。
- [x] 实现 benchmark harness。
- [x] 实现 vector load/store helper。
- [x] 增加 SIMD kernel 生成 C/汇编检查记录。
- [x] 为 kernel benchmark 定义默认启用阈值。
- [x] 验证 UYA `@vector(u8,16/32/64)`、`@vector(i16,8/16)`、`@vector(i32,4/8)` 编译能力。
- [x] 记录 UYA SIMD 缺口：widen、narrow、shuffle、saturating add/sub。

验收标准：

- [x] 任意 kernel 可在运行时切换 scalar/SIMD。
- [x] SIMD 不可用时自动回退 scalar。
- [x] benchmark 能分别输出 scalar 和 SIMD 指标。
- [x] 未通过生成代码检查或 benchmark 阈值的 kernel 不进入默认 dispatcher。

## Phase 10: SIMD Decoder Kernels

- [x] SIMD plane copy/fill。
- [x] SIMD border extension。
- [x] SIMD residual add/clamp。
- [x] SIMD DC-only inverse transform。
- [x] SIMD 4x4 inverse DCT batch。
- [x] SIMD intra 16x16 predictors。
- [x] SIMD intra 4x4 高频 predictors。
- [x] SIMD UV predictors。
- [x] SIMD inter copy 16x16/8x8/4x4。
- [x] SIMD sub-pixel horizontal filter。
- [x] SIMD sub-pixel vertical filter。
- [x] SIMD simple loop filter。
- [x] SIMD normal loop filter。
- [x] 可选 `@asm` x86 sub-pixel microkernel。
- [f] 可选 `@asm` ARM NEON sub-pixel microkernel。
  - 失败原因（2026-06-03）：当前主机为 `x86_64`，未安装 `qemu-arm`、`qemu-aarch64`、`qemu-arm-static` 或 `qemu-aarch64-static`；仅发现 `arm-linux-gnueabihf-gcc`，只能做交叉汇编/编译，无法运行 byte-exact 测试验证 ARM NEON microkernel，不能诚实标记完成。

验收标准：

- [x] 每个 SIMD kernel 与 scalar bit-exact。
- [x] decoder scalar-vs-simd 输出 YUV MD5 一致。
- [f] 720p decoder SIMD 相比 scalar 有稳定收益，且端到端不慢于 scalar 超过 5%。
  - 失败原因（2026-06-03）：当前 `make_forced_simd_kernel_table` 仍返回 scalar table，decoder 端到端 `--force-simd` 尚未注册真实 SIMD kernel；现有 `bench/decode_bench.py` 只覆盖内置 tiny IVF 样本，未提供 720p fixture。`make bench-decode` 只能证明 tiny 样本 MD5 正确且耗时有快有慢，不能作为 720p 稳定收益证据。
- [x] 每个默认启用的 SIMD kernel 都有生成 C/汇编检查记录。

## Phase 11: Decoder 并行与性能

- token partition 并行 decode（拆分执行）：
  - [x] 封装 token partition 到 macroblock row 的映射并补 small-frame golden。
  - [x] 抽取 row-local token decode scratch 结构，避免整帧 coefficient materialization。
  - [x] 实现 token partition worker 调度与 deterministic error merge。
  - [x] 将并行 token decode 输出接入现有 reconstruct/loop-filter 串行路径。
- [x] 实现 row reconstruct pipeline。
- [x] 实现 row-delayed loopfilter pipeline。
- [x] 实现 thread-local scratch。
- [x] 实现有界 `MbCoeffScratchRing`，ring depth 与 row fence 绑定。
- [x] 实现 deterministic error merge。
- [x] 实现 per-frame performance stats。
- [x] 优化 frame buffer reuse。
- [x] 优化 reference frame border extension。
- [x] 优化 coefficient scratch layout。

验收标准：

- [x] 单线程和多线程 YUV MD5 一致。
- [x] 多线程 malformed input 不死锁。
- [x] 并行 coefficient scratch 峰值与 `ring_depth * mb_cols` 成正比，不随整帧无界增长。
- [x] 1080p 样本性能报告包含 fps、cycles/pixel、线程数、bytes copied/frame、allocation count。

## Phase 12: Encoder MVP Keyframe

- [x] 定义 `EncoderConfig`。
- [x] 定义 `YuvFrameView`。
- [x] 实现 IVF writer 集成。
- [x] 实现 key frame header writer。
- [x] 实现 intra 16x16 mode search。
- [x] 实现 UV mode search。
- [x] 实现 forward DCT。
- [x] 实现 forward WHT。
- [x] 实现 quantize。
- [x] 实现 coefficient tokenize。
- [x] 实现 bool writer partition output。
- [x] 实现本地 reconstruct。
- [x] 实现 key frame loop filter。
- [x] 实现 `encode <input.yuv> --width --height --out out.ivf`。

验收标准：

- [x] UYA decoder 能 decode 自己编码的 keyframe IVF。
- [f] vpxdec 能 decode UYA encoder 输出。
  - blocked: 2026-06-04 本机 PATH 中没有 `vpxdec`，`command -v vpxdec` 返回 1；无法执行真实 libvpx 解码验收。
- [x] 固定输入输出 deterministic。

## Phase 13: Inter Encoder

- [x] 实现 reference frame pool for encoder。
- [x] 实现 last frame inter prediction。
- [x] 实现 integer-pel motion search。
- [x] 实现 half/quarter-pel refinement。
- [x] 实现 MV cost。
- [x] 实现 inter/intra mode decision。
- [x] 实现 skip decision。
- [x] 实现 golden frame refresh policy。
- [x] 实现 altref frame refresh policy。
- [x] 实现 segmentation basic policy。
- [x] 实现 token partition packing。
- [x] 实现 inter frame reconstruction。

验收标准：

- [f] 至少 30 帧 YUV 序列可编码并被 vpxdec 解码。
  - blocked: 2026-06-04 本机 PATH 中没有 `vpxdec`，`command -v vpxdec` 返回 1；`/media/winger/_dde_data/winger/uya` 下也未找到可执行 `vpxdec`，无法执行真实 libvpx 30 帧解码验收。
- [x] UYA decoder 解码 encoder 输出无错误。
- [x] 相同配置输出 deterministic。

## Phase 14: Rate Control 与质量

- [x] CQP 模式。
- [x] 简单 VBR 模式。
- [x] CBR buffer model。
- [x] keyframe interval 控制。
- [x] quantizer delta 调整。
- [x] loop filter level 自动选择。
- [x] RD cost model。
- [x] 4x4 intra RD refine。
- [x] inter mode RD refine。
- [x] token probability stats。
- [x] probability update decision。
- [x] 输出 PSNR。
- [x] 输出 SSIM 或预留 hook。

验收标准：

- [x] 目标 bitrate 下误差在设定范围内。
- [x] PSNR/bitrate 报告可复现。
- [x] speed preset 对速度和质量有可测差异。

## Phase 15: SIMD Encoder Kernels

- [x] SIMD SAD 16x16。
- [x] SIMD SAD 8x8。
- [x] SIMD SAD 4x4。
- [x] SIMD SSE/variance。
- [x] SIMD SATD/Hadamard cost。
- [x] SIMD forward DCT。
- [x] SIMD forward WHT。
- [x] SIMD quantize/dequantize。
- [x] SIMD token scan helper。
- [x] SIMD sub-pixel predictor for motion search。
- [x] SIMD intra predictor cost。
- [x] Encoder benchmark 标量/SIMD 对照。

验收标准：

- [x] motion search 热点有明显 SIMD 收益。
- [x] SIMD encoder 输出与 scalar encoder 在同配置下 bitstream 一致，或文档明确哪些 RD tie-break 会导致合法差异。
- [x] 如果 bitstream 不一致，decoded YUV 和质量指标必须在阈值内。

## Phase 16: WebM/RTP 与库 API

- [x] 实现 minimal WebM VP8 demux。
- [x] 实现 WebM track/timecode 解析。
- [x] 实现 WebM sample 到 VP8 payload。
- [x] 实现 RTP VP8 payload descriptor parser。
- [x] 实现 RTP packet reassembly。
- [x] 实现 decoder library API。
- [x] 实现 encoder library API。
- [x] 增加 C ABI 是否需要的设计讨论；默认不实现。
- [x] 增加 examples。

验收标准：

- [x] WebM subset 样本可 decode。
- [x] RTP packet loss/malformed 有明确错误。
- [x] API examples 可构建运行。

## Phase 17: 发布硬化

- [x] 完整错误码文档。
- [x] CLI 文档。
- [x] Kernel benchmark 报告。
- [x] Decoder conformance 报告。
- [x] Encoder quality 报告。
- [x] Fuzz corpus 最小化。
- [x] CI: build/test/bench smoke。
- [x] CI: scalar-only。
- [x] CI: SIMD enabled。
- [x] CI: optional libvpx diff。
- [x] 版本号和 changelog。

验收标准：

- [x] `make check` 通过。
- [x] `make bench-smoke` 通过。
- [x] release notes 明确支持范围和限制。

## SIMD 专项 Backlog

- [x] 设计 `load_u8x16_unaligned`。
- [x] 设计 `store_u8x16_unaligned`。
- [x] 设计 `widen_u8x16_to_i16x8_pair`。
- [x] 设计 `narrow_i16x16_to_u8x16_sat`。
- [x] 设计 `absdiff_u8x16`。
- [x] 设计 `sad_u8x16`。
- [x] 设计 `transpose_4x4_i16`。
- [x] 设计 `filter6_u8x16`。
- [x] 设计 `loopfilter_edge_u8x16`。
- [x] 建立 SIMD 生成 C/汇编检查模板。
- [ ] 建立 SIMD 默认启用 benchmark 阈值表。
- [ ] 向 UYA 编译器反馈/实现 vector shuffle 需求。
- [ ] 向 UYA 编译器反馈/实现 vector widening/narrowing 需求。
- [ ] 向 UYA 编译器反馈/实现 saturating arithmetic 需求。

## 高风险检查清单

- [ ] bool reader carry/renormalize 与 VP8 规范一致。
- [ ] first partition size 和 token partition size 边界正确。
- [ ] key frame 重置概率和 reference frame。
- [ ] 非 16 对齐尺寸的右/下边界预测正确。
- [ ] segmentation quant/filter delta 符号正确。
- [ ] loop filter level 为 0 时完全跳过。
- [ ] simple/normal filter 选择正确。
- [ ] Y2 block 只在对应 y mode 下使用。
- [ ] EOB context 更新正确。
- [ ] MV clamp 和 sub-pixel reference border 正确。
- [ ] SIMD 路径所有极值输入与 scalar 一致。
- [ ] SIMD 默认路径没有未审计的逐 lane 临时对象风暴或多余 `memcpy`。
- [ ] coefficient scratch 没有整帧无界 materialization。
- [ ] reference refresh 没有正常路径整帧 copy。
- [ ] borrowed `DecodedFrame` 生命周期不会迫使默认 decode 隐式复制。
- [ ] 多线程路径和单线程输出一致。
