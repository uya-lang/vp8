# Fuzz corpus minimization

Date: 2026-06-04

The deterministic fuzz smoke target currently generates 32 raw IVF byte blobs
and 32 valid IVF containers with random VP8 payloads from seed `5656632`. That
produces 64 generated files and 96 CLI commands.

The 2026-06-04 run collapsed to three distinct command outcome classes:

| Class | Count | Result |
| --- | ---: | --- |
| raw IVF `info` | 32 | exit `2`, `error: invalid IVF header` |
| random-payload IVF `info` | 32 | exit `0`, `ivf.payloads=1` |
| random-payload IVF `decode` | 32 | exit `2`, `error: failed to decode VP8 frame` |

The minimized corpus in `fixtures/fuzz_minimized/manifest.json` keeps one
small representative for each outcome class:

| Case | Bytes | Commands | Covered class |
| --- | ---: | ---: | --- |
| `raw-invalid-header-min` | 1 | 1 | invalid raw IVF header |
| `valid-ivf-empty-payload-min` | 44 | 2 | valid IVF metadata plus controlled VP8 decode failure |

`make test-fuzz-minimized` materializes those two cases under
`build/fuzz-minimized/`, runs the three commands, and writes
`build/fuzz-minimized/report.json`.

Verification on 2026-06-04:

| Command | Result |
| --- | --- |
| `make test-fuzz-minimized` | passed |
| `make test-fuzz-smoke` | passed |

This minimized corpus is a regression seed set, not a replacement for
`make test-fuzz-smoke`. The random smoke target remains in `make test` to keep
sampling more input shapes, while the minimized corpus provides a compact
failure-class guard that is easier to inspect and preserve.
