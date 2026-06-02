# Benchmarks

This directory is reserved for benchmark harnesses, baseline records, and
performance notes.

Benchmarks must not be required for normal correctness tests. Scalar and SIMD
paths should use comparable inputs and report enough context to explain runtime
changes, allocation behavior, and memory bandwidth-sensitive paths.

The current scaffold has no real VP8 codec hot path to benchmark yet.
