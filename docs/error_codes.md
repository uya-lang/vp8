# Error Codes

This document is the release-hardening catalog for errors declared in `src/`.
UYA errors are symbolic, module-scoped names declared with `error Err...;`.
The project does not currently expose a stable C ABI or numeric error table, so
these names are the compatibility surface for UYA callers and the diagnostic
surface for tests.

Run this check after adding or renaming an error:

```sh
make test-error-codes-doc
```

The check scans every `error Err...;` declaration under `src/` and verifies that
the symbol appears in this file.

## CLI Messages

The CLI maps internal errors to stable user-facing text and exits with status
`2` for controlled input, file, allocation, or encode/decode failures. Unknown
commands currently return status `1`.

| Command area | Messages |
| --- | --- |
| File input | `error: failed to read input file`, `error: failed to read input YUV file` |
| IVF info/decode | `error: invalid IVF header`, `error: invalid IVF frame data` |
| WebM decode | `error: invalid WebM subset`, `error: invalid WebM segment info`, `error: invalid WebM VP8 sample`, `error: invalid WebM video geometry` |
| Decoder resources | `error: invalid decode scratch geometry`, `error: failed to allocate decoder context`, `error: failed to open output file`, `error: failed to open stats file` |
| Decoder frame flow | `error: failed to decode VP8 frame`, `error: failed to write YUV output`, `error: failed to write decode stats`, `error: failed to release decoded frame`, `error: frame index not found` |
| Encoder input/config | `error: encode width and height must be positive`, `error: invalid rate control config`, `error: failed to choose CQP quantizer`, `error: input YUV is too short for I420 width/height`, `error: input YUV must contain exactly the requested I420 frames`, `error: invalid encode output geometry` |
| Encoder output/metrics | `error: failed to allocate encode output`, `error: failed to encode keyframe IVF`, `error: failed to compute encode quality metrics`, `error: failed to finish rate control frame`, `error: failed to open encode output file`, `error: failed to write encode output file`, `error: failed to compute encode bitrate report` |
| Option parsing | `error: --threads requires N`, `error: --threads must be positive`, `error: info requires <input.ivf>`, `error: decode requires <input.ivf\|input.webm> --yuv <out.yuv> [--stats <out.jsonl>]`, `error: decode currently requires --yuv <out.yuv>`, `error: --stats requires <out.jsonl>`, `error: unknown decode option: %s`, `error: decode-frame requires <input.ivf> --index N --yuv <out.yuv>`, `error: decode-frame requires --index N`, `error: frame index must be non-negative`, `error: decode-frame requires --yuv <out.yuv>` |
| Encode option parsing | `error: encode requires <input.yuv> --width W --height H [--frames N] [--fps NUM/DEN] [--quantizer Q] [--target-bitrate BPS] [--speed fastest\|fast\|balanced\|best] --out <out.ivf>`, `error: --width requires W`, `error: --width must be positive`, `error: --height requires H`, `error: --height must be positive`, `error: --frames requires N`, `error: --frames must be positive`, `error: --fps requires NUM/DEN`, `error: --fps must be NUM/DEN with positive integers`, `error: --quantizer requires Q`, `error: --quantizer must be in 0..127`, `error: --target-bitrate requires BPS`, `error: --target-bitrate must be positive`, `error: --speed requires fastest\|fast\|balanced\|best`, `error: --speed must be fastest, fast, balanced, or best`, `error: --out requires <out.ivf>`, `error: unknown encode option: %s`, `error: encode requires --width W --height H [--frames N] [--fps NUM/DEN] [--quantizer Q] [--target-bitrate BPS] [--speed fastest\|fast\|balanced\|best] --out <out.ivf>` |

Encode `--frames` and `--fps` argument validation failures are controlled
option parsing errors and return status `2`. Encode input length validation uses
the requested I420 frame count: too few bytes report `error: input YUV is too
short for I420 width/height`, while extra bytes report `error: input YUV must
contain exactly the requested I420 frames`.

CLI-only internal helpers are declared in `src/main.uya`:

| Error | Meaning |
| --- | --- |
| `ErrOpenFile` | Input or output file could not be opened. |
| `ErrInvalidFileSize` | File size query or seek failed, or the file is empty. |
| `ErrOutOfMemory` | CLI heap allocation failed. |
| `ErrReadFile` | File read returned fewer bytes than expected. |
| `ErrWriteFile` | File write returned fewer bytes than expected. |
| `ErrCliScratchCapacityOverflow` | Row scratch sizing overflowed or produced invalid geometry. |
| `ErrCliWebmGeometryOverflow` | WebM pixel width or height cannot be represented as a local `usize`. |
| `ErrEncodeBitrateUnavailable` | Encoded payload length cannot be represented as frame bits. |
| `ErrEncodeQualityUnavailable` | Encoded output could not be decoded for quality analysis. |
| `ErrInvalidSpeedPreset` | CLI speed preset string is not recognized. |
| `ErrInvalidCliFps` | CLI `--fps` parsing rejected a malformed, zero, or overflowing `NUM/DEN` value. |

## Public API

`src/vp8/api.uya` declares the errors that library callers should treat as the
primary API contract.

| Error | Meaning |
| --- | --- |
| `ErrVp8DecoderInvalidOptions` | Decoder options are invalid before allocation or initialization. |
| `ErrVp8DecoderInvalidState` | Decoder method was called on an invalid, uninitialized, or already-released state. |
| `ErrVp8DecoderUnsupportedSimdLevel` | Requested decoder SIMD level is unavailable. |
| `ErrVp8EncoderInvalidOptions` | Encoder options or source frame view are invalid. |
| `ErrVp8EncoderInvalidState` | Encoder method was called on an invalid or uninitialized state. |
| `ErrVp8EncoderOutputOverflow` | Caller-provided packet buffer is too small. |
| `ErrVp8EncoderUnsupportedSimdLevel` | Requested encoder SIMD level is unavailable. |

## Bitstream

These errors report bounded byte reads, VP8 frame header parsing/writing,
boolean arithmetic coding, coefficient token parsing, and mode/MV parsing.

| Module | Errors |
| --- | --- |
| `src/vp8/bitstream/readers.uya` | `ErrReaderOutOfBounds` |
| `src/vp8/bitstream/bool_reader.uya` | `ErrBoolReaderOverread`, `ErrBoolReaderTraceFull` |
| `src/vp8/bitstream/bool_writer.uya` | `ErrBoolWriterOutOfBounds` |
| `src/vp8/bitstream/header.uya` | `ErrInvalidKeyFrameStartCode`, `ErrFirstPartitionOutOfBounds`, `ErrInvalidTokenPartitionCount`, `ErrTokenPartitionOutOfBounds`, `ErrVp8HeaderWriteOutOfBounds`, `ErrInvalidVp8HeaderValue` |
| `src/vp8/token/parse.uya` | `ErrVp8CoefficientIndexOutOfBounds` |
| `src/vp8/mode/parse.uya` | `ErrVp8BModeProbOutOfBounds`, `ErrVp8MvProbOutOfBounds`, `ErrVp8MvInvalidGeometry` |

## Containers

Container errors are kept separate from decode errors. Parsers validate
container shape and expose bounded payload slices; the decoder then validates
the VP8 payload.

| Module | Errors |
| --- | --- |
| `src/vp8/container/ivf.uya` | `ErrInvalidIvfSignature`, `ErrInvalidIvfHeaderSize`, `ErrUnsupportedIvfFourcc`, `ErrIvfWriteOutOfBounds` |
| `src/vp8/container/raw.uya` | `ErrEmptyRawVp8Payload`, `ErrYuvWriteOutOfBounds` |
| `src/vp8/container/webm_subset.uya` | `ErrWebmInvalidElementId`, `ErrWebmInvalidElementSize`, `ErrWebmUnknownElementSize`, `ErrWebmElementOutOfBounds`, `ErrWebmMissingEbmlHeader`, `ErrWebmUnsupportedDocType`, `ErrWebmMissingSegment`, `ErrWebmInvalidUnsignedInt`, `ErrWebmMissingTracks`, `ErrWebmMissingVideoTrack`, `ErrWebmUnsupportedCodec`, `ErrWebmMissingCluster`, `ErrWebmMissingClusterTimecode`, `ErrWebmInvalidSimpleBlock`, `ErrWebmUnsupportedLacing`, `ErrWebmMissingSample` |
| `src/vp8/container/rtp_vp8.uya` | `ErrRtpVp8PayloadDescriptorTooShort`, `ErrRtpVp8ReservedBitSet`, `ErrRtpVp8MissingPayload`, `ErrRtpVp8ReassemblyMissingStart`, `ErrRtpVp8ReassemblyUnexpectedStart`, `ErrRtpVp8PacketLoss`, `ErrRtpVp8PictureIdMismatch`, `ErrRtpVp8ReassemblyBufferTooSmall` |

## Decoder

Decoder errors cover unsupported or malformed frame structure, state mismatch,
row pipeline sequencing, and token-partition worker inputs.

| Module | Errors |
| --- | --- |
| `src/vp8/decoder/scalar.uya` | `ErrDecoderInvalidFrame`, `ErrDecoderUnsupportedInterFrame`, `ErrDecoderFrameSizeMismatch`, `ErrDecoderCoeffProbOutOfBounds`, `ErrDecoderUnsupportedSubpixelInterFrame` |
| `src/vp8/decoder/row_pipeline.uya` | `ErrRowReconstructPipelineInvalidRows`, `ErrRowReconstructPipelineOutOfOrder`, `ErrRowReconstructPipelineComplete`, `ErrRowLoopFilterPipelineInvalidRows`, `ErrRowLoopFilterPipelineOutOfOrder`, `ErrRowLoopFilterPipelineIncomplete`, `ErrRowLoopFilterPipelineComplete` |
| `src/vp8/decoder/token_partition.uya` | `ErrTokenPartitionWorkerInvalidRows` |

## Common Runtime Structures

Common errors describe allocation geometry, frame-pool state, macroblock
addressing, coefficient/mode context bounds, and row scratch arena limits.

| Module | Errors |
| --- | --- |
| `src/vp8/common/plane.uya` | `ErrPlaneInvalidGeometry`, `ErrPlaneOutOfBounds` |
| `src/vp8/common/frame_alloc.uya` | `ErrFrameAllocationInvalidGeometry`, `ErrFrameAllocationOverflow`, `ErrFrameAllocationOutOfMemory` |
| `src/vp8/common/frame.uya` | `ErrFrameBufferInvalidGeometry`, `ErrFramePoolInvalidSlot`, `ErrFramePoolNoFreeSlot` |
| `src/vp8/common/mb_grid.uya` | `ErrMacroblockGridInvalidGeometry`, `ErrMacroblockGridOutOfBounds`, `ErrMacroblockGridOverflow` |
| `src/vp8/common/mb_info.uya` | `ErrMacroblockInfoInvalidGeometry`, `ErrMacroblockInfoOutOfMemory`, `ErrMacroblockInfoOutOfBounds`, `ErrMacroblockInfoOverflow`, `ErrMacroblockCoeffSummaryCountOutOfBounds` |
| `src/vp8/common/mode_context.uya` | `ErrModeContextInvalidGeometry`, `ErrModeContextOutOfMemory`, `ErrModeContextOutOfBounds` |
| `src/vp8/common/coeff_context.uya` | `ErrCoeffContextInvalidGeometry`, `ErrCoeffContextOutOfMemory`, `ErrCoeffContextOutOfBounds`, `ErrCoeffContextOverflow` |
| `src/vp8/common/scratch.uya` | `ErrScratchInvalidGeometry`, `ErrScratchOverflow`, `ErrScratchOutOfMemory`, `ErrScratchCapacityExceeded`, `ErrScratchOutOfBounds`, `ErrMbCoeffScratchRingInvalidGeometry`, `ErrMbCoeffScratchRingFull`, `ErrMbCoeffScratchRingOutOfOrder`, `ErrMbCoeffScratchRingRowNotReady` |
| `src/vp8/common/decode_context.uya` | `ErrDecoderContextInvalidGeometry`, `ErrDecoderContextInvalidWorker` |

## Encoder

Encoder errors are organized by subsystem. Most `InvalidInput` and
`InvalidGeometry` errors mean the caller supplied inconsistent dimensions,
strides, counts, frame views, qindex values, or mode identifiers before the
encoder wrote output bytes.

| Module | Errors |
| --- | --- |
| `src/vp8/encoder/context.uya` | `ErrEncoderConfigInvalidValue`, `ErrEncoderIvfWriteOutOfBounds`, `ErrYuvFrameViewInvalidGeometry` |
| `src/vp8/encoder/keyframe.uya` | `ErrEncoderKeyframeInvalidInput`, `ErrEncoderKeyframeInvalidGeometry`, `ErrEncoderKeyframeOutOfMemory`, `ErrEncoderKeyframeOutOfBounds`, `ErrEncoderKeyframeSizeOverflow` |
| `src/vp8/encoder/inter_frame.uya` | `ErrEncoderInterFrameInvalidInput`, `ErrEncoderInterFrameInvalidGeometry`, `ErrEncoderInterFrameOutOfMemory`, `ErrEncoderInterFrameOutOfBounds`, `ErrEncoderInterFrameSizeOverflow` |
| `src/vp8/encoder/keyframe_interval.uya` | `ErrEncoderKeyframeIntervalInvalidInput` |
| `src/vp8/encoder/rate_control.uya` | `ErrEncoderRateControlInvalidInput`, `ErrEncoderRateControlUnsupportedMode`, `ErrEncoderRateControlFrameIndexOverflow`, `ErrEncoderRateControlTargetOverflow`, `ErrEncoderCbrBufferInvalidInput` |
| `src/vp8/encoder/quality.uya` | `ErrEncoderQualityInvalidInput` |
| `src/vp8/encoder/rd_cost.uya` | `ErrEncoderRdCostInvalidInput`, `ErrEncoderRdCostOverflow` |
| `src/vp8/encoder/quantizer_delta.uya` | `ErrEncoderQuantizerDeltaInvalidInput` |
| `src/vp8/encoder/loop_filter_level.uya` | `ErrEncoderLoopFilterLevelInvalidInput` |
| `src/vp8/encoder/loop_filter.uya` | `ErrEncoderLoopFilterInvalidInput`, `ErrEncoderLoopFilterInvalidFrame` |
| `src/vp8/encoder/mode_decision.uya` | `ErrEncoderModeDecisionInvalidGeometry`, `ErrEncoderModeDecisionScoreOverflow` |
| `src/vp8/encoder/mode_search.uya` | `ErrIntra4x4ModeSearchInvalidGeometry`, `ErrIntra4x4ModeSearchInvalidMode`, `ErrIntra16x16ModeSearchInvalidGeometry`, `ErrIntra16x16ModeSearchInvalidMode`, `ErrUvModeSearchInvalidGeometry`, `ErrUvModeSearchInvalidMode` |
| `src/vp8/encoder/motion_search.uya` | `ErrEncoderMotionSearchInvalidGeometry`, `ErrEncoderMotionSearchInvalidBaseMv`, `ErrEncoderMotionSearchOutOfBounds`, `ErrEncoderMotionSearchNoCandidate` |
| `src/vp8/encoder/mv_cost.uya` | `ErrEncoderMvCostInvalidBit`, `ErrEncoderMvCostInvalidMode`, `ErrEncoderMvCostInvalidMagnitude`, `ErrEncoderMvCostInvalidProbabilityTable` |
| `src/vp8/encoder/inter_prediction.uya` | `ErrEncoderInterPredictionInvalidGeometry`, `ErrEncoderInterPredictionUnsupportedSubpixel`, `ErrEncoderInterPredictionOutOfBounds` |
| `src/vp8/encoder/inter_reconstruct.uya` | `ErrEncoderInterReconstructInvalidInput`, `ErrEncoderInterReconstructInvalidGeometry` |
| `src/vp8/encoder/reconstruct.uya` | `ErrEncoderReconstructInvalidInput`, `ErrEncoderReconstructInvalidGeometry`, `ErrEncoderReconstructInvalidFactor` |
| `src/vp8/encoder/quant.uya` | `ErrEncoderQuantizeInvalidInput`, `ErrEncoderQuantizeInvalidFactor`, `ErrEncoderTokenizeInvalidInput`, `ErrEncoderTokenizeInvalidPosition`, `ErrEncoderTokenizeOutputTooSmall`, `ErrEncoderTokenizeCoefficientTooLarge` |
| `src/vp8/encoder/partition_output.uya` | `ErrEncoderBoolPartitionOutputInvalidInput`, `ErrEncoderBoolPartitionOutputInvalidCount`, `ErrEncoderBoolPartitionOutputOutOfBounds`, `ErrEncoderBoolPartitionOutputPartitionTooLarge` |
| `src/vp8/encoder/token_partition_packing.uya` | `ErrEncoderTokenPartitionPackingInvalidInput`, `ErrEncoderTokenPartitionPackingInvalidCount`, `ErrEncoderTokenPartitionPackingRowOutOfBounds` |
| `src/vp8/encoder/token_stats.uya` | `ErrEncoderTokenStatsInvalidInput`, `ErrEncoderTokenStatsOverflow` |
| `src/vp8/encoder/probability_update.uya` | `ErrEncoderProbabilityUpdateInvalidInput` |
| `src/vp8/encoder/refresh_policy.uya` | `ErrEncoderRefreshPolicyInvalidInput` |
| `src/vp8/encoder/segmentation_policy.uya` | `ErrEncoderSegmentationPolicyInvalidInput` |
| `src/vp8/encoder/skip_decision.uya` | `ErrEncoderSkipDecisionInvalidInput`, `ErrEncoderSkipDecisionInvalidCount`, `ErrEncoderSkipDecisionInvalidSummary` |

## Kernels

Kernel errors are internal dispatch or mode-selection guards. They should be
caught by tests before a public API or CLI path reaches them.

| Module | Errors |
| --- | --- |
| `src/vp8/kernels/dispatch.uya` | `ErrKernelFunctionTableInvalidEntry` |
| `src/vp8/kernels/scalar.uya` | `ErrScalarKernelInvalidIntraPredictorMode` |
| `src/vp8/kernels/simd.uya` | `ErrSimdKernelInvalidIntraPredictorMode` |

## Maintenance Rules

- Add new UYA error declarations only when a caller or test can observe a
  distinct failure class.
- Keep CLI text stable when tests or downstream scripts assert it.
- Prefer module-specific names over generic names unless the error is shared by
  a cross-module public API.
- If a future C ABI is added, define a numeric mapping in a separate ABI table
  and keep the UYA symbols here as source-level names.
