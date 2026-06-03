#!/usr/bin/env python3
"""Optional libvpx/vpxdec differential check for manifest fixtures."""

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


def run_vpxdec(vpxdec: str, ivf_path: Path, yuv_path: Path) -> None:
    command = [
        vpxdec,
        "--codec=vp8",
        "--i420",
        "-o",
        str(yuv_path),
        str(ivf_path),
    ]
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if result.returncode != 0:
        output = result.stdout.strip()
        raise RuntimeError(f"vpxdec failed for {ivf_path.name}: {output}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print("usage: vpxdiff.py <out-dir>", file=sys.stderr)
        return 2

    vpxdec = shutil.which("vpxdec")
    if vpxdec is None:
        print("skip: vpxdec not found")
        return 0

    manifest_samples = load_vpxdec_compatible_samples()
    if not manifest_samples:
        print("skip: no vpxdec_compatible samples in fixtures/manifest.json")
        return 0

    out_dir = Path(argv[1])
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    samples_by_name = {sample.name: sample for sample in tiny_ivf_md5.SAMPLES}
    failures = []
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
