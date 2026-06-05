# Encoder libvpx compare report

## Run Summary

- Benchmark target: libvpx `vpxenc --best`
- git commit: `00f3c9df0805ad03192a2ab23ca29e310280b291`
- generated at: `2026-06-05T07:54:57Z`
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
| vp8uya_bits_per_pixel | 1.138569 |
| libvpx_bits_per_pixel | 0.261376 |
| vp8uya_psnr_all_db | 13.607930 |
| libvpx_psnr_all_db | 38.421882 |
| vp8uya_fps | 23.35 |
| libvpx_fps | 122.60 |

## Sample Results

| Sample | Group | Frames | vp8uya bpp | libvpx bpp | vp8uya PSNR-all | libvpx PSNR-all | vp8uya SSIM-all | libvpx SSIM-all | vp8uya fps | libvpx fps | Passed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| akiyo_qcif |  | 60 | 0.298732 | 0.261521 | 12.431347 | 48.320138 | 0.475601 | 0.999593 | 30.57 | 267.14 | false |
| foreman_qcif |  | 60 | 0.929603 | 0.336706 | 13.365196 | 41.488222 | 0.448745 | 0.994510 | 27.83 | 99.11 | false |
| coastguard_qcif |  | 60 | 1.052878 | 0.342419 | 16.280590 | 36.434307 | 0.570368 | 0.990787 | 28.49 | 98.06 | false |
| mobile_cif |  | 60 | 2.273064 | 0.104857 | 12.354588 | 27.444861 | 0.258488 | 0.976963 | 6.51 | 26.07 | false |

## VP8UYA Macroblock Mode Distribution

| Scope | Macroblocks | Inter MBs | Intra MBs |
| --- | ---: | ---: | ---: |
| summary | 40887 | 40373 | 514 |
| akiyo_qcif | 5841 | 5841 | 0 |
| foreman_qcif | 5841 | 5817 | 24 |
| coastguard_qcif | 5841 | 5838 | 3 |
| mobile_cif | 23364 | 22877 | 487 |

## VP8UYA Skip Distribution

| Scope | Macroblocks | Skip MBs | Skip Ratio |
| --- | ---: | ---: | ---: |
| summary | 40887 | 1146 | 2.80% |
| akiyo_qcif | 5841 | 875 | 14.98% |
| foreman_qcif | 5841 | 72 | 1.23% |
| coastguard_qcif | 5841 | 0 | 0.00% |
| mobile_cif | 23364 | 199 | 0.85% |

## VP8UYA Motion Distribution

| Scope | Macroblocks | Zero MV | NEWMV | Non-zero MV |
| --- | ---: | ---: | ---: | ---: |
| summary | 40373 | 15985 | 24388 | 24388 |
| akiyo_qcif | 5841 | 5792 | 49 | 49 |
| foreman_qcif | 5817 | 2687 | 3130 | 3130 |
| coastguard_qcif | 5838 | 1084 | 4754 | 4754 |
| mobile_cif | 22877 | 6422 | 16455 | 16455 |

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
- bitrate_ratio 1.142285 exceeds max 1.100000
- psnr_all_delta_db -35.888791 below min -0.500000
- fps_ratio 0.114430 below min 0.800000

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
- bitrate_ratio 2.760879 exceeds max 1.100000
- psnr_all_delta_db -28.123026 below min -0.500000
- fps_ratio 0.280817 below min 0.800000

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
- bitrate_ratio 3.074823 exceeds max 1.100000
- psnr_all_delta_db -20.153717 below min -0.500000
- fps_ratio 0.290517 below min 0.800000

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
- bitrate_ratio 21.677717 exceeds max 1.100000
- psnr_all_delta_db -15.090273 below min -0.500000
- fps_ratio 0.249630 below min 0.800000

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
