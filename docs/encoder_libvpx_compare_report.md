# Encoder libvpx compare report

## Run Summary

- Benchmark target: libvpx `vpxenc --best`
- git commit: `6403a753920de758cf8e315fc20aef72eb416ac4`
- generated at: `2026-06-05T07:34:53Z`
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
| vp8uya_bits_per_pixel | 1.135080 |
| libvpx_bits_per_pixel | 0.261376 |
| vp8uya_psnr_all_db | 12.152230 |
| libvpx_psnr_all_db | 38.421882 |
| vp8uya_fps | 23.30 |
| libvpx_fps | 122.01 |

## Sample Results

| Sample | Group | Frames | vp8uya bpp | libvpx bpp | vp8uya PSNR-all | libvpx PSNR-all | vp8uya SSIM-all | libvpx SSIM-all | vp8uya fps | libvpx fps | Passed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| akiyo_qcif |  | 60 | 0.296628 | 0.261521 | 10.811141 | 48.320138 | 0.357118 | 0.999593 | 30.52 | 263.33 | false |
| foreman_qcif |  | 60 | 0.925658 | 0.336706 | 12.138211 | 41.488222 | 0.347223 | 0.994510 | 27.76 | 101.91 | false |
| coastguard_qcif |  | 60 | 1.048753 | 0.342419 | 14.037170 | 36.434307 | 0.443129 | 0.990787 | 28.40 | 96.96 | false |
| mobile_cif |  | 60 | 2.269281 | 0.104857 | 11.622400 | 27.444861 | 0.245597 | 0.976963 | 6.53 | 25.86 | false |

## VP8UYA Macroblock Mode Distribution

| Scope | Macroblocks | Inter MBs | Intra MBs |
| --- | ---: | ---: | ---: |
| summary | 40887 | 40373 | 514 |
| akiyo_qcif | 5841 | 5841 | 0 |
| foreman_qcif | 5841 | 5817 | 24 |
| coastguard_qcif | 5841 | 5838 | 3 |
| mobile_cif | 23364 | 22877 | 487 |

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
- bitrate_ratio 1.134239 exceeds max 1.100000
- psnr_all_delta_db -37.508997 below min -0.500000
- fps_ratio 0.115891 below min 0.800000

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
- bitrate_ratio 2.749160 exceeds max 1.100000
- psnr_all_delta_db -29.350012 below min -0.500000
- fps_ratio 0.272443 below min 0.800000

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
- bitrate_ratio 3.062778 exceeds max 1.100000
- psnr_all_delta_db -22.397137 below min -0.500000
- fps_ratio 0.292892 below min 0.800000

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
- bitrate_ratio 21.641643 exceeds max 1.100000
- psnr_all_delta_db -15.822461 below min -0.500000
- fps_ratio 0.252500 below min 0.800000

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
