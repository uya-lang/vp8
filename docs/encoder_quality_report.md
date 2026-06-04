# Encoder quality report

Date: 2026-06-04

This report records the current encoder quality evidence for the
release-hardening phase. It covers the current one-frame I420-to-IVF encoder
path and the supporting quality, rate-control, mode-search, and roundtrip
tests.

## Scope

The current CLI encoder accepts exactly one contiguous I420 frame and writes a
one-frame IVF VP8 keyframe stream:

```sh
build/vp8uya encode <input.yuv> --width W --height H [--quantizer Q] [--target-bitrate BPS] [--speed fastest|fast|balanced|best] --out <out.ivf>
```

The quality metrics are computed by decoding the encoded frame with the local
decoder and comparing visible I420 output to the original input. This makes the
metrics useful for local regression tracking, but they are not external libvpx
quality validation or subjective visual quality ratings.

## Verification commands

The following commands were run on 2026-06-04:

```sh
make test
make check
make bench-encode
```

Results:

| Command | Result | Notes |
| --- | --- | --- |
| `make test` | passed | Covers encoder config, rate control, quality metrics, keyframe output, mode search, transform/quant/token paths, CLI encode smoke, and decode roundtrips. |
| `make check` | passed | `uya check src/main.uya` completed type checking. |
| `make bench-encode` | passed | Ran two deterministic encode samples in scalar and forced-SIMD modes. |

## Quality metric tests

`src/vp8_encoder_quality_test.uya` covers:

- PSNR infinity for identical frames
- per-plane and aggregate PSNR for a known non-identical frame
- SSIM of 1.0 for identical frames
- per-plane and aggregate SSIM for a known non-identical frame
- geometry mismatch rejection for both metric families

These tests validate the metric math used by the CLI and benchmark reports.

## CLI encode smoke

`make test` exercises the CLI encoder on 16x16 I420 samples. The generated IVF
streams are parsed by `info`, decoded back to I420, and checked for 384-byte
visible output.

| Scenario | PSNR all | SSIM all | Speed preset | Work units | Notes |
| --- | ---: | ---: | --- | ---: | --- |
| default zero frame | 49.12 | 0.9072 | balanced | 112 | Repeated encode output is byte-identical. |
| speed fastest | 20.19 | 0.8436 | fastest | 16 | Output differs from `best`, as expected. |
| speed best | 20.42 | 0.8489 | best | 112 | Higher work count and slightly higher measured quality than `fastest`. |
| target bitrate 13680 bps | inf | 1.0000 | balanced | 112 | Target bits 456, actual bits 456, within tolerance. |

The CLI gate also checks invalid quantizer and invalid target bitrate exits,
deterministic VBR logs, and that quantizer/speed/bitrate variants produce
different IVF files when expected.

## Encode benchmark samples

`make bench-encode` ran with `repeats=5`, `warmups=1`, and
`cycles_per_second=1_000_000_000.0`. Cycles per pixel are derived from
wall-clock nanoseconds, not a hardware cycle counter.

| Sample | Mode | Size | Q | Speed | Median ns | FPS | cycles/pixel | Work units | IVF bytes | PSNR all | SSIM all | IVF MD5 |
| --- | --- | ---: | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| gradient-32x16 | scalar | 32x16 | 40 | best | 3469979 | 288.186 | 6777.303 | 244 | 524 | 20.16 | 0.8525 | d51585b5ac8b0a75327806b7f6454c08 |
| gradient-32x16 | simd | 32x16 | 40 | best | 3732791 | 267.896 | 7290.607 | 244 | 524 | 20.16 | 0.8525 | d51585b5ac8b0a75327806b7f6454c08 |
| mode-search-64x64 | scalar | 64x64 | 40 | best | 16684630 | 59.935 | 4073.396 | 2356 | 2613 | 20.43 | 0.8678 | 3bd9940fc44edc56b9264f05e05ed3ae |
| mode-search-64x64 | simd | 64x64 | 40 | best | 19576250 | 51.082 | 4779.358 | 2356 | 2613 | 20.43 | 0.8678 | 3bd9940fc44edc56b9264f05e05ed3ae |

Scalar and forced-SIMD bitstreams were byte-identical for both benchmark
samples, and mode-search work units matched. Forced SIMD was slower in this
run: `gradient-32x16` speedup was `0.930`, and `mode-search-64x64` speedup was
`0.852`.

## Encoder behavior covered by tests

The current unit and CLI gates cover:

- encoder config validation for geometry, timing, quantizer, bitrate, threads,
  and speed preset
- contiguous and strided YUV420 input views
- IVF writer timing and short-buffer rejection
- constant-quantizer, simple VBR, target-bitrate frame reports, and CBR buffer
  model helpers
- keyframe IVF output parsing and local decoder roundtrip
- deterministic keyframe output for fixed input
- speed preset work-count differences and output differences
- non-DC luma 4x4 mode selection
- coefficient probability updates from token stats
- scalar/forced-SIMD predictor-cost equivalence for encoder analysis paths

## Current boundary

This quality report does not claim broad encoder quality. Missing evidence
includes multi-frame CLI encoding, long-running rate-control behavior, external
decoder or libvpx quality comparison, real-world video clips, subjective visual
assessment, large-resolution samples, and stable SIMD encoder speedups.

The current evidence is best read as a deterministic regression baseline for
the one-frame keyframe encoder path.
