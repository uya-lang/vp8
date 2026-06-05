# Encoder libvpx compare report template

> This is a template for future generated reports. It is not a completed
> benchmark result.

## Run Summary

- Benchmark target: libvpx `vpxenc --best`
- vp8uya binary: `<path>`
- vpxenc path: `<path>`
- vpxdec path: `<path>`
- git commit: `<commit>`
- generated at: `<timestamp>`

## Tool Versions

| Tool | Version |
| --- | --- |
| vp8uya | `<version or commit>` |
| vpxenc | `<vpxenc --version output>` |
| vpxdec | `<vpxdec --version output>` |

## Thresholds

| Metric | Hard threshold |
| --- | --- |
| Bitrate | `vp8uya_bits_per_pixel <= libvpx_bits_per_pixel * 1.10` |
| PSNR-all | `vp8uya_psnr_all_db >= libvpx_psnr_all_db - 0.50` |
| Encoding fps | `vp8uya_fps >= libvpx_fps * 0.80` |

`SSIM-all` is recorded for diagnosis only and does not decide hard pass/fail in
the first report version.

## Summary JSON Contract

Future `summary.json` output records core comparison fields with these exact
names:

- `vp8uya_bits_per_pixel`
- `libvpx_bits_per_pixel`
- `vp8uya_psnr_all_db`
- `libvpx_psnr_all_db`
- `vp8uya_fps`
- `libvpx_fps`
- `quantizer_ladder`
- `q_ladder_summary`
- `vpxenc_version`
- `vpxdec_version`

## Sample Results

| Sample | Q | Group | Frames | vp8uya bpp | libvpx bpp | vp8uya PSNR-all | libvpx PSNR-all | vp8uya SSIM-all | libvpx SSIM-all | vp8uya fps | libvpx fps | Passed |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `<sample>` | `<Q or blank>` | `<groups>` | `<frames>` | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` | `<true/false>` |

## Q Ladder Summary

| Q | Samples | vp8uya bpp | libvpx bpp | vp8uya PSNR-all | libvpx PSNR-all | vp8uya fps | libvpx fps |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `16/24/32/40/48` | `<count>` | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` | `<value>` |

## Failed Samples

### `<sample>`

- Failure reasons: `<failure_reasons>`
- vp8uya command: `<command>`
- libvpx command: `vpxenc --best <...>`
- vpxdec command for vp8uya output: `<command>`
- vpxdec command for libvpx output: `<command>`

## Conclusion

`<overall pass/fail and next optimization target>`
