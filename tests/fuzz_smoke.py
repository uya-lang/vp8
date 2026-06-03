#!/usr/bin/env python3
"""Deterministic fuzz smoke for CLI malformed-input handling."""

from __future__ import annotations

import json
import random
import shutil
import struct
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SEED = 0x565038
RAW_IVF_CASES = 32
RANDOM_PAYLOAD_CASES = 32
ALLOWED_RETURN_CODES = {0, 2}


def ivf_with_payload(payload: bytes) -> bytes:
    out = bytearray()
    out.extend(b"DKIF")
    out.extend(struct.pack("<H", 0))
    out.extend(struct.pack("<H", 32))
    out.extend(b"VP80")
    out.extend(struct.pack("<H", 16))
    out.extend(struct.pack("<H", 16))
    out.extend(struct.pack("<I", 30))
    out.extend(struct.pack("<I", 1))
    out.extend(struct.pack("<I", 1))
    out.extend(struct.pack("<I", 0))
    out.extend(struct.pack("<I", len(payload)))
    out.extend(struct.pack("<Q", 0))
    out.extend(payload)
    return bytes(out)


def randbytes(rng: random.Random, length: int) -> bytes:
    return bytes(rng.randrange(0, 256) for _ in range(length))


def run_command(command: list[str]) -> tuple[int, str]:
    completed = subprocess.run(
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return completed.returncode, completed.stdout


def check_return(name: str, action: str, command: list[str]) -> dict[str, object]:
    returncode, output = run_command(command)
    return {
        "name": name,
        "action": action,
        "returncode": returncode,
        "output": output.strip(),
        "ok": returncode in ALLOWED_RETURN_CODES,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: fuzz_smoke.py <vp8uya-bin> <out-dir>", file=sys.stderr)
        return 2

    bin_path = Path(argv[1])
    out_dir = Path(argv[2])
    if not bin_path.exists():
        print(f"error: binary not found: {bin_path}", file=sys.stderr)
        return 2

    if out_dir.exists():
        shutil.rmtree(out_dir)
    corpus_dir = out_dir / "corpus"
    corpus_dir.mkdir(parents=True)

    rng = random.Random(SEED)
    results = []

    for index in range(RAW_IVF_CASES):
        name = f"raw-ivf-{index:02d}"
        path = corpus_dir / f"{name}.ivf"
        path.write_bytes(randbytes(rng, rng.randrange(1, 96)))
        results.append(check_return(name, "info", [str(bin_path), "info", str(path)]))

    for index in range(RANDOM_PAYLOAD_CASES):
        name = f"random-payload-{index:02d}"
        path = corpus_dir / f"{name}.ivf"
        payload = randbytes(rng, rng.randrange(0, 80))
        path.write_bytes(ivf_with_payload(payload))
        results.append(check_return(name, "info", [str(bin_path), "info", str(path)]))
        results.append(check_return(name, "decode", [str(bin_path), "decode", str(path), "--yuv", str(out_dir / f"{name}.yuv")]))

    report = {
        "seed": SEED,
        "raw_ivf_cases": RAW_IVF_CASES,
        "random_payload_cases": RANDOM_PAYLOAD_CASES,
        "results": results,
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    failures = [result for result in results if not result["ok"]]
    if failures:
        for failure in failures:
            print(
                f"{failure['name']} {failure['action']}: "
                f"exit {failure['returncode']} output {failure['output']!r}",
                file=sys.stderr,
            )
        return 1

    print(
        f"fuzz-smoke seed={SEED} raw_ivf={RAW_IVF_CASES} "
        f"random_payload={RANDOM_PAYLOAD_CASES} commands={len(results)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
