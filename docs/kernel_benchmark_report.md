# Kernel benchmark report

Date: 2026-06-04

This report records the current smoke-level scalar-vs-forced-SIMD benchmark
evidence for the VP8 decoder, encoder, and motion-search kernel harnesses. It
is a release-hardening snapshot, not a default-dispatch enablement decision.

## Scope

The benchmark smoke target runs three harnesses:

```sh
python3 bench/decode_bench.py --repeats 1 --warmups 0 build/vp8uya build/bench
python3 bench/encode_bench.py --group smoke --repeats 1 --warmups 0 build/vp8uya build/bench-encode
python3 bench/motion_search_bench.py --repeats 3 --warmups 0 --iterations 1 build/vp8_motion_search_bench build/bench-motion-search
```

All harnesses report wall-clock timings. `cycles_per_second` is set to
`1_000_000_000.0`, so `cycles_per_pixel` and `cycles_per_candidate` are derived
from elapsed nanoseconds. They are comparable smoke metrics, not hardware cycle
counter readings.

## Decode smoke

`decode_bench.py` generated eight tiny IVF samples and decoded each sample once
with `--force-scalar` and once with `--force-simd`. Each scalar/SIMD pair
produced the same YUV MD5. All reported rows had `allocation_count=0`,
`hot_loop_heap_allocation_count=0`, and `bytes_copied_per_frame=0.0`; every
frame stat also reported `bytes_copied_for_ref_refresh=0`.

| Sample | Scalar median ns | SIMD median ns | Speedup |
| --- | ---: | ---: | ---: |
| gray-16x16 | 2073109 | 1739243 | 1.192 |
| u-dc-16x16 | 1569880 | 1453184 | 1.080 |
| v-dc-16x16 | 1563411 | 1670626 | 0.936 |
| gray-32x16 | 1664644 | 1629139 | 1.022 |
| gray-17x17 | 1559596 | 1513205 | 1.031 |
| inter-copy-16x16 | 1577297 | 1596404 | 0.988 |
| segmentation-zero-16x16 | 1590557 | 1562424 | 1.018 |
| multi-token-4-16x64 | 1816419 | 1698138 | 1.070 |

Interpretation: the tiny decode set confirms bit-exact output, zero hot-loop
heap allocation, and no reference-refresh frame copy in both forced modes. It
does not establish a stable end-to-end decoder default-SIMD win: several tiny
samples are faster under forced SIMD, while `v-dc-16x16` and
`inter-copy-16x16` are slower in this run.

## Encode smoke

`encode_bench.py --group smoke` generated one deterministic I420 input and ran
the encoder once per forced mode.

| Sample | Mode | Median ns | FPS | cycles/pixel | Work units | IVF bytes | IVF MD5 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| gradient-32x16 | scalar | 3923855 | 254.851 | 7663.779 | 244 | 524 | d51585b5ac8b0a75327806b7f6454c08 |
| gradient-32x16 | simd | 3723096 | 268.594 | 7271.672 | 244 | 524 | d51585b5ac8b0a75327806b7f6454c08 |

The scalar and forced-SIMD bitstreams were identical, mode-search work units
matched, and smoke speedup was `1.054`. This is useful regression evidence for
the current encoder path, but one 32x16 smoke sample is not enough to claim a
default encoder SIMD policy.

## Motion-search smoke

`motion_search_bench.py` measures the integer-pel motion-search SAD hotspot in
the repository-local `vp8_motion_search_bench` binary.

| Mode | Candidates | Median ns | ns/candidate | cycles/candidate | Checksum |
| --- | ---: | ---: | ---: | ---: | ---: |
| scalar | 10404 | 33903204 | 3258.670 | 3258.670 | 9436896 |
| simd | 10404 | 5567600 | 535.140 | 535.140 | 9436896 |

The comparison reported `same_work=1`, speedup `6.089`, and required minimum
speedup `1.050`. This is strong smoke evidence that the SAD hotspot benefits
from the current forced-SIMD path while preserving the candidate count and
checksum.

## Threshold policy

`bench/kernel_thresholds.json` keeps all default dispatcher entries under
`disabled_until_threshold_passes`. Its default-enable gates require bit-exact
output, code generation evidence, and benchmark evidence. The configured
minimum speedups are:

| Class | Minimum speedup to default-enable | Minimum repeats | Warmups |
| --- | ---: | ---: | ---: |
| memory | 1.10 | 5 | 1 |
| compute | 1.25 | 5 | 1 |
| end_to_end_decoder | 0.95 | 5 | 1 |

The table also reserves disabled benchmark targets for the current SIMD helper
backlog: unaligned load/store, widening, saturated narrowing, absdiff, SAD,
4x4 transpose, six-tap filtering, and simple loop-filter edge updates. These
entries are not default-dispatch approval; they define the measurement units and
minimum evidence needed before any helper-backed dispatcher path can be enabled.

This smoke run uses fewer repeats and smaller synthetic samples than the
threshold table requires for default dispatch. The motion-search hotspot clears
its smoke threshold by a wide margin, but the decode and encode smoke results
should be treated as correctness and trend evidence only.

## Verification

This report uses a `make bench-smoke` run that passed on 2026-06-04.
