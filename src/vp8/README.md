# VP8 Module Root

This directory is reserved for pure UYA VP8 runtime modules.

Planned submodules follow the layout in `docs/design.md`: bitstream readers,
container parsing, decoder state, scalar kernels, encoder support, and SIMD
dispatch. The current scaffold does not expose real VP8 parsing, decoding, or
encoding behavior yet.
