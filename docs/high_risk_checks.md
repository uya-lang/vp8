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

## Partition Size Boundaries

Status: passed.

Evidence:

- `parse_vp8_frame_tag_checked` rejects inter-frame first partitions whose
  declared size exceeds the remaining payload.
- Key-frame size validation accounts for the 10-byte key-frame header before
  checking first partition bytes.
- `parse_vp8_token_partition_readers` rejects first partition offsets beyond the
  payload, first partition end beyond the payload, token size table overrun, and
  declared token partition lengths that exceed remaining token bytes.
- Encoder partition output tests cover multi-partition size table writing,
  single token partition mode without a size table, non-zero output offsets, and
  decoder-side reader reconstruction from the packed payload.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_bitstream_header_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_partition_output_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_token_partition_packing_test.uya`

## Key Frame Probability Reset And Reference Refresh

Status: passed.

Evidence:

- `parse_vp8_frame_probability_updates(reader, probs, true)` calls
  `reset_vp8_key_frame_probs` before reading coefficient probability updates and
  returns before reading motion-vector probability updates, so key frames do not
  inherit stale inter-frame entropy state.
- `decoder_decode_frame` snapshots the decoder probability arrays, passes the
  key-frame flag into probability parsing, and stores the reset arrays back into
  the decoder before mode/token parsing uses them.
- `decoder_decode_frame` refreshes last, golden, and altref references after a
  successfully reconstructed key frame by calling
  `frame_pool_refresh_references(..., true, true, true)`.
- `src/vp8_decoder_scalar_test.uya` now pollutes decoder probability state,
  decodes a minimal key frame, and checks that y/uv/coeff/mv probabilities match
  VP8 defaults and that last/golden/altref all alias the current frame without
  reference-refresh copies.
- Existing frame-pool and encoder-reference-pool tests cover logical reference
  aliasing, ref counts, current-slot selection, and zero-copy refresh semantics.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_decoder_scalar_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_bitstream_header_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_frame_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_reference_pool_test.uya`
