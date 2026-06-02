# Agent Constraints

This file records repository rules for coding agents working on `vp8uya`.

## Pure UYA Runtime

- Runtime codec code must be implemented in `.uya` files.
- Do not add libvpx, FFmpeg, C/C++ intrinsics, generated C runtime code, or
  external assembly as decoder or encoder dependencies.
- External tools such as `vpxdec`, `vpxenc`, or FFmpeg may be used only in
  tests, fixture generation, and differential validation.
- UYA `@asm` is allowed only for optional isolated hot kernels. It must never be
  required for correctness, and scalar builds must keep passing without it.

## Bit-Exact Correctness

- The scalar decoder is the reference path. SIMD and parallel paths must compare
  against it block-by-block or frame-by-frame before they are accepted.
- Do not call a feature "decoded" until reconstruction, loop filtering,
  reference refresh, visible crop, and YUV output are all implemented.
- Parse errors must return explicit diagnostics with enough context to locate
  the frame, partition, and byte offset.
- Bounds checks are part of correctness. Never silence assertions or skip
  malformed input checks to make tests pass.

## SIMD And Performance

- Prefer UYA `@vector(T,N)` and `@mask(N)` for SIMD semantics so the C99 backend
  can choose platform code or scalar fallback.
- Keep all SIMD kernels behind a dispatch table and retain a scalar reference.
- Avoid whole-frame coefficient materialization in decoder hot paths. Use
  macroblock or row-local scratch storage with bounded lifetime.
- Reference frame refresh must alias or swap frame buffers where VP8 semantics
  allow it; do not copy whole frames as the default path.
- Performance changes need benchmark coverage or explicit baseline notes.

## Tests

- `make test` must pass without external codec tools.
- Differential tests that need libvpx or FFmpeg must be optional targets.
- Golden fixtures must record source, dimensions, frame count, and output MD5.
- Malformed IVF and VP8 payload tests must check for controlled errors, not
  crashes or out-of-bounds reads.
- Do not fake validation results, skip failing checks, or replace real codec
  behavior with hardcoded fixture answers.
