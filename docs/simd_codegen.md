# SIMD 生成代码检查记录

## 当前检查对象

- UYA 源：`src/vp8_kernels_simd_test.uya`
- 生成 C 快照：`build/simd-codegen/vp8_kernels_simd_test.c`
- 生成汇编快照：`build/simd-codegen/vp8_kernels_simd_test.s`
- 复现命令：`make check-simd-codegen`

## C lowering 结论

| helper | generated C symbol | vector struct | load/store lowering |
| --- | --- | --- | --- |
| load_u8x16 | `vp8_kernels_simd_load_u8x16` | `struct uya_simd_vector_uint8_t_16` | memcpy |
| store_u8x16 | `vp8_kernels_simd_store_u8x16` | `struct uya_simd_vector_uint8_t_16` | memcpy |
| load_i16x8 | `vp8_kernels_simd_load_i16x8` | `struct uya_simd_vector_int16_t_8` | memcpy |
| store_i16x8 | `vp8_kernels_simd_store_i16x8` | `struct uya_simd_vector_int16_t_8` | memcpy |
| load_i32x4 | `vp8_kernels_simd_load_i32x4` | `struct uya_simd_vector_int32_t_4` | memcpy |
| store_i32x4 | `vp8_kernels_simd_store_i32x4` | `struct uya_simd_vector_int32_t_4` | memcpy |

检查结果：

- 6 个 portable SIMD load/store helper 都生成了稳定的 C 符号。
- 当前 C99 后端将 `@vector.load` / `@vector.store` 通过 `__uya_memcpy` 表达，本次生成 C 中 `__uya_memcpy` 出现 28 次。
- 这条记录只证明当前 helper 可生成、可链接、可测试，并记录了实际 lowering；它不证明这些 helper 已经是单条硬件 SIMD load/store。

## SIMD kernel 符号快照

| kernel | generated C symbol |
| --- | --- |
| plane_copy_u8x16 | `vp8_kernels_simd_plane_copy_u8x16` |
| plane_fill_u8x16 | `vp8_kernels_simd_plane_fill_u8x16` |
| extend_plane_border_u8x16 | `vp8_kernels_simd_extend_plane_border_u8x16` |
| predict_inter_copy_16x16_u8x16 | `vp8_kernels_simd_predict_inter_copy_16x16_u8x16` |
| predict_inter_copy_8x8_u8x16 | `vp8_kernels_simd_predict_inter_copy_8x8_u8x16` |
| predict_inter_copy_4x4_u8x16 | `vp8_kernels_simd_predict_inter_copy_4x4_u8x16` |
| add_residual_4x4_clamped_u8x16 | `vp8_kernels_simd_add_residual_4x4_clamped_u8x16` |
| inverse_transform_dc_only_4x4_i16x16 | `vp8_kernels_simd_inverse_transform_dc_only_4x4_i16x16` |
| inverse_transform_4x4_batch_i32x4 | `vp8_kernels_simd_inverse_transform_4x4_batch_i32x4` |
| predict_y16x16_dc_u8x16 | `vp8_kernels_simd_predict_y16x16_dc_u8x16` |
| predict_y16x16_vertical_u8x16 | `vp8_kernels_simd_predict_y16x16_vertical_u8x16` |
| predict_y16x16_horizontal_u8x16 | `vp8_kernels_simd_predict_y16x16_horizontal_u8x16` |
| predict_y16x16_true_motion_u8x16 | `vp8_kernels_simd_predict_y16x16_true_motion_u8x16` |
| predict_y4x4_dc_u8x16 | `vp8_kernels_simd_predict_y4x4_dc_u8x16` |
| predict_y4x4_true_motion_u8x16 | `vp8_kernels_simd_predict_y4x4_true_motion_u8x16` |
| predict_y4x4_vertical_edge_u8x16 | `vp8_kernels_simd_predict_y4x4_vertical_edge_u8x16` |
| predict_y4x4_horizontal_edge_u8x16 | `vp8_kernels_simd_predict_y4x4_horizontal_edge_u8x16` |
| predict_y4x4_down_left_u8x16 | `vp8_kernels_simd_predict_y4x4_down_left_u8x16` |
| predict_y4x4_down_right_u8x16 | `vp8_kernels_simd_predict_y4x4_down_right_u8x16` |
| predict_y4x4_vertical_right_u8x16 | `vp8_kernels_simd_predict_y4x4_vertical_right_u8x16` |
| predict_y4x4_vertical_left_u8x16 | `vp8_kernels_simd_predict_y4x4_vertical_left_u8x16` |
| predict_y4x4_horizontal_down_u8x16 | `vp8_kernels_simd_predict_y4x4_horizontal_down_u8x16` |
| predict_y4x4_horizontal_up_u8x16 | `vp8_kernels_simd_predict_y4x4_horizontal_up_u8x16` |
| predict_uv8x8_dc_u8x16 | `vp8_kernels_simd_predict_uv8x8_dc_u8x16` |
| predict_uv8x8_vertical_u8x16 | `vp8_kernels_simd_predict_uv8x8_vertical_u8x16` |
| predict_uv8x8_horizontal_u8x16 | `vp8_kernels_simd_predict_uv8x8_horizontal_u8x16` |
| predict_uv8x8_true_motion_u8x16 | `vp8_kernels_simd_predict_uv8x8_true_motion_u8x16` |

检查结果：

- 当前 plane copy/fill/border extension/inter copy/residual add clamp/DC-only inverse transform/4x4 inverse DCT batch/Y16x16/Y4x4/UV8x8 predictor SIMD kernel 都生成了稳定 C 符号，并在汇编快照中检测到对应 label。
- `plane_copy_u8x16` 以 16 字节 vector load/store 处理整块，尾部保留 scalar copy。
- `plane_fill_u8x16` 以 `@vector.splat` + 16 字节 vector store 处理整块，尾部保留 scalar fill。
- `extend_plane_border_u8x16` 复用 16 字节 plane fill/copy helper 处理左右边界和顶部/底部复制。
- `predict_inter_copy_16x16/8x8/4x4_u8x16` 覆盖 VP8 integer-pixel inter copy block 尺寸；16x16 复用 plane copy，8x8 两行一组，4x4 单块表达。
- `add_residual_4x4_clamped_u8x16` 使用 `i16x16` signed saturating vector add，因当前缺少 narrow-to-u8 vector path，最终 clamp/store 仍逐 lane 完成。
- `inverse_transform_dc_only_4x4_i16x16` 使用 `i16x16` splat/store 填充 4x4 residual block。
- `inverse_transform_4x4_batch_i32x4` 使用 `i32x4` 执行两阶段 inverse DCT 算术；因当前缺少 shuffle/transpose，4x4 转置仍通过小数组 gather/scatter 完成。
- `predict_y16x16_dc_u8x16` / `vertical` / `horizontal` 复用 16 字节 fill/copy helper；`true_motion` 使用 `i16x16` 行向量计算并逐 lane clamp/store。
- `predict_y4x4_*_u8x16` 覆盖 DC/TM/VE/HE/DL/DR/VR/VL/HD/HU；4x4 block 以 `u8x16` 表达，stride 为 4 时直接 store，通用 stride 通过小数组 scatter。
- `predict_uv8x8_*_u8x16` 覆盖 DC/vertical/horizontal/true_motion；8x8 block 以两行一组 `u8x16` 表达，stride 为 8 时直接 store，通用 stride 通过两行 scatter。
- 这些 kernel 目前只作为 forced/测试用 portable SIMD 实现记录，不进入默认 dispatcher。

## 汇编快照结论

- `cc -std=c99 -O0 -g -fno-builtin -S` 可从生成 C 产出汇编快照。
- 汇编中检测到 33 个 SIMD helper/kernel label：`vp8_kernels_simd_load_u8x16, vp8_kernels_simd_store_u8x16, vp8_kernels_simd_load_i16x8, vp8_kernels_simd_store_i16x8, vp8_kernels_simd_load_i32x4, vp8_kernels_simd_store_i32x4, vp8_kernels_simd_plane_copy_u8x16, vp8_kernels_simd_plane_fill_u8x16, vp8_kernels_simd_extend_plane_border_u8x16, vp8_kernels_simd_predict_inter_copy_16x16_u8x16, vp8_kernels_simd_predict_inter_copy_8x8_u8x16, vp8_kernels_simd_predict_inter_copy_4x4_u8x16, vp8_kernels_simd_add_residual_4x4_clamped_u8x16, vp8_kernels_simd_inverse_transform_dc_only_4x4_i16x16, vp8_kernels_simd_inverse_transform_4x4_batch_i32x4, vp8_kernels_simd_predict_y16x16_dc_u8x16, vp8_kernels_simd_predict_y16x16_vertical_u8x16, vp8_kernels_simd_predict_y16x16_horizontal_u8x16, vp8_kernels_simd_predict_y16x16_true_motion_u8x16, vp8_kernels_simd_predict_y4x4_dc_u8x16, vp8_kernels_simd_predict_y4x4_true_motion_u8x16, vp8_kernels_simd_predict_y4x4_vertical_edge_u8x16, vp8_kernels_simd_predict_y4x4_horizontal_edge_u8x16, vp8_kernels_simd_predict_y4x4_down_left_u8x16, vp8_kernels_simd_predict_y4x4_down_right_u8x16, vp8_kernels_simd_predict_y4x4_vertical_right_u8x16, vp8_kernels_simd_predict_y4x4_vertical_left_u8x16, vp8_kernels_simd_predict_y4x4_horizontal_down_u8x16, vp8_kernels_simd_predict_y4x4_horizontal_up_u8x16, vp8_kernels_simd_predict_uv8x8_dc_u8x16, vp8_kernels_simd_predict_uv8x8_vertical_u8x16, vp8_kernels_simd_predict_uv8x8_horizontal_u8x16, vp8_kernels_simd_predict_uv8x8_true_motion_u8x16`。
- 本次汇编快照中 `__uya_memcpy` 出现 32 次。后续若编译器或优化级别改变，应重新检查实际热路径指令。

## 默认启用判断

当前记录不允许把任何 SIMD kernel 放进默认 dispatcher。默认启用还需要对应 kernel 的 scalar-vs-simd 正确性、生成代码检查和 benchmark 阈值结果同时通过。
