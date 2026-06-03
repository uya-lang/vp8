#!/usr/bin/env python3
"""Generate and inspect C/assembly for the current portable SIMD helpers."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_UYA = REPO_ROOT.parent / "uya" / "bin" / "uya"
DEFAULT_SOURCE = Path("src/vp8_kernels_simd_test.uya")
DEFAULT_OUT_DIR = Path("build/simd-codegen")
DEFAULT_REPORT = Path("docs/simd_codegen.md")

HELPERS = (
    {
        "name": "load_u8x16",
        "symbol": "vp8_kernels_simd_load_u8x16",
        "kind": "load",
        "vector_struct": "struct uya_simd_vector_uint8_t_16",
    },
    {
        "name": "store_u8x16",
        "symbol": "vp8_kernels_simd_store_u8x16",
        "kind": "store",
        "vector_struct": "struct uya_simd_vector_uint8_t_16",
    },
    {
        "name": "load_i16x8",
        "symbol": "vp8_kernels_simd_load_i16x8",
        "kind": "load",
        "vector_struct": "struct uya_simd_vector_int16_t_8",
    },
    {
        "name": "store_i16x8",
        "symbol": "vp8_kernels_simd_store_i16x8",
        "kind": "store",
        "vector_struct": "struct uya_simd_vector_int16_t_8",
    },
    {
        "name": "load_i32x4",
        "symbol": "vp8_kernels_simd_load_i32x4",
        "kind": "load",
        "vector_struct": "struct uya_simd_vector_int32_t_4",
    },
    {
        "name": "store_i32x4",
        "symbol": "vp8_kernels_simd_store_i32x4",
        "kind": "store",
        "vector_struct": "struct uya_simd_vector_int32_t_4",
    },
)

SIMD_KERNELS = (
    {
        "name": "plane_copy_u8x16",
        "symbol": "vp8_kernels_simd_plane_copy_u8x16",
    },
    {
        "name": "plane_fill_u8x16",
        "symbol": "vp8_kernels_simd_plane_fill_u8x16",
    },
    {
        "name": "extend_plane_border_u8x16",
        "symbol": "vp8_kernels_simd_extend_plane_border_u8x16",
    },
    {
        "name": "predict_inter_copy_16x16_u8x16",
        "symbol": "vp8_kernels_simd_predict_inter_copy_16x16_u8x16",
    },
    {
        "name": "predict_inter_copy_8x8_u8x16",
        "symbol": "vp8_kernels_simd_predict_inter_copy_8x8_u8x16",
    },
    {
        "name": "predict_inter_copy_4x4_u8x16",
        "symbol": "vp8_kernels_simd_predict_inter_copy_4x4_u8x16",
    },
    {
        "name": "predict_luma_subpixel_horizontal_u8x16",
        "symbol": "vp8_kernels_simd_predict_luma_subpixel_horizontal_u8x16",
    },
    {
        "name": "add_residual_4x4_clamped_u8x16",
        "symbol": "vp8_kernels_simd_add_residual_4x4_clamped_u8x16",
    },
    {
        "name": "inverse_transform_dc_only_4x4_i16x16",
        "symbol": "vp8_kernels_simd_inverse_transform_dc_only_4x4_i16x16",
    },
    {
        "name": "inverse_transform_4x4_batch_i32x4",
        "symbol": "vp8_kernels_simd_inverse_transform_4x4_batch_i32x4",
    },
    {
        "name": "predict_y16x16_dc_u8x16",
        "symbol": "vp8_kernels_simd_predict_y16x16_dc_u8x16",
    },
    {
        "name": "predict_y16x16_vertical_u8x16",
        "symbol": "vp8_kernels_simd_predict_y16x16_vertical_u8x16",
    },
    {
        "name": "predict_y16x16_horizontal_u8x16",
        "symbol": "vp8_kernels_simd_predict_y16x16_horizontal_u8x16",
    },
    {
        "name": "predict_y16x16_true_motion_u8x16",
        "symbol": "vp8_kernels_simd_predict_y16x16_true_motion_u8x16",
    },
    {
        "name": "predict_y4x4_dc_u8x16",
        "symbol": "vp8_kernels_simd_predict_y4x4_dc_u8x16",
    },
    {
        "name": "predict_y4x4_true_motion_u8x16",
        "symbol": "vp8_kernels_simd_predict_y4x4_true_motion_u8x16",
    },
    {
        "name": "predict_y4x4_vertical_edge_u8x16",
        "symbol": "vp8_kernels_simd_predict_y4x4_vertical_edge_u8x16",
    },
    {
        "name": "predict_y4x4_horizontal_edge_u8x16",
        "symbol": "vp8_kernels_simd_predict_y4x4_horizontal_edge_u8x16",
    },
    {
        "name": "predict_y4x4_down_left_u8x16",
        "symbol": "vp8_kernels_simd_predict_y4x4_down_left_u8x16",
    },
    {
        "name": "predict_y4x4_down_right_u8x16",
        "symbol": "vp8_kernels_simd_predict_y4x4_down_right_u8x16",
    },
    {
        "name": "predict_y4x4_vertical_right_u8x16",
        "symbol": "vp8_kernels_simd_predict_y4x4_vertical_right_u8x16",
    },
    {
        "name": "predict_y4x4_vertical_left_u8x16",
        "symbol": "vp8_kernels_simd_predict_y4x4_vertical_left_u8x16",
    },
    {
        "name": "predict_y4x4_horizontal_down_u8x16",
        "symbol": "vp8_kernels_simd_predict_y4x4_horizontal_down_u8x16",
    },
    {
        "name": "predict_y4x4_horizontal_up_u8x16",
        "symbol": "vp8_kernels_simd_predict_y4x4_horizontal_up_u8x16",
    },
    {
        "name": "predict_uv8x8_dc_u8x16",
        "symbol": "vp8_kernels_simd_predict_uv8x8_dc_u8x16",
    },
    {
        "name": "predict_uv8x8_vertical_u8x16",
        "symbol": "vp8_kernels_simd_predict_uv8x8_vertical_u8x16",
    },
    {
        "name": "predict_uv8x8_horizontal_u8x16",
        "symbol": "vp8_kernels_simd_predict_uv8x8_horizontal_u8x16",
    },
    {
        "name": "predict_uv8x8_true_motion_u8x16",
        "symbol": "vp8_kernels_simd_predict_uv8x8_true_motion_u8x16",
    },
)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inspect UYA SIMD helper C/assembly lowering")
    parser.add_argument("--uya", type=Path, default=DEFAULT_UYA, help="UYA compiler path")
    parser.add_argument("--cc", default=os.environ.get("CC", "cc"), help="C compiler used for assembly snapshot")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="UYA test source to compile")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="directory for generated snapshots")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="markdown report to write")
    return parser.parse_args(argv[1:])


def run_command(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def find_generated_c_path(output: str) -> Path:
    match = re.search(r"代码生成完成:\s*(\S+)", output)
    if match is None:
        raise RuntimeError("could not find generated C path in UYA output")
    path = Path(match.group(1))
    if not path.exists():
        raise RuntimeError(f"generated C path does not exist: {path}")
    return path


def require_tool(path_or_name: str, label: str) -> None:
    path = Path(path_or_name)
    if path.is_absolute() or path.parent != Path("."):
        if not path.exists():
            raise RuntimeError(f"{label} not found: {path}")
        return
    if shutil.which(path_or_name) is None:
        raise RuntimeError(f"{label} not found in PATH: {path_or_name}")


def inspect_c(c_text: str) -> list[dict[str, object]]:
    results = []
    for helper in HELPERS:
        symbol = helper["symbol"]
        vector_struct = helper["vector_struct"]
        kind = helper["kind"]
        if symbol not in c_text:
            raise RuntimeError(f"missing generated C symbol: {symbol}")
        if vector_struct not in c_text:
            raise RuntimeError(f"missing generated C vector struct for {symbol}: {vector_struct}")

        if kind == "load":
            lowering_pattern = "__uya_memcpy(&__uya_simd_load_"
        else:
            lowering_pattern = "__uya_memcpy((void*)(dst), &__uya_simd_store_"
        lowering = "memcpy" if lowering_pattern in c_text else "unknown"
        if lowering != "memcpy":
            raise RuntimeError(f"unexpected C lowering for {symbol}; expected {lowering_pattern}")

        results.append(
            {
                "name": helper["name"],
                "symbol": symbol,
                "kind": kind,
                "vector_struct": vector_struct,
                "c_lowering": lowering,
            }
        )
    return results


def inspect_kernel_symbols(c_text: str) -> list[dict[str, str]]:
    results = []
    for kernel in SIMD_KERNELS:
        symbol = kernel["symbol"]
        if symbol not in c_text:
            raise RuntimeError(f"missing generated C SIMD kernel symbol: {symbol}")
        results.append({"name": kernel["name"], "symbol": symbol})
    return results


def inspect_assembly(asm_text: str) -> list[str]:
    labels = []
    for entry in HELPERS + SIMD_KERNELS:
        label = f"{entry['symbol']}:"
        if label not in asm_text:
            raise RuntimeError(f"missing generated assembly label: {label}")
        labels.append(label)
    return labels


def write_report(
    report_path: Path,
    source: Path,
    generated_c: Path,
    generated_asm: Path,
    c_results: list[dict[str, object]],
    kernel_results: list[dict[str, str]],
    asm_labels: list[str],
    c_memcpy_mentions: int,
    asm_memcpy_mentions: int,
) -> None:
    rows = []
    for result in c_results:
        rows.append(
            "| {name} | `{symbol}` | `{vector_struct}` | {c_lowering} |".format(**result)
        )
    kernel_rows = []
    for result in kernel_results:
        kernel_rows.append("| {name} | `{symbol}` |".format(**result))

    report = f"""# SIMD 生成代码检查记录

## 当前检查对象

- UYA 源：`{source.as_posix()}`
- 生成 C 快照：`{generated_c.as_posix()}`
- 生成汇编快照：`{generated_asm.as_posix()}`
- 复现命令：`make check-simd-codegen`

## C lowering 结论

| helper | generated C symbol | vector struct | load/store lowering |
| --- | --- | --- | --- |
{chr(10).join(rows)}

检查结果：

- 6 个 portable SIMD load/store helper 都生成了稳定的 C 符号。
- 当前 C99 后端将 `@vector.load` / `@vector.store` 通过 `__uya_memcpy` 表达，本次生成 C 中 `__uya_memcpy` 出现 {c_memcpy_mentions} 次。
- 这条记录只证明当前 helper 可生成、可链接、可测试，并记录了实际 lowering；它不证明这些 helper 已经是单条硬件 SIMD load/store。

## SIMD kernel 符号快照

| kernel | generated C symbol |
| --- | --- |
{chr(10).join(kernel_rows)}

检查结果：

- 当前 plane copy/fill/border extension/inter copy/sub-pixel horizontal/residual add clamp/DC-only inverse transform/4x4 inverse DCT batch/Y16x16/Y4x4/UV8x8 predictor SIMD kernel 都生成了稳定 C 符号，并在汇编快照中检测到对应 label。
- `plane_copy_u8x16` 以 16 字节 vector load/store 处理整块，尾部保留 scalar copy。
- `plane_fill_u8x16` 以 `@vector.splat` + 16 字节 vector store 处理整块，尾部保留 scalar fill。
- `extend_plane_border_u8x16` 复用 16 字节 plane fill/copy helper 处理左右边界和顶部/底部复制。
- `predict_inter_copy_16x16/8x8/4x4_u8x16` 覆盖 VP8 integer-pixel inter copy block 尺寸；16x16 复用 plane copy，8x8 两行一组，4x4 单块表达。
- `predict_luma_subpixel_horizontal_u8x16` 使用 `i32x4` 执行 4 像素一组的 VP8 luma 六抽头水平滤波；当前 narrow-store 缺口下逐 lane clamp/store。
- `add_residual_4x4_clamped_u8x16` 使用 `i16x16` signed saturating vector add，因当前缺少 narrow-to-u8 vector path，最终 clamp/store 仍逐 lane 完成。
- `inverse_transform_dc_only_4x4_i16x16` 使用 `i16x16` splat/store 填充 4x4 residual block。
- `inverse_transform_4x4_batch_i32x4` 使用 `i32x4` 执行两阶段 inverse DCT 算术；因当前缺少 shuffle/transpose，4x4 转置仍通过小数组 gather/scatter 完成。
- `predict_y16x16_dc_u8x16` / `vertical` / `horizontal` 复用 16 字节 fill/copy helper；`true_motion` 使用 `i16x16` 行向量计算并逐 lane clamp/store。
- `predict_y4x4_*_u8x16` 覆盖 DC/TM/VE/HE/DL/DR/VR/VL/HD/HU；4x4 block 以 `u8x16` 表达，stride 为 4 时直接 store，通用 stride 通过小数组 scatter。
- `predict_uv8x8_*_u8x16` 覆盖 DC/vertical/horizontal/true_motion；8x8 block 以两行一组 `u8x16` 表达，stride 为 8 时直接 store，通用 stride 通过两行 scatter。
- 这些 kernel 目前只作为 forced/测试用 portable SIMD 实现记录，不进入默认 dispatcher。

## 汇编快照结论

- `cc -std=c99 -O0 -g -fno-builtin -S` 可从生成 C 产出汇编快照。
- 汇编中检测到 {len(asm_labels)} 个 SIMD helper/kernel label：`{", ".join(label[:-1] for label in asm_labels)}`。
- 本次汇编快照中 `__uya_memcpy` 出现 {asm_memcpy_mentions} 次。后续若编译器或优化级别改变，应重新检查实际热路径指令。

## 默认启用判断

当前记录不允许把任何 SIMD kernel 放进默认 dispatcher。默认启用还需要对应 kernel 的 scalar-vs-simd 正确性、生成代码检查和 benchmark 阈值结果同时通过。
"""
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        require_tool(str(args.uya), "UYA compiler")
        require_tool(args.cc, "C compiler")

        source = args.source
        out_dir = args.out_dir
        report_path = args.report
        if not source.is_absolute():
            source = REPO_ROOT / source
        if not out_dir.is_absolute():
            out_dir = REPO_ROOT / out_dir
        if not report_path.is_absolute():
            report_path = REPO_ROOT / report_path

        shutil.rmtree(out_dir, ignore_errors=True)
        out_dir.mkdir(parents=True)

        uya_cmd = [str(args.uya), "test", str(source.relative_to(REPO_ROOT))]
        completed = run_command(uya_cmd, REPO_ROOT)
        if completed.returncode != 0:
            raise RuntimeError(
                f"UYA SIMD test failed with exit {completed.returncode}:\n{completed.stdout.strip()}"
            )

        generated_tmp_c = find_generated_c_path(completed.stdout)
        generated_c = out_dir / "vp8_kernels_simd_test.c"
        shutil.copyfile(generated_tmp_c, generated_c)

        generated_asm = out_dir / "vp8_kernels_simd_test.s"
        cc_cmd = [
            args.cc,
            "-std=c99",
            "-O0",
            "-g",
            "-fno-builtin",
            "-S",
            str(generated_c),
            "-o",
            str(generated_asm),
        ]
        cc_completed = run_command(cc_cmd, REPO_ROOT)
        if cc_completed.returncode != 0:
            raise RuntimeError(
                f"assembly generation failed with exit {cc_completed.returncode}:\n"
                f"{cc_completed.stdout.strip()}"
            )

        c_text = generated_c.read_text(encoding="utf-8")
        asm_text = generated_asm.read_text(encoding="utf-8", errors="replace")
        c_results = inspect_c(c_text)
        kernel_results = inspect_kernel_symbols(c_text)
        asm_labels = inspect_assembly(asm_text)
        c_memcpy_mentions = c_text.count("__uya_memcpy")
        asm_memcpy_mentions = asm_text.count("__uya_memcpy")

        manifest = {
            "source": str(source.relative_to(REPO_ROOT)),
            "generated_c": str(generated_c.relative_to(REPO_ROOT)),
            "generated_asm": str(generated_asm.relative_to(REPO_ROOT)),
            "helpers": c_results,
            "simd_kernels": kernel_results,
            "c_memcpy_mentions": c_memcpy_mentions,
            "asm_memcpy_mentions": asm_memcpy_mentions,
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        write_report(
            report_path,
            source.relative_to(REPO_ROOT),
            generated_c.relative_to(REPO_ROOT),
            generated_asm.relative_to(REPO_ROOT),
            c_results,
            kernel_results,
            asm_labels,
            c_memcpy_mentions,
            asm_memcpy_mentions,
        )

        print(f"simd-codegen source={source.relative_to(REPO_ROOT)}")
        print(f"simd-codegen generated_c={generated_c.relative_to(REPO_ROOT)}")
        print(f"simd-codegen generated_asm={generated_asm.relative_to(REPO_ROOT)}")
        print(f"simd-codegen report={report_path.relative_to(REPO_ROOT)}")
        print(
            f"simd-codegen helpers={len(c_results)} kernels={len(kernel_results)} "
            f"c_memcpy={c_memcpy_mentions} asm_memcpy={asm_memcpy_mentions}"
        )
        print("simd-codegen result=ok")
        return 0
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
