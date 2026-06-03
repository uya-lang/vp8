# Tests

This directory is reserved for UYA unit tests, golden conformance checks, and
malformed-input smoke tests.

Current validation is driven by `make test`, which runs UYA unit tests and an
end-to-end tiny IVF MD5 check. `tests/tiny_ivf_md5.py` generates five built-in
IVF samples under `build/tiny-md5/`, decodes them with `build/vp8uya`, and
compares the YUV output with golden MD5 values.

Future tests should keep external codec tools optional. Built-in tests must run
without libvpx, FFmpeg, or network access; differential tests may live behind
separate make targets.
