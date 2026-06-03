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
