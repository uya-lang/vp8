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

## Non-16 Right/Bottom Prediction Boundaries

Status: passed.

Evidence:

- `macroblock_grid_for_frame(17, 17)` rounds to a 2x2 macroblock grid, while
  `macroblock_grid_position` exposes the bottom-right macroblock as a clipped
  1x1 luma region and a 1x1 chroma region.
- Frame allocation keeps visible 17x17 luma and 9x9 chroma dimensions while
  retaining border storage, so full 16x16/8x8 reconstruction of cropped edge
  macroblocks stays inside allocated planes and output views expose only visible
  pixels.
- `src/vp8_decoder_scalar_test.uya` now constructs a 17x17 key frame with four
  macroblocks and checks the decoded visible crop directly: output dimensions
  are 17x17 luma and 9x9 chroma, and the right column, bottom row, bottom-right
  luma pixel, and bottom-right U/V pixels all contain the expected predictor
  value.
- `tests/tiny_ivf_md5.py` generates the tracked `gray-17x17` fixture by writing
  mode and token data for all four macroblocks, including the right, bottom, and
  bottom-right cropped macroblocks.
- `make test-non16-md5` verifies that `gray-17x17` decodes to 451 visible I420
  bytes with MD5 `2671dd258a7442dc814db1376ce7682d`; the same MD5 passed under
  forced SIMD.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_decoder_scalar_test.uya`
- `VP8UYA_FORCE_SCALAR=1 /media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_decoder_scalar_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_mb_grid_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_frame_test.uya`
- `make test-non16-md5`
- `VP8UYA_FORCE_SIMD=1 make test-non16-md5`

## Segmentation And Quant Delta Signs

Status: passed.

Evidence:

- `read_signed_value` reads magnitude bits followed by a sign bit and returns
  `-magnitude` when the sign bit is set.
- `parse_vp8_segmentation` uses 7-bit signed values for segment quantizer
  deltas and 6-bit signed values for segment loop-filter deltas.
- `src/vp8_bitstream_header_test.uya` now encodes a segmentation update-data
  header with mixed positive, negative, and omitted quant/filter deltas, then
  verifies the parser preserves `-7`, `9`, `-63`, `-5`, `12`, and `-31` in the
  expected slots.
- Existing quant-header parsing tests cover 4-bit signed frame quant deltas,
  including negative Y1 and UV deltas, while scalar dequant-factor tests cover
  signed delta application and clamping in the quant lookup path.
- Encoder segmentation policy tests preserve configured negative flat deltas
  and positive noisy deltas in `Vp8Segmentation`; current keyframe encoding
  writes segmentation disabled, so there is no encoder bitstream serialization
  path for non-zero segmentation deltas to audit yet.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_bitstream_header_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_bitstream_bool_reader_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_segmentation_policy_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_quantizer_delta_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_kernels_scalar_test.uya`
- `make test-segmentation-md5`

## Loop Filter Level Zero Skip

Status: passed.

Evidence:

- `build_loop_filter_thresholds(0, ...)` returns `enabled = false`.
- `decoder_apply_row_delayed_loop_filter` returns before row scheduling when
  thresholds are disabled, so neither normal nor simple row dispatchers run for
  level 0.
- `encoder_apply_key_frame_loop_filter` uses the same threshold helper and
  returns before normal/simple dispatch and before marking the frame border
  dirty when level 0 disables filtering.
- `src/vp8_encoder_loop_filter_test.uya` now fills normal and simple filter
  edge fixtures, applies level-0 decoder and encoder filtering, and checks the
  visible frame data remains byte-identical to the unfiltered reference. The
  encoder frames also remain border-clean, proving the skipped path avoids the
  post-filter dirty mark.
- Existing loop-filter level selection tests cover quantizer 0 producing VP8
  loop-filter level 0, and scalar filter tests cover active normal/simple
  filtering when the level is non-zero.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_loop_filter_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_kernels_scalar_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_loop_filter_level_test.uya`

## Simple Vs Normal Loop Filter Selection

Status: passed.

Evidence:

- `parse_vp8_loop_filter_header` reads the VP8 loop-filter type bit into
  `Vp8LoopFilterHeader.filter_type`, while header tests cover both type 0 and
  type 1 parsing.
- Decoder row-delayed filtering enables the normal dispatcher only when
  thresholds are enabled and `filter_type == 0`, and enables the simple
  dispatcher only when thresholds are enabled and `filter_type != 0`.
- Encoder key-frame filtering uses the same type split before dispatch:
  type 0 runs the normal Y/UV macroblock and subblock filters, while type 1
  runs the simple Y-only dispatcher.
- `src/vp8_decoder_scalar_test.uya` proves the row-delayed decoder normal path
  filters luma and chroma edges, and the simple path filters luma while leaving
  U/V edge samples untouched.
- `src/vp8_encoder_loop_filter_test.uya` compares encoder key-frame filtering
  against decoder row-delayed filtering for both filter types. The normal test
  observes changed Y/U/V edge samples; the simple test observes changed Y
  samples and untouched chroma samples.
- Encoder loop-filter level tests cover the selector that emits type 0 for the
  default path and type 1 when high quantizer simple filtering is preferred.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_loop_filter_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_decoder_scalar_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_bitstream_header_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_loop_filter_level_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_kernels_scalar_test.uya`

## Y2 Block Mode Selection

Status: passed.

Evidence:

- VP8 residue syntax uses a Y2 block for macroblocks that are not intra
  `B_PRED` and are not inter `SPLITMV`. The supported decoder inter path is
  non-split, so inter-coded macroblocks now read Y2 before Y1 tokens.
- Key-frame token decode already gates Y2 on `y_mode != VP8_Y_MODE_B`; the
  accompanying Y1 blocks use block type 0 from position 1 when Y2 is present
  and block type 3 from position 0 for `B_PRED`.
- Inter-frame token decode now uses the same predicate for current-frame intra
  macroblocks, and treats supported non-current inter macroblocks as Y2-bearing.
  It clears/stores Y2 summaries, updates Y contexts with either Y1 coefficients
  or non-zero Y2 DC, and reconstructs Y blocks with optional Y2 DC.
- `src/vp8_decoder_scalar_test.uya` now builds a key-frame `B_PRED` macroblock
  whose token stream contains no Y2 block and whose first luma DC coefficient is
  decoded from Y1. The test checks the decoded y mode, all 16 B modes, and the
  reconstructed luma/chroma samples.
- The same decoder test now builds an inter LAST/ZERO-MV macroblock with a
  non-zero Y2 token followed by Y1 EOB tokens from position 1. The decoded
  reference prediction gains the expected luma residual while chroma stays
  unchanged.
- Tiny IVF fixture generation now writes inter-copy token partitions with Y2
  EOB followed by Y1 position-1 EOB tokens, matching the supported inter
  non-split syntax.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_decoder_scalar_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_mode_parse_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_token_parse_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_kernels_scalar_test.uya`
- `make test-inter-md5`
- `make test`

## EOB Context Updates

Status: passed.

Evidence:

- `coefficient_eob_context(above, left)` maps the neighboring non-zero flags to
  VP8's coefficient contexts 0, 1, and 2 by summing the above and left
  `has_coeff` states.
- `parse_block_coefficients_with_context` starts each block from that
  above/left EOB context, then updates the in-block context after every
  non-EOB token: ZERO selects context 0, ONE selects context 1, and larger
  tokens select context 2. EOB stops the block without writing a coefficient.
- Key-frame and inter-frame token decode store `summary.has_coeff` back into
  `AboveLeftCoeffContext` for Y2, Y, U, and V blocks. Skip-coeff macroblocks
  clear the relevant above/left contexts, while Y blocks with Y2 include
  non-zero Y2 DC in the Y context state.
- `src/vp8_decoder_scalar_test.uya` now includes a key-frame `B_PRED` fixture
  whose first Y block writes `ZERO, ONE, EOB`. The following neighbor blocks
  write their EOB tokens using the left/above context propagated from that
  non-zero block, and the test checks the macroblock coefficient summary and
  reconstructed samples.
- Existing decoder fixtures cover UV left/above propagation and Y2-derived Y
  context propagation, while `src/vp8_common_coeff_context_test.uya` verifies
  row-start behavior preserves above contexts and clears left contexts.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_decoder_scalar_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_token_parse_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_coeff_context_test.uya`
- `make test-decoder-scalar`

## MV Clamp And Sub-pixel Reference Border

Status: passed.

Evidence:

- `clamp_inter_motion_vector` validates frame/block geometry, derives the
  per-axis min/max bounds from the macroblock origin and visible
  `frame_size - block_size` extent in eighth-pel units, and preserves the
  parsed MV mode while clamping x/y. `inter_motion_vector_inside_frame` uses
  the same bounds for validation.
- Decoder inter-mode parsing clamps parsed LAST/GOLDEN/ALTREF motion vectors
  before storing them in `MacroblockInfo`. The current decoder reconstruction
  path explicitly rejects luma sub-pixel inter MVs with
  `ErrDecoderUnsupportedSubpixelInterFrame`, so this evidence is scoped to the
  supported integer inter decoder path plus encoder sub-pixel motion search.
- Supported decoder and encoder integer inter prediction both extend the
  selected reference frame before copying from it. The encoder regression for a
  negative integer MV proves a left-border luma sample is read from the
  replicated reference edge.
- Encoder motion search extends the last-frame reference before integer-pel
  SAD and half/quarter-pel refinement. Sub-pixel refinement uses floor-div8
  motion-vector splitting, derives x/y offsets in `0..7`, and accesses the
  luma six-tap window at `ref_x - 2, ref_y - 2` with a 21x21 bounds check, so
  edge candidates read the reference border rather than unextended memory.
- `src/vp8_encoder_motion_search_test.uya` now constructs a top-left
  macroblock from the extended reference border at negative half-pel offset,
  then verifies refinement finds `mv_x = -4`, `mv_y = -4`, zero distortion,
  and `border_extension_count == 3`.
- Existing frame and kernel tests cover border replication for Y/U/V planes,
  scalar luma/chroma sub-pixel filtering, and SIMD luma sub-pixel filtering
  against scalar byte-exact output.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_mode_parse_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_inter_prediction_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_motion_search_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_frame_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_kernels_scalar_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_kernels_simd_test.uya`
- `make test-inter-md5`

## SIMD Extreme Inputs Match Scalar

Status: passed.

Evidence:

- `src/vp8_kernels_simd_test.uya` compares current SIMD kernels against scalar
  kernels for helpers, border extension, residual add/clamp, transforms,
  intra/inter predictors, SAD/SSE/variance/SATD, sub-pixel filters, loop
  filters, quant/dequant, and token scan.
- Existing helper tests already cover unsigned byte widening, saturated
  narrowing below 0 and above 255, 0/255 absolute differences, and VP8 six-tap
  filter lanes with negative coefficients and clipping endpoints.
- The SIMD residual-add regression includes large positive and negative
  residuals (`30000`, `-30000`, `512`, `-512`) over 0/255 destination samples
  and verifies byte-exact scalar clipping.
- The quant/dequant regression now includes high signed coefficients
  (`32767`, `-32768`, `30000`, `-30000`) with a large factor, and checks SIMD
  qcoeff, dqcoeff, and coefficient summary against scalar.
- The new byte-extreme regression drives true-motion predictors for Y16, Y4,
  and UV with alternating 0/255 edges, runs combined luma sub-pixel filtering
  over a 0/255 checkerboard at offset 7, and checks max-difference 16x16,
  8x8, and 4x4 SAD/SSE/variance/SATD against scalar.
- Forced SIMD dispatch is exercised separately by the scalar-vs-SIMD CLI
  regression, which decodes the tracked tiny fixtures through both modes and
  compares visible output hashes.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_kernels_simd_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_kernels_dispatch_test.uya`
- `make test-scalar-vs-simd`

## SIMD Default Path Lane Temporaries And Memcpy

Status: passed.

Evidence:

- The default runtime SIMD level is scalar: `simd_level_default()` returns
  `SimdLevel.scalar`, `make_default_kernel_table(...)` ignores detected
  capabilities and returns `make_scalar_kernel_table()`, and
  `make_decoder(...)` uses that default table.
- CLI default decoding uses `make_decoder(...)`; CLI encoding/mode helpers use
  `make_cli_kernel_table(false, false)`, which also returns the scalar table.
  SIMD kernels are only selected by explicit `--force-simd`,
  `VP8UYA_FORCE_SIMD=1`, or API `SimdLevel.vector128`.
- `src/vp8_kernels_dispatch_test.uya` asserts that the default kernel table
  remains scalar and separately checks the forced SIMD table entries.
- `docs/simd_codegen.md` audits current generated C/assembly for forced SIMD:
  vector load/store lowering is recorded as `__uya_memcpy`, and sub-pixel,
  residual clamp, true-motion, and transform paths document their current
  lane-array or gather/scatter fallbacks.
- `docs/simd_gaps.md`, `docs/uya_compiler_requests.md`, and
  `bench/kernel_thresholds.json` keep these lowering gaps visible and mark
  default dispatch as `disabled_until_threshold_passes`, requiring bit-exact,
  codegen, and benchmark evidence before any SIMD kernel can become default.
- `docs/phase9_acceptance.md` now matches the current implementation: default
  dispatch is scalar, while forced SIMD registers vector128 entries when
  available and falls back to scalar otherwise.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_cpu_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_kernels_dispatch_test.uya`
- `make check-simd-codegen`
- `make check-kernel-thresholds`
- `make test-scalar-vs-simd`

## Coefficient Scratch Bounded To Row Windows

Status: passed.

Evidence:

- `TokenDecodeRowOutput` allocates coefficient blocks and packed block summaries
  from `RowScratchArena` for `mb_cols` only. Its byte formula is
  `token_decode_row_output_bytes(mb_cols)`, so it does not multiply by
  `mb_rows` or frame macroblock count.
- The scalar decoder calls `decoder_context_begin_worker_row(...)` before each
  key/inter token row, allocates one row output, reconstructs that row, and then
  records coefficient scratch read/write bytes for that row.
- Key-frame token decode uses the row output plus a fixed
  `TokenDecodeRowScratch` block for Y2/dequant temporaries. Inter-frame token
  decode uses the row output without the extra key-frame scratch block.
- The public API and CLI default row scratch capacity are computed from one row
  output plus `token_decode_row_scratch_bytes()` and padding, not from frame
  height.
- The parallel row scratch primitive is an explicit `MbCoeffScratchRing` with a
  fixed ring depth and reconstruct fence. Existing tests verify that its bound
  is `row_output_bytes * ring_depth` and that high-water does not grow as more
  frame rows pass through the ring.
- `src/vp8_decoder_scalar_test.uya` now decodes a 17x17 key frame and asserts
  coefficient scratch high-water equals one aligned row output plus fixed
  key-frame scratch, remains lower than a full-frame row-output materialization,
  and still records per-row read/write totals across the frame.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_decoder_scalar_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_scratch_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_decode_context_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_api_decoder_test.uya`
- `make test-token-partition-md5`

## Reference Refresh Avoids Full-frame Copies

Status: passed.

Evidence:

- `frame_pool_refresh_references(...)` implements refresh by marking the
  current frame border dirty, decrementing the old logical reference slot count,
  assigning `last_slot`, `golden_slot`, and/or `altref_slot` to
  `current_slot`, and incrementing that slot refcount. It does not call a plane
  copy, frame copy, or `memcpy` path.
- `FramePool.bytes_copied_for_ref_refresh` is initialized to zero and is only
  read for decoder/encoder performance stats. It is not incremented in the
  normal refresh path; any future full-plane fallback must make that statistic
  non-zero.
- `frame_pool_begin_frame(...)` only reuses or switches to a slot that is not a
  logical reference and has no outstanding decoded-frame lease. If all slots are
  protected, it returns `ErrFramePoolNoFreeSlot` instead of copying frame data to
  manufacture a free slot.
- Decoder `decoder_decode_frame(...)` snapshots
  `bytes_copied_for_ref_refresh` before frame parsing and reports the per-frame
  delta through `DecoderFramePerformanceStats`. Existing key-frame and
  inter-frame decoder tests assert that this delta remains zero.
- Encoder refresh helpers are thin wrappers over the same frame-pool refresh
  function. Encoder reference-pool and golden/altref refresh-policy tests verify
  that refreshed logical refs alias the reconstructed current frame and that
  `encoder_reference_bytes_copied(...)` remains zero.
- `docs/design.md` records the invariant that full-plane copy is only an
  explicit fallback and must be counted through
  `bytes_copied_for_ref_refresh`; normal decode expects the metric to be zero.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_frame_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_decoder_scalar_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_reference_pool_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_encoder_refresh_policy_test.uya`
- `make test-keyframe-md5`
- `make test-inter-md5`

## Borrowed DecodedFrame Lifetime Avoids Implicit Copies

Status: passed.

Evidence:

- `frame_pool_borrow_current_decoded_frame(...)` increments the current slot's
  lease count and returns a `DecodedFrame` whose `FrameVisibleView` points at
  the frame buffer plane origins. It does not allocate or copy an owned output
  frame.
- `decoded_frame_release(...)` only decrements the borrowed slot lease count and
  marks the handle released; repeated release is idempotent.
- `frame_pool_begin_frame(...)` treats leased slots as unavailable for current
  decode. It reuses/switches to an unreferenced, unleased slot and returns
  `ErrFramePoolNoFreeSlot` if no such slot exists, rather than copying a leased
  output to free storage.
- Decoder `decoder_decode_frame(...)` borrows the current frame only when
  `show_frame` is true. Hidden frames return `has_output=false` and take no
  output lease.
- The public API preserves the same ownership model: `Vp8DecodedFrame` stores
  the borrowed `DecodedFrame`, exposes its borrowed `FrameVisibleView`, and
  releases the internal lease through `vp8_decoded_frame_release(...)`.
- The new public API regression decodes two shown key frames while keeping the
  first output unreleased. The decoder switches from slot 0 to slot 1, both
  slot leases remain active, the two output views point at different frame
  slots, and `bytes_copied_for_ref_refresh` remains zero.
- CLI decode writes YUV from the borrowed view and releases the decoded frame
  immediately after writing output/stats. The temporary output buffer used for
  file I/O is not a decoder lifetime workaround and does not change the default
  decode ownership model.

Verification:

- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_api_decoder_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_common_frame_test.uya`
- `/media/winger/_dde_data/winger/uya/gui-uya/uya/bin/uya test src/vp8_decoder_scalar_test.uya`
- `make test-examples`
- `make test-keyframe-md5`
- `make test-inter-md5`
