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
- [ ] 实现 inter copy predictor。
- [ ] 实现 luma sub-pixel filter。
- [ ] 实现 chroma sub-pixel filter。
- [ ] 实现 border extension。
- [ ] 实现 simple loop filter。
- [ ] 实现 normal loop filter。

验收标准：

- [ ] 每个 transform 有 deterministic golden。
- [ ] 每个 predictor 有边界 golden。
- [ ] loop filter 单边测试覆盖 hev、limit、blimit。
- [ ] scalar kernels 无 heap allocation。

## Phase 7: Scalar Decoder 完整闭环

- [ ] 将 header/mode/token/kernel 串成 `Decoder.decode_frame`。
- [ ] 实现单线程 token decode -> dequant/transform -> reconstruct 融合路径。
- [ ] 实现 key frame decode。
- [ ] 实现 inter frame decode。
- [ ] 实现 current frame reconstruction。
- [ ] 实现 row-delayed loop filter。
- [ ] 实现 reference refresh。
- [ ] 实现 show_frame output。
- [ ] 实现 visible crop。
- [ ] 实现 `decode <input.ivf> --yuv out.yuv`。
- [ ] 实现 `info <input.ivf>`。
- [ ] 实现 `decode-frame --index N`。

验收标准：

- [ ] 至少 5 个 tiny IVF 样本输出 YUV MD5 与 golden 一致。
- [ ] 至少 1 个 inter sample 能完整 decode。
- [ ] 强制 scalar 路径可通过全部 decoder 测试。

## Phase 8: Conformance 与差分测试

- [ ] 建立 `fixtures/manifest.json`，记录样本来源、帧数、MD5。
- [ ] 增加 libvpx/vpxdec 可选差分脚本。
- [ ] 对 key frame 样本做 YUV MD5 对照。
- [ ] 对 inter frame 样本做 YUV MD5 对照。
- [ ] 对尺寸非 16 对齐样本做对照。
- [ ] 对 segmentation 样本做对照。
- [ ] 对多 token partition 样本做对照。
- [ ] 增加 malformed IVF corpus。
- [ ] 增加 malformed VP8 payload corpus。
- [ ] 增加 fuzz smoke target。

验收标准：

- [ ] `make test` 不需要外部 libvpx 即可通过内置 golden。
- [ ] `make test-vpxdiff` 在安装 libvpx 时通过。
- [ ] malformed corpus 不崩溃、不越界。

## Phase 9: SIMD 框架

- [ ] 定义 `SimdLevel`。
- [ ] 实现 CPU/构建能力检测。
- [ ] 实现 kernel function table。
- [ ] 实现 `--force-scalar`。
- [ ] 实现 `--force-simd`。
- [ ] 实现 scalar-vs-simd test harness。
- [ ] 实现 benchmark harness。
- [ ] 实现 vector load/store helper。
- [ ] 增加 SIMD kernel 生成 C/汇编检查记录。
- [ ] 为 kernel benchmark 定义默认启用阈值。
- [ ] 验证 UYA `@vector(u8,16/32/64)`、`@vector(i16,8/16)`、`@vector(i32,4/8)` 编译能力。
- [ ] 记录 UYA SIMD 缺口：widen、narrow、shuffle、saturating add/sub。

验收标准：

- [ ] 任意 kernel 可在运行时切换 scalar/SIMD。
- [ ] SIMD 不可用时自动回退 scalar。
- [ ] benchmark 能分别输出 scalar 和 SIMD 指标。
- [ ] 未通过生成代码检查或 benchmark 阈值的 kernel 不进入默认 dispatcher。

## Phase 10: SIMD Decoder Kernels

- [ ] SIMD plane copy/fill。
- [ ] SIMD border extension。
- [ ] SIMD residual add/clamp。
- [ ] SIMD DC-only inverse transform。
- [ ] SIMD 4x4 inverse DCT batch。
- [ ] SIMD intra 16x16 predictors。
- [ ] SIMD intra 4x4 高频 predictors。
- [ ] SIMD UV predictors。
- [ ] SIMD inter copy 16x16/8x8/4x4。
- [ ] SIMD sub-pixel horizontal filter。
- [ ] SIMD sub-pixel vertical filter。
- [ ] SIMD simple loop filter。
- [ ] SIMD normal loop filter。
- [ ] 可选 `@asm` x86 sub-pixel microkernel。
- [ ] 可选 `@asm` ARM NEON sub-pixel microkernel。

验收标准：

- [ ] 每个 SIMD kernel 与 scalar bit-exact。
- [ ] decoder scalar-vs-simd 输出 YUV MD5 一致。
- [ ] 720p decoder SIMD 相比 scalar 有稳定收益，且端到端不慢于 scalar 超过 5%。
- [ ] 每个默认启用的 SIMD kernel 都有生成 C/汇编检查记录。

## Phase 11: Decoder 并行与性能

- [ ] 实现 token partition 并行 decode。
- [ ] 实现 row reconstruct pipeline。
- [ ] 实现 row-delayed loopfilter pipeline。
- [ ] 实现 thread-local scratch。
- [ ] 实现有界 `MbCoeffScratchRing`，ring depth 与 row fence 绑定。
- [ ] 实现 deterministic error merge。
- [ ] 实现 per-frame performance stats。
- [ ] 优化 frame buffer reuse。
- [ ] 优化 reference frame border extension。
- [ ] 优化 coefficient scratch layout。

验收标准：

- [ ] 单线程和多线程 YUV MD5 一致。
- [ ] 多线程 malformed input 不死锁。
- [ ] 并行 coefficient scratch 峰值与 `ring_depth * mb_cols` 成正比，不随整帧无界增长。
- [ ] 1080p 样本性能报告包含 fps、cycles/pixel、线程数、bytes copied/frame、allocation count。

## Phase 12: Encoder MVP Keyframe

- [ ] 定义 `EncoderConfig`。
- [ ] 定义 `YuvFrameView`。
- [ ] 实现 IVF writer 集成。
- [ ] 实现 key frame header writer。
- [ ] 实现 intra 16x16 mode search。
- [ ] 实现 UV mode search。
- [ ] 实现 forward DCT。
- [ ] 实现 forward WHT。
- [ ] 实现 quantize。
- [ ] 实现 coefficient tokenize。
- [ ] 实现 bool writer partition output。
- [ ] 实现本地 reconstruct。
- [ ] 实现 key frame loop filter。
- [ ] 实现 `encode <input.yuv> --width --height --out out.ivf`。

验收标准：

- [ ] UYA decoder 能 decode 自己编码的 keyframe IVF。
- [ ] vpxdec 能 decode UYA encoder 输出。
- [ ] 固定输入输出 deterministic。

## Phase 13: Inter Encoder

- [ ] 实现 reference frame pool for encoder。
- [ ] 实现 last frame inter prediction。
- [ ] 实现 integer-pel motion search。
- [ ] 实现 half/quarter-pel refinement。
- [ ] 实现 MV cost。
- [ ] 实现 inter/intra mode decision。
- [ ] 实现 skip decision。
- [ ] 实现 golden frame refresh policy。
- [ ] 实现 altref frame refresh policy。
- [ ] 实现 segmentation basic policy。
- [ ] 实现 token partition packing。
- [ ] 实现 inter frame reconstruction。

验收标准：

- [ ] 至少 30 帧 YUV 序列可编码并被 vpxdec 解码。
- [ ] UYA decoder 解码 encoder 输出无错误。
- [ ] 相同配置输出 deterministic。

## Phase 14: Rate Control 与质量

- [ ] CQP 模式。
- [ ] 简单 VBR 模式。
- [ ] CBR buffer model。
- [ ] keyframe interval 控制。
- [ ] quantizer delta 调整。
- [ ] loop filter level 自动选择。
- [ ] RD cost model。
- [ ] 4x4 intra RD refine。
- [ ] inter mode RD refine。
- [ ] token probability stats。
- [ ] probability update decision。
- [ ] 输出 PSNR。
- [ ] 输出 SSIM 或预留 hook。

验收标准：

- [ ] 目标 bitrate 下误差在设定范围内。
- [ ] PSNR/bitrate 报告可复现。
- [ ] speed preset 对速度和质量有可测差异。

## Phase 15: SIMD Encoder Kernels

- [ ] SIMD SAD 16x16。
- [ ] SIMD SAD 8x8。
- [ ] SIMD SAD 4x4。
- [ ] SIMD SSE/variance。
- [ ] SIMD SATD/Hadamard cost。
- [ ] SIMD forward DCT。
- [ ] SIMD forward WHT。
- [ ] SIMD quantize/dequantize。
- [ ] SIMD token scan helper。
- [ ] SIMD sub-pixel predictor for motion search。
- [ ] SIMD intra predictor cost。
- [ ] Encoder benchmark 标量/SIMD 对照。

验收标准：

- [ ] motion search 热点有明显 SIMD 收益。
- [ ] SIMD encoder 输出与 scalar encoder 在同配置下 bitstream 一致，或文档明确哪些 RD tie-break 会导致合法差异。
- [ ] 如果 bitstream 不一致，decoded YUV 和质量指标必须在阈值内。

## Phase 16: WebM/RTP 与库 API

- [ ] 实现 minimal WebM VP8 demux。
- [ ] 实现 WebM track/timecode 解析。
- [ ] 实现 WebM sample 到 VP8 payload。
- [ ] 实现 RTP VP8 payload descriptor parser。
- [ ] 实现 RTP packet reassembly。
- [ ] 实现 decoder library API。
- [ ] 实现 encoder library API。
- [ ] 增加 C ABI 是否需要的设计讨论；默认不实现。
- [ ] 增加 examples。

验收标准：

- [ ] WebM subset 样本可 decode。
- [ ] RTP packet loss/malformed 有明确错误。
- [ ] API examples 可构建运行。

## Phase 17: 发布硬化

- [ ] 完整错误码文档。
- [ ] CLI 文档。
- [ ] Kernel benchmark 报告。
- [ ] Decoder conformance 报告。
- [ ] Encoder quality 报告。
- [ ] Fuzz corpus 最小化。
- [ ] CI: build/test/bench smoke。
- [ ] CI: scalar-only。
- [ ] CI: SIMD enabled。
- [ ] CI: optional libvpx diff。
- [ ] 版本号和 changelog。

验收标准：

- [ ] `make check` 通过。
- [ ] `make bench-smoke` 通过。
- [ ] release notes 明确支持范围和限制。

## SIMD 专项 Backlog

- [ ] 设计 `load_u8x16_unaligned`。
- [ ] 设计 `store_u8x16_unaligned`。
- [ ] 设计 `widen_u8x16_to_i16x8_pair`。
- [ ] 设计 `narrow_i16x16_to_u8x16_sat`。
- [ ] 设计 `absdiff_u8x16`。
- [ ] 设计 `sad_u8x16`。
- [ ] 设计 `transpose_4x4_i16`。
- [ ] 设计 `filter6_u8x16`。
- [ ] 设计 `loopfilter_edge_u8x16`。
- [ ] 建立 SIMD 生成 C/汇编检查模板。
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
