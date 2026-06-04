# Decoder conformance report

Date: 2026-06-04

This report records the current decoder conformance evidence for the
release-hardening phase. The built-in suite is self-contained and does not
require libvpx, FFmpeg, or network access.

## Verification commands

The following commands were run on 2026-06-04:

```sh
make test
make check
make test-vpxdiff
```

Results:

| Command | Result | Notes |
| --- | --- | --- |
| `make test` | passed | Runs unit tests, built-in decoder golden checks, malformed input checks, fuzz smoke, WebM subset decode, scalar-vs-SIMD compare, and single-vs-multithread compare. |
| `make check` | passed | `uya check src/main.uya` completed type checking. |
| `make test-vpxdiff` | skipped cleanly | Current machine does not have `vpxdec`; output was `skip: vpxdec not found`. |

## Golden IVF samples

`fixtures/manifest.json` defines eight generated IVF samples. `make test`
regenerates these samples under `build/tiny-md5/`, decodes them through the CLI,
and compares YUV MD5 values against the tracked manifest.

| Sample | Groups | Size | IVF frames | Output frames | YUV bytes | YUV MD5 |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| gray-16x16 | tiny,key | 16x16 | 1 | 1 | 384 | 02b5d5d5ba2a5de00017b31c40c527bc |
| u-dc-16x16 | tiny,key | 16x16 | 1 | 1 | 384 | 02b5d5d5ba2a5de00017b31c40c527bc |
| v-dc-16x16 | tiny,key | 16x16 | 1 | 1 | 384 | 02b5d5d5ba2a5de00017b31c40c527bc |
| gray-32x16 | tiny,key | 32x16 | 1 | 1 | 768 | e979abdb2b582b325de6f5bb97b0e643 |
| gray-17x17 | tiny,key,non16 | 17x17 | 1 | 1 | 451 | 2671dd258a7442dc814db1376ce7682d |
| inter-copy-16x16 | tiny,inter | 16x16 | 2 | 2 | 768 | e979abdb2b582b325de6f5bb97b0e643 |
| segmentation-zero-16x16 | tiny,key,segmentation | 16x16 | 1 | 1 | 384 | 02b5d5d5ba2a5de00017b31c40c527bc |
| multi-token-4-16x64 | tiny,key,token-partition | 16x64 | 1 | 1 | 1536 | fe9733a1ef21e979fbd8b00080423cf3 |

Coverage represented by these samples:

- key-frame decode and visible I420 output
- one zero-motion inter-frame sequence
- non-16-aligned visible crop
- segmentation enabled with zero deltas
- four token partitions

## Forced mode and threading checks

`make test-scalar-vs-simd` decoded all eight manifest samples with
`--force-scalar` and `--force-simd`. Every scalar MD5 matched the forced-SIMD
MD5 and the expected manifest MD5.

`make test-single-vs-multithread` decoded the same eight samples with
`--threads 1` and `--threads 4`. Every four-thread MD5 matched the single-thread
MD5 and the expected manifest MD5.

These checks prove bit-exact output for the generated manifest set across the
current forced-mode and worker-count switches. They do not prove complete VP8
bitstream coverage.

## WebM subset

`make test-webm-subset-decode` generated a minimal WebM VP8 subset sample from
the `gray-16x16` VP8 payload. The decoded YUV output was 384 bytes with MD5
`02b5d5d5ba2a5de00017b31c40c527bc`, matching the IVF golden for the same VP8
payload.

This validates the current minimal WebM subset demuxer path for one supported
VP8 SimpleBlock sample. It is not broad WebM container conformance.

## Malformed and fuzz coverage

The built-in malformed corpus is generated at test time:

| Corpus | Cases | Gate |
| --- | ---: | --- |
| malformed IVF | 7 | `info` and `decode` must return controlled errors. |
| malformed VP8 payloads in valid IVF | 6 | `info` must still succeed; `decode` and `decode-frame` must return controlled errors. |

`make test-multithread-malformed` reran the malformed IVF and malformed VP8
commands with `--threads 4` and per-command timeouts; all cases completed
without timeout.

`make test-fuzz-smoke` used seed `5656632`, generated 32 random raw IVF blobs
and 32 valid IVF containers with random VP8 payloads, and exercised 96 CLI
commands. The target accepts only success or controlled error exits.

## Optional libvpx differential status

`make test-vpxdiff` is the optional external differential gate. It requires
`vpxdec` and `vpxenc`; the current machine did not have `vpxdec`, so the target
reported `skip: vpxdec not found` and exited successfully.

Current tracked manifest samples do not mark any `vpxdec_compatible` entries.
The optional path can still generate a small `vpxenc-gray-16x16` stream when
both libvpx tools are available, then compare `vp8uya` YUV output against
`vpxdec`.

## Current boundary

The current decoder conformance evidence is enough to guard the supported tiny
fixture shapes, forced scalar/SIMD equivalence on those shapes, four-thread
determinism on those shapes, minimal WebM subset demuxing for one VP8 payload,
and controlled failures for the generated malformed/fuzz corpus.

It is not a full VP8 conformance suite. Missing coverage includes broad
third-party VP8 streams, large-resolution inter content, rich motion-vector
patterns, non-zero segmentation deltas, all token partition combinations across
larger frame grids, complete WebM container behavior, and libvpx differential
evidence on this host.
