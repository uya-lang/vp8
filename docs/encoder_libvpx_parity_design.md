# Encoder libvpx 追赶详细设计

Date: 2026-06-05

## 1. 本轮范围

本文档只定义后续 encoder 追赶 libvpx 的设计，不包含任何实现。

本轮只做：

- 新增 `docs/encoder_libvpx_parity_design.md`。
- 新增 `docs/encoder_libvpx_parity_todo.md`。
- 通过文档级文本检查确认没有 whitespace 问题。

本轮明确不做：

- 不编辑 `src/`。
- 不修改 `Makefile`。
- 不实现 `encode --frames`。
- 不下载 `vpxenc`、`vpxdec` 或真实样本。
- 不新增 benchmark 脚本或 fixture manifest。
- 不运行完整测试。

后续实现必须另起目标，再按 TODO 逐项推进。

本文档中的 CLI、脚本、manifest、Makefile target、JSON/Markdown 报告均为未来设计，不代表本轮已经实现或生成。

## 2. 目标结论

### 2.1 不追 MD5 一致

本项目 encoder 输出不追求和 libvpx encoder 输出 MD5 一致。

VP8 bitstream 只规定解码语义，不规定 encoder 必须选择相同的 mode、MV、概率更新、token partition、quantizer 或 rate control。对同一输入，多个不同 VP8 bitstream 都可以合法，并且都能解码成可比较的视频。因此用 IVF 文件 MD5 对齐 libvpx 不是正确目标。

正确目标是：同一输入序列、同一帧数、同一测量流程下，对比解码后质量、输出码率和编码速度。

### 2.2 对标目标

第一版对标使用 libvpx `vpxenc --best`。UYA encoder 追赶目标不是 bitstream 形状，而是以下三个维度：

- 码率：同等输入下输出 bits per pixel 不明显高于 libvpx。
- 质量：解码后 `PSNR-all` 不明显低于 libvpx。
- 速度：编码 fps 不明显低于 libvpx `--best`。

第一版硬阈值：

| 指标 | 硬阈值 |
| --- | --- |
| 码率 | `vp8uya_bits_per_pixel <= libvpx_bits_per_pixel * 1.10` |
| PSNR-all | `vp8uya_psnr_all_db >= libvpx_psnr_all_db - 0.50` |
| 编码速度 | `vp8uya_fps >= libvpx_fps * 0.80` |

`SSIM-all` 第一版只记录，不作为硬失败条件。后续若 PSNR-all、码率和速度已经稳定，可以再把 SSIM 纳入门禁。

## 3. 当前问题判断

当前用户反馈是“性能和质量都比 libvpx 差”。因此下一阶段不能只验证可解码、roundtrip 或 deterministic MD5，需要建立真实样本和 libvpx 对标闭环。

需要拆开的概念：

- 可解码：输出 VP8/IVF 能被本项目 decoder 或 `vpxdec` 解码。
- 稳定性：相同输入是否 deterministic。
- 质量：解码后 Y/U/V/all PSNR、SSIM。
- 码率：payload bits、bits per pixel、bitrate ratio。
- 速度：编码 elapsed ns、fps、fps ratio。

只有质量、码率、速度同时达到硬阈值，才算完成第一版 libvpx 追赶门禁。

## 4. 未来 CLI 设计

后续在现有 `encode` 命令上扩展多帧输入能力：

```sh
build/vp8uya encode <input.i420> \
  --width W \
  --height H \
  --frames N \
  --fps NUM/DEN \
  --out <out.ivf>
```

默认值：

- `--frames 1`
- `--fps 30/1`

行为要求：

- `--frames 1` 保持现有单帧 encode 行为兼容。
- `--frames N` 时输入长度必须等于 `frame_size * N`。
- I420 `frame_size` 使用 `width * height + 2 * ceil(width / 2) * ceil(height / 2)`。
- 输入不足、输入多余、`--frames 0`、非法 `--fps` 都必须返回受控错误。
- 输出 IVF header 的 `frame_count` 必须等于 N。
- IVF timestamp 从 0 开始逐帧递增。
- 第一帧默认 key frame，后续帧由 encoder API 的 reference/rate-control 状态决定。

CLI 不应复制 inter-frame 状态机。多帧 encode 应优先复用公共 `Vp8Encoder` API，并让 API 维护 reference pool、frame index、rate control 和 stats。

## 5. libvpx 工具链设计

后续对标脚本需要自动获取或发现 `vpxenc`、`vpxdec`，但本轮不实现。

查找顺序建议：

1. 使用 `VPXENC`、`VPXDEC` 环境变量。
2. 查找 `PATH` 中的 `vpxenc`、`vpxdec`。
3. 查找 `build/deps/vpx-tools-root/usr/bin/`。
4. 无 sudo 使用系统包下载并解包 `vpx-tools` 到 `build/deps/vpx-tools-root/`。

建议命令形态：

```sh
apt-get download vpx-tools
dpkg-deb -x vpx-tools_*.deb build/deps/vpx-tools-root
```

约束：

- 不使用 sudo。
- 不修改系统包安装状态。
- 下载失败时报告明确原因。
- 报告必须记录 `vpxenc --version` 和 `vpxdec --version`。

## 6. 真实样本设计

后续脚本需要自动下载 Xiph Derf 真实 Y4M 样本，不把媒体文件提交进 git。

第一批建议样本：

| 名称 | URL | 覆盖点 |
| --- | --- | --- |
| `akiyo_qcif` | `https://media.xiph.org/video/derf/y4m/akiyo_qcif.y4m` | 低运动人像 |
| `foreman_qcif` | `https://media.xiph.org/video/derf/y4m/foreman_qcif.y4m` | 中等运动 |
| `coastguard_qcif` | `https://media.xiph.org/video/derf/y4m/coastguard_qcif.y4m` | 平移运动 |
| `mobile_cif` | `https://media.xiph.org/video/derf/y4m/mobile_cif.y4m` | 复杂纹理 |

manifest 后续建议产物：

```text
fixtures/encoder_libvpx_real_samples.json
```

缓存目录建议：

```text
build/real-y4m/
build/libvpx-encode-compare/fixtures/
```

manifest 字段建议：

```json
{
  "name": "foreman_qcif",
  "url": "https://media.xiph.org/video/derf/y4m/foreman_qcif.y4m",
  "width": 176,
  "height": 144,
  "frames": 60,
  "fps": "30/1",
  "sha256": "<downloaded-y4m-sha256>",
  "groups": ["real", "qcif", "motion"]
}
```

处理流程：

1. 下载 Y4M 到 `build/real-y4m/`。
2. 校验 sha256。
3. 截取前 60 帧。
4. 转换为 raw I420。
5. 校验 I420 文件大小等于 `frame_size * frames`。

## 7. 对标流程设计

### 7.1 UYA encode

未来命令形态：

```sh
build/vp8uya encode build/libvpx-encode-compare/fixtures/foreman_qcif.i420 \
  --width 176 \
  --height 144 \
  --frames 60 \
  --fps 30/1 \
  --out build/libvpx-encode-compare/runs/foreman_qcif.vp8uya.ivf
```

### 7.2 libvpx encode

未来命令形态：

```sh
vpxenc --codec=vp8 \
  --best \
  --ivf \
  --width=176 \
  --height=144 \
  --fps=30/1 \
  --limit=60 \
  -o build/libvpx-encode-compare/runs/foreman_qcif.libvpx.ivf \
  build/libvpx-encode-compare/fixtures/foreman_qcif.i420
```

### 7.3 decode 与质量统计

两个输出都用 `vpxdec` 解码为 raw I420：

```sh
vpxdec --rawvideo -o foreman_qcif.vp8uya.decoded.i420 foreman_qcif.vp8uya.ivf
vpxdec --rawvideo -o foreman_qcif.libvpx.decoded.i420 foreman_qcif.libvpx.ivf
```

质量统计统一比较原始 I420 与 decoded I420：

- `PSNR-Y`
- `PSNR-U`
- `PSNR-V`
- `PSNR-all`
- `SSIM-Y`
- `SSIM-U`
- `SSIM-V`
- `SSIM-all`

码率统计使用 IVF frame payload bits，不把 IVF file header 和 per-frame IVF header 计入 payload。

速度统计使用同一机器、同一脚本、同一 warmup/repeat 策略记录 elapsed ns，并转换为 fps。

## 8. 报告产物设计

后续对标脚本需要生成机器可读和人可读报告。

建议产物：

```text
build/libvpx-encode-compare/results.ndjson
build/libvpx-encode-compare/summary.json
docs/encoder_libvpx_compare_report.md
```

`results.ndjson` 每行记录一个样本一次对比：

- sample name、width、height、frames、fps
- vp8uya command、libvpx command
- tool paths、tool versions
- encode elapsed ns、fps
- payload bits、bits per pixel、bitrate ratio
- PSNR/SSIM 指标
- threshold pass/fail
- failure reasons

`summary.json` 记录整体结果：

- run timestamp
- git commit
- host summary
- threshold config
- sample count
- passed count
- failed count

`docs/encoder_libvpx_compare_report.md` 记录：

- 结论表
- 每个样本的码率、质量、速度对比
- 未达标样本的复现命令
- 工具版本
- 后续优化建议

## 9. 硬阈值判定

每个样本独立判定，任一样本失败则硬阈值门禁失败。

失败条件：

- `vp8uya_bits_per_pixel > libvpx_bits_per_pixel * 1.10`
- `vp8uya_psnr_all_db < libvpx_psnr_all_db - 0.50`
- `vp8uya_fps < libvpx_fps * 0.80`
- UYA 输出无法被 `vpxdec` 解码
- libvpx 输出无法被 `vpxdec` 解码
- decoded I420 大小不等于 `frame_size * frames`

第一版只把 `PSNR-all` 作为质量硬阈值。Y/U/V PSNR 和 SSIM-all 进入报告，用于定位问题。

## 10. 后续优化方向

对标闭环建立后，优化应按失败证据排序：

- 若码率高：优先检查 token cost、mode cost、skip decision、rate control。
- 若 PSNR-all 低：优先检查 inter/intra mode decision、MV 搜索、chroma distortion、Q 分配。
- 若 fps 低：优先检查 hot path allocation、mode search work units、SAD/SSE/transform SIMD。
- 若 only real samples 失败：优先补充样本分组和失败复现命令。

每个优化项都必须以报告中的指标变化作为验收依据。

## 11. 文档级验收

本轮只执行文档级检查：

```sh
git diff --check
git status --short
```

验收标准：

- `git diff --check` 无输出且返回 0。
- 本轮范围内只新增或修改 `docs/encoder_libvpx_parity_design.md` 和 `docs/encoder_libvpx_parity_todo.md`。
- 文档为中文，命令、API、指标名保留英文。
