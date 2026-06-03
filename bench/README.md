# Benchmarks

This directory contains benchmark harnesses, baseline records, and performance
notes.

Benchmarks must not be required for normal correctness tests. Scalar and SIMD
paths should use comparable inputs and report enough context to explain runtime
changes, allocation behavior, and memory bandwidth-sensitive paths.

`decode_bench.py` benchmarks built-in IVF decode samples through both
`--force-scalar` and `--force-simd`, validates YUV MD5, and writes
`results.ndjson` plus `summary.json` under the selected output directory.

Use `make bench-smoke` for a quick single-repeat validation, or
`make bench-decode` for the default repeated decode benchmark.

`kernel_thresholds.json` defines the default-enable gates for future SIMD
kernel benchmarks. `make check-kernel-thresholds` validates the table. The
speedup metric is `scalar_median_ns / simd_median_ns`; memory-bound kernels must
reach 1.10x, compute-heavy kernels must reach 1.25x, and the end-to-end decoder
forced-SIMD path must not be more than 5% slower than forced scalar. Every
default-enabled kernel also needs bit-exact output, codegen inspection, and
benchmark evidence.
