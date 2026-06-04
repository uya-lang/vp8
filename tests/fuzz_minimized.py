#!/usr/bin/env python3
"""Run minimized deterministic fuzz corpus representatives."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import fuzz_smoke


REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_MANIFEST = REPO_ROOT / "fixtures" / "fuzz_minimized" / "manifest.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def bytes_from_hex(value: Any, field: str) -> bytes:
    require(isinstance(value, str), f"{field} must be a string")
    try:
        return bytes.fromhex(value)
    except ValueError as exc:
        raise RuntimeError(f"{field} must be hex") from exc


def materialize_case(case: dict[str, Any]) -> bytes:
    kind = case.get("kind")
    if kind == "raw-bytes":
        return bytes_from_hex(case.get("data_hex", ""), "data_hex")
    if kind == "ivf-payload":
        return fuzz_smoke.ivf_with_payload(bytes_from_hex(case.get("payload_hex", ""), "payload_hex"))
    raise RuntimeError(f"unknown minimized fuzz case kind: {kind}")


def command_for_action(bin_path: Path, out_dir: Path, case_path: Path, name: str, action: str) -> list[str]:
    if action == "info":
        return [str(bin_path), "info", str(case_path)]
    if action == "decode":
        return [str(bin_path), "decode", str(case_path), "--yuv", str(out_dir / f"{name}.yuv")]
    raise RuntimeError(f"unknown minimized fuzz action: {action}")


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


def validate_manifest(manifest: dict[str, Any]) -> None:
    require(manifest.get("version") == 1, "manifest version must be 1")
    source = manifest.get("source")
    require(isinstance(source, dict), "source must be an object")
    require(source.get("seed") == fuzz_smoke.SEED, "source seed must match tests/fuzz_smoke.py")
    require(source.get("raw_ivf_cases") == fuzz_smoke.RAW_IVF_CASES, "source raw_ivf_cases must match tests/fuzz_smoke.py")
    require(
        source.get("random_payload_cases") == fuzz_smoke.RANDOM_PAYLOAD_CASES,
        "source random_payload_cases must match tests/fuzz_smoke.py",
    )
    cases = manifest.get("cases")
    require(isinstance(cases, list) and cases, "cases must be a non-empty list")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: fuzz_minimized.py <vp8uya-bin> <out-dir>", file=sys.stderr)
        return 2

    bin_path = Path(argv[1])
    out_dir = Path(argv[2])
    if not bin_path.exists():
        print(f"error: binary not found: {bin_path}", file=sys.stderr)
        return 2

    try:
        manifest = json.loads(CORPUS_MANIFEST.read_text(encoding="utf-8"))
        validate_manifest(manifest)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if out_dir.exists():
        shutil.rmtree(out_dir)
    corpus_dir = out_dir / "corpus"
    corpus_dir.mkdir(parents=True)

    results: list[dict[str, Any]] = []
    for case in manifest["cases"]:
        name = str(case["name"])
        case_path = corpus_dir / f"{name}.ivf"
        case_path.write_bytes(materialize_case(case))

        commands = case.get("commands")
        if not isinstance(commands, list) or not commands:
            print(f"error: {name} commands must be a non-empty list", file=sys.stderr)
            return 1

        for command_spec in commands:
            action = str(command_spec["action"])
            expected_exit = int(command_spec["expected_exit"])
            expected_output = str(command_spec["expected_output"])
            command = command_for_action(bin_path, out_dir, case_path, name, action)
            returncode, output = run_command(command)
            ok = returncode == expected_exit and expected_output in output
            results.append({
                "name": name,
                "action": action,
                "path": str(case_path),
                "bytes": case_path.stat().st_size,
                "returncode": returncode,
                "expected_exit": expected_exit,
                "expected_output": expected_output,
                "output": output.strip(),
                "ok": ok,
            })

    report = {
        "source": manifest["source"],
        "cases": len(manifest["cases"]),
        "commands": len(results),
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

    for result in results:
        print(
            f"{result['name']} {result['action']} bytes={result['bytes']} "
            f"exit={result['returncode']} {result['expected_output']}"
        )
    print(
        f"fuzz-minimized seed={manifest['source']['seed']} "
        f"cases={len(manifest['cases'])} commands={len(results)} "
        f"observed_classes={manifest['source']['observed_command_classes']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
