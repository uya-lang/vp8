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

## `widen_u8x16_to_i16x8_pair`

Purpose: convert one `u8x16` value into two `i16x8` values without changing lane
order or interpreting high-bit `u8` values as signed bytes. VP8 SAD, sub-pixel
filtering, true-motion prediction, residual math, and loop-filter conditions all
need `u8` pixels promoted to at least `i16` before subtracting or accumulating.

Contract:

- Input lane `0..7` becomes `result.low[0..7]`.
- Input lane `8..15` becomes `result.high[0..7]`.
- Each output lane is zero-extended: input `255u8` becomes `255i16`, not `-1`.
- The helper takes a vector value rather than a pointer so callers can pair it
  with either aligned or unaligned load helpers.
- Current implementation stores the `u8x16` into a local lane array, widens each
  lane explicitly, and reloads two `i16x8` vectors. This documents the desired
  semantics while UYA lacks a direct vector widen builtin.

Fallback and testing:

- Scalar fallback is two eight-lane loops with unsigned-to-signed promotion.
- `src/vp8_kernels_simd_test.uya` verifies low/high lane order and high-bit
  inputs (`128..255`) promote to positive `i16` values.
- `docs/simd_gaps.md` still records native vector widening as an upstream UYA
  compiler gap; replacing this helper with a builtin must preserve the same
  zero-extension contract.

## `narrow_i16x16_to_u8x16_sat`

Purpose: convert one `i16x16` value into one `u8x16` value with VP8 pixel clamp
semantics. This is the vector-value counterpart to the scalar `clip_u8` path
used after prediction, inverse transform residual addition, and loop-filter
updates.

Contract:

- Each input lane is independently clamped to `[0, 255]`.
- Negative values become `0u8`.
- Values in `[0, 255]` preserve their numeric value.
- Values above `255` become `255u8`.
- Lane order is unchanged: input lane `N` becomes output lane `N`.
- The helper takes and returns vector values. Storing the result is a separate
  operation so callers can choose aligned, unaligned, or scatter writes.
- Current implementation stores `i16x16` lanes to a local array, applies the
  scalar clamp per lane, and reloads `u8x16`. This captures the contract while
  UYA lacks direct narrow/convert and unsigned saturation builtins.

Fallback and testing:

- Scalar fallback is sixteen independent clamp-and-cast operations.
- `src/vp8_kernels_simd_test.uya` verifies negative, in-range, boundary, and
  above-range values.
- Existing `store_clipped_i16x16_to_u8` now reuses this helper before doing an
  unaligned 16-byte store.

## `absdiff_u8x16`

Purpose: compute per-lane absolute pixel differences for two `u8x16` values.
This is the primitive needed by SAD, variance, loop-filter threshold checks, and
mode-search costs when the source and predictor pixels are already loaded as
vectors.

Contract:

- Output lane `N` is `abs(a[N] - b[N])`.
- Inputs are interpreted as unsigned pixels, so `abs(0u8 - 255u8)` is `255u8`.
- The helper never wraps through unsigned subtraction; it promotes each lane
  before subtracting.
- Lane order is unchanged.
- The result is representable in `u8` because the maximum pixel difference is
  255.
- Current implementation stores both vectors to local arrays, computes each
  lane with `i16` intermediates, and reloads `u8x16`. A future unsigned absdiff
  builtin or target-specific intrinsic must preserve the same unsigned
  interpretation.

Fallback and testing:

- Scalar fallback is sixteen unsigned pixel differences.
- `src/vp8_kernels_simd_test.uya` covers equal lanes, increasing differences,
  decreasing differences, and 0/255 extremes.

## `sad_u8x16`

Purpose: compute the sum of absolute differences for two `u8x16` vectors. This
is the row-level building block for VP8 16-pixel-wide SAD and a reusable
primitive for mode-search and motion-search cost functions.

Contract:

- The result is `sum(abs(a[N] - b[N]))` for lanes `0..15`.
- Inputs are interpreted as unsigned pixels.
- The maximum result is `16 * 255 = 4080`, so `u32` is used for easy accumulation
  into larger block SAD totals.
- Lane order does not matter for the final sum, but the helper delegates lane
  difference semantics to `absdiff_u8x16`.
- Current implementation stores the absdiff vector into a local lane array and
  accumulates in scalar `u32`. A future horizontal reduce or target intrinsic
  may replace this if it preserves the same unsigned-pixel sum.

Fallback and testing:

- Scalar fallback is `absdiff_u8x16` followed by sixteen `u32` additions.
- `src/vp8_kernels_simd_test.uya` checks a mixed high/low input vector with a
  known total.
- `sad_row_16_u8x16` now uses this helper for the 16-wide row case.

## `transpose_4x4_i16`

Purpose: transpose a row-major 4x4 block carried in one `i16x16` value. VP8
transform code repeatedly crosses between row and column passes, so this helper
defines the exact lane mapping that a future shuffle-based implementation must
preserve.

Contract:

- Input lane `row * 4 + col` becomes output lane `col * 4 + row`.
- Both input and output are row-major 4x4 layouts.
- All values are copied exactly; no arithmetic, clamping, or rounding occurs.
- Current implementation stores to a local 16-lane array and performs explicit
  gather/scatter because UYA does not yet expose vector shuffle/permute.

Fallback and testing:

- Scalar fallback is the same nested 4x4 copy.
- `src/vp8_kernels_simd_test.uya` verifies a block with distinct row/column
  values, making lane swaps visible.
- The helper is intended for transform staging. Refactoring existing DCT/IDCT
  code to use it can be done after benchmark/codegen evidence shows the helper
  is not adding extra hot-path cost.

## `filter6_u8x16`

Purpose: apply one VP8 six-tap luma sub-pixel filter to sixteen independent
output lanes. Horizontal filtering supplies six overlapping row vectors;
vertical filtering supplies the same column span from six neighboring rows.

Contract:

- Inputs `tap0..tap5` contain the six filter taps for output lanes `0..15`.
- `filter_index` selects VP8 sub-pixel filter `0..7`; values above `7` clamp to
  filter `7`, matching the existing scalar/SIMD offset guard.
- Each output lane computes
  `(64 + tap0*c0 + tap1*c1 + tap2*c2 + tap3*c3 + tap4*c4 + tap5*c5) >> 7`.
- The rounded value is clamped to `[0, 255]` before becoming `u8`.
- Lane order is unchanged, so output lane `N` uses tap lane `N` from every input
  vector.
- Current implementation stores each vector to local lanes, applies the six
  coefficients per lane, and reloads `u8x16`. This keeps the contract explicit
  while UYA lacks vector widening, multiply-accumulate, and shuffle helpers.

Fallback and testing:

- Scalar fallback is sixteen independent VP8 six-tap filter calculations with
  the same rounding and clamp.
- `src/vp8_kernels_simd_test.uya` covers negative coefficients, clipping at both
  pixel bounds, and mixed lane values.
- `predict_luma_subpixel_horizontal_u8x16` and
  `predict_luma_subpixel_vertical_u8x16` now use this helper for full 16-lane
  spans and keep the existing 4-lane/tail paths for smaller blocks.

## `loopfilter_edge_u8x16`

Purpose: apply the VP8 simple loop filter edge update to sixteen independent
lanes. Each lane represents one p1/p0/q0/q1 neighborhood crossing an edge; the
helper returns the updated p0/q0 vectors while leaving p1/q1 unchanged.

Contract:

- Inputs `p1`, `p0`, `q0`, and `q1` contain corresponding edge neighborhoods in
  lanes `0..15`.
- A lane is filtered only when
  `2 * abs(p0 - q0) + (abs(p1 - q1) >> 1) <= limit`.
- Lanes that do not pass the edge predicate return their original p0/q0 values.
- Passing lanes use the VP8 simple edge update:
  `filter = signed_clamp(signed_clamp(p1 - q1) + 3 * (q0 - p0))`, then p0/q0
  are adjusted with `signed_clamp(filter + 3) >> 3` for p0 and
  `signed_clamp(filter + 4) >> 3` for q0, then clipped to `[0, 255]`.
- The result is a `LoopFilterEdgeResultU8x16` carrying updated `p0` and `q0`
  vectors. Lane order is unchanged.
- Current implementation stores the four inputs to local lane arrays and applies
  the scalar edge update per lane. This defines behavior while UYA lacks vector
  compare masks and saturating signed-byte arithmetic.

Fallback and testing:

- Scalar fallback is sixteen calls to the existing simple loop-filter sample
  update.
- `src/vp8_kernels_simd_test.uya` checks mixed passing/failing lanes with known
  p0/q0 outputs.
- `loop_filter_simple_vertical_edge_u8x16` and
  `loop_filter_simple_horizontal_edge_u8x16` now use this helper for full
  16-lane spans. Normal and macroblock loop-filter helpers still use their
  wider p3..q3 scalar-lane logic until a separate wide-edge contract is defined.
