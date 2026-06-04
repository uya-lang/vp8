# Encoder libvpx 追赶 TODO

Date: 2026-06-04

## 状态说明

- `[x]` 已完成。
- `[ ]` 未开始。
- `[~]` 进行中。
- `[f]` 失败或阻塞。

本轮范围：只生成本文档和 `docs/encoder_libvpx_parity_design.md`，不实现代码、不改 CLI、不新增脚本、不改 `Makefile`、不下载 `vpxenc`/`vpxdec`、不下载真实样本、不运行完整测试。后续实现必须另起目标。

本文档中除 Phase 0 的文档创建项外，所有任务都是未来任务，当前必须保持 `[ ]`。

## Phase 0: 文档创建

- [x] 创建 `docs/encoder_libvpx_parity_design.md`。
  - 验收：文件存在，写清“不追 MD5，追 libvpx `--best` 的质量/码率/速度”。
- [x] 创建 `docs/encoder_libvpx_parity_todo.md`。
  - 验收：文件存在，未来实现任务均保持 `[ ]`。

## Phase 1: 指标契约

- [x] 固化对标对象为 libvpx `vpxenc --best`。
  - 验收：设计文档和未来报告模板都出现 `vpxenc --best`。
- [x] 固化码率指标名。
  - 验收产物：未来 `summary.json` 包含 `vp8uya_bits_per_pixel` 和 `libvpx_bits_per_pixel`。
- [x] 固化码率硬阈值。
  - 验收：当 `vp8uya_bits_per_pixel > libvpx_bits_per_pixel * 1.10` 时，未来门禁返回非 0。
- [x] 固化质量指标名。
  - 验收产物：未来 `summary.json` 包含 `vp8uya_psnr_all_db` 和 `libvpx_psnr_all_db`。
- [x] 固化 `PSNR-all` 硬阈值。
  - 验收：当 `vp8uya_psnr_all_db < libvpx_psnr_all_db - 0.50` 时，未来门禁返回非 0。
- [x] 固化速度指标名。
  - 验收产物：未来 `summary.json` 包含 `vp8uya_fps` 和 `libvpx_fps`。
- [x] 固化 fps 硬阈值。
  - 验收：当 `vp8uya_fps < libvpx_fps * 0.80` 时，未来门禁返回非 0。
- [x] 明确 `SSIM-all` 第一版只记录不设硬门禁。
  - 验收产物：未来报告包含 `SSIM-all`，但 SSIM 不影响 hard threshold pass/fail。
- [x] 定义失败原因字段。
  - 验收产物：未来 `results.ndjson` 中失败样本包含非空 `failure_reasons`。

## Phase 2: libvpx 工具链获取

- [x] 新增 `vpxenc` 查找 helper。
  - 验收命令：`VPXENC=/tmp/fake-vpxenc python3 bench/libvpx_encode_compare.py --probe-tools` 优先报告该路径。
- [x] 新增 `vpxdec` 查找 helper。
  - 验收命令：`VPXDEC=/tmp/fake-vpxdec python3 bench/libvpx_encode_compare.py --probe-tools` 优先报告该路径。
- [x] 支持从 `PATH` 查找工具。
  - 验收命令：`python3 bench/libvpx_encode_compare.py --probe-tools` 能打印 PATH 中发现的 `vpxenc` 和 `vpxdec`。
- [x] 支持从 `build/deps/vpx-tools-root/usr/bin/` 查找工具。
  - 验收：把可执行 `vpxenc`、`vpxdec` 放入该目录后，不设置环境变量也能发现。
- [x] 实现无 sudo 下载 `vpx-tools`。
  - 验收命令：`python3 bench/libvpx_encode_compare.py --fetch-vpx-tools` 在 `build/deps/` 下生成 `.deb`。
- [x] 实现解包 `vpx-tools`。
  - 验收命令：`python3 bench/libvpx_encode_compare.py --extract-vpx-tools` 生成 `build/deps/vpx-tools-root/usr/bin/vpxenc`。
- [x] 校验 `vpxenc` 可执行。
  - 验收命令：`python3 bench/libvpx_encode_compare.py --probe-tools` 返回 0，并记录 `vpxenc_probe_returncode`。
- [x] 校验 `vpxdec` 可执行。
  - 验收命令：`python3 bench/libvpx_encode_compare.py --probe-tools` 返回 0，并记录 `vpxdec_probe_returncode`。
- [x] 记录工具版本。
  - 验收产物：未来 `summary.json` 包含 `vpxenc_version` 和 `vpxdec_version`。
- [x] 工具缺失时输出明确修复建议。
  - 验收：无工具时脚本返回非 0，stderr 包含 `VPXENC`、`VPXDEC`、`--fetch-vpx-tools`。

## Phase 3: Xiph Derf 真实样本

- [x] 新增真实样本 manifest。
  - 产物：`fixtures/encoder_libvpx_real_samples.json`。
- [x] 在 manifest 中添加 `akiyo_qcif`。
  - 验收：记录 URL、width、height、frames、fps、sha256、groups，groups 包含 `low-motion`。
- [x] 在 manifest 中添加 `foreman_qcif`。
  - 验收：记录 URL、width、height、frames、fps、sha256、groups，groups 包含 `motion`。
- [x] 在 manifest 中添加 `coastguard_qcif`。
  - 验收：记录 URL、width、height、frames、fps、sha256、groups，groups 包含 `pan`。
- [x] 在 manifest 中添加 `mobile_cif`。
  - 验收：记录 URL、width、height、frames、fps、sha256、groups，groups 包含 `texture`。
- [x] 实现样本下载缓存目录。
  - 产物：`build/real-y4m/`，且该目录不进入 git。
- [ ] 实现 Y4M 原子下载。
  - 验收：下载完成前只存在临时文件，失败时不留下可被复用的半截 `.y4m`。
- [ ] 实现 sha256 校验。
  - 验收：sha256 不匹配时脚本返回非 0，并拒绝生成 I420 fixture。
- [ ] 实现缓存复用。
  - 验收：第二次运行同一 sha256 样本不重新下载。
- [ ] 实现 Y4M 到 I420 转换。
  - 验收命令：`ffmpeg -y -i <sample>.y4m -frames:v 60 -pix_fmt yuv420p -f rawvideo <sample>.i420` 生成 raw I420。
- [ ] 校验 I420 文件大小。
  - 验收：`stat -c %s <sample>.i420` 等于 `frame_size * frames`。
- [ ] 确认真实媒体文件不入库。
  - 验收命令：`git status --short` 不显示 `.y4m`、`.i420`、`.ivf` 真实样本文件。

## Phase 4: `encode --frames N --fps NUM/DEN`

- [ ] 为 `encode` 增加 `--frames N` 参数解析。
  - 验收命令：`build/vp8uya encode input.i420 --width 16 --height 16 --frames 1 --out out.ivf` 与不传 `--frames` 行为一致。
- [ ] 拒绝缺少值的 `--frames`。
  - 验收命令：`build/vp8uya encode input.i420 --width 16 --height 16 --frames --out out.ivf` 返回参数错误。
- [ ] 拒绝 `--frames 0`。
  - 验收命令：`build/vp8uya encode input.i420 --width 16 --height 16 --frames 0 --out out.ivf` 返回参数错误。
- [ ] 拒绝非数字 `--frames`。
  - 验收命令：`build/vp8uya encode input.i420 --width 16 --height 16 --frames abc --out out.ivf` 返回参数错误。
- [ ] 为 `encode` 增加 `--fps NUM/DEN` 参数解析。
  - 验收命令：`build/vp8uya encode input.i420 --width 16 --height 16 --fps 30/1 --out out.ivf` 写入 IVF timebase。
- [ ] 拒绝缺少值的 `--fps`。
  - 验收命令：`build/vp8uya encode input.i420 --width 16 --height 16 --fps --out out.ivf` 返回参数错误。
- [ ] 拒绝非法 `--fps`。
  - 验收命令：`--fps 0/1`、`--fps 30/0`、`--fps abc` 均返回参数错误。
- [ ] 实现多帧 I420 输入大小计算。
  - 验收：17x17 I420 使用 `17 * 17 + 2 * 9 * 9` 作为单帧大小。
- [ ] 拒绝输入不足。
  - 验收：输入小于 `frame_size * frames` 时返回明确错误。
- [ ] 拒绝输入多余。
  - 验收：输入大于 `frame_size * frames` 时返回明确错误。
- [ ] 输出多帧 IVF header。
  - 验收命令：`build/vp8uya info out.ivf` 显示 `ivf.frame_count=N`。
- [ ] 输出逐帧 IVF timestamp。
  - 验收：解析 IVF frame headers 时 timestamp 为 `0..N-1`。
- [ ] 复用公共 `Vp8Encoder` API。
  - 验收：CLI 不复制 reference pool、inter frame 状态机或 rate control 状态。
- [ ] 保持单帧 encode 行为兼容。
  - 验收命令：`make test` 中现有单帧 encode 用例通过。
- [ ] 更新 CLI 文档。
  - 产物：`docs/cli.md` 说明 `--frames` 和 `--fps`。
- [ ] 更新 error code 文档。
  - 产物：`docs/error_codes.md` 说明新增参数错误和输入长度错误。

## Phase 5: 多帧 encode 测试

- [ ] 增加 3 帧 16x16 I420 测试输入生成。
  - 验收：生成文件大小为 `384 * 3` 字节。
- [ ] 验证多帧 IVF frame count。
  - 验收命令：`build/vp8uya info out.ivf` 输出 `ivf.frame_count=3`。
- [ ] 验证本项目 decoder 可解多帧输出。
  - 验收命令：`build/vp8uya decode out.ivf --yuv out.i420` 输出大小为 `384 * 3` 字节。
- [ ] 验证 `vpxdec` 可解多帧输出。
  - 验收命令：`vpxdec --rawvideo -o out.vpxdec.i420 out.ivf` 输出大小为 `384 * 3` 字节。
- [ ] 验证 deterministic。
  - 验收命令：相同输入编码两次后 `md5sum first.ivf second.ivf` 相同。
- [ ] 增加非 16 对齐多帧测试。
  - 验收：17x17 三帧 encode/decode 输出大小正确。
- [ ] 增加 forced scalar 测试。
  - 验收命令：`VP8UYA_FORCE_SCALAR=1 build/vp8uya encode ... --frames 3 ...` 成功。
- [ ] 增加 forced SIMD 测试。
  - 验收命令：`VP8UYA_FORCE_SIMD=1 build/vp8uya encode ... --frames 3 ...` 成功或明确 fallback。

## Phase 6: libvpx 对标脚本

- [ ] 新增 `bench/libvpx_encode_compare.py`。
  - 验收命令：`python3 bench/libvpx_encode_compare.py --help`。
- [ ] 支持传入 `build/vp8uya` 路径。
  - 验收：二进制不存在时返回非 0，并打印传入路径。
- [ ] 支持 `--group` 样本过滤。
  - 验收命令：`python3 bench/libvpx_encode_compare.py --group qcif --dry-run` 只列出 QCIF 样本。
- [ ] 支持 `--frames` 覆盖。
  - 验收：`--frames 30` 时报告中 sample frame count 为 30。
- [ ] 支持 `--warmups`。
  - 验收：JSON 记录 warmup 次数。
- [ ] 支持 `--repeats`。
  - 验收：JSON 记录 repeat 次数和最终采用的统计值。
- [ ] 调用 `vp8uya encode --frames N --fps NUM/DEN`。
  - 验收产物：生成 `<sample>.vp8uya.ivf`。
- [ ] 调用 `vpxenc --best`。
  - 验收产物：生成 `<sample>.libvpx.ivf`。
- [ ] 调用 `vpxdec` 解码 UYA 输出。
  - 验收产物：生成 `<sample>.vp8uya.decoded.i420`。
- [ ] 调用 `vpxdec` 解码 libvpx 输出。
  - 验收产物：生成 `<sample>.libvpx.decoded.i420`。
- [ ] 记录完整复现命令。
  - 验收：Markdown 报告中每个失败样本包含 `vp8uya`、`vpxenc`、`vpxdec` 命令。

## Phase 7: 指标计算与报告

- [ ] 统计 IVF payload bits。
  - 验收产物：`results.ndjson` 包含 `vp8uya_payload_bits` 和 `libvpx_payload_bits`。
- [ ] 统计 bits per pixel。
  - 验收产物：`results.ndjson` 包含 `vp8uya_bits_per_pixel` 和 `libvpx_bits_per_pixel`。
- [ ] 统计 encoding elapsed ns。
  - 验收产物：`results.ndjson` 包含 `vp8uya_encode_elapsed_ns` 和 `libvpx_encode_elapsed_ns`。
- [ ] 统计 encoding fps。
  - 验收产物：`results.ndjson` 包含 `vp8uya_fps` 和 `libvpx_fps`。
- [ ] 计算 PSNR Y/U/V/all。
  - 验收产物：`results.ndjson` 包含 `psnr_y_db`、`psnr_u_db`、`psnr_v_db`、`psnr_all_db`。
- [ ] 计算 SSIM Y/U/V/all。
  - 验收产物：`results.ndjson` 包含 `ssim_y`、`ssim_u`、`ssim_v`、`ssim_all`。
- [ ] 输出 NDJSON 明细。
  - 产物：`build/libvpx-encode-compare/results.ndjson`。
- [ ] 输出 JSON 汇总。
  - 产物：`build/libvpx-encode-compare/summary.json`。
- [ ] 输出 Markdown 报告。
  - 产物：`docs/encoder_libvpx_compare_report.md`。

## Phase 8: 报告门禁

- [ ] 实现码率门禁。
  - 验收：`vp8uya_bits_per_pixel <= libvpx_bits_per_pixel * 1.10` 时码率项通过。
- [ ] 实现 `PSNR-all` 门禁。
  - 验收：`vp8uya_psnr_all_db >= libvpx_psnr_all_db - 0.50` 时质量项通过。
- [ ] 实现 fps 门禁。
  - 验收：`vp8uya_fps >= libvpx_fps * 0.80` 时速度项通过。
- [ ] 输出失败原因。
  - 验收：任一门禁失败时 `failure_reasons` 至少包含一个原因。
- [ ] 所有样本通过时返回 0。
  - 验收命令：`python3 bench/libvpx_encode_compare.py --threshold` 的 shell `$?` 为 0。
- [ ] 任一样本失败时返回非 0。
  - 验收命令：构造失败样本后 `python3 bench/libvpx_encode_compare.py --threshold` 的 shell `$?` 非 0。

## Phase 9: Makefile 与 CI 集成

- [ ] 新增 `fetch-vpx-tools` 目标。
  - 验收命令：`make fetch-vpx-tools`。
- [ ] 新增 `fetch-real-y4m` 目标。
  - 验收命令：`make fetch-real-y4m`。
- [ ] 新增 `bench-libvpx-encode` 目标。
  - 验收命令：`make bench-libvpx-encode`。
- [ ] 新增 `test-libvpx-encode-threshold` 目标。
  - 验收命令：`make test-libvpx-encode-threshold`。
- [ ] 确保普通 `make test` 不下载真实样本。
  - 验收命令：`make -n test` 不出现 `fetch-real-y4m`。
- [ ] 增加可选 CI job。
  - 验收：CI job 名称包含 `libvpx encode threshold`，且不会在普通 PR 强制下载大样本。

## Phase 10: 质量追赶优化

- [ ] 记录 key/inter/skip frame 或 macroblock 计数。
  - 验收产物：benchmark JSON 包含 mode distribution 字段。
- [ ] 接入 integer-pel motion search 到实际 encode path。
  - 验收：运动样本报告中 non-zero MV count 大于 0。
- [ ] 接入 sub-pel refinement。
  - 验收：报告中记录 half-pel 或 quarter-pel candidate count。
- [ ] 写出 per-MB MV。
  - 验收：含 non-zero MV 的输出可被本项目 decoder 和 `vpxdec` 解码。
- [ ] 接入 MV rate cost。
  - 验收：mode decision 分数包含 MV bit cost。
- [ ] 接入 inter/intra mode decision。
  - 验收：静态样本 inter 占优，复杂运动样本存在合理 intra refresh。
- [ ] 接入 skip decision。
  - 验收：`akiyo_qcif` 的 skip ratio 高于 `mobile_cif`。
- [ ] 调整 chroma distortion 权重。
  - 验收：PSNR-U/V 不出现明显退化，`PSNR-all` 达到硬阈值。

## Phase 11: 码率与 RD 优化

- [ ] 建立 Q ladder 对标。
  - 验收：Q=16/24/32/40/48 均输出 bpp、`PSNR-all`、fps。
- [ ] 拟合 lambda-Q 表。
  - 产物：lambda table 文档或 JSON。
- [ ] 替换简单 lambda 逻辑。
  - 验收：mode decision 使用新 lambda table。
- [ ] 增加 token bit estimate。
  - 验收：RD score 包含 token rate cost。
- [ ] 增加 mode bit estimate。
  - 验收：RD score 包含 mode rate cost。
- [ ] 调整 target bitrate 到 quantizer 映射。
  - 验收：同一样本 60 帧内 Q 不出现无意义振荡。
- [ ] 增加 keyframe boost。
  - 验收：首帧 PSNR 不显著拖低 `PSNR-all`。

## Phase 12: 性能优化

- [ ] 记录 encoder hot path allocation count。
  - 验收产物：benchmark JSON 包含 allocation count 或等价统计。
- [ ] 复用 frame buffers。
  - 验收：多帧编码不为每帧重新分配 reference pool。
- [ ] 复用 token buffers。
  - 验收：多帧编码 token buffer allocation 次数下降。
- [ ] 降低 mode search work units。
  - 验收：work units 下降且 `PSNR-all`、码率不越过硬阈值。
- [ ] 默认启用达标 SIMD SAD。
  - 验收：SIMD 与 scalar decoded YUV 一致，fps 提升。
- [ ] 默认启用达标 SIMD SSE/variance。
  - 验收：fps 提升，质量和码率门禁不退化。
- [ ] 默认启用达标 SIMD transform。
  - 验收：输出可解码且 fps 提升。
- [ ] 增加性能回归门禁。
  - 验收：同一真实样本 fps 相比基线下降超过 5% 时报告失败或要求更新基线说明。

## Phase 13: 发布文档

- [ ] 生成 `docs/encoder_libvpx_compare_report.md`。
  - 验收：包含样本表、工具版本、命令、指标和结论。
- [ ] 更新 `docs/encoder_quality_report.md`。
  - 验收：新增外部 libvpx 对标章节。
- [ ] 更新 `docs/cli.md`。
  - 验收：描述多帧 `encode --frames N --fps NUM/DEN`。
- [ ] 更新 `docs/error_codes.md`。
  - 验收：描述新增参数和输入长度错误。
- [ ] 更新 `README.md` capability boundary。
  - 验收：README 与当前 encoder 能力一致。
- [ ] 更新 `CHANGELOG.md`。
  - 验收：记录多帧 CLI、libvpx 对标报告或门禁变化。

## Phase 14: 总体验收

- [ ] 普通测试通过。
  - 验收命令：`make test`。
- [ ] 文档检查通过。
  - 验收命令：`git diff --check`。
- [ ] libvpx 对标 benchmark 可运行。
  - 验收命令：`make bench-libvpx-encode`。
- [ ] libvpx 硬阈值通过。
  - 验收命令：`make test-libvpx-encode-threshold`。
- [ ] 大样本未进入 git。
  - 验收命令：`git status --short` 不显示 `build/real-y4m/` 或 raw media 文件。
- [ ] UYA 输出可被 `vpxdec` 解码。
  - 验收：所有真实样本 `.vp8uya.ivf` 均可由 `vpxdec` 输出正确大小 I420。
- [ ] UYA 输出可被本项目 decoder 解码。
  - 验收：所有真实样本 `.vp8uya.ivf` 均可由 `build/vp8uya decode` 输出正确大小 I420。
- [ ] 所有真实样本达到硬阈值。
  - 验收：`summary.json` 中所有样本 `passed=true`。
