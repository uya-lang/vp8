# Tests

This directory is reserved for UYA unit tests, golden conformance checks, and
malformed-input smoke tests.

Current validation is driven by `make test`, which runs UYA unit tests and an
end-to-end tiny IVF MD5 check. `tests/tiny_ivf_md5.py` generates eight built-in
IVF samples, including key+inter, segmentation, and multi-token partition
samples, under `build/tiny-md5/`, decodes them with `build/vp8uya`, and
compares the YUV output with golden MD5 values. It also runs generated
malformed IVF and malformed VP8 payload corpus checks plus deterministic fuzz
smoke.
`make test-decoder-scalar` runs the same decoder suite with
`VP8UYA_FORCE_SCALAR=1` as the scalar reference gate.
Fixture metadata is tracked in `fixtures/manifest.json`; generated binary
outputs remain under ignored build directories.
`make test-keyframe-md5` filters the manifest to key-frame MD5 samples.
`make test-inter-md5` filters the manifest to inter-frame MD5 samples.
`make test-non16-md5` filters the manifest to non-16-aligned MD5 samples.
`make test-segmentation-md5` filters the manifest to segmentation MD5 samples.
`make test-token-partition-md5` filters the manifest to multi-token-partition
MD5 samples.
`make test-malformed-ivf` generates malformed IVF cases from
`fixtures/malformed_ivf/manifest.json` and checks `info`/`decode` return
controlled errors instead of crashing.
`make test-malformed-vp8` wraps malformed VP8 payloads in valid IVF containers,
checks `info` still succeeds, and checks `decode`/`decode-frame` return
controlled errors instead of crashing.
`make test-fuzz-smoke` generates deterministic random IVF blobs and valid IVF
containers with random VP8 payloads, accepting only success or controlled error
exits.
`make test-vpxdiff` optionally compares compatible manifest samples with
`vpxdec`; it skips cleanly when libvpx tools are unavailable.

Future tests should keep external codec tools optional. Built-in tests must run
without libvpx, FFmpeg, or network access; differential tests may live behind
separate make targets.
