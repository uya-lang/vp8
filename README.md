# vp8uya

`vp8uya` is a pure UYA VP8 codec project. The first target is a bit-exact
VP8 decoder for IVF and raw VP8 payloads. Encoder support, SIMD kernels, row
parallelism, and broader container support are planned after the scalar
decoder is correct.

## Current Status

This repository has a scalar decoder work-in-progress. It can parse IVF
container metadata, decode the supported scalar VP8 path for tiny built-in
samples, and write visible I420 YUV output. Broader conformance coverage,
SIMD, parallelism, and encoder support are still pending.

Current command surface:

- `vp8uya --help`
- `vp8uya version`
- `vp8uya info <input.ivf>` prints IVF width, height, frame count, timebase,
  fps, and the number of bounded frame payloads found.
- `vp8uya decode <input.ivf> --yuv <out.yuv>` writes decoded I420 output for
  supported scalar VP8 frames.
- `vp8uya decode-frame <input.ivf> --index N --yuv <out.yuv>` writes one
  decoded visible frame by IVF frame index.

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

## Tests And Benchmarks

`make test` runs UYA unit tests for bitstream, boolean coder, container,
decoder context, scalar kernels, and scalar decoder behavior. It also generates
six tiny IVF samples, including a key+inter sample, decodes them through the
CLI, and checks their YUV MD5 values against built-in goldens.

`make test-decoder-scalar` runs the decoder suite with
`VP8UYA_FORCE_SCALAR=1` and is the scalar reference regression gate.
Tiny fixture metadata lives in `fixtures/manifest.json`; binary IVF and YUV
outputs are generated under `build/tiny-md5/`.
`make test-keyframe-md5` runs only manifest samples in the `key` group.
`make test-inter-md5` runs only manifest samples in the `inter` group.

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
