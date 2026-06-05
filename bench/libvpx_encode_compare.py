#!/usr/bin/env python3
"""Compare vp8uya encoder output against libvpx.

The first landed surface is the machine-readable metric contract used by the
future benchmark and threshold gate. Real sample execution is added later.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shlex
import shutil
import struct
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any
from typing import Callable
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DEPS_DIR = REPO_ROOT / "build" / "deps"
DEFAULT_VPX_TOOLS_ROOT = DEFAULT_DEPS_DIR / "vpx-tools-root"
DEFAULT_VPX_TOOLS_DIR = DEFAULT_VPX_TOOLS_ROOT / "usr" / "bin"
DEFAULT_Y4M_CACHE_DIR = REPO_ROOT / "build" / "real-y4m"
DEFAULT_I420_CACHE_DIR = REPO_ROOT / "build" / "libvpx-encode-compare" / "fixtures"
DEFAULT_VP8UYA_BIN = REPO_ROOT / "build" / "vp8uya"
DEFAULT_MANIFEST_PATH = REPO_ROOT / "fixtures" / "encoder_libvpx_real_samples.json"
DEFAULT_RUNS_DIR = REPO_ROOT / "build" / "libvpx-encode-compare" / "runs"
DEFAULT_REPRO_REPORT_PATH = REPO_ROOT / "build" / "libvpx-encode-compare" / "repro.md"
DEFAULT_RESULTS_NDJSON_PATH = REPO_ROOT / "build" / "libvpx-encode-compare" / "results.ndjson"
DEFAULT_SUMMARY_JSON_PATH = REPO_ROOT / "build" / "libvpx-encode-compare" / "summary.json"
DEFAULT_MARKDOWN_REPORT_PATH = REPO_ROOT / "docs" / "encoder_libvpx_compare_report.md"
LIBVPX_PRESET = "vpxenc --best"
REPEAT_STATISTIC = "median"

REQUIRED_RESULT_FIELDS = (
    "sample",
    "width",
    "height",
    "frames",
    "fps",
    "vp8uya_payload_bits",
    "libvpx_payload_bits",
    "vp8uya_bits_per_pixel",
    "libvpx_bits_per_pixel",
    "vp8uya_encode_elapsed_ns",
    "libvpx_encode_elapsed_ns",
    "psnr_y_db",
    "psnr_u_db",
    "psnr_v_db",
    "psnr_all_db",
    "bitrate_ratio",
    "vp8uya_psnr_y_db",
    "vp8uya_psnr_u_db",
    "vp8uya_psnr_v_db",
    "vp8uya_psnr_all_db",
    "libvpx_psnr_y_db",
    "libvpx_psnr_u_db",
    "libvpx_psnr_v_db",
    "libvpx_psnr_all_db",
    "psnr_all_delta_db",
    "ssim_y",
    "ssim_u",
    "ssim_v",
    "ssim_all",
    "vp8uya_ssim_y",
    "vp8uya_ssim_u",
    "vp8uya_ssim_v",
    "vp8uya_ssim_all",
    "libvpx_ssim_y",
    "libvpx_ssim_u",
    "libvpx_ssim_v",
    "libvpx_ssim_all",
    "vp8uya_fps",
    "libvpx_fps",
    "fps_ratio",
    "passed",
    "failure_reasons",
)

REQUIRED_SUMMARY_FIELDS = (
    "vp8uya_bits_per_pixel",
    "libvpx_bits_per_pixel",
    "vp8uya_psnr_all_db",
    "libvpx_psnr_all_db",
    "vp8uya_fps",
    "libvpx_fps",
    "vpxenc_version",
    "vpxdec_version",
)

HARD_THRESHOLD_FIELDS = (
    "bitrate_ratio",
    "psnr_all_delta_db",
    "fps_ratio",
)

THRESHOLDS = {
    "max_bitrate_ratio": 1.10,
    "min_psnr_all_delta_db": -0.50,
    "min_fps_ratio": 0.80,
}


def tool_lookup_result(path: str | None, source: str | None, error: str | None, attempted: list[str]) -> dict[str, Any]:
    return {
        "path": path,
        "source": source,
        "error": error,
        "attempted": attempted,
    }


def is_executable_file(path: Path) -> bool:
    return path.is_file() and os.access(path, os.X_OK)


def validate_vp8uya_binary(path: Path) -> dict[str, Any]:
    if is_executable_file(path):
        return {
            "ok": True,
            "path": str(path),
            "error": None,
        }
    return {
        "ok": False,
        "path": str(path),
        "error": f"vp8uya binary not found or not executable: {path}",
    }


def positive_int_arg(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def nonnegative_int_arg(value: str) -> int:
    try:
        parsed = int(value, 10)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a non-negative integer") from exc
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be a non-negative integer")
    return parsed


def run_command(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def first_nonempty_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return ""


def extract_help_version(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if "WebM Project VP8" in stripped and ("Encoder" in stripped or "Decoder" in stripped):
            return stripped
    return ""


def attach_tool_metadata(lookup: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(lookup)
    path = enriched.get("path")
    if path is None:
        enriched["version_returncode"] = None
        enriched["version_stdout"] = ""
        enriched["version_stderr"] = ""
        enriched["version"] = None
        enriched["probe_command"] = []
        enriched["probe_returncode"] = None
        enriched["probe_stdout"] = ""
        enriched["probe_stderr"] = ""
        return enriched

    version_completed = run_command([str(path), "--version"], REPO_ROOT)
    stdout = version_completed.stdout.strip()
    stderr = version_completed.stderr.strip()
    version_line = first_nonempty_line(stdout)
    if not version_line:
        version_line = first_nonempty_line(stderr)
    enriched["version_returncode"] = version_completed.returncode
    enriched["version_stdout"] = stdout
    enriched["version_stderr"] = stderr
    enriched["version"] = version_line
    enriched["version_source"] = "version" if version_completed.returncode == 0 else "version-error"

    if version_completed.returncode == 0:
        enriched["probe_command"] = [str(path), "--version"]
        enriched["probe_returncode"] = 0
        enriched["probe_stdout"] = stdout
        enriched["probe_stderr"] = stderr
        return enriched

    help_completed = run_command([str(path), "--help"], REPO_ROOT)
    help_stdout = help_completed.stdout.strip()
    help_stderr = help_completed.stderr.strip()
    enriched["probe_command"] = [str(path), "--help"]
    enriched["probe_returncode"] = help_completed.returncode
    enriched["probe_stdout"] = help_stdout
    enriched["probe_stderr"] = help_stderr
    help_version = extract_help_version(help_stdout)
    if not help_version:
        help_version = extract_help_version(help_stderr)
    if help_version:
        enriched["version"] = help_version
        enriched["version_source"] = "help"
    if help_completed.returncode != 0:
        enriched["error"] = f"{path} --help failed with exit {help_completed.returncode}"
    return enriched


def compact_tool_metadata(tool: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": tool.get("path"),
        "source": tool.get("source"),
        "version": tool.get("version"),
        "probe_returncode": tool.get("probe_returncode"),
        "error": tool.get("error"),
    }


def find_vpx_tool(
    name: str,
    env_var: str,
    *,
    env: Mapping[str, str] | None = None,
    path: str | None = None,
    extracted_dir: Path | None = None,
) -> dict[str, Any]:
    env_map = os.environ if env is None else env
    search_path = env_map.get("PATH", os.environ.get("PATH", "")) if path is None else path
    tool_dir = DEFAULT_VPX_TOOLS_DIR if extracted_dir is None else extracted_dir
    attempted: list[str] = []

    env_value = env_map.get(env_var)
    if env_value:
        attempted.append(env_value)
        env_path = Path(env_value)
        if is_executable_file(env_path):
            return tool_lookup_result(str(env_path), env_var, None, attempted)
        return tool_lookup_result(
            None,
            env_var,
            f"{env_var} points to a missing or non-executable {name}: {env_value}",
            attempted,
        )

    path_value = shutil.which(name, path=search_path)
    if path_value is not None:
        attempted.append(path_value)
        return tool_lookup_result(path_value, "PATH", None, attempted)

    extracted_path = tool_dir / name
    attempted.append(str(extracted_path))
    if is_executable_file(extracted_path):
        return tool_lookup_result(str(extracted_path), "extracted", None, attempted)

    return tool_lookup_result(
        None,
        None,
        f"{name} not found; set {env_var}, add {name} to PATH, or run "
        "python3 bench/libvpx_encode_compare.py --fetch-vpx-tools followed by "
        "python3 bench/libvpx_encode_compare.py --extract-vpx-tools to fetch vpx-tools",
        attempted,
    )


def fetch_vpx_tools(
    *,
    download_dir: Path = DEFAULT_DEPS_DIR,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    download_dir.mkdir(parents=True, exist_ok=True)
    command = ["apt-get", "download", "vpx-tools"]
    try:
        completed = runner(command, download_dir)
    except OSError as exc:
        return {
            "ok": False,
            "command": command,
            "download_dir": str(download_dir),
            "deb_files": [],
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }

    deb_files = sorted(download_dir.glob("vpx-tools_*.deb"))
    return {
        "ok": completed.returncode == 0 and len(deb_files) > 0,
        "command": command,
        "download_dir": str(download_dir),
        "deb_files": [str(path) for path in deb_files],
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def latest_vpx_tools_deb(deps_dir: Path) -> Path | None:
    debs = sorted(deps_dir.glob("vpx-tools_*.deb"))
    if not debs:
        return None
    return debs[-1]


def extract_vpx_tools(
    *,
    deps_dir: Path = DEFAULT_DEPS_DIR,
    extract_root: Path = DEFAULT_VPX_TOOLS_ROOT,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    deb = latest_vpx_tools_deb(deps_dir)
    if deb is None:
        return {
            "ok": False,
            "command": [],
            "deps_dir": str(deps_dir),
            "extract_root": str(extract_root),
            "vpxenc": str(extract_root / "usr" / "bin" / "vpxenc"),
            "vpxdec": str(extract_root / "usr" / "bin" / "vpxdec"),
            "returncode": None,
            "stdout": "",
            "stderr": "no vpx-tools .deb found",
        }

    deps_dir.mkdir(parents=True, exist_ok=True)
    extract_root.mkdir(parents=True, exist_ok=True)
    command = ["dpkg-deb", "-x", str(deb), str(extract_root)]
    try:
        completed = runner(command, deps_dir)
    except OSError as exc:
        return {
            "ok": False,
            "command": command,
            "deps_dir": str(deps_dir),
            "extract_root": str(extract_root),
            "vpxenc": str(extract_root / "usr" / "bin" / "vpxenc"),
            "vpxdec": str(extract_root / "usr" / "bin" / "vpxdec"),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }

    vpxenc = extract_root / "usr" / "bin" / "vpxenc"
    vpxdec = extract_root / "usr" / "bin" / "vpxdec"
    return {
        "ok": completed.returncode == 0 and is_executable_file(vpxenc) and is_executable_file(vpxdec),
        "command": command,
        "deps_dir": str(deps_dir),
        "extract_root": str(extract_root),
        "vpxenc": str(vpxenc),
        "vpxdec": str(vpxdec),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def prepare_sample_dirs(
    *,
    y4m_dir: Path = DEFAULT_Y4M_CACHE_DIR,
    i420_dir: Path = DEFAULT_I420_CACHE_DIR,
) -> dict[str, Any]:
    y4m_dir.mkdir(parents=True, exist_ok=True)
    i420_dir.mkdir(parents=True, exist_ok=True)
    return {
        "ok": y4m_dir.is_dir() and i420_dir.is_dir(),
        "y4m_cache_dir": str(y4m_dir),
        "i420_cache_dir": str(i420_dir),
    }


def load_sample_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ValueError(f"failed to read sample manifest {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"failed to parse sample manifest {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"sample manifest {path} must contain an object")
    samples = data.get("samples")
    if not isinstance(samples, list):
        raise ValueError(f"sample manifest {path} must contain a samples array")
    return data


def manifest_samples(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_samples = manifest.get("samples")
    if not isinstance(raw_samples, list):
        raise ValueError("sample manifest must contain a samples array")

    samples: list[dict[str, Any]] = []
    for index, raw_sample in enumerate(raw_samples):
        if not isinstance(raw_sample, dict):
            raise ValueError(f"sample manifest entry {index} must be an object")
        name = raw_sample.get("name")
        groups = raw_sample.get("groups")
        if not isinstance(name, str) or not name:
            raise ValueError(f"sample manifest entry {index} must have a non-empty name")
        if not isinstance(groups, list) or not all(isinstance(group, str) for group in groups):
            raise ValueError(f"sample manifest entry {name} must have string groups")
        samples.append(dict(raw_sample))
    return samples


def filter_samples_by_group(samples: list[dict[str, Any]], group: str | None) -> list[dict[str, Any]]:
    if group is None:
        return list(samples)
    return [sample for sample in samples if group in sample["groups"]]


def plan_sample_entries(samples: list[dict[str, Any]], frames_override: int | None) -> list[dict[str, Any]]:
    planned_samples: list[dict[str, Any]] = []
    for sample in samples:
        planned = dict(sample)
        if frames_override is not None:
            planned["manifest_frames"] = planned.get("frames")
            planned["frames"] = frames_override
        planned_samples.append(planned)
    return planned_samples


def dry_run_samples(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    group: str | None = None,
    frames_override: int | None = None,
    warmups: int = 0,
    repeats: int = 1,
) -> dict[str, Any]:
    try:
        manifest = load_sample_manifest(manifest_path)
        selected = filter_samples_by_group(manifest_samples(manifest), group)
    except ValueError as exc:
        return {
            "ok": False,
            "manifest_path": str(manifest_path),
            "group": group,
            "warmups": warmups,
            "repeats": repeats,
            "repeat_statistic": REPEAT_STATISTIC,
            "samples": [],
            "error": str(exc),
        }

    planned_samples = plan_sample_entries(selected, frames_override)

    return {
        "ok": True,
        "manifest_path": str(manifest_path),
        "group": group,
        "frames_override": frames_override,
        "warmups": warmups,
        "repeats": repeats,
        "repeat_statistic": REPEAT_STATISTIC,
        "samples": planned_samples,
        "sample_count": len(planned_samples),
    }


def sample_fps(sample: Mapping[str, Any]) -> str:
    fps = sample.get("fps", "30/1")
    if not isinstance(fps, str) or not fps:
        raise ValueError("sample fps must be a non-empty string")
    return fps


def http_download(url: str, dest: Path) -> None:
    with urllib.request.urlopen(url, timeout=60) as response:
        with dest.open("wb") as out:
            shutil.copyfileobj(response, out)


def sample_y4m_path(sample: Mapping[str, Any], y4m_dir: Path) -> Path:
    name = sample.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("sample name must be a non-empty string")
    return y4m_dir / f"{name}.y4m"


def download_y4m_sample(
    sample: Mapping[str, Any],
    *,
    y4m_dir: Path = DEFAULT_Y4M_CACHE_DIR,
    downloader: Callable[[str, Path], None] = http_download,
) -> dict[str, Any]:
    y4m_dir.mkdir(parents=True, exist_ok=True)
    try:
        url = sample["url"]
        if not isinstance(url, str) or not url:
            raise ValueError("sample url must be a non-empty string")
        final_path = sample_y4m_path(sample, y4m_dir)
    except (KeyError, ValueError) as exc:
        return {
            "ok": False,
            "cached": False,
            "path": "",
            "partial_path": "",
            "url": "",
            "error": str(exc),
        }

    partial_path = final_path.with_name(final_path.name + ".part")
    if final_path.exists():
        return {
            "ok": True,
            "cached": True,
            "path": str(final_path),
            "partial_path": str(partial_path),
            "url": url,
            "error": None,
        }

    if partial_path.exists():
        partial_path.unlink()

    try:
        downloader(url, partial_path)
        if not partial_path.exists() or partial_path.stat().st_size <= 0:
            raise RuntimeError("download produced an empty file")
        partial_path.replace(final_path)
        return {
            "ok": True,
            "cached": False,
            "path": str(final_path),
            "partial_path": str(partial_path),
            "url": url,
            "error": None,
        }
    except Exception as exc:
        if partial_path.exists():
            partial_path.unlink()
        return {
            "ok": False,
            "cached": False,
            "path": str(final_path),
            "partial_path": str(partial_path),
            "url": url,
            "error": str(exc),
        }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_y4m_sample_sha256(
    sample: Mapping[str, Any],
    *,
    y4m_dir: Path = DEFAULT_Y4M_CACHE_DIR,
) -> dict[str, Any]:
    try:
        expected = sample["sha256"]
        if not isinstance(expected, str) or len(expected) != 64:
            raise ValueError("sample sha256 must be a 64-character hex string")
        path = sample_y4m_path(sample, y4m_dir)
    except (KeyError, ValueError) as exc:
        return {
            "ok": False,
            "path": "",
            "expected_sha256": "",
            "actual_sha256": "",
            "error": str(exc),
        }

    if not path.exists():
        return {
            "ok": False,
            "path": str(path),
            "expected_sha256": expected,
            "actual_sha256": "",
            "error": f"missing downloaded sample: {path}",
        }

    actual = sha256_file(path)
    if actual == expected.lower():
        return {
            "ok": True,
            "path": str(path),
            "expected_sha256": expected.lower(),
            "actual_sha256": actual,
            "error": None,
        }

    bad_path = path.with_name(path.name + ".bad-sha256")
    if bad_path.exists():
        bad_path.unlink()
    path.replace(bad_path)
    return {
        "ok": False,
        "path": str(path),
        "bad_path": str(bad_path),
        "expected_sha256": expected.lower(),
        "actual_sha256": actual,
        "error": f"sha256 mismatch for {path}: expected {expected.lower()} got {actual}",
    }


def ensure_y4m_sample(
    sample: Mapping[str, Any],
    *,
    y4m_dir: Path = DEFAULT_Y4M_CACHE_DIR,
    downloader: Callable[[str, Path], None] = http_download,
) -> dict[str, Any]:
    try:
        path = sample_y4m_path(sample, y4m_dir)
    except ValueError as exc:
        return {
            "ok": False,
            "download": None,
            "sha256": None,
            "error": str(exc),
        }

    if path.exists():
        sha_report = verify_y4m_sample_sha256(sample, y4m_dir=y4m_dir)
        if sha_report["ok"]:
            return {
                "ok": True,
                "download": {
                    "ok": True,
                    "cached": True,
                    "path": str(path),
                    "partial_path": str(path.with_name(path.name + ".part")),
                    "url": sample.get("url", ""),
                    "error": None,
                },
                "sha256": sha_report,
                "error": None,
            }
        return {
            "ok": False,
            "download": None,
            "sha256": sha_report,
            "error": sha_report["error"],
        }

    download_report = download_y4m_sample(sample, y4m_dir=y4m_dir, downloader=downloader)
    if not download_report["ok"]:
        return {
            "ok": False,
            "download": download_report,
            "sha256": None,
            "error": download_report["error"],
        }
    sha_report = verify_y4m_sample_sha256(sample, y4m_dir=y4m_dir)
    return {
        "ok": sha_report["ok"],
        "download": download_report,
        "sha256": sha_report,
        "error": None if sha_report["ok"] else sha_report["error"],
    }


def sample_i420_path(sample: Mapping[str, Any], i420_dir: Path) -> Path:
    name = sample.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("sample name must be a non-empty string")
    return i420_dir / f"{name}.i420"


def sample_vp8uya_ivf_path(sample: Mapping[str, Any], runs_dir: Path) -> Path:
    name = sample.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("sample name must be a non-empty string")
    return runs_dir / f"{name}.vp8uya.ivf"


def sample_libvpx_ivf_path(sample: Mapping[str, Any], runs_dir: Path) -> Path:
    name = sample.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("sample name must be a non-empty string")
    return runs_dir / f"{name}.libvpx.ivf"


def sample_decoded_i420_path(sample: Mapping[str, Any], runs_dir: Path, encoder_label: str) -> Path:
    name = sample.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("sample name must be a non-empty string")
    return runs_dir / f"{name}.{encoder_label}.decoded.i420"


def sample_encode_metadata_path(sample: Mapping[str, Any], runs_dir: Path, encoder_label: str) -> Path:
    name = sample.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("sample name must be a non-empty string")
    return runs_dir / f"{name}.{encoder_label}.encode.json"


def sample_frames(sample: Mapping[str, Any]) -> int:
    frames = sample.get("frames", 60)
    if not isinstance(frames, int) or frames <= 0:
        raise ValueError("sample frames must be a positive integer")
    return frames


def sample_dimension(sample: Mapping[str, Any], field: str) -> int:
    value = sample.get(field)
    if not isinstance(value, int) or value <= 0:
        raise ValueError(f"sample {field} must be a positive integer")
    return value


def i420_frame_size(width: int, height: int) -> int:
    if width <= 0 or height <= 0:
        raise ValueError("I420 width and height must be positive")
    chroma_width = (width + 1) // 2
    chroma_height = (height + 1) // 2
    return (width * height) + (2 * chroma_width * chroma_height)


def validate_i420_sample_size(
    sample: Mapping[str, Any],
    *,
    i420_dir: Path = DEFAULT_I420_CACHE_DIR,
) -> dict[str, Any]:
    try:
        output_path = sample_i420_path(sample, i420_dir)
        width = sample_dimension(sample, "width")
        height = sample_dimension(sample, "height")
        frames = sample_frames(sample)
        expected = i420_frame_size(width, height) * frames
    except ValueError as exc:
        return {
            "ok": False,
            "path": "",
            "expected_bytes": 0,
            "actual_bytes": 0,
            "error": str(exc),
        }

    if not output_path.exists():
        return {
            "ok": False,
            "path": str(output_path),
            "expected_bytes": expected,
            "actual_bytes": 0,
            "error": f"missing I420 output: {output_path}",
        }

    actual = output_path.stat().st_size
    if actual != expected:
        return {
            "ok": False,
            "path": str(output_path),
            "expected_bytes": expected,
            "actual_bytes": actual,
            "error": f"I420 size mismatch for {output_path}: expected {expected} got {actual}",
        }

    return {
        "ok": True,
        "path": str(output_path),
        "expected_bytes": expected,
        "actual_bytes": actual,
        "error": None,
    }


def convert_y4m_to_i420(
    sample: Mapping[str, Any],
    *,
    y4m_dir: Path = DEFAULT_Y4M_CACHE_DIR,
    i420_dir: Path = DEFAULT_I420_CACHE_DIR,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    try:
        input_path = sample_y4m_path(sample, y4m_dir)
        output_path = sample_i420_path(sample, i420_dir)
        frames = sample_frames(sample)
    except ValueError as exc:
        return {
            "ok": False,
            "command": [],
            "input_path": "",
            "output_path": "",
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }

    if not input_path.exists():
        return {
            "ok": False,
            "command": [],
            "input_path": str(input_path),
            "output_path": str(output_path),
            "returncode": None,
            "stdout": "",
            "stderr": f"missing Y4M input: {input_path}",
        }

    i420_dir.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-frames:v",
        str(frames),
        "-pix_fmt",
        "yuv420p",
        "-f",
        "rawvideo",
        str(output_path),
    ]
    try:
        completed = runner(command, REPO_ROOT)
    except OSError as exc:
        return {
            "ok": False,
            "command": command,
            "input_path": str(input_path),
            "output_path": str(output_path),
            "returncode": None,
            "stdout": "",
            "stderr": str(exc),
        }

    return {
        "ok": completed.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0,
        "command": command,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def prepare_i420_encode_input(
    sample: Mapping[str, Any],
    *,
    i420_dir: Path = DEFAULT_I420_CACHE_DIR,
    runs_dir: Path = DEFAULT_RUNS_DIR,
) -> dict[str, Any]:
    try:
        input_path = sample_i420_path(sample, i420_dir)
        width = sample_dimension(sample, "width")
        height = sample_dimension(sample, "height")
        frames = sample_frames(sample)
        expected_bytes = i420_frame_size(width, height) * frames
    except ValueError as exc:
        return {
            "ok": False,
            "path": "",
            "source_path": "",
            "expected_bytes": 0,
            "actual_bytes": 0,
            "truncated": False,
            "error": str(exc),
        }

    if not input_path.exists():
        return {
            "ok": False,
            "path": str(input_path),
            "source_path": str(input_path),
            "expected_bytes": expected_bytes,
            "actual_bytes": 0,
            "truncated": False,
            "error": f"missing I420 input: {input_path}",
        }

    actual_bytes = input_path.stat().st_size
    if actual_bytes == expected_bytes:
        return {
            "ok": True,
            "path": str(input_path),
            "source_path": str(input_path),
            "expected_bytes": expected_bytes,
            "actual_bytes": actual_bytes,
            "truncated": False,
            "error": None,
        }

    if actual_bytes < expected_bytes:
        return {
            "ok": False,
            "path": str(input_path),
            "source_path": str(input_path),
            "expected_bytes": expected_bytes,
            "actual_bytes": actual_bytes,
            "truncated": False,
            "error": f"I420 input is too short for requested frames: {input_path}",
        }

    try:
        name = sample["name"]
        if not isinstance(name, str) or not name:
            raise ValueError("sample name must be a non-empty string")
    except (KeyError, ValueError) as exc:
        return {
            "ok": False,
            "path": str(input_path),
            "source_path": str(input_path),
            "expected_bytes": expected_bytes,
            "actual_bytes": actual_bytes,
            "truncated": False,
            "error": str(exc),
        }

    runs_dir.mkdir(parents=True, exist_ok=True)
    trimmed_path = runs_dir / f"{name}.frames{sample_frames(sample)}.i420"
    if trimmed_path.exists() and trimmed_path.stat().st_size == expected_bytes:
        return {
            "ok": True,
            "path": str(trimmed_path),
            "source_path": str(input_path),
            "expected_bytes": expected_bytes,
            "actual_bytes": actual_bytes,
            "truncated": True,
            "error": None,
        }
    with input_path.open("rb") as src, trimmed_path.open("wb") as dst:
        remaining = expected_bytes
        while remaining > 0:
            chunk = src.read(min(1024 * 1024, remaining))
            if not chunk:
                break
            dst.write(chunk)
            remaining -= len(chunk)

    return {
        "ok": remaining == 0,
        "path": str(trimmed_path),
        "source_path": str(input_path),
        "expected_bytes": expected_bytes,
        "actual_bytes": actual_bytes,
        "truncated": True,
        "error": None if remaining == 0 else f"failed to trim I420 input to {expected_bytes} bytes",
    }


def encode_vp8uya_samples(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    group: str | None = None,
    frames_override: int | None = None,
    i420_dir: Path = DEFAULT_I420_CACHE_DIR,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    vp8uya_bin: Path = DEFAULT_VP8UYA_BIN,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    binary = validate_vp8uya_binary(vp8uya_bin)
    if not binary["ok"]:
        return {
            "ok": False,
            "vp8uya_bin": str(vp8uya_bin),
            "runs_dir": str(runs_dir),
            "results": [],
            "error": binary["error"],
        }

    try:
        manifest = load_sample_manifest(manifest_path)
        selected = plan_sample_entries(
            filter_samples_by_group(manifest_samples(manifest), group),
            frames_override,
        )
    except ValueError as exc:
        return {
            "ok": False,
            "vp8uya_bin": str(vp8uya_bin),
            "runs_dir": str(runs_dir),
            "results": [],
            "error": str(exc),
        }

    runs_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for sample in selected:
        try:
            width = sample_dimension(sample, "width")
            height = sample_dimension(sample, "height")
            frames = sample_frames(sample)
            fps = sample_fps(sample)
            output_path = sample_vp8uya_ivf_path(sample, runs_dir)
            metadata_path = sample_encode_metadata_path(sample, runs_dir, "vp8uya")
        except ValueError as exc:
            results.append({
                "sample": sample.get("name", ""),
                "ok": False,
                "error": str(exc),
            })
            continue

        input_report = prepare_i420_encode_input(sample, i420_dir=i420_dir, runs_dir=runs_dir)
        if not input_report["ok"]:
            results.append({
                "sample": sample["name"],
                "ok": False,
                "input": input_report,
                "output_path": str(output_path),
                "vp8uya_command": [],
                "returncode": None,
                "stdout": "",
                "stderr": input_report["error"],
            })
            continue

        command = [
            str(vp8uya_bin),
            "encode",
            input_report["path"],
            "--width",
            str(width),
            "--height",
            str(height),
            "--frames",
            str(frames),
            "--fps",
            fps,
            "--out",
            str(output_path),
        ]
        started_ns = time.perf_counter_ns()
        try:
            completed = runner(command, REPO_ROOT)
        except OSError as exc:
            completed = subprocess.CompletedProcess(command, 127, "", str(exc))
        elapsed_ns = time.perf_counter_ns() - started_ns

        metadata_error = write_encode_metadata(
            metadata_path,
            elapsed_field="vp8uya_encode_elapsed_ns",
            elapsed_ns=elapsed_ns,
            command=command,
            output_path=output_path,
            ok=completed.returncode == 0 and output_path.exists(),
            returncode=completed.returncode,
        )

        results.append({
            "sample": sample["name"],
            "ok": completed.returncode == 0 and output_path.exists() and metadata_error is None,
            "input": input_report,
            "output_path": str(output_path),
            "encode_metadata_path": str(metadata_path),
            "encode_metadata_error": metadata_error,
            "vp8uya_command": command,
            "vp8uya_encode_elapsed_ns": elapsed_ns,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        })

    return {
        "ok": all(result["ok"] for result in results),
        "vp8uya_bin": str(vp8uya_bin),
        "runs_dir": str(runs_dir),
        "i420_cache_dir": str(i420_dir),
        "group": group,
        "frames_override": frames_override,
        "results": results,
    }


def encode_libvpx_samples(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    group: str | None = None,
    frames_override: int | None = None,
    i420_dir: Path = DEFAULT_I420_CACHE_DIR,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    vpxenc = attach_tool_metadata(find_vpx_tool("vpxenc", "VPXENC"))
    vpxenc_report = compact_tool_metadata(vpxenc)
    if vpxenc["path"] is None or vpxenc["probe_returncode"] != 0:
        return {
            "ok": False,
            "vpxenc": vpxenc_report,
            "runs_dir": str(runs_dir),
            "results": [],
            "error": vpxenc.get("error") or "vpxenc probe failed",
        }

    try:
        manifest = load_sample_manifest(manifest_path)
        selected = plan_sample_entries(
            filter_samples_by_group(manifest_samples(manifest), group),
            frames_override,
        )
    except ValueError as exc:
        return {
            "ok": False,
            "vpxenc": vpxenc_report,
            "runs_dir": str(runs_dir),
            "results": [],
            "error": str(exc),
        }

    runs_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for sample in selected:
        try:
            width = sample_dimension(sample, "width")
            height = sample_dimension(sample, "height")
            frames = sample_frames(sample)
            fps = sample_fps(sample)
            output_path = sample_libvpx_ivf_path(sample, runs_dir)
            metadata_path = sample_encode_metadata_path(sample, runs_dir, "libvpx")
        except ValueError as exc:
            results.append({
                "sample": sample.get("name", ""),
                "ok": False,
                "error": str(exc),
            })
            continue

        input_report = prepare_i420_encode_input(sample, i420_dir=i420_dir, runs_dir=runs_dir)
        if not input_report["ok"]:
            results.append({
                "sample": sample["name"],
                "ok": False,
                "input": input_report,
                "output_path": str(output_path),
                "libvpx_command": [],
                "returncode": None,
                "stdout": "",
                "stderr": input_report["error"],
            })
            continue

        command = [
            str(vpxenc["path"]),
            "--codec=vp8",
            "--best",
            "--ivf",
            "--i420",
            "--disable-warning-prompt",
            "--quiet",
            f"--width={width}",
            f"--height={height}",
            f"--fps={fps}",
            f"--limit={frames}",
            "-o",
            str(output_path),
            input_report["path"],
        ]
        started_ns = time.perf_counter_ns()
        try:
            completed = runner(command, REPO_ROOT)
        except OSError as exc:
            completed = subprocess.CompletedProcess(command, 127, "", str(exc))
        elapsed_ns = time.perf_counter_ns() - started_ns

        metadata_error = write_encode_metadata(
            metadata_path,
            elapsed_field="libvpx_encode_elapsed_ns",
            elapsed_ns=elapsed_ns,
            command=command,
            output_path=output_path,
            ok=completed.returncode == 0 and output_path.exists(),
            returncode=completed.returncode,
        )

        results.append({
            "sample": sample["name"],
            "ok": completed.returncode == 0 and output_path.exists() and metadata_error is None,
            "input": input_report,
            "output_path": str(output_path),
            "encode_metadata_path": str(metadata_path),
            "encode_metadata_error": metadata_error,
            "libvpx_command": command,
            "libvpx_encode_elapsed_ns": elapsed_ns,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        })

    return {
        "ok": all(result["ok"] for result in results),
        "vpxenc": vpxenc_report,
        "runs_dir": str(runs_dir),
        "i420_cache_dir": str(i420_dir),
        "group": group,
        "frames_override": frames_override,
        "results": results,
    }


def encoded_ivf_path(sample: Mapping[str, Any], runs_dir: Path, encoder_label: str) -> Path:
    if encoder_label == "vp8uya":
        return sample_vp8uya_ivf_path(sample, runs_dir)
    if encoder_label == "libvpx":
        return sample_libvpx_ivf_path(sample, runs_dir)
    raise ValueError(f"unsupported encoder label: {encoder_label}")


def decode_vpxdec_samples(
    *,
    encoder_label: str,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    group: str | None = None,
    frames_override: int | None = None,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    runner: Callable[[list[str], Path], subprocess.CompletedProcess[str]] = run_command,
) -> dict[str, Any]:
    vpxdec = attach_tool_metadata(find_vpx_tool("vpxdec", "VPXDEC"))
    vpxdec_report = compact_tool_metadata(vpxdec)
    if vpxdec["path"] is None or vpxdec["probe_returncode"] != 0:
        return {
            "ok": False,
            "vpxdec": vpxdec_report,
            "runs_dir": str(runs_dir),
            "encoder_label": encoder_label,
            "results": [],
            "error": vpxdec.get("error") or "vpxdec probe failed",
        }

    try:
        manifest = load_sample_manifest(manifest_path)
        selected = plan_sample_entries(
            filter_samples_by_group(manifest_samples(manifest), group),
            frames_override,
        )
    except ValueError as exc:
        return {
            "ok": False,
            "vpxdec": vpxdec_report,
            "runs_dir": str(runs_dir),
            "encoder_label": encoder_label,
            "results": [],
            "error": str(exc),
        }

    results: list[dict[str, Any]] = []
    for sample in selected:
        try:
            input_path = encoded_ivf_path(sample, runs_dir, encoder_label)
            output_path = sample_decoded_i420_path(sample, runs_dir, encoder_label)
        except ValueError as exc:
            results.append({
                "sample": sample.get("name", ""),
                "ok": False,
                "error": str(exc),
            })
            continue

        if not input_path.exists():
            results.append({
                "sample": sample["name"],
                "ok": False,
                "input_path": str(input_path),
                "output_path": str(output_path),
                "vpxdec_command": [],
                "returncode": None,
                "stdout": "",
                "stderr": f"missing encoded IVF input: {input_path}",
            })
            continue

        command = [
            str(vpxdec["path"]),
            "--rawvideo",
            "-o",
            str(output_path),
            str(input_path),
        ]
        try:
            completed = runner(command, REPO_ROOT)
        except OSError as exc:
            completed = subprocess.CompletedProcess(command, 127, "", str(exc))

        results.append({
            "sample": sample["name"],
            "ok": completed.returncode == 0 and output_path.exists(),
            "input_path": str(input_path),
            "output_path": str(output_path),
            "vpxdec_command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        })

    return {
        "ok": all(result["ok"] for result in results),
        "vpxdec": vpxdec_report,
        "runs_dir": str(runs_dir),
        "encoder_label": encoder_label,
        "group": group,
        "frames_override": frames_override,
        "results": results,
    }


def require_number(result: dict[str, Any], field: str) -> float:
    value = result.get(field)
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} must be numeric")
    return float(value)


def metric_contract() -> dict[str, Any]:
    return {
        "libvpx_preset": LIBVPX_PRESET,
        "required_result_fields": list(REQUIRED_RESULT_FIELDS),
        "required_summary_fields": list(REQUIRED_SUMMARY_FIELDS),
        "hard_threshold_fields": list(HARD_THRESHOLD_FIELDS),
        "thresholds": dict(THRESHOLDS),
    }


def probe_tools(*, env: Mapping[str, str] | None = None) -> dict[str, Any]:
    vpxenc = attach_tool_metadata(find_vpx_tool("vpxenc", "VPXENC", env=env))
    vpxdec = attach_tool_metadata(find_vpx_tool("vpxdec", "VPXDEC", env=env))
    return {
        "ok": (
            vpxenc["path"] is not None
            and vpxdec["path"] is not None
            and vpxenc["probe_returncode"] == 0
            and vpxdec["probe_returncode"] == 0
        ),
        "vpxenc": vpxenc,
        "vpxenc_probe_returncode": vpxenc["probe_returncode"],
        "vpxdec": vpxdec,
        "vpxdec_probe_returncode": vpxdec["probe_returncode"],
        "vpxenc_version": vpxenc["version"],
        "vpxdec_version": vpxdec["version"],
    }


def evaluate_thresholds(result: dict[str, Any]) -> dict[str, Any]:
    evaluated = dict(result)
    failure_reasons: list[str] = []

    try:
        vp8uya_bpp = require_number(evaluated, "vp8uya_bits_per_pixel")
        libvpx_bpp = require_number(evaluated, "libvpx_bits_per_pixel")
        if libvpx_bpp <= 0.0:
            evaluated["bitrate_ratio"] = float("inf")
            failure_reasons.append("libvpx_bits_per_pixel must be positive")
        else:
            bitrate_ratio = vp8uya_bpp / libvpx_bpp
            evaluated["bitrate_ratio"] = bitrate_ratio
            if bitrate_ratio > THRESHOLDS["max_bitrate_ratio"]:
                failure_reasons.append(
                    "bitrate_ratio "
                    f"{bitrate_ratio:.6f} exceeds max {THRESHOLDS['max_bitrate_ratio']:.6f}"
                )
    except ValueError as exc:
        failure_reasons.append(str(exc))

    try:
        vp8uya_psnr = require_number(evaluated, "vp8uya_psnr_all_db")
        libvpx_psnr = require_number(evaluated, "libvpx_psnr_all_db")
        psnr_delta = round(vp8uya_psnr - libvpx_psnr, 6)
        evaluated["psnr_all_delta_db"] = psnr_delta
        if psnr_delta < THRESHOLDS["min_psnr_all_delta_db"]:
            failure_reasons.append(
                "psnr_all_delta_db "
                f"{psnr_delta:.6f} below min {THRESHOLDS['min_psnr_all_delta_db']:.6f}"
            )
    except ValueError as exc:
        failure_reasons.append(str(exc))

    try:
        vp8uya_fps = require_number(evaluated, "vp8uya_fps")
        libvpx_fps = require_number(evaluated, "libvpx_fps")
        if libvpx_fps <= 0.0:
            evaluated["fps_ratio"] = 0.0
            failure_reasons.append("libvpx_fps must be positive")
        else:
            fps_ratio = round(vp8uya_fps / libvpx_fps, 6)
            evaluated["fps_ratio"] = fps_ratio
            if fps_ratio < THRESHOLDS["min_fps_ratio"]:
                failure_reasons.append(
                    "fps_ratio "
                    f"{fps_ratio:.6f} below min {THRESHOLDS['min_fps_ratio']:.6f}"
                )
    except ValueError as exc:
        failure_reasons.append(str(exc))

    evaluated["failure_reasons"] = failure_reasons
    evaluated["passed"] = len(failure_reasons) == 0
    return evaluated


def evaluate_result_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {
            "passed": False,
            "failure_reasons": [f"failed to read result JSON {path}: {exc}"],
        }
    except json.JSONDecodeError as exc:
        return {
            "passed": False,
            "failure_reasons": [f"failed to parse result JSON {path}: {exc}"],
        }

    if not isinstance(data, dict):
        return {
            "passed": False,
            "failure_reasons": [f"result JSON {path} must contain an object"],
        }
    return evaluate_thresholds(data)


def evaluate_threshold_record(record: dict[str, Any]) -> dict[str, Any]:
    evaluated = evaluate_thresholds(record)
    failure_reasons = list(evaluated.get("failure_reasons", []))
    existing_reasons = record.get("failure_reasons")
    if isinstance(existing_reasons, list):
        for reason in existing_reasons:
            reason_text = str(reason)
            if reason_text not in failure_reasons:
                failure_reasons.append(reason_text)
    if (record.get("passed") is False or record.get("ok") is False) and not failure_reasons:
        failure_reasons.append("sample result was marked failed")
    evaluated["failure_reasons"] = failure_reasons
    evaluated["passed"] = len(failure_reasons) == 0
    return evaluated


def load_repro_result_records(path: Path) -> tuple[list[dict[str, Any]], str | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], f"failed to read result records {path}: {exc}"

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        records: list[dict[str, Any]] = []
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                return [], f"failed to parse {path}:{line_number}: {exc}"
            if not isinstance(value, dict):
                return [], f"result record {path}:{line_number} must contain an object"
            records.append(value)
        return records, None

    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, list):
            records = []
            for index, value in enumerate(results):
                if not isinstance(value, dict):
                    return [], f"results[{index}] in {path} must contain an object"
                records.append(value)
            return records, None
        return [data], None

    if isinstance(data, list):
        records = []
        for index, value in enumerate(data):
            if not isinstance(value, dict):
                return [], f"result entry {index} in {path} must contain an object"
            records.append(value)
        return records, None

    return [], f"result records {path} must be a JSON object, array, or NDJSON objects"


def command_to_shell(command: Any) -> str:
    if isinstance(command, str):
        return command
    if isinstance(command, list):
        return shlex.join(str(part) for part in command)
    return ""


def first_command(result: Mapping[str, Any], field_names: tuple[str, ...]) -> str:
    for field_name in field_names:
        command = command_to_shell(result.get(field_name))
        if command:
            return command
    return ""


def all_commands(result: Mapping[str, Any], field_names: tuple[str, ...]) -> list[str]:
    commands: list[str] = []
    seen: set[str] = set()
    for field_name in field_names:
        command = command_to_shell(result.get(field_name))
        if command and command not in seen:
            seen.add(command)
            commands.append(command)
    return commands


def result_failed(result: Mapping[str, Any]) -> bool:
    if result.get("passed") is False:
        return True
    if result.get("ok") is False:
        return True
    failure_reasons = result.get("failure_reasons")
    return isinstance(failure_reasons, list) and len(failure_reasons) > 0


def threshold_results(
    *,
    results_path: Path = DEFAULT_RESULTS_NDJSON_PATH,
) -> dict[str, Any]:
    records, error = load_repro_result_records(results_path)
    if error is not None:
        return {
            "ok": False,
            "passed": False,
            "results_ndjson": str(results_path),
            "sample_count": 0,
            "passed_count": 0,
            "failed_count": 0,
            "failed_samples": [],
            "failure_reasons": [error],
        }

    evaluated_records = [evaluate_threshold_record(record) for record in records]
    failed_records = [record for record in evaluated_records if result_failed(record)]
    failed_samples = [
        str(record.get("sample", record.get("name", f"#{index}")))
        for index, record in enumerate(evaluated_records)
        if result_failed(record)
    ]
    return {
        "ok": True,
        "passed": len(failed_records) == 0,
        "results_ndjson": str(results_path),
        "sample_count": len(evaluated_records),
        "passed_count": len(evaluated_records) - len(failed_records),
        "failed_count": len(failed_records),
        "failed_samples": failed_samples,
        "failed_results": failed_records,
        "thresholds": dict(THRESHOLDS),
        "failure_reasons": [],
    }


def collect_repro_commands(result: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        "vp8uya": [command]
        if (command := first_command(result, ("vp8uya_command", "vp8uya_encode_command")))
        else [],
        "vpxenc": [command]
        if (command := first_command(result, ("vpxenc_command", "libvpx_command", "libvpx_encode_command")))
        else [],
        "vpxdec": all_commands(
            result,
            (
                "vp8uya_vpxdec_command",
                "vpxdec_vp8uya_command",
                "libvpx_vpxdec_command",
                "vpxdec_libvpx_command",
                "vpxdec_command",
            ),
        ),
    }


def append_command_block(lines: list[str], label: str, commands: list[str]) -> None:
    lines.append(f"### {label}")
    lines.append("```sh")
    if commands:
        lines.extend(commands)
    else:
        lines.append(f"# missing {label} command")
    lines.append("```")
    lines.append("")


def write_repro_report(results_path: Path, report_path: Path = DEFAULT_REPRO_REPORT_PATH) -> dict[str, Any]:
    records, error = load_repro_result_records(results_path)
    if error is not None:
        return {
            "ok": False,
            "input_path": str(results_path),
            "report_path": str(report_path),
            "sample_count": 0,
            "failed_sample_count": 0,
            "missing_commands": [],
            "error": error,
        }

    failed_records = [record for record in records if result_failed(record)]
    missing_commands: list[dict[str, str]] = []
    lines = [
        "# libvpx Reproduction Commands",
        "",
        f"Input: `{results_path}`",
        "",
    ]

    if not failed_records:
        lines.append("No failing samples.")
        lines.append("")

    for record in failed_records:
        sample = record.get("sample", record.get("name", "unknown"))
        sample_name = str(sample)
        lines.append(f"## {sample_name}")
        lines.append("")

        failure_reasons = record.get("failure_reasons")
        if isinstance(failure_reasons, list) and failure_reasons:
            lines.append("Failure reasons:")
            for reason in failure_reasons:
                lines.append(f"- {reason}")
            lines.append("")

        commands = collect_repro_commands(record)
        for label in ("vp8uya", "vpxenc", "vpxdec"):
            if not commands[label]:
                missing_commands.append({
                    "sample": sample_name,
                    "command": label,
                })
            append_command_block(lines, label, commands[label])

    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text("\n".join(lines), encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "input_path": str(results_path),
            "report_path": str(report_path),
            "sample_count": len(records),
            "failed_sample_count": len(failed_records),
            "missing_commands": missing_commands,
            "error": f"failed to write repro report {report_path}: {exc}",
        }

    return {
        "ok": len(missing_commands) == 0,
        "input_path": str(results_path),
        "report_path": str(report_path),
        "sample_count": len(records),
        "failed_sample_count": len(failed_records),
        "missing_commands": missing_commands,
        "error": None,
    }


def mean_required_field(records: list[dict[str, Any]], field: str) -> float:
    if not records:
        raise ValueError("summary requires at least one result record")
    values = [require_number(record, field) for record in records]
    return sum(values) / float(len(values))


def first_string_field(records: list[dict[str, Any]], field: str) -> str:
    for record in records:
        value = record.get(field)
        if isinstance(value, str):
            return value
    return ""


def current_git_commit() -> str:
    completed = run_command(["git", "rev-parse", "HEAD"], REPO_ROOT)
    if completed.returncode != 0:
        return ""
    return completed.stdout.strip()


def build_summary(records: list[dict[str, Any]], *, results_path: Path) -> dict[str, Any]:
    failed_count = sum(1 for record in records if result_failed(record))
    sample_count = len(records)
    passed_count = sample_count - failed_count
    return {
        "generated_at_unix": time.time(),
        "git_commit": current_git_commit(),
        "host": {
            "platform": sys.platform,
            "python": sys.version.split()[0],
        },
        "thresholds": dict(THRESHOLDS),
        "libvpx_preset": LIBVPX_PRESET,
        "results_ndjson": str(results_path),
        "sample_count": sample_count,
        "passed_count": passed_count,
        "failed_count": failed_count,
        "passed": failed_count == 0,
        "vp8uya_bits_per_pixel": mean_required_field(records, "vp8uya_bits_per_pixel"),
        "libvpx_bits_per_pixel": mean_required_field(records, "libvpx_bits_per_pixel"),
        "vp8uya_psnr_all_db": mean_required_field(records, "vp8uya_psnr_all_db"),
        "libvpx_psnr_all_db": mean_required_field(records, "libvpx_psnr_all_db"),
        "vp8uya_fps": mean_required_field(records, "vp8uya_fps"),
        "libvpx_fps": mean_required_field(records, "libvpx_fps"),
        "vpxenc_version": first_string_field(records, "vpxenc_version"),
        "vpxdec_version": first_string_field(records, "vpxdec_version"),
    }


def write_summary_json(
    *,
    results_path: Path = DEFAULT_RESULTS_NDJSON_PATH,
    summary_path: Path = DEFAULT_SUMMARY_JSON_PATH,
) -> dict[str, Any]:
    records, error = load_repro_result_records(results_path)
    if error is not None:
        return {
            "ok": False,
            "results_ndjson": str(results_path),
            "summary_json": str(summary_path),
            "sample_count": 0,
            "error": error,
        }
    try:
        summary = build_summary(records, results_path=results_path)
    except ValueError as exc:
        return {
            "ok": False,
            "results_ndjson": str(results_path),
            "summary_json": str(summary_path),
            "sample_count": len(records),
            "error": str(exc),
        }

    try:
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "results_ndjson": str(results_path),
            "summary_json": str(summary_path),
            "sample_count": len(records),
            "error": f"failed to write summary JSON {summary_path}: {exc}",
        }

    return {
        "ok": True,
        "results_ndjson": str(results_path),
        "summary_json": str(summary_path),
        "sample_count": len(records),
        "passed_count": summary["passed_count"],
        "failed_count": summary["failed_count"],
        "error": None,
    }


def load_summary_json(path: Path) -> tuple[dict[str, Any], str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {}, f"failed to read summary JSON {path}: {exc}"
    except json.JSONDecodeError as exc:
        return {}, f"failed to parse summary JSON {path}: {exc}"
    if not isinstance(data, dict):
        return {}, f"summary JSON {path} must contain an object"
    return data, None


def markdown_cell(value: Any) -> str:
    text = str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def markdown_number(value: Any, digits: int = 6) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return ""
    return f"{float(value):.{digits}f}"


def markdown_timestamp(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return ""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(float(value)))


def sample_groups(record: Mapping[str, Any]) -> str:
    groups = record.get("groups")
    if isinstance(groups, list):
        return ",".join(str(group) for group in groups)
    group = record.get("group")
    if isinstance(group, str):
        return group
    return ""


def build_markdown_report(summary: Mapping[str, Any], records: list[dict[str, Any]]) -> str:
    thresholds = summary.get("thresholds")
    if not isinstance(thresholds, dict):
        thresholds = {}

    lines = [
        "# Encoder libvpx compare report",
        "",
        "## Run Summary",
        "",
        f"- Benchmark target: libvpx `{summary.get('libvpx_preset', LIBVPX_PRESET)}`",
        f"- git commit: `{summary.get('git_commit', '')}`",
        f"- generated at: `{markdown_timestamp(summary.get('generated_at_unix'))}`",
        f"- sample count: {summary.get('sample_count', len(records))}",
        f"- passed count: {summary.get('passed_count', '')}",
        f"- failed count: {summary.get('failed_count', '')}",
        "",
        "## Tool Versions",
        "",
        "| Tool | Version |",
        "| --- | --- |",
        f"| vpxenc | {markdown_cell(summary.get('vpxenc_version', ''))} |",
        f"| vpxdec | {markdown_cell(summary.get('vpxdec_version', ''))} |",
        "",
        "## Thresholds",
        "",
        "| Metric | Hard threshold |",
        "| --- | --- |",
        f"| Bitrate | `vp8uya_bits_per_pixel <= libvpx_bits_per_pixel * {thresholds.get('max_bitrate_ratio', THRESHOLDS['max_bitrate_ratio']):.2f}` |",
        f"| PSNR-all | `vp8uya_psnr_all_db >= libvpx_psnr_all_db {thresholds.get('min_psnr_all_delta_db', THRESHOLDS['min_psnr_all_delta_db']):+.2f}` |",
        f"| Encoding fps | `vp8uya_fps >= libvpx_fps * {thresholds.get('min_fps_ratio', THRESHOLDS['min_fps_ratio']):.2f}` |",
        "",
        "`SSIM-all` is recorded for diagnosis only and does not decide hard pass/fail in the first report version.",
        "",
        "## Aggregate Summary",
        "",
        "| Field | Value |",
        "| --- | ---: |",
        f"| vp8uya_bits_per_pixel | {markdown_number(summary.get('vp8uya_bits_per_pixel'))} |",
        f"| libvpx_bits_per_pixel | {markdown_number(summary.get('libvpx_bits_per_pixel'))} |",
        f"| vp8uya_psnr_all_db | {markdown_number(summary.get('vp8uya_psnr_all_db'))} |",
        f"| libvpx_psnr_all_db | {markdown_number(summary.get('libvpx_psnr_all_db'))} |",
        f"| vp8uya_fps | {markdown_number(summary.get('vp8uya_fps'), 2)} |",
        f"| libvpx_fps | {markdown_number(summary.get('libvpx_fps'), 2)} |",
        "",
        "## Sample Results",
        "",
        "| Sample | Group | Frames | vp8uya bpp | libvpx bpp | vp8uya PSNR-all | libvpx PSNR-all | vp8uya SSIM-all | libvpx SSIM-all | vp8uya fps | libvpx fps | Passed |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ]

    for record in records:
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_cell(record.get("sample", record.get("name", ""))),
                    markdown_cell(sample_groups(record)),
                    markdown_cell(record.get("frames", "")),
                    markdown_number(record.get("vp8uya_bits_per_pixel")),
                    markdown_number(record.get("libvpx_bits_per_pixel")),
                    markdown_number(record.get("vp8uya_psnr_all_db")),
                    markdown_number(record.get("libvpx_psnr_all_db")),
                    markdown_number(record.get("vp8uya_ssim_all")),
                    markdown_number(record.get("libvpx_ssim_all")),
                    markdown_number(record.get("vp8uya_fps"), 2),
                    markdown_number(record.get("libvpx_fps"), 2),
                    "true" if record.get("passed") is True else "false",
                ]
            )
            + " |"
        )

    failed_records = [record for record in records if result_failed(record)]
    lines.extend(["", "## Failed Samples", ""])
    if not failed_records:
        lines.extend(["No failing samples.", ""])
    for record in failed_records:
        sample = markdown_cell(record.get("sample", record.get("name", "unknown")))
        lines.extend([f"### {sample}", ""])
        failure_reasons = record.get("failure_reasons")
        if isinstance(failure_reasons, list) and failure_reasons:
            lines.append("Failure reasons:")
            for reason in failure_reasons:
                lines.append(f"- {reason}")
            lines.append("")
        commands = collect_repro_commands(record)
        for label in ("vp8uya", "vpxenc", "vpxdec"):
            append_command_block(lines, label, commands[label])

    conclusion = "PASS" if summary.get("passed") is True else "FAIL"
    lines.extend([
        "## Conclusion",
        "",
        f"{conclusion}: {summary.get('passed_count', '')}/{summary.get('sample_count', len(records))} samples passed.",
        "",
    ])
    return "\n".join(lines)


def write_markdown_report(
    *,
    results_path: Path = DEFAULT_RESULTS_NDJSON_PATH,
    summary_path: Path = DEFAULT_SUMMARY_JSON_PATH,
    report_path: Path = DEFAULT_MARKDOWN_REPORT_PATH,
) -> dict[str, Any]:
    records, error = load_repro_result_records(results_path)
    if error is not None:
        return {
            "ok": False,
            "results_ndjson": str(results_path),
            "summary_json": str(summary_path),
            "report_md": str(report_path),
            "sample_count": 0,
            "failed_sample_count": 0,
            "error": error,
        }
    summary, error = load_summary_json(summary_path)
    if error is not None:
        return {
            "ok": False,
            "results_ndjson": str(results_path),
            "summary_json": str(summary_path),
            "report_md": str(report_path),
            "sample_count": len(records),
            "failed_sample_count": 0,
            "error": error,
        }
    failed_records = [record for record in records if result_failed(record)]
    markdown = build_markdown_report(summary, records)
    try:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(markdown, encoding="utf-8")
    except OSError as exc:
        return {
            "ok": False,
            "results_ndjson": str(results_path),
            "summary_json": str(summary_path),
            "report_md": str(report_path),
            "sample_count": len(records),
            "failed_sample_count": len(failed_records),
            "error": f"failed to write Markdown report {report_path}: {exc}",
        }
    return {
        "ok": True,
        "results_ndjson": str(results_path),
        "summary_json": str(summary_path),
        "report_md": str(report_path),
        "sample_count": len(records),
        "failed_sample_count": len(failed_records),
        "error": None,
    }


def read_ivf_payload_bits(path: Path) -> dict[str, Any]:
    try:
        data = path.read_bytes()
    except OSError as exc:
        return {
            "ok": False,
            "path": str(path),
            "payload_bytes": 0,
            "payload_bits": 0,
            "frame_count": 0,
            "declared_frame_count": 0,
            "error": f"failed to read IVF {path}: {exc}",
        }

    if len(data) < 32:
        return {
            "ok": False,
            "path": str(path),
            "payload_bytes": 0,
            "payload_bits": 0,
            "frame_count": 0,
            "declared_frame_count": 0,
            "error": f"IVF file is too short for header: {path}",
        }
    if data[0:4] != b"DKIF":
        return {
            "ok": False,
            "path": str(path),
            "payload_bytes": 0,
            "payload_bits": 0,
            "frame_count": 0,
            "declared_frame_count": 0,
            "error": f"invalid IVF signature: {path}",
        }
    if data[8:12] != b"VP80":
        return {
            "ok": False,
            "path": str(path),
            "payload_bytes": 0,
            "payload_bits": 0,
            "frame_count": 0,
            "declared_frame_count": 0,
            "error": f"unsupported IVF fourcc: {path}",
        }

    header_size = struct.unpack_from("<H", data, 6)[0]
    declared_frame_count = struct.unpack_from("<I", data, 24)[0]
    if header_size < 32 or header_size > len(data):
        return {
            "ok": False,
            "path": str(path),
            "payload_bytes": 0,
            "payload_bits": 0,
            "frame_count": 0,
            "declared_frame_count": declared_frame_count,
            "error": f"invalid IVF header size {header_size}: {path}",
        }

    offset = header_size
    frame_count = 0
    payload_bytes = 0
    while offset < len(data):
        if offset + 12 > len(data):
            return {
                "ok": False,
                "path": str(path),
                "payload_bytes": payload_bytes,
                "payload_bits": payload_bytes * 8,
                "frame_count": frame_count,
                "declared_frame_count": declared_frame_count,
                "error": f"truncated IVF frame header at byte {offset}: {path}",
            }
        payload_size = struct.unpack_from("<I", data, offset)[0]
        payload_start = offset + 12
        payload_end = payload_start + payload_size
        if payload_end > len(data):
            return {
                "ok": False,
                "path": str(path),
                "payload_bytes": payload_bytes,
                "payload_bits": payload_bytes * 8,
                "frame_count": frame_count,
                "declared_frame_count": declared_frame_count,
                "error": f"truncated IVF frame payload at byte {payload_start}: {path}",
            }
        payload_bytes += payload_size
        frame_count += 1
        offset = payload_end

    if declared_frame_count not in (0, frame_count):
        return {
            "ok": False,
            "path": str(path),
            "payload_bytes": payload_bytes,
            "payload_bits": payload_bytes * 8,
            "frame_count": frame_count,
            "declared_frame_count": declared_frame_count,
            "error": (
                f"IVF declared frame_count={declared_frame_count} "
                f"but observed {frame_count}: {path}"
            ),
        }

    return {
        "ok": True,
        "path": str(path),
        "payload_bytes": payload_bytes,
        "payload_bits": payload_bytes * 8,
        "frame_count": frame_count,
        "declared_frame_count": declared_frame_count,
        "error": None,
    }


def bits_per_pixel(payload_bits: int | float, width: int, height: int, frames: int) -> float:
    denominator = width * height * frames
    if denominator <= 0:
        raise ValueError("bits per pixel denominator must be positive")
    return float(payload_bits) / float(denominator)


def encode_fps(frames: int, elapsed_ns: int) -> float:
    if frames <= 0:
        raise ValueError("encode fps frames must be positive")
    if elapsed_ns <= 0:
        raise ValueError("encode elapsed ns must be positive")
    return (float(frames) * 1_000_000_000.0) / float(elapsed_ns)


def psnr_db(sse: int, samples: int) -> float:
    if samples <= 0:
        raise ValueError("PSNR sample count must be positive")
    if sse < 0:
        raise ValueError("PSNR SSE must be non-negative")
    if sse == 0:
        return float("inf")
    mse = float(sse) / float(samples)
    return 10.0 * math.log10(65025.0 / mse)


def psnr_all_delta_db(vp8uya_psnr_all: float, libvpx_psnr_all: float) -> float:
    if math.isinf(vp8uya_psnr_all) and math.isinf(libvpx_psnr_all):
        return 0.0
    return round(vp8uya_psnr_all - libvpx_psnr_all, 6)


def psnr_failure_result(reference_path: Path | None, decoded_path: Path | None, error: str) -> dict[str, Any]:
    return {
        "ok": False,
        "reference_path": "" if reference_path is None else str(reference_path),
        "decoded_path": "" if decoded_path is None else str(decoded_path),
        "psnr_y_db": 0.0,
        "psnr_u_db": 0.0,
        "psnr_v_db": 0.0,
        "psnr_all_db": 0.0,
        "error": error,
    }


def ssim_failure_result(reference_path: Path | None, decoded_path: Path | None, error: str) -> dict[str, Any]:
    return {
        "ok": False,
        "reference_path": "" if reference_path is None else str(reference_path),
        "decoded_path": "" if decoded_path is None else str(decoded_path),
        "ssim_y": 0.0,
        "ssim_u": 0.0,
        "ssim_v": 0.0,
        "ssim_all": 0.0,
        "error": error,
    }


def nonnegative_variance(value: float) -> float:
    if value < 0.0 and value > -0.0000001:
        return 0.0
    return value


def ssim_from_stats(stats: dict[str, float]) -> float:
    sample_count = int(stats["sample_count"])
    if sample_count <= 0:
        raise ValueError("SSIM sample count must be positive")
    inv_count = 1.0 / float(sample_count)
    mean_reference = stats["sum_reference"] * inv_count
    mean_decoded = stats["sum_decoded"] * inv_count
    variance_reference = nonnegative_variance((stats["sum_reference_squared"] * inv_count) - (mean_reference * mean_reference))
    variance_decoded = nonnegative_variance((stats["sum_decoded_squared"] * inv_count) - (mean_decoded * mean_decoded))
    covariance = (stats["sum_cross"] * inv_count) - (mean_reference * mean_decoded)
    c1 = 6.5025
    c2 = 58.5225
    numerator = (((2.0 * mean_reference * mean_decoded) + c1) * ((2.0 * covariance) + c2))
    denominator = (((mean_reference * mean_reference) + (mean_decoded * mean_decoded) + c1) * (variance_reference + variance_decoded + c2))
    return numerator / denominator


def new_ssim_stats() -> dict[str, float]:
    return {
        "sample_count": 0.0,
        "sum_reference": 0.0,
        "sum_decoded": 0.0,
        "sum_reference_squared": 0.0,
        "sum_decoded_squared": 0.0,
        "sum_cross": 0.0,
    }


def add_ssim_samples(stats: dict[str, float], reference_samples: bytes, decoded_samples: bytes) -> None:
    stats["sample_count"] += float(len(reference_samples))
    for reference_value, decoded_value in zip(reference_samples, decoded_samples):
        reference_sample = float(reference_value)
        decoded_sample = float(decoded_value)
        stats["sum_reference"] += reference_sample
        stats["sum_decoded"] += decoded_sample
        stats["sum_reference_squared"] += reference_sample * reference_sample
        stats["sum_decoded_squared"] += decoded_sample * decoded_sample
        stats["sum_cross"] += reference_sample * decoded_sample


def weighted_ssim(y_ssim: float, u_ssim: float, v_ssim: float, y_samples: int, uv_samples: int) -> float:
    total_samples = y_samples + (2 * uv_samples)
    if total_samples <= 0:
        raise ValueError("SSIM total sample count must be positive")
    return ((y_ssim * y_samples) + (u_ssim * uv_samples) + (v_ssim * uv_samples)) / float(total_samples)


def read_i420_psnr(
    reference_path: Path,
    decoded_path: Path,
    *,
    width: int,
    height: int,
    frames: int,
) -> dict[str, Any]:
    try:
        expected_size = i420_frame_size(width, height) * frames
    except ValueError as exc:
        return psnr_failure_result(reference_path, decoded_path, str(exc))
    if frames <= 0:
        return psnr_failure_result(reference_path, decoded_path, "I420 PSNR frames must be positive")

    try:
        reference = reference_path.read_bytes()
    except OSError as exc:
        return psnr_failure_result(reference_path, decoded_path, f"failed to read reference I420 {reference_path}: {exc}")
    try:
        decoded = decoded_path.read_bytes()
    except OSError as exc:
        return psnr_failure_result(reference_path, decoded_path, f"failed to read decoded I420 {decoded_path}: {exc}")

    if len(reference) != expected_size:
        return psnr_failure_result(
            reference_path,
            decoded_path,
            f"reference I420 {reference_path} has {len(reference)} bytes, expected {expected_size}",
        )
    if len(decoded) != expected_size:
        return psnr_failure_result(
            reference_path,
            decoded_path,
            f"decoded I420 {decoded_path} has {len(decoded)} bytes, expected {expected_size}",
        )

    y_size = width * height
    chroma_width = (width + 1) // 2
    chroma_height = (height + 1) // 2
    uv_size = chroma_width * chroma_height
    frame_size = y_size + (2 * uv_size)
    y_sse = 0
    u_sse = 0
    v_sse = 0
    for frame_index in range(frames):
        frame_offset = frame_index * frame_size
        y_start = frame_offset
        u_start = y_start + y_size
        v_start = u_start + uv_size
        y_sse += sum(
            (reference_value - decoded_value) * (reference_value - decoded_value)
            for reference_value, decoded_value in zip(
                reference[y_start:u_start],
                decoded[y_start:u_start],
            )
        )
        u_sse += sum(
            (reference_value - decoded_value) * (reference_value - decoded_value)
            for reference_value, decoded_value in zip(
                reference[u_start:v_start],
                decoded[u_start:v_start],
            )
        )
        v_sse += sum(
            (reference_value - decoded_value) * (reference_value - decoded_value)
            for reference_value, decoded_value in zip(
                reference[v_start:v_start + uv_size],
                decoded[v_start:v_start + uv_size],
            )
        )

    y_samples = y_size * frames
    uv_samples = uv_size * frames
    return {
        "ok": True,
        "reference_path": str(reference_path),
        "decoded_path": str(decoded_path),
        "psnr_y_db": psnr_db(y_sse, y_samples),
        "psnr_u_db": psnr_db(u_sse, uv_samples),
        "psnr_v_db": psnr_db(v_sse, uv_samples),
        "psnr_all_db": psnr_db(y_sse + u_sse + v_sse, y_samples + (2 * uv_samples)),
        "error": None,
    }


def read_i420_ssim(
    reference_path: Path,
    decoded_path: Path,
    *,
    width: int,
    height: int,
    frames: int,
) -> dict[str, Any]:
    try:
        expected_size = i420_frame_size(width, height) * frames
    except ValueError as exc:
        return ssim_failure_result(reference_path, decoded_path, str(exc))
    if frames <= 0:
        return ssim_failure_result(reference_path, decoded_path, "I420 SSIM frames must be positive")

    try:
        reference = reference_path.read_bytes()
    except OSError as exc:
        return ssim_failure_result(reference_path, decoded_path, f"failed to read reference I420 {reference_path}: {exc}")
    try:
        decoded = decoded_path.read_bytes()
    except OSError as exc:
        return ssim_failure_result(reference_path, decoded_path, f"failed to read decoded I420 {decoded_path}: {exc}")

    if len(reference) != expected_size:
        return ssim_failure_result(
            reference_path,
            decoded_path,
            f"reference I420 {reference_path} has {len(reference)} bytes, expected {expected_size}",
        )
    if len(decoded) != expected_size:
        return ssim_failure_result(
            reference_path,
            decoded_path,
            f"decoded I420 {decoded_path} has {len(decoded)} bytes, expected {expected_size}",
        )

    y_size = width * height
    chroma_width = (width + 1) // 2
    chroma_height = (height + 1) // 2
    uv_size = chroma_width * chroma_height
    frame_size = y_size + (2 * uv_size)
    y_stats = new_ssim_stats()
    u_stats = new_ssim_stats()
    v_stats = new_ssim_stats()
    for frame_index in range(frames):
        frame_offset = frame_index * frame_size
        y_start = frame_offset
        u_start = y_start + y_size
        v_start = u_start + uv_size
        add_ssim_samples(y_stats, reference[y_start:u_start], decoded[y_start:u_start])
        add_ssim_samples(u_stats, reference[u_start:v_start], decoded[u_start:v_start])
        add_ssim_samples(v_stats, reference[v_start:v_start + uv_size], decoded[v_start:v_start + uv_size])

    y_ssim = ssim_from_stats(y_stats)
    u_ssim = ssim_from_stats(u_stats)
    v_ssim = ssim_from_stats(v_stats)
    y_samples = y_size * frames
    uv_samples = uv_size * frames
    return {
        "ok": True,
        "reference_path": str(reference_path),
        "decoded_path": str(decoded_path),
        "ssim_y": y_ssim,
        "ssim_u": u_ssim,
        "ssim_v": v_ssim,
        "ssim_all": weighted_ssim(y_ssim, u_ssim, v_ssim, y_samples, uv_samples),
        "error": None,
    }


def read_sample_psnr(
    sample: Mapping[str, Any],
    *,
    i420_dir: Path,
    runs_dir: Path,
    encoder_label: str,
) -> dict[str, Any]:
    try:
        decoded_path = sample_decoded_i420_path(sample, runs_dir, encoder_label)
        width = sample_dimension(sample, "width")
        height = sample_dimension(sample, "height")
        frames = sample_frames(sample)
    except ValueError as exc:
        return psnr_failure_result(None, None, str(exc))
    input_report = prepare_i420_encode_input(sample, i420_dir=i420_dir, runs_dir=runs_dir)
    if not input_report["ok"]:
        return psnr_failure_result(
            Path(str(input_report["path"])) if input_report["path"] else None,
            decoded_path,
            str(input_report["error"]),
        )
    reference_path = Path(str(input_report["path"]))
    return read_i420_psnr(reference_path, decoded_path, width=width, height=height, frames=frames)


def read_sample_ssim(
    sample: Mapping[str, Any],
    *,
    i420_dir: Path,
    runs_dir: Path,
    encoder_label: str,
) -> dict[str, Any]:
    try:
        decoded_path = sample_decoded_i420_path(sample, runs_dir, encoder_label)
        width = sample_dimension(sample, "width")
        height = sample_dimension(sample, "height")
        frames = sample_frames(sample)
    except ValueError as exc:
        return ssim_failure_result(None, None, str(exc))
    input_report = prepare_i420_encode_input(sample, i420_dir=i420_dir, runs_dir=runs_dir)
    if not input_report["ok"]:
        return ssim_failure_result(
            Path(str(input_report["path"])) if input_report["path"] else None,
            decoded_path,
            str(input_report["error"]),
        )
    reference_path = Path(str(input_report["path"]))
    return read_i420_ssim(reference_path, decoded_path, width=width, height=height, frames=frames)


def write_encode_metadata(
    path: Path,
    *,
    elapsed_field: str,
    elapsed_ns: int,
    command: list[str],
    output_path: Path,
    ok: bool,
    returncode: int | None,
) -> str | None:
    metadata = {
        elapsed_field: elapsed_ns,
        "command": command,
        "ok": ok,
        "output_path": str(output_path),
        "returncode": returncode,
    }
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(metadata, sort_keys=True) + "\n", encoding="utf-8")
    except OSError as exc:
        return f"failed to write encode metadata {path}: {exc}"
    return None


def read_encode_elapsed_ns(sample: Mapping[str, Any], runs_dir: Path, encoder_label: str) -> dict[str, Any]:
    try:
        path = sample_encode_metadata_path(sample, runs_dir, encoder_label)
    except ValueError as exc:
        return {
            "ok": False,
            "path": "",
            "elapsed_ns": 0,
            "error": str(exc),
        }

    field = f"{encoder_label}_encode_elapsed_ns"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return {
            "ok": False,
            "path": str(path),
            "elapsed_ns": 0,
            "error": f"failed to read encode metadata {path}: {exc}",
        }
    except json.JSONDecodeError as exc:
        return {
            "ok": False,
            "path": str(path),
            "elapsed_ns": 0,
            "error": f"failed to parse encode metadata {path}: {exc}",
        }

    if not isinstance(data, dict):
        return {
            "ok": False,
            "path": str(path),
            "elapsed_ns": 0,
            "error": f"encode metadata {path} must contain an object",
        }
    elapsed_ns = data.get(field)
    if isinstance(elapsed_ns, bool) or not isinstance(elapsed_ns, int) or elapsed_ns < 0:
        return {
            "ok": False,
            "path": str(path),
            "elapsed_ns": 0,
            "error": f"encode metadata {path} must contain non-negative integer {field}",
        }
    return {
        "ok": True,
        "path": str(path),
        "elapsed_ns": elapsed_ns,
        "error": None,
    }


def write_results_ndjson_payload_bits(
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    group: str | None = None,
    frames_override: int | None = None,
    i420_dir: Path = DEFAULT_I420_CACHE_DIR,
    runs_dir: Path = DEFAULT_RUNS_DIR,
    results_path: Path = DEFAULT_RESULTS_NDJSON_PATH,
) -> dict[str, Any]:
    try:
        manifest = load_sample_manifest(manifest_path)
        selected = plan_sample_entries(
            filter_samples_by_group(manifest_samples(manifest), group),
            frames_override,
        )
    except ValueError as exc:
        return {
            "ok": False,
            "manifest_path": str(manifest_path),
            "runs_dir": str(runs_dir),
            "results_ndjson": str(results_path),
            "sample_count": 0,
            "error": str(exc),
        }

    results: list[dict[str, Any]] = []
    for sample in selected:
        sample_name = str(sample.get("name", ""))
        failure_reasons: list[str] = []
        try:
            result = {
                "sample": sample_name,
                "width": sample_dimension(sample, "width"),
                "height": sample_dimension(sample, "height"),
                "frames": sample_frames(sample),
                "fps": sample_fps(sample),
            }
            vp8uya_path = sample_vp8uya_ivf_path(sample, runs_dir)
            libvpx_path = sample_libvpx_ivf_path(sample, runs_dir)
        except ValueError as exc:
            failure_reasons.append(str(exc))
            result = {
                "sample": sample_name,
                "width": sample.get("width"),
                "height": sample.get("height"),
                "frames": sample.get("frames"),
                "fps": sample.get("fps"),
            }
            vp8uya_path = runs_dir / f"{sample_name}.vp8uya.ivf"
            libvpx_path = runs_dir / f"{sample_name}.libvpx.ivf"

        vp8uya_payload = read_ivf_payload_bits(vp8uya_path)
        libvpx_payload = read_ivf_payload_bits(libvpx_path)
        if not vp8uya_payload["ok"]:
            failure_reasons.append(f"vp8uya: {vp8uya_payload['error']}")
        if not libvpx_payload["ok"]:
            failure_reasons.append(f"libvpx: {libvpx_payload['error']}")
        vp8uya_elapsed = read_encode_elapsed_ns(sample, runs_dir, "vp8uya")
        libvpx_elapsed = read_encode_elapsed_ns(sample, runs_dir, "libvpx")
        if not vp8uya_elapsed["ok"]:
            failure_reasons.append(f"vp8uya: {vp8uya_elapsed['error']}")
        if not libvpx_elapsed["ok"]:
            failure_reasons.append(f"libvpx: {libvpx_elapsed['error']}")
        vp8uya_psnr = read_sample_psnr(sample, i420_dir=i420_dir, runs_dir=runs_dir, encoder_label="vp8uya")
        libvpx_psnr = read_sample_psnr(sample, i420_dir=i420_dir, runs_dir=runs_dir, encoder_label="libvpx")
        if not vp8uya_psnr["ok"]:
            failure_reasons.append(f"vp8uya psnr: {vp8uya_psnr['error']}")
        if not libvpx_psnr["ok"]:
            failure_reasons.append(f"libvpx psnr: {libvpx_psnr['error']}")
        vp8uya_ssim = read_sample_ssim(sample, i420_dir=i420_dir, runs_dir=runs_dir, encoder_label="vp8uya")
        libvpx_ssim = read_sample_ssim(sample, i420_dir=i420_dir, runs_dir=runs_dir, encoder_label="libvpx")
        if not vp8uya_ssim["ok"]:
            failure_reasons.append(f"vp8uya ssim: {vp8uya_ssim['error']}")
        if not libvpx_ssim["ok"]:
            failure_reasons.append(f"libvpx ssim: {libvpx_ssim['error']}")

        try:
            vp8uya_bpp = bits_per_pixel(
                vp8uya_payload["payload_bits"],
                int(result["width"]),
                int(result["height"]),
                int(result["frames"]),
            )
            libvpx_bpp = bits_per_pixel(
                libvpx_payload["payload_bits"],
                int(result["width"]),
                int(result["height"]),
                int(result["frames"]),
            )
            vp8uya_fps = encode_fps(int(result["frames"]), int(vp8uya_elapsed["elapsed_ns"]))
            libvpx_fps = encode_fps(int(result["frames"]), int(libvpx_elapsed["elapsed_ns"]))
        except (TypeError, ValueError) as exc:
            vp8uya_bpp = 0.0
            libvpx_bpp = 0.0
            vp8uya_fps = 0.0
            libvpx_fps = 0.0
            failure_reasons.append(str(exc))

        try:
            psnr_delta = psnr_all_delta_db(
                float(vp8uya_psnr["psnr_all_db"]),
                float(libvpx_psnr["psnr_all_db"]),
            )
        except (TypeError, ValueError) as exc:
            psnr_delta = 0.0
            failure_reasons.append(str(exc))

        result.update({
            "vp8uya_ivf_path": str(vp8uya_path),
            "libvpx_ivf_path": str(libvpx_path),
            "vp8uya_payload_bits": vp8uya_payload["payload_bits"],
            "libvpx_payload_bits": libvpx_payload["payload_bits"],
            "vp8uya_bits_per_pixel": vp8uya_bpp,
            "libvpx_bits_per_pixel": libvpx_bpp,
            "vp8uya_encode_elapsed_ns": vp8uya_elapsed["elapsed_ns"],
            "libvpx_encode_elapsed_ns": libvpx_elapsed["elapsed_ns"],
            "vp8uya_fps": vp8uya_fps,
            "libvpx_fps": libvpx_fps,
            "psnr_y_db": vp8uya_psnr["psnr_y_db"],
            "psnr_u_db": vp8uya_psnr["psnr_u_db"],
            "psnr_v_db": vp8uya_psnr["psnr_v_db"],
            "psnr_all_db": vp8uya_psnr["psnr_all_db"],
            "vp8uya_psnr_y_db": vp8uya_psnr["psnr_y_db"],
            "vp8uya_psnr_u_db": vp8uya_psnr["psnr_u_db"],
            "vp8uya_psnr_v_db": vp8uya_psnr["psnr_v_db"],
            "vp8uya_psnr_all_db": vp8uya_psnr["psnr_all_db"],
            "libvpx_psnr_y_db": libvpx_psnr["psnr_y_db"],
            "libvpx_psnr_u_db": libvpx_psnr["psnr_u_db"],
            "libvpx_psnr_v_db": libvpx_psnr["psnr_v_db"],
            "libvpx_psnr_all_db": libvpx_psnr["psnr_all_db"],
            "psnr_all_delta_db": psnr_delta,
            "vp8uya_psnr_reference_path": vp8uya_psnr["reference_path"],
            "vp8uya_psnr_decoded_path": vp8uya_psnr["decoded_path"],
            "libvpx_psnr_reference_path": libvpx_psnr["reference_path"],
            "libvpx_psnr_decoded_path": libvpx_psnr["decoded_path"],
            "ssim_y": vp8uya_ssim["ssim_y"],
            "ssim_u": vp8uya_ssim["ssim_u"],
            "ssim_v": vp8uya_ssim["ssim_v"],
            "ssim_all": vp8uya_ssim["ssim_all"],
            "vp8uya_ssim_y": vp8uya_ssim["ssim_y"],
            "vp8uya_ssim_u": vp8uya_ssim["ssim_u"],
            "vp8uya_ssim_v": vp8uya_ssim["ssim_v"],
            "vp8uya_ssim_all": vp8uya_ssim["ssim_all"],
            "libvpx_ssim_y": libvpx_ssim["ssim_y"],
            "libvpx_ssim_u": libvpx_ssim["ssim_u"],
            "libvpx_ssim_v": libvpx_ssim["ssim_v"],
            "libvpx_ssim_all": libvpx_ssim["ssim_all"],
            "vp8uya_ssim_reference_path": vp8uya_ssim["reference_path"],
            "vp8uya_ssim_decoded_path": vp8uya_ssim["decoded_path"],
            "libvpx_ssim_reference_path": libvpx_ssim["reference_path"],
            "libvpx_ssim_decoded_path": libvpx_ssim["decoded_path"],
            "vp8uya_encode_metadata_path": vp8uya_elapsed["path"],
            "libvpx_encode_metadata_path": libvpx_elapsed["path"],
            "vp8uya_payload_bytes": vp8uya_payload["payload_bytes"],
            "libvpx_payload_bytes": libvpx_payload["payload_bytes"],
            "vp8uya_ivf_frame_count": vp8uya_payload["frame_count"],
            "libvpx_ivf_frame_count": libvpx_payload["frame_count"],
            "passed": len(failure_reasons) == 0,
            "failure_reasons": failure_reasons,
        })
        results.append(result)

    try:
        results_path.parent.mkdir(parents=True, exist_ok=True)
        with results_path.open("w", encoding="utf-8") as fh:
            for result in results:
                fh.write(json.dumps(result, sort_keys=True) + "\n")
    except OSError as exc:
        return {
            "ok": False,
            "manifest_path": str(manifest_path),
            "runs_dir": str(runs_dir),
            "results_ndjson": str(results_path),
            "sample_count": len(results),
            "error": f"failed to write results NDJSON {results_path}: {exc}",
        }

    return {
        "ok": all(result["passed"] for result in results),
        "manifest_path": str(manifest_path),
        "runs_dir": str(runs_dir),
        "results_ndjson": str(results_path),
        "sample_count": len(results),
        "error": None,
    }


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare vp8uya encoder output against libvpx")
    parser.add_argument(
        "--print-metric-contract",
        action="store_true",
        help="print the required benchmark metric names and hard thresholds as JSON",
    )
    parser.add_argument(
        "--probe-tools",
        action="store_true",
        help="locate vpxenc/vpxdec and print the lookup result as JSON",
    )
    parser.add_argument(
        "--fetch-vpx-tools",
        action="store_true",
        help="download vpx-tools .deb into build/deps without sudo",
    )
    parser.add_argument(
        "--extract-vpx-tools",
        action="store_true",
        help="extract the downloaded vpx-tools .deb into build/deps/vpx-tools-root",
    )
    parser.add_argument(
        "--prepare-sample-dirs",
        action="store_true",
        help="create real Y4M and converted I420 cache directories",
    )
    parser.add_argument(
        "--evaluate-result-json",
        type=Path,
        help="read one benchmark result JSON object, apply hard thresholds, and return non-zero on failure",
    )
    parser.add_argument(
        "--threshold",
        action="store_true",
        help="read results NDJSON, apply hard thresholds, and return non-zero on any failed sample",
    )
    parser.add_argument(
        "--write-repro-report",
        type=Path,
        help="read benchmark result JSON/NDJSON records and write failing-sample reproduction commands as Markdown",
    )
    parser.add_argument(
        "--write-results-ndjson",
        action="store_true",
        help="write per-sample benchmark result records",
    )
    parser.add_argument(
        "--write-summary-json",
        action="store_true",
        help="read results NDJSON and write aggregate summary JSON",
    )
    parser.add_argument(
        "--write-markdown-report",
        action="store_true",
        help="read results NDJSON and summary JSON and write Markdown report",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the selected sample plan without downloading, encoding, or decoding",
    )
    parser.add_argument(
        "--encode-vp8uya",
        action="store_true",
        help="run vp8uya encode for selected prepared I420 samples",
    )
    parser.add_argument(
        "--encode-libvpx",
        action="store_true",
        help="run vpxenc --best for selected prepared I420 samples",
    )
    parser.add_argument(
        "--decode-vp8uya",
        action="store_true",
        help="run vpxdec on selected vp8uya IVF outputs",
    )
    parser.add_argument(
        "--decode-libvpx",
        action="store_true",
        help="run vpxdec on selected libvpx IVF outputs",
    )
    parser.add_argument(
        "--group",
        help="only select samples whose manifest groups include this value",
    )
    parser.add_argument(
        "--frames",
        type=positive_int_arg,
        help="override each selected sample frame count",
    )
    parser.add_argument(
        "--warmups",
        type=nonnegative_int_arg,
        default=0,
        help="number of warmup encode runs to record in the benchmark plan",
    )
    parser.add_argument(
        "--repeats",
        type=positive_int_arg,
        default=1,
        help=f"number of measured encode runs; final statistic is {REPEAT_STATISTIC}",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST_PATH,
        help=f"path to the real-sample manifest, defaulting to {DEFAULT_MANIFEST_PATH}",
    )
    parser.add_argument(
        "--vp8uya-bin",
        type=Path,
        default=None,
        help=f"path to the vp8uya binary, defaulting to {DEFAULT_VP8UYA_BIN}",
    )
    parser.add_argument(
        "--y4m-cache-dir",
        type=Path,
        default=DEFAULT_Y4M_CACHE_DIR,
        help="directory for downloaded Y4M samples",
    )
    parser.add_argument(
        "--i420-cache-dir",
        type=Path,
        default=DEFAULT_I420_CACHE_DIR,
        help="directory for converted raw I420 samples",
    )
    parser.add_argument(
        "--runs-dir",
        type=Path,
        default=DEFAULT_RUNS_DIR,
        help=f"directory for benchmark run artifacts, defaulting to {DEFAULT_RUNS_DIR}",
    )
    parser.add_argument(
        "--repro-report-md",
        type=Path,
        default=DEFAULT_REPRO_REPORT_PATH,
        help=f"Markdown path for --write-repro-report, defaulting to {DEFAULT_REPRO_REPORT_PATH}",
    )
    parser.add_argument(
        "--results-ndjson",
        type=Path,
        default=DEFAULT_RESULTS_NDJSON_PATH,
        help=f"NDJSON path for --write-results-ndjson, defaulting to {DEFAULT_RESULTS_NDJSON_PATH}",
    )
    parser.add_argument(
        "--summary-json",
        type=Path,
        default=DEFAULT_SUMMARY_JSON_PATH,
        help=f"JSON summary path for --write-summary-json, defaulting to {DEFAULT_SUMMARY_JSON_PATH}",
    )
    parser.add_argument(
        "--markdown-report-md",
        type=Path,
        default=DEFAULT_MARKDOWN_REPORT_PATH,
        help=f"Markdown report path for --write-markdown-report, defaulting to {DEFAULT_MARKDOWN_REPORT_PATH}",
    )
    return parser.parse_args(argv[1:])


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.vp8uya_bin is not None:
        report = validate_vp8uya_binary(args.vp8uya_bin)
        if not report["ok"]:
            print(report["error"], file=sys.stderr)
            return 2
    if args.print_metric_contract:
        print(json.dumps(metric_contract(), indent=2, sort_keys=True))
        return 0
    if args.probe_tools:
        report = probe_tools()
        print(json.dumps(report, indent=2, sort_keys=True))
        if not report["ok"]:
            for tool_name in ("vpxenc", "vpxdec"):
                error = report[tool_name].get("error")
                if error:
                    print(error, file=sys.stderr)
        return 0 if report["ok"] else 2
    if args.fetch_vpx_tools:
        report = fetch_vpx_tools()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.extract_vpx_tools:
        report = extract_vpx_tools()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.dry_run:
        report = dry_run_samples(
            manifest_path=args.manifest,
            group=args.group,
            frames_override=args.frames,
            warmups=args.warmups,
            repeats=args.repeats,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.encode_vp8uya:
        report = encode_vp8uya_samples(
            manifest_path=args.manifest,
            group=args.group,
            frames_override=args.frames,
            i420_dir=args.i420_cache_dir,
            runs_dir=args.runs_dir,
            vp8uya_bin=args.vp8uya_bin or DEFAULT_VP8UYA_BIN,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.encode_libvpx:
        report = encode_libvpx_samples(
            manifest_path=args.manifest,
            group=args.group,
            frames_override=args.frames,
            i420_dir=args.i420_cache_dir,
            runs_dir=args.runs_dir,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.decode_vp8uya:
        report = decode_vpxdec_samples(
            encoder_label="vp8uya",
            manifest_path=args.manifest,
            group=args.group,
            frames_override=args.frames,
            runs_dir=args.runs_dir,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.decode_libvpx:
        report = decode_vpxdec_samples(
            encoder_label="libvpx",
            manifest_path=args.manifest,
            group=args.group,
            frames_override=args.frames,
            runs_dir=args.runs_dir,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.prepare_sample_dirs:
        report = prepare_sample_dirs(y4m_dir=args.y4m_cache_dir, i420_dir=args.i420_cache_dir)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.evaluate_result_json is not None:
        report = evaluate_result_json(args.evaluate_result_json)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 2
    if args.threshold:
        report = threshold_results(results_path=args.results_ndjson)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["passed"] else 2
    if args.write_repro_report is not None:
        report = write_repro_report(args.write_repro_report, report_path=args.repro_report_md)
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.write_results_ndjson:
        report = write_results_ndjson_payload_bits(
            manifest_path=args.manifest,
            group=args.group,
            frames_override=args.frames,
            i420_dir=args.i420_cache_dir,
            runs_dir=args.runs_dir,
            results_path=args.results_ndjson,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.write_summary_json:
        report = write_summary_json(
            results_path=args.results_ndjson,
            summary_path=args.summary_json,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2
    if args.write_markdown_report:
        report = write_markdown_report(
            results_path=args.results_ndjson,
            summary_path=args.summary_json,
            report_path=args.markdown_report_md,
        )
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0 if report["ok"] else 2

    print("error: no action requested; use --print-metric-contract, --probe-tools, --fetch-vpx-tools, --extract-vpx-tools, --dry-run, --encode-vp8uya, --encode-libvpx, --decode-vp8uya, --decode-libvpx, --prepare-sample-dirs, --evaluate-result-json, --threshold, --write-repro-report, --write-results-ndjson, --write-summary-json, or --write-markdown-report", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
