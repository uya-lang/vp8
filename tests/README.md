# Tests

This directory is reserved for UYA unit tests, golden conformance checks, and
malformed-input smoke tests.

Current validation is driven by `make test`, which runs UYA unit tests and an
end-to-end tiny IVF MD5 check. `tests/tiny_ivf_md5.py` generates six built-in
IVF samples, including a key+inter sample, under `build/tiny-md5/`, decodes
them with `build/vp8uya`, and compares the YUV output with golden MD5 values.
`make test-decoder-scalar` runs the same decoder suite with
`VP8UYA_FORCE_SCALAR=1` as the scalar reference gate.
Fixture metadata is tracked in `fixtures/manifest.json`; generated binary
outputs remain under ignored build directories.
`make test-keyframe-md5` filters the manifest to key-frame MD5 samples.
`make test-vpxdiff` optionally compares compatible manifest samples with
`vpxdec`; it skips cleanly when libvpx tools are unavailable.

Future tests should keep external codec tools optional. Built-in tests must run
without libvpx, FFmpeg, or network access; differential tests may live behind
separate make targets.
