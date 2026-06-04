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
