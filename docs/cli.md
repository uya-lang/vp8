# CLI

`vp8uya` is the command-line surface for the pure UYA VP8 codec. The current
CLI focuses on deterministic workflows: inspect IVF, decode supported VP8
samples to I420 YUV, encode one I420 frame to IVF, and force scalar/SIMD
dispatch paths for regression checks.

Build the binary first:

```sh
make build
```

The default binary path is:

```sh
build/vp8uya
```

## Usage

The built-in help currently prints:

```text
vp8uya CLI
Usage:
  vp8uya [--help|-h]
  vp8uya [--force-scalar|--force-simd] [--threads N] <command> [args]
  vp8uya version
  vp8uya info <input.ivf>
  vp8uya decode <input.ivf|input.webm> --yuv <out.yuv> [--stats <out.jsonl>]
  vp8uya decode-frame <input.ivf> --index N --yuv <out.yuv>
  vp8uya encode <input.yuv> --width W --height H [--quantizer Q] [--target-bitrate BPS] [--speed fastest|fast|balanced|best] --out <out.ivf>
```

Global flags must appear before the command:

| Flag | Effect |
| --- | --- |
| `--force-scalar` | Use the scalar kernel table for decode and encode analysis paths. |
| `--force-simd` | Request the forced SIMD kernel table. Kernels that are not available fall back according to the dispatcher implementation. |
| `--threads N` | Configure decoder worker scratch for `N` positive workers. |

Equivalent environment toggles are available for smoke tests:

| Environment variable | Effect |
| --- | --- |
| `VP8UYA_FORCE_SCALAR=1` | Enables scalar dispatch unless a later CLI flag overrides it. |
| `VP8UYA_FORCE_SIMD=1` | Enables forced SIMD dispatch unless a later CLI flag overrides it. |

## Exit Status

| Status | Meaning |
| --- | --- |
| `0` | Command succeeded, or help was printed for an empty command line. |
| `1` | Unknown command. |
| `2` | Controlled usage, file, allocation, parse, encode, or decode failure. |

Detailed CLI error text is cataloged in `docs/error_codes.md`.

## `version`

```sh
build/vp8uya version
```

Prints:

```text
vp8uya 0.1.0-alpha.1
```

The release version is tracked in the top-level `VERSION` file and summarized in
`CHANGELOG.md`.

## `info`

```sh
build/vp8uya info <input.ivf>
```

`info` accepts IVF only. It validates the IVF header and bounded frame iterator,
then prints key/value lines:

```text
ivf.width=<pixels>
ivf.height=<pixels>
ivf.frame_count=<declared-frame-count>
ivf.timebase=<numerator>/<denominator>
ivf.fps=<denominator>/<numerator>
ivf.payloads=<bounded-payload-count>
```

Example:

```sh
build/vp8uya info build/sample.ivf
```

## `decode`

```sh
build/vp8uya decode <input.ivf|input.webm> --yuv <out.yuv> [--stats <out.jsonl>]
```

`decode` writes visible I420 output to `--yuv`. IVF inputs may contain multiple
frames; each visible decoded frame is appended to the output YUV file.

WebM support is intentionally limited to the repository's minimal VP8 subset:

- EBML `DocType` must be `webm`.
- The first video track must use codec id `V_VP8`.
- The first matching `SimpleBlock` is extracted and decoded.
- Laced SimpleBlocks are rejected.
- Only the first matching VP8 sample is decoded by the CLI WebM path.

The optional `--stats` path writes JSON Lines, one object per decoded input
frame or WebM sample:

```json
{"frame_index":0,"has_output":1,"macroblock_count":1,"thread_count":1,"hot_loop_heap_allocation_count":0,"bytes_copied_for_ref_refresh":0,"coeff_scratch_bytes_written":0,"coeff_scratch_bytes_read":0,"coeff_scratch_high_water":0,"border_extension_count":0}
```

The exact numeric values depend on the frame and active decode path.

Examples:

```sh
build/vp8uya decode input.ivf --yuv out.yuv
build/vp8uya --force-scalar decode input.ivf --yuv out.yuv --stats stats.jsonl
build/vp8uya decode input.webm --yuv out.yuv
```

## `decode-frame`

```sh
build/vp8uya decode-frame <input.ivf> --index N --yuv <out.yuv>
```

`decode-frame` accepts IVF only. It decodes frames in order, writes the visible
frame whose IVF frame index equals `N`, and exits. If no matching frame exists,
the command exits with status `2`.

Example:

```sh
build/vp8uya decode-frame input.ivf --index 0 --yuv frame0.yuv
```

## `encode`

```sh
build/vp8uya encode <input.yuv> --width W --height H [--quantizer Q] [--target-bitrate BPS] [--speed fastest|fast|balanced|best] --out <out.ivf>
```

`encode` currently expects exactly one contiguous I420 frame:

- Y plane: `W * H` bytes.
- U plane: `ceil(W / 2) * ceil(H / 2)` bytes.
- V plane: `ceil(W / 2) * ceil(H / 2)` bytes.

Options:

| Option | Meaning |
| --- | --- |
| `--width W` | Required positive visible width in pixels. |
| `--height H` | Required positive visible height in pixels. |
| `--quantizer Q` | Optional VP8 qindex in `0..127`. If omitted, the default encoder config decides. |
| `--target-bitrate BPS` | Optional target bitrate in bits per second. When present, the CLI reports bitrate error metrics. |
| `--speed fastest|fast|balanced|best` | Optional speed preset. Default is `balanced`. |
| `--out <out.ivf>` | Required IVF output path. |

Successful encode prints quality and speed metrics:

```text
encode.psnr.y=<value-or-inf>
encode.psnr.u=<value-or-inf>
encode.psnr.v=<value-or-inf>
encode.psnr.all=<value-or-inf>
encode.ssim.y=<value>
encode.ssim.u=<value>
encode.ssim.v=<value>
encode.ssim.all=<value>
encode.speed.preset=<preset>
encode.speed.mode_search_work_units=<count>
```

When `--target-bitrate` is provided, it also prints:

```text
encode.bitrate.target_bits=<bits>
encode.bitrate.actual_bits=<bits>
encode.bitrate.error_bits=<signed-bits>
encode.bitrate.error_ppm=<parts-per-million>
encode.bitrate.tolerance_ppm=<parts-per-million>
encode.bitrate.within_tolerance=<0-or-1>
```

Example:

```sh
build/vp8uya encode input.yuv --width 16 --height 16 --quantizer 32 --speed best --out out.ivf
```

## Capability Boundary

The CLI does not currently provide a full WebM demuxer, WebM muxer, RTP command
surface, arbitrary raw VP8 command, multi-frame encoder command, or external
libvpx integration. Those boundaries are intentional for this release stage;
covered command behavior is enforced by `make test`.
