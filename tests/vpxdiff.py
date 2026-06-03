#!/usr/bin/env python3
"""Optional libvpx differential checks for generated VP8 fixtures."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = REPO_ROOT / "fixtures" / "manifest.json"
TESTS_DIR = REPO_ROOT / "tests"

sys.path.insert(0, str(TESTS_DIR))
import tiny_ivf_md5  # noqa: E402


def load_vpxdec_compatible_samples() -> list[dict[str, object]]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [sample for sample in manifest["samples"] if sample.get("vpxdec_compatible", False)]


def run_checked(command: list[str], *, label: str) -> None:
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        output = result.stdout.strip()
        raise RuntimeError(f"{label} failed: {output}")


def run_vpxdec(vpxdec: str, ivf_path: Path, yuv_path: Path) -> None:
    command = [
        vpxdec,
        "--codec=vp8",
        "--i420",
        "-o",
        str(yuv_path),
        str(ivf_path),
    ]
    run_checked(command, label=f"vpxdec {ivf_path.name}")


def run_vp8uya_decode(vp8uya: Path, ivf_path: Path, yuv_path: Path) -> None:
    command = [
        str(vp8uya),
        "decode",
        str(ivf_path),
        "--yuv",
        str(yuv_path),
    ]
    run_checked(command, label=f"vp8uya decode {ivf_path.name}")


def write_gray_i420(path: Path, width: int, height: int) -> None:
    y_size = width * height
    uv_size = (width // 2) * (height // 2)
    path.write_bytes(bytes([128]) * (y_size + uv_size + uv_size))


def run_vpxenc_gray_sample(vpxenc: str, out_dir: Path, failures: list[str]) -> None:
    name = "vpxenc-gray-16x16"
    yuv_path = out_dir / f"{name}.i420"
    ivf_path = out_dir / f"{name}.ivf"
    write_gray_i420(yuv_path, 16, 16)
    command = [
        vpxenc,
        "--codec=vp8",
        "--ivf",
        "--i420",
        "--width=16",
        "--height=16",
        "--limit=1",
        "--fps=30/1",
        "--kf-min-dist=0",
        "--kf-max-dist=0",
        "--lag-in-frames=0",
        "--end-usage=q",
        "--cq-level=63",
        "--min-q=55",
        "--max-q=63",
        "--token-parts=0",
        "--cpu-used=16",
        "--static-thresh=1000",
        "--auto-alt-ref=0",
        "--disable-warning-prompt",
        "--quiet",
        "-o",
        str(ivf_path),
        str(yuv_path),
    ]
    try:
        run_checked(command, label=name)
    except RuntimeError as exc:
        failures.append(str(exc))


def main(argv: list[str]) -> int:
    if len(argv) not in (2, 3):
        print("usage: vpxdiff.py <out-dir> [vp8uya-bin]", file=sys.stderr)
        return 2

    vpxdec = shutil.which("vpxdec")
    vpxenc = shutil.which("vpxenc")
    if vpxdec is None or vpxenc is None:
        missing = "vpxdec" if vpxdec is None else "vpxenc"
        print(f"skip: {missing} not found")
        return 0
    vp8uya = Path(argv[2]) if len(argv) == 3 else REPO_ROOT / "build" / "vp8uya"
    if not vp8uya.is_absolute():
        vp8uya = REPO_ROOT / vp8uya
    if not vp8uya.exists():
        print(f"error: vp8uya binary not found: {vp8uya}", file=sys.stderr)
        return 2

    out_dir = Path(argv[1])
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    failures = []
    run_vpxenc_gray_sample(vpxenc, out_dir, failures)
    if not failures:
        ivf_path = out_dir / "vpxenc-gray-16x16.ivf"
        uya_yuv_path = out_dir / "vpxenc-gray-16x16.vp8uya.yuv"
        vpx_yuv_path = out_dir / "vpxenc-gray-16x16.vpxdec.yuv"
        try:
            run_vp8uya_decode(vp8uya, ivf_path, uya_yuv_path)
            run_vpxdec(vpxdec, ivf_path, vpx_yuv_path)
            uya_digest = hashlib.md5(uya_yuv_path.read_bytes()).hexdigest()
            vpx_digest = hashlib.md5(vpx_yuv_path.read_bytes()).hexdigest()
            if uya_yuv_path.read_bytes() != vpx_yuv_path.read_bytes():
                failures.append(f"vpxenc-gray-16x16: vp8uya {uya_digest} vpxdec {vpx_digest}")
            else:
                print(f"vpxenc-gray-16x16 {uya_digest}")
        except RuntimeError as exc:
            failures.append(str(exc))

    manifest_samples = load_vpxdec_compatible_samples()
    samples_by_name = {sample.name: sample for sample in tiny_ivf_md5.SAMPLES}
    for manifest_sample in manifest_samples:
        name = str(manifest_sample["name"])
        sample = samples_by_name.get(name)
        if sample is None:
            failures.append(f"{name}: missing generated sample definition")
            continue

        ivf_path = out_dir / f"{name}.ivf"
        yuv_path = out_dir / f"{name}.vpxdec.yuv"
        ivf_path.write_bytes(tiny_ivf_md5.make_ivf(sample))
        try:
            run_vpxdec(vpxdec, ivf_path, yuv_path)
        except RuntimeError as exc:
            failures.append(str(exc))
            continue

        digest = hashlib.md5(yuv_path.read_bytes()).hexdigest()
        expected = str(manifest_sample["yuv_md5"])
        if digest != expected:
            failures.append(f"{name}: expected {expected} got {digest}")
        else:
            print(f"{name} {digest}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
