# vp8uya

`vp8uya` is a pure UYA VP8 codec project. The first target is a bit-exact
VP8 decoder for IVF and raw VP8 payloads. Encoder support, SIMD kernels, row
parallelism, and broader container support are planned after the scalar
decoder is correct.

## Current Status

This repository is currently a project scaffold. It does not yet decode,
encode, parse, or write real VP8 bitstreams. The CLI only exposes placeholder
commands so the build and command surface can be validated while the codec
modules are implemented.

Current command surface:

- `vp8uya --help`
- `vp8uya version`
- `vp8uya info <input.ivf>` reports that IVF parsing is not implemented yet.
- `vp8uya decode <input.ivf> --yuv <out.yuv>` reports that decoding is not
  implemented yet.

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

Run the scaffold after building:

```sh
build/vp8uya --help
```

## Tests And Benchmarks

`make test` currently verifies the scaffold files and CLI help output. Codec
correctness tests will be added with the bitstream, boolean coder, container,
decoder, and kernel phases.

`bench/` is reserved for benchmark harnesses and baseline records. Benchmarks
must keep scalar and SIMD paths comparable and must not become correctness
dependencies.

## Capability Boundary

This project intentionally does not depend on libvpx, FFmpeg, C/C++
intrinsics, or external assembly in runtime codec code. External tools may be
used only for test fixture generation and differential validation.

Until the Phase 1 through Phase 7 tasks are complete, this project has no real
VP8 decoding or encoding capability.
