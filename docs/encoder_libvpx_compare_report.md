# Encoder libvpx compare report

## Run Summary

- Benchmark target: libvpx `vpxenc --best`
- git commit: `e0a61fe1c05fbd0653af59604f8ea39d5af5127b`
- generated at: `2026-06-05T06:11:13Z`
- sample count: 4
- passed count: 4
- failed count: 0

## Tool Versions

| Tool | Version |
| --- | --- |
| vpxenc | vp8    - WebM Project VP8 Encoder v1.11.0 |
| vpxdec | vp8    - WebM Project VP8 Decoder v1.11.0 |

## Thresholds

| Metric | Hard threshold |
| --- | --- |
| Bitrate | `vp8uya_bits_per_pixel <= libvpx_bits_per_pixel * 1.10` |
| PSNR-all | `vp8uya_psnr_all_db >= libvpx_psnr_all_db -0.50` |
| Encoding fps | `vp8uya_fps >= libvpx_fps * 0.80` |

`SSIM-all` is recorded for diagnosis only and does not decide hard pass/fail in the first report version.

## Aggregate Summary

| Field | Value |
| --- | ---: |
| vp8uya_bits_per_pixel | 1.137184 |
| libvpx_bits_per_pixel | 0.261376 |
| vp8uya_psnr_all_db | 12.311845 |
| libvpx_psnr_all_db | 38.421882 |
| vp8uya_fps | 54.01 |
| libvpx_fps | 125.28 |

## Sample Results

| Sample | Group | Frames | vp8uya bpp | libvpx bpp | vp8uya PSNR-all | libvpx PSNR-all | vp8uya SSIM-all | libvpx SSIM-all | vp8uya fps | libvpx fps | Passed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| akiyo_qcif |  | 60 | 0.296628 | 0.261521 | 10.811141 | 48.320138 | 0.357118 | 0.999593 | 72.31 | 272.43 | true |
| foreman_qcif |  | 60 | 0.927141 | 0.336706 | 12.794459 | 41.488222 | 0.377962 | 0.994510 | 64.93 | 102.58 | true |
| coastguard_qcif |  | 60 | 1.049263 | 0.342419 | 14.058654 | 36.434307 | 0.439904 | 0.990787 | 64.66 | 99.57 | true |
| mobile_cif |  | 60 | 2.275704 | 0.104857 | 11.583125 | 27.444861 | 0.231459 | 0.976963 | 14.15 | 26.56 | true |

## Failed Samples

No failing samples.

## Conclusion

PASS: 4/4 samples passed.
