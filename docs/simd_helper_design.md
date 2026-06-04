# SIMD helper design

This document records the small helper contracts that sit below the portable
SIMD VP8 kernels. Each helper must keep scalar fallbacks possible until the
generated C/assembly checks and benchmark thresholds prove that the helper is a
good default-dispatch building block.

## `load_u8x16_unaligned`

Purpose: load sixteen consecutive `u8` lanes from a byte address that is not
required to have 16-byte alignment. VP8 uses this shape for plane rows, border
extension, prediction references, and loop-filter neighborhoods where visible
frame origins and block offsets are not guaranteed to line up on SIMD-friendly
boundaries.

Contract:

- Input points to at least 16 readable bytes.
- The pointer may be byte-aligned only; callers must not assume stronger
  alignment from plane origin, crop offset, or macroblock position.
- The lane order is memory order: lane `0` receives `src[0]`, lane `15`
  receives `src[15]`.
- The helper does not perform bounds checks. Existing frame/plane/container
  bounds validation remains responsible for proving the 16-byte range is valid.
- Current UYA C99 lowering is the same as `load_u8x16`: `@vector.load` lowers
  through a `memcpy`-style copy, so unaligned addresses are accepted by the
  generated C path. Future hardware-specific lowering may replace this only if
  it preserves byte-exact behavior for unaligned pointers.

Fallback and testing:

- Scalar fallback is sixteen byte reads in lane order.
- `src/vp8_kernels_simd_test.uya` covers a deliberately offset load and verifies
  sentinel bytes outside the loaded range remain untouched after a store.
- `docs/simd_codegen.md` remains the generated-code source of truth for actual
  lowering; this helper alone does not default-enable any dispatcher entry.

## `store_u8x16_unaligned`

Purpose: store sixteen consecutive `u8` lanes to a byte address that is not
required to have 16-byte alignment. This is the write-side pair for
`load_u8x16_unaligned` and is needed for reconstructed rows, copied predictors,
border fills, and loop-filter edge updates whose destination offset may be any
byte position inside a plane.

Contract:

- Output points to at least 16 writable bytes.
- The pointer may be byte-aligned only; callers must not depend on macroblock
  or row origins being 16-byte aligned.
- The lane order is memory order: lane `0` writes `dst[0]`, lane `15` writes
  `dst[15]`.
- The helper does not perform bounds checks. Plane allocation and caller-side
  geometry checks remain responsible for proving the 16-byte range is valid.
- Current UYA C99 lowering is the same as `store_u8x16`: `@vector.store` lowers
  through a `memcpy`-style copy. Hardware-specific lowering may replace this
  only when unaligned stores remain byte-exact.

Fallback and testing:

- Scalar fallback is sixteen byte writes in lane order.
- `src/vp8_kernels_simd_test.uya` covers a deliberately offset store and verifies
  sentinel bytes before and after the write range remain untouched.
- Like the load helper, this helper is a portability contract and does not by
  itself default-enable a SIMD dispatcher entry.
