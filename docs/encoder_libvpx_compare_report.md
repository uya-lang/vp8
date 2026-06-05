# Encoder libvpx compare report

## Run Summary

- Benchmark target: libvpx `vpxenc --best`
- git commit: `4a8db4702153e8b0affd85b8e337ec719d56d10a`
- generated at: `2026-06-05T05:12:30Z`
- sample count: 3
- passed count: 3
- failed count: 0

## Tool Versions

| Tool | Version |
| --- | --- |
| vpxenc |  |
| vpxdec |  |

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
| vp8uya_bits_per_pixel | 1.194339 |
| libvpx_bits_per_pixel | 2.681292 |
| vp8uya_psnr_all_db | 15.710501 |
| libvpx_psnr_all_db | 47.962539 |
| vp8uya_fps | 17.73 |
| libvpx_fps | 127.87 |

## Sample Results

| Sample | Group | Frames | vp8uya bpp | libvpx bpp | vp8uya PSNR-all | libvpx PSNR-all | vp8uya SSIM-all | libvpx SSIM-all | vp8uya fps | libvpx fps | Passed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| akiyo_qcif |  | 1 | 0.992109 | 2.078283 | 12.612939 | 48.575122 | 0.859610 | 0.999604 | 16.77 | 103.64 | true |
| foreman_qcif |  | 1 | 1.095013 | 2.668245 | 16.033617 | 47.651895 | 0.874370 | 0.997823 | 18.22 | 126.03 | true |
| coastguard_qcif |  | 1 | 1.495896 | 3.297348 | 18.484947 | 47.660601 | 0.851976 | 0.997558 | 18.19 | 153.94 | true |

## Failed Samples

No failing samples.

## Conclusion

PASS: 3/3 samples passed.
