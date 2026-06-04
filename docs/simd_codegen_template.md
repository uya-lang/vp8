# SIMD C/assembly check template

This template is the repeatable checklist for every portable SIMD helper or
kernel before it is used as default-dispatch evidence. The generated snapshot
report lives in `docs/simd_codegen.md`; this file records how to extend and read
that report.

## Scope

- Source under test: `src/vp8_kernels_simd_test.uya`.
- Generator/checker: `tools/check_simd_codegen.py`.
- Reproduction command: `make check-simd-codegen`.
- Generated C snapshot: `build/simd-codegen/vp8_kernels_simd_test.c`.
- Generated assembly snapshot: `build/simd-codegen/vp8_kernels_simd_test.s`.
- Report: `docs/simd_codegen.md`.

## Add A Helper Or Kernel

1. Add or update a focused runtime test in `src/vp8_kernels_simd_test.uya`.
2. Add the exported helper to `HELPERS` or the exported kernel to `SIMD_KERNELS`
   in `tools/check_simd_codegen.py`.
3. For helpers, list the vector structs that must appear in the generated C
   signature or body. Use the existing `vector_structs` entries as examples.
4. Run `make check-simd-codegen`.
5. Keep `docs/simd_codegen.md` updated from the generated report.
6. Record the helper contract in `docs/simd_helper_design.md` when the item is a
   reusable primitive.

## Minimum Evidence

Each checked item needs:

- A stable generated C symbol.
- A matching assembly label from the C snapshot.
- A runtime test that exercises the exported helper or a kernel path using it.
- A short note in `docs/simd_codegen.md` describing current lowering risk.
- A benchmark threshold entry before the item can be used to justify default
  SIMD dispatch.

## C Snapshot Review

When reviewing `build/simd-codegen/vp8_kernels_simd_test.c`, check:

- Whether `@vector.load` and `@vector.store` lower through `__uya_memcpy`.
- Whether lane loops allocate large temporary arrays in hot paths.
- Whether helper calls remain visible or are duplicated unexpectedly.
- Whether scalar tails stay bounded by block width/height.
- Whether generated signatures still use the expected vector structs.

## Assembly Snapshot Review

When reviewing `build/simd-codegen/vp8_kernels_simd_test.s`, check:

- The helper/kernel label appears exactly enough to prove the symbol was emitted.
- The `__uya_memcpy` count did not jump in a way that contradicts the helper
  contract.
- No default-dispatch decision is made from labels alone; labels prove emission,
  not speed.
- If compiler flags, optimization level, or UYA lowering changes, regenerate the
  report before using older conclusions.

## Failure Handling

- Missing C symbol: add the export to the test source or the checker table, then
  rerun.
- Missing vector struct: inspect the generated signature/body and update the
  helper contract or checker entry.
- Missing assembly label: confirm C generation succeeded and the C compiler
  produced the requested assembly snapshot.
- Unexpected `__uya_memcpy` growth: leave SIMD disabled by default until a
  benchmark threshold shows the path is still worthwhile.
