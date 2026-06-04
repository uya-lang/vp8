# High-risk checklist evidence

This document records the concrete evidence used to close items in the high-risk
checklist in `docs/todo.md`.

## Bool Reader Carry/Renormalize

Status: passed.

Evidence:

- `src/vp8/bitstream/bool_reader.uya` uses the VP8 split formula
  `1 + (((range - 1) * probability) >> 8)` and renormalizes while `range < 128`.
- Existing reader tests cover probability split math, MSB-first literals,
  overread boundaries, stable offsets after failed overread, trace offsets, and
  a libvpx boolhuff small sample.
- `src/vp8_bitstream_bool_writer_test.uya` now includes a carry-producing stream
  test: writing forty `1` bits at probability 128 produces the known
  `0xfe 0xff 0xff 0xff 0xff 0x02 0x00` style carry output, then the bool reader
  reads back forty `1` bits across the renormalized byte stream.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_bitstream_bool_reader_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_bitstream_bool_writer_test.uya`
