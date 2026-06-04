#!/usr/bin/env python3
"""Verify release version metadata, CLI output, and release notes stay aligned."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REQUIRED_CHANGELOG_PHRASES = (
    "### Release notes",
    "### Supported scope",
    "### Known limits",
    "not a full VP8 conformance suite",
    "one-frame I420-to-IVF keyframe encoder",
    "minimal WebM VP8 subset",
    "forced SIMD",
    "optional libvpx differential",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def read_single_line(path: Path) -> str:
    require(path.exists(), f"{path} does not exist")
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    require(len(lines) == 1, f"{path} must contain exactly one non-empty line")
    return lines[0]


def main(argv: list[str]) -> int:
    if len(argv) != 5:
        print(
            "usage: release_notes.py <VERSION> <CHANGELOG.md> <docs/cli.md> <vp8uya-bin>",
            file=sys.stderr,
        )
        return 2

    version_path = Path(argv[1])
    changelog_path = Path(argv[2])
    cli_doc_path = Path(argv[3])
    bin_path = Path(argv[4])

    version = read_single_line(version_path)
    require(version[0].isdigit(), f"{version_path} must start with a numeric version")

    completed = subprocess.run(
        [str(bin_path), "version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=True,
    )
    expected_output = f"vp8uya {version}"
    require(
        completed.stdout.strip() == expected_output,
        f"version output mismatch: expected {expected_output!r}, got {completed.stdout.strip()!r}",
    )

    cli_doc = cli_doc_path.read_text(encoding="utf-8")
    require(expected_output in cli_doc, f"{cli_doc_path} does not document {expected_output!r}")

    require(changelog_path.exists(), f"{changelog_path} does not exist")
    changelog = changelog_path.read_text(encoding="utf-8")
    require(
        f"## {version} - " in changelog,
        f"{changelog_path} does not contain a dated section for {version}",
    )
    for phrase in REQUIRED_CHANGELOG_PHRASES:
        require(phrase in changelog, f"{changelog_path} is missing release note phrase: {phrase}")

    print(f"release-notes result=ok version={version} changelog={changelog_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
