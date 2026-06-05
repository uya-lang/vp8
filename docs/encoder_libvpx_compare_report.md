# Encoder libvpx compare report

## Run Summary

- Benchmark target: libvpx `vpxenc --best`
- git commit: `695c07a2ec0fd19d9245774f837f2fb0c0fa7170`
- generated at: `2026-06-05T07:06:10Z`
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
| vp8uya_bits_per_pixel | 1.137184 |
| libvpx_bits_per_pixel | 0.261376 |
| vp8uya_psnr_all_db | 12.311845 |
| libvpx_psnr_all_db | 38.421882 |
| vp8uya_fps | 24.06 |
| libvpx_fps | 122.56 |

## Sample Results

| Sample | Group | Frames | vp8uya bpp | libvpx bpp | vp8uya PSNR-all | libvpx PSNR-all | vp8uya SSIM-all | libvpx SSIM-all | vp8uya fps | libvpx fps | Passed |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| akiyo_qcif |  | 60 | 0.296628 | 0.261521 | 10.811141 | 48.320138 | 0.357118 | 0.999593 | 31.71 | 264.46 | false |
| foreman_qcif |  | 60 | 0.927141 | 0.336706 | 12.794459 | 41.488222 | 0.377962 | 0.994510 | 28.41 | 101.41 | false |
| coastguard_qcif |  | 60 | 1.049263 | 0.342419 | 14.058654 | 36.434307 | 0.439904 | 0.990787 | 29.36 | 98.05 | false |
| mobile_cif |  | 60 | 2.275704 | 0.104857 | 11.583125 | 27.444861 | 0.231459 | 0.976963 | 6.76 | 26.32 | false |

## VP8UYA Motion Distribution

| Scope | Macroblocks | Zero MV | NEWMV | Non-zero MV |
| --- | ---: | ---: | ---: | ---: |
| summary | 40887 | 15990 | 24897 | 24897 |
| akiyo_qcif | 5841 | 5792 | 49 | 49 |
| foreman_qcif | 5841 | 2672 | 3169 | 3169 |
| coastguard_qcif | 5841 | 1084 | 4757 | 4757 |
| mobile_cif | 23364 | 6442 | 16922 | 16922 |

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
- fps_ratio 0.119897 below min 0.800000

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
- bitrate_ratio 2.753566 exceeds max 1.100000
- psnr_all_delta_db -28.693763 below min -0.500000
- fps_ratio 0.280173 below min 0.800000

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
- bitrate_ratio 3.064268 exceeds max 1.100000
- psnr_all_delta_db -22.375653 below min -0.500000
- fps_ratio 0.299409 below min 0.800000

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
- bitrate_ratio 21.702891 exceeds max 1.100000
- psnr_all_delta_db -15.861736 below min -0.500000
- fps_ratio 0.257001 below min 0.800000

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
