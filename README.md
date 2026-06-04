# vp8uya

`vp8uya` is a pure UYA VP8 codec project. The first target is a bit-exact
VP8 decoder for IVF, raw VP8 payloads, and a minimal WebM VP8 subset. Encoder
support, SIMD kernels, row parallelism, and broader container support are
planned after the scalar decoder is correct.

## Current Status

This repository has a scalar decoder work-in-progress. It can parse IVF
container metadata and a minimal WebM VP8 subset, decode the supported scalar
VP8 path for tiny built-in samples, and write visible I420 YUV output. Broader
conformance coverage, SIMD, parallelism, and encoder support are still
pending.

Current command surface:

- `vp8uya --help`
- `vp8uya version`
- `vp8uya info <input.ivf>` prints IVF width, height, frame count, timebase,
  fps, and the number of bounded frame payloads found.
- `vp8uya decode <input.ivf|input.webm> --yuv <out.yuv>` writes decoded I420
  output for supported scalar VP8 frames. WebM support is limited to the
  minimal VP8 subset demuxer and the first matching SimpleBlock sample.
- `vp8uya decode-frame <input.ivf> --index N --yuv <out.yuv>` writes one
  decoded visible frame by IVF frame index.

Full command documentation lives in `docs/cli.md`.

## Build

The Makefile builds `build/vp8uya` from `src/main.uya`:

```sh
make build
```

Compiler selection:

- Set `UYA=/path/to/uya` to use an explicit compiler.
- Otherwise `make` uses `uya` from `PATH` when available.
- On this machine, a local compiler was found at
  `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya`.
- If no compiler is available, `make build` fails early with a clear message
  instead of producing a fake binary.
- `make check-toolchain` builds and runs a minimal UYA hello-world program to
  confirm the compiler can produce a native executable.

Run the scaffold after building:

```sh
build/vp8uya --help
```

## Library API Examples

Small executable examples for the public UYA API live at:

- `src/vp8_example_decoder_api.uya`
- `src/vp8_example_encoder_api.uya`

Build and run both examples through the Makefile:

```sh
make test-examples
```

The generated binaries are written to `build/examples/`.

## Tests And Benchmarks

`make test` runs UYA unit tests for bitstream, boolean coder, container,
decoder context, scalar kernels, and scalar decoder behavior. It also generates
eight tiny IVF samples, including key+inter, segmentation, and multi-token
partition samples. It decodes them through the CLI and checks their YUV MD5
values against built-in goldens. It also runs generated malformed IVF corpus
and malformed VP8 payload corpus checks for controlled CLI errors, plus a
deterministic fuzz smoke pass.

`make test-decoder-scalar` runs the decoder suite with
`VP8UYA_FORCE_SCALAR=1` and is the scalar reference regression gate.
Tiny fixture metadata lives in `fixtures/manifest.json`; binary IVF and YUV
outputs are generated under `build/tiny-md5/`.
`make test-keyframe-md5` runs only manifest samples in the `key` group.
`make test-inter-md5` runs only manifest samples in the `inter` group.
`make test-non16-md5` runs only manifest samples in the `non16` group.
`make test-segmentation-md5` runs only manifest samples in the `segmentation`
group.
`make test-token-partition-md5` runs only manifest samples in the
`token-partition` group.
`make test-malformed-ivf` generates malformed IVF cases from
`fixtures/malformed_ivf/manifest.json` and checks `info`/`decode` error exits.
`make test-malformed-vp8` wraps malformed VP8 payloads in valid IVF containers
and checks `decode`/`decode-frame` error exits while `info` still succeeds.
`make test-fuzz-smoke` generates deterministic random IVF blobs and valid IVF
containers with random VP8 payloads, accepting only success or controlled error
exits.
`make test-webm-subset-decode` generates a minimal WebM VP8 subset sample,
decodes it through the CLI, and checks the YUV MD5.
`make test-error-codes-doc` verifies `docs/error_codes.md` lists every UYA
error declaration under `src/`.
`make test-cli-doc` verifies `docs/cli.md` covers every current CLI usage line.
`make test-examples` builds and runs the library API examples.

`make test-vpxdiff` is an optional libvpx/vpxdec differential target. It skips
cleanly when `vpxdec` is not installed or no compatible manifest samples exist.

`bench/` is reserved for benchmark harnesses and baseline records. Benchmarks
must keep scalar and SIMD paths comparable and must not become correctness
dependencies.

## Capability Boundary

This project intentionally does not depend on libvpx, FFmpeg, C/C++
intrinsics, or external assembly in runtime codec code. External tools may be
used only for test fixture generation and differential validation.

Until conformance work is complete, decoder support is limited to the covered
scalar path and built-in fixture shapes. Encoder support is not implemented.
