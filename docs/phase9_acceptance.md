# Phase 9 SIMD 框架验收记录

## 运行时切换 scalar/SIMD

- CLI 支持 `--force-scalar` / `--force-simd`，环境变量支持 `VP8UYA_FORCE_SCALAR=1` / `VP8UYA_FORCE_SIMD=1`。
- `src/main.uya` 通过 `make_scalar_kernel_table`、`make_forced_simd_kernel_table` 和 `make_decoder_with_kernel_table` 构造 decoder。
- `src/vp8_kernels_dispatch_test.uya` 覆盖 kernel table entry 调用、默认 scalar 表、forced SIMD 表和无效 entry 拒绝。

## SIMD 不可用时回退 scalar

- 当前没有已注册的默认 SIMD kernel。
- `make_forced_simd_kernel_table` 当前返回 scalar table。
- `src/vp8_kernels_dispatch_test.uya` 的 `forced SIMD kernel table falls back to scalar until SIMD kernels are registered` 覆盖该行为。

## benchmark scalar/SIMD 指标

- `make bench-smoke` 运行 `bench/decode_bench.py --repeats 1 --warmups 0 build/vp8uya build/bench`。
- benchmark 输出每个样本的 `mode=scalar` 和 `mode=simd` 行，并写入 `build/bench/results.ndjson` / `summary.json`。
- `make bench-smoke` 在当前树通过，且所有样本 MD5 校验通过。

## 默认 dispatcher 门禁

- `docs/simd_codegen.md` 记录当前 SIMD helper 生成 C/汇编检查结论；当前 load/store helper lowering 为 `__uya_memcpy`，不能作为默认启用收益证据。
- `bench/kernel_thresholds.json` 定义默认启用阈值和 `disabled_until_threshold_passes` 策略。
- `make check-simd-codegen` 和 `make check-kernel-thresholds` 在当前树通过。
- `make_default_kernel_table` 当前保持 scalar，未通过生成代码检查和 benchmark 阈值的 kernel 不进入默认 dispatcher。

## 本次验收命令

- `make check-simd-codegen`
- `make check-kernel-thresholds`
- `make test-scalar-vs-simd`
- `make bench-smoke`
- `make test`
