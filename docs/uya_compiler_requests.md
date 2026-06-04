# UYA compiler SIMD requests

This file records VP8-driven requests for the UYA compiler. Each request is
written as a concrete builtin or lowering contract so it can become either a
compiler issue or an implementation task without re-deriving the VP8 need.

Default VP8 dispatch remains scalar unless the affected path also has
byte-exact tests, generated C/assembly inspection, and benchmark threshold
evidence.

## Vector Shuffle / Permute

Requested capability:

- A vector lane permute builtin such as
  `@vector.shuffle(T, N, value: @vector(T, N), indices: [usize: N]) @vector(T, N)`,
  or an equivalent form that can be constant-folded by the compiler.
- A two-input variant for sliding windows is also useful:
  `@vector.shuffle2(a, b, indices)` where indices `0..N-1` select lanes from
  `a` and `N..(2*N-1)` select lanes from `b`.
- Indices should be compile-time constants for the first implementation. That is
  enough for VP8 transpose, six-tap windows, and loop-filter neighborhoods.

VP8 blockers:

- `transpose_4x4_i16` currently stores a whole `i16x16` block to a local array
  and reloads after scalar gather/scatter.
- `filter6_u8x16` can use overlapping loads for full 16-pixel spans, but a
  shuffle/slide primitive would avoid repeated scalar lane staging for narrower
  blocks and target-specific rewrites.
- Vertical loop-filter edges still gather lanes through local arrays because
  neighboring edge samples are not naturally contiguous in vector lane order.

Expected semantics:

- Lane `i` in the result receives lane `indices[i]` from the input vector for
  one-input shuffle.
- For two-input shuffle, lane `i` receives from `a[indices[i]]` when
  `indices[i] < N`, otherwise from `b[indices[i] - N]`.
- Out-of-range indices must be a compile-time error, not runtime undefined
  behavior.
- The operation must preserve lane element type and vector width.

Suggested VP8 regression tests:

- 4x4 `i16x16` transpose: `[0,1,2,3,10,...,33]` becomes
  `[0,10,20,30,1,11,...,33]`.
- `u8x16` lane slide by one byte across two adjacent vectors.
- Mixed low/high lane selection to prove the generated C does not accidentally
  reverse lane order.

Fallback status in this repository:

- `docs/simd_helper_design.md` records the current scalar-lane helper contracts.
- `docs/simd_codegen.md` records that these helpers generate stable symbols but
  are not default-dispatch evidence by themselves.

## Vector Widening / Narrowing

Requested capability:

- Unsigned widen from narrow pixel lanes to wider signed or unsigned lanes, for
  example `u8x16 -> i16x16` or low/high `u8x16 -> i16x8` halves.
- Signed widen for transform and residual paths, for example `i16x8 -> i32x8`
  or low/high `i16x16 -> i32x8` halves.
- Narrow or pack operations that explicitly state whether they truncate, clamp,
  or saturate. VP8 needs the non-wrapping saturating forms for final pixel
  writes, but a separate truncating builtin can still be useful when callers
  have already proven range.
- A type-directed syntax such as `@vector.widen(Tout, value)` and
  `@vector.narrow(Tout, value)`, or named unsigned/signed variants if that is
  easier for type checking.

VP8 blockers:

- `widen_u8x16_to_i16x8_pair` currently stores the input vector to a local array
  and manually zero-extends each lane into two `i16x8` halves.
- `filter6_u8x16` and loop-filter helpers need `u8 -> i16/i32` intermediates
  before subtracting or multiplying by signed coefficients.
- `narrow_i16x16_to_u8x16_sat` currently performs scalar lane clamps and reloads
  a `u8x16` value before storing.
- Residual add and transform output paths cannot express a native vector pack
  back to pixels.

Expected semantics:

- Unsigned widen must preserve high-bit pixels: `255u8` becomes `255i16`, not
  `-1i16`.
- Signed widen must sign-extend negative transform lanes.
- Narrow/truncate and narrow/saturate must be distinct operations or distinct
  modes; silent wraparound is not acceptable for VP8 pixel writes.
- Low/high half widening must preserve memory lane order so helper contracts can
  be swapped to native builtins without changing tests.

Suggested VP8 regression tests:

- `u8x16` values `0, 1, 127, 128, 255` widen to positive `i16` lanes.
- `i16x16` values below zero, in range, and above 255 narrow to `u8x16` only
  through the saturating form.
- `widen_u8x16_to_i16x8_pair` low/high lane order matches the existing helper
  test in `src/vp8_kernels_simd_test.uya`.
- Residual add clamp can replace scalar lane stores without changing byte-exact
  output.

Fallback status in this repository:

- `widen_u8x16_to_i16x8_pair` and `narrow_i16x16_to_u8x16_sat` define the current
  portable helper contracts.
- `bench/kernel_thresholds.json` keeps widening/narrowing helper-backed targets
  disabled until codegen and benchmark evidence pass.

## Saturating Arithmetic

Requested capability:

- Extend vector saturating operators or builtins to unsigned integer vectors,
  especially `u8x16` and `u16x8`.
- Provide explicit saturating narrow/pack forms such as
  `@vector.narrow_sat(u8, value)` for `i16/i32 -> u8` pixel writes.
- Keep signed saturating arithmetic for `i16/i32` vectors, which already works
  in current UYA tests, and add unsigned variants without changing signed
  behavior.
- If operator spelling stays as `+|`, `-|`, and `*|`, type checking should
  accept unsigned vectors with unsigned saturation bounds. Named builtins such as
  `@vector.add_sat_unsigned` are also acceptable if clearer.

VP8 blockers:

- `narrow_i16x16_to_u8x16_sat` currently clamps each lane with scalar branches
  before reloading a `u8x16`.
- Residual add, prediction, and loop-filter output paths repeatedly need pixel
  clamp semantics `[0, 255]`.
- Simple and normal loop filters need signed-byte clamps around intermediate
  filter values as well as unsigned pixel clamps on final writes.
- Current UYA negative coverage rejects unsigned vector saturating operators,
  so portable VP8 code cannot express native unsigned pixel saturation yet.

Expected semantics:

- `u8x16` saturating add clamps at `255`; for example `250 +| 10 == 255`.
- `u8x16` saturating subtract clamps at `0`; for example `5 -| 10 == 0`.
- Saturating narrow to `u8` maps negative values to `0`, values in range
  unchanged, and values above `255` to `255`.
- Signed vector saturation must keep signed min/max bounds and must not be
  reinterpreted as unsigned.
- Overflow behavior must be defined by the vector operation, not delegated to C
  signed-overflow or implementation-defined casts.

Suggested VP8 regression tests:

- Unsigned `u8x16` add/sub around `0`, `1`, `254`, and `255`.
- `i16x16 -> u8x16` saturating narrow over `-300, -1, 0, 1, 255, 256, 1024`.
- Residual add clamp and loopfilter edge helpers produce byte-exact output when
  scalar clamp helpers are replaced by native saturating operations.
- Existing signed saturating tests keep passing for `i16` / `i32` vectors.

Fallback status in this repository:

- `narrow_i16x16_to_u8x16_sat` and `loopfilter_edge_u8x16` are the current
  scalar-lane contracts for unsigned pixel saturation.
- `docs/simd_gaps.md` records the current unsigned saturating operator rejection
  evidence.
