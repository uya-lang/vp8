# Changelog

## 0.1.0-alpha.1 - 2026-06-04

### Release notes

This is the first release-hardening alpha for `vp8uya`. It publishes a concrete
version number, a reproducible CLI version output, CI gates for the current
support matrix, and release notes that spell out what is ready for regression
use versus what remains experimental.

### Supported scope

- CLI metadata: `vp8uya --help`, `vp8uya version`, and documented exit status
  behavior.
- IVF inspection through `vp8uya info <input.ivf>`, including bounded frame
  iteration and controlled malformed-input errors.
- Decoder CLI coverage for generated tiny IVF fixtures: key frames, one
  zero-motion inter sequence, non-16-aligned visible crop, zero-delta
  segmentation, and four token partitions.
- Minimal WebM VP8 subset decode for the generated SimpleBlock fixture used by
  the regression suite.
- Visible I420 output through `vp8uya decode` and single-frame output through
  `vp8uya decode-frame` for the supported fixture shapes.
- Forced scalar and forced SIMD regression paths through CLI flags and
  `VP8UYA_FORCE_SCALAR=1` / `VP8UYA_FORCE_SIMD=1` environment toggles.
- Single-vs-multithread decoder determinism checks over the built-in manifest.
- One-frame I420-to-IVF keyframe encoder CLI with quantizer, target bitrate,
  speed preset, PSNR/SSIM reporting, and deterministic local decoder roundtrip.
- Public UYA decoder and encoder API examples under `src/vp8_example_*_api.uya`.
- CI gates for build/test/bench smoke, scalar-only, forced SIMD, and optional
  libvpx differential validation.

### Known limits

- This release is not a full VP8 conformance suite. The decoder evidence is
  intentionally limited to the generated fixtures, malformed corpora, fuzz smoke
  coverage, and the optional libvpx differential path.
- Broad third-party VP8 streams, large-resolution inter content, complex
  motion-vector patterns, non-zero segmentation deltas, and complete token
  partition combinations across larger frame grids still need coverage.
- WebM support is a minimal WebM VP8 subset, not general Matroska/WebM
  demuxing.
- RTP VP8 parsing and reassembly are module-level coverage only; there is no
  end-to-end RTP media ingest CLI.
- Encoder support is limited to a one-frame I420-to-IVF keyframe encoder. It
  does not provide multi-frame CLI encoding, inter-frame encoding, full
  rate-control validation over clips, or external visual-quality claims.
- SIMD paths are available for forced regression and benchmark checks, but the
  default dispatcher keeps benchmark-threshold-gated entries disabled until the
  required repeated evidence is available.
- The optional libvpx differential gate requires `vpxdec` and `vpxenc`; without
  those tools it skips cleanly.
- No C ABI is promised in this release.

### Verification

Release-hardening evidence for this snapshot is recorded in:

- `docs/error_codes.md`
- `docs/cli.md`
- `docs/kernel_benchmark_report.md`
- `docs/decoder_conformance_report.md`
- `docs/encoder_quality_report.md`
- `docs/fuzz_corpus_minimization.md`

The release gates include `make check`, `make test`, `make bench-smoke`,
`make ci-scalar-only`, `make ci-simd-enabled`, and `make ci-libvpx-diff`.
