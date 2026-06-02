# Tests

This directory is reserved for UYA unit tests, golden conformance checks, and
malformed-input smoke tests.

Current scaffold validation is driven by `make test`, which verifies that the
CLI builds and that placeholder commands return controlled status codes. These
checks do not claim real VP8 parsing or decoding coverage.

Future tests should keep external codec tools optional. Built-in tests must run
without libvpx, FFmpeg, or network access; differential tests may live behind
separate make targets.
