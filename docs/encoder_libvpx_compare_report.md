# Encoder libvpx compare report

## Run Summary

- Benchmark target: libvpx `vpxenc --best`
- git commit: `fbe46e8811f2ad3cbdbeb2ba67025f82f6acee65`
- generated at: `2026-06-05T08:14:26Z`
- sample count: 4
- passed count: 0
- failed count: 4

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
| vp8uya_bits_per_pixel | 1.141300 |
| libvpx_bits_per_pixel | 0.261376 |
| vp8uya_psnr_all_db | 13.697339 |
| libvpx_psnr_all_db | 38.421882 |
| vp8uya_fps | 20.22 |
| libvpx_fps | 122.51 |

## Sample Results

| Sample | Group | Frames | vp8uya bpp | libvpx bpp | vp8uya PSNR-all | libvpx PSNR-all | vp8uya SSIM-all | libvpx SSIM-all | vp8uya fps | libvpx fps | Passed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| akiyo_qcif |  | 60 | 0.318424 | 0.261521 | 12.613254 | 48.320138 | 0.476393 | 0.999593 | 26.43 | 267.21 | false |
| foreman_qcif |  | 60 | 0.924290 | 0.336706 | 13.523675 | 41.488222 | 0.442943 | 0.994510 | 23.74 | 100.40 | false |
| coastguard_qcif |  | 60 | 1.051794 | 0.342419 | 16.194688 | 36.434307 | 0.565465 | 0.990787 | 25.12 | 96.63 | false |
| mobile_cif |  | 60 | 2.270694 | 0.104857 | 12.457739 | 27.444861 | 0.260286 | 0.976963 | 5.59 | 25.82 | false |

## VP8UYA Macroblock Mode Distribution

| Scope | Macroblocks | Inter MBs | Intra MBs |
| --- | ---: | ---: | ---: |
| summary | 40887 | 38980 | 1907 |
| akiyo_qcif | 5841 | 5178 | 663 |
| foreman_qcif | 5841 | 5649 | 192 |
| coastguard_qcif | 5841 | 5820 | 21 |
| mobile_cif | 23364 | 22333 | 1031 |

## VP8UYA Skip Distribution

| Scope | Macroblocks | Skip MBs | Skip Ratio |
| --- | ---: | ---: | ---: |
| summary | 40887 | 565 | 1.38% |
| akiyo_qcif | 5841 | 455 | 7.79% |
| foreman_qcif | 5841 | 37 | 0.63% |
| coastguard_qcif | 5841 | 0 | 0.00% |
| mobile_cif | 23364 | 73 | 0.31% |

## VP8UYA Motion Distribution

| Scope | Macroblocks | Zero MV | NEWMV | Non-zero MV |
| --- | ---: | ---: | ---: | ---: |
| summary | 38980 | 15043 | 23937 | 23937 |
| akiyo_qcif | 5178 | 5142 | 36 | 36 |
| foreman_qcif | 5649 | 2582 | 3067 | 3067 |
| coastguard_qcif | 5820 | 1080 | 4740 | 4740 |
| mobile_cif | 22333 | 6239 | 16094 | 16094 |

## VP8UYA Subpel Distribution

| Scope | Macroblocks | Half-pel Candidates | Quarter-pel Candidates |
| --- | ---: | ---: | ---: |
| summary | 40887 | 367983 | 367983 |
| akiyo_qcif | 5841 | 52569 | 52569 |
| foreman_qcif | 5841 | 52569 | 52569 |
| coastguard_qcif | 5841 | 52569 | 52569 |
| mobile_cif | 23364 | 210276 | 210276 |

## Failed Samples

### akiyo_qcif

Failure reasons:
- bitrate_ratio 1.217582 exceeds max 1.100000
- psnr_all_delta_db -35.706884 below min -0.500000
- fps_ratio 0.098903 below min 0.800000

### vp8uya
```sh
build/vp8uya encode /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/fixtures/akiyo_qcif.i420 --width 176 --height 144 --frames 60 --fps 30000/1001 --out /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/akiyo_qcif.vp8uya.ivf
```

### vpxenc
```sh
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxenc --codec=vp8 --best --ivf --i420 --disable-warning-prompt --quiet --width=176 --height=144 --fps=30000/1001 --limit=60 -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/akiyo_qcif.libvpx.ivf /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/fixtures/akiyo_qcif.i420
```

### vpxdec
```sh
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxdec --rawvideo -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/akiyo_qcif.vp8uya.decoded.i420 /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/akiyo_qcif.vp8uya.ivf
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxdec --rawvideo -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/akiyo_qcif.libvpx.decoded.i420 /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/akiyo_qcif.libvpx.ivf
```

### foreman_qcif

Failure reasons:
- bitrate_ratio 2.745098 exceeds max 1.100000
- psnr_all_delta_db -27.964548 below min -0.500000
- fps_ratio 0.236409 below min 0.800000

### vp8uya
```sh
build/vp8uya encode /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/fixtures/foreman_qcif.i420 --width 176 --height 144 --frames 60 --fps 30000/1001 --out /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/foreman_qcif.vp8uya.ivf
```

### vpxenc
```sh
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxenc --codec=vp8 --best --ivf --i420 --disable-warning-prompt --quiet --width=176 --height=144 --fps=30000/1001 --limit=60 -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/foreman_qcif.libvpx.ivf /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/fixtures/foreman_qcif.i420
```

### vpxdec
```sh
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxdec --rawvideo -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/foreman_qcif.vp8uya.decoded.i420 /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/foreman_qcif.vp8uya.ivf
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxdec --rawvideo -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/foreman_qcif.libvpx.decoded.i420 /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/foreman_qcif.libvpx.ivf
```

### coastguard_qcif

Failure reasons:
- bitrate_ratio 3.071658 exceeds max 1.100000
- psnr_all_delta_db -20.239620 below min -0.500000
- fps_ratio 0.259962 below min 0.800000

### vp8uya
```sh
build/vp8uya encode /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/fixtures/coastguard_qcif.i420 --width 176 --height 144 --frames 60 --fps 30000/1001 --out /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/coastguard_qcif.vp8uya.ivf
```

### vpxenc
```sh
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxenc --codec=vp8 --best --ivf --i420 --disable-warning-prompt --quiet --width=176 --height=144 --fps=30000/1001 --limit=60 -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/coastguard_qcif.libvpx.ivf /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/fixtures/coastguard_qcif.i420
```

### vpxdec
```sh
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxdec --rawvideo -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/coastguard_qcif.vp8uya.decoded.i420 /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/coastguard_qcif.vp8uya.ivf
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxdec --rawvideo -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/coastguard_qcif.libvpx.decoded.i420 /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/coastguard_qcif.libvpx.ivf
```

### mobile_cif

Failure reasons:
- bitrate_ratio 21.655114 exceeds max 1.100000
- psnr_all_delta_db -14.987121 below min -0.500000
- fps_ratio 0.216468 below min 0.800000

### vp8uya
```sh
build/vp8uya encode /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/fixtures/mobile_cif.i420 --width 352 --height 288 --frames 60 --fps 30000/1001 --out /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/mobile_cif.vp8uya.ivf
```

### vpxenc
```sh
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxenc --codec=vp8 --best --ivf --i420 --disable-warning-prompt --quiet --width=352 --height=288 --fps=30000/1001 --limit=60 -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/mobile_cif.libvpx.ivf /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/fixtures/mobile_cif.i420
```

### vpxdec
```sh
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxdec --rawvideo -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/mobile_cif.vp8uya.decoded.i420 /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/mobile_cif.vp8uya.ivf
/media/winger/_dde_home/winger/uya/vp8/build/deps/vpx-tools-root/usr/bin/vpxdec --rawvideo -o /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/mobile_cif.libvpx.decoded.i420 /media/winger/_dde_home/winger/uya/vp8/build/libvpx-encode-compare/runs/mobile_cif.libvpx.ivf
```

## Conclusion

FAIL: 0/4 samples passed.
