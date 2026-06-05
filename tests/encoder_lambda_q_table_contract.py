#!/usr/bin/env python3
"""Contract checks for the encoder lambda-vs-qindex table."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
TABLE_PATH = REPO_ROOT / "docs" / "encoder_lambda_q_table.json"
EXPECTED_ANCHORS = {
    16: 128,
    24: 160,
    32: 192,
    40: 224,
    48: 256,
}


def assert_int(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise AssertionError(f"{name} must be an integer")
    return value


def main() -> None:
    if not TABLE_PATH.exists():
        raise AssertionError(f"missing lambda table: {TABLE_PATH}")

    table = json.loads(TABLE_PATH.read_text(encoding="utf-8"))
    if not isinstance(table, dict):
        raise AssertionError("lambda table must be a JSON object")

    assert table.get("version") == 1
    assert table.get("lambda_scale") == "q8"
    assert table.get("qindex_min") == 0
    assert table.get("qindex_max") == 127
    assert table.get("formula") == "lambda_q8 = 64 + 4 * qindex"

    entries = table.get("entries")
    if not isinstance(entries, list):
        raise AssertionError("entries must be a list")
    if len(entries) != 128:
        raise AssertionError(f"entries must cover qindex 0..127, got {len(entries)} rows")

    previous_lambda = -1
    for expected_qindex, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise AssertionError(f"entry {expected_qindex} must be an object")
        qindex = assert_int(f"entry {expected_qindex} qindex", entry.get("qindex"))
        lambda_q8 = assert_int(f"entry {expected_qindex} lambda_q8", entry.get("lambda_q8"))
        if qindex != expected_qindex:
            raise AssertionError(f"entry {expected_qindex} has qindex {qindex}")
        if lambda_q8 != 64 + (4 * qindex):
            raise AssertionError(f"qindex {qindex} lambda_q8 {lambda_q8} does not match fitted formula")
        if lambda_q8 <= previous_lambda:
            raise AssertionError(f"lambda_q8 must be strictly increasing at qindex {qindex}")
        previous_lambda = lambda_q8

    anchors = table.get("ladder_anchors")
    if not isinstance(anchors, list):
        raise AssertionError("ladder_anchors must be a list")
    actual_anchors = {
        assert_int(f"anchor {index} qindex", anchor.get("qindex")):
        assert_int(f"anchor {index} lambda_q8", anchor.get("lambda_q8"))
        for index, anchor in enumerate(anchors)
        if isinstance(anchor, dict)
    }
    if actual_anchors != EXPECTED_ANCHORS:
        raise AssertionError(f"unexpected ladder anchors: {actual_anchors}")


if __name__ == "__main__":
    main()
