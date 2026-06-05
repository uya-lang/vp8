#!/usr/bin/env python3
"""Contract checks for libvpx encoder comparison metrics."""

from __future__ import annotations

import importlib.util
import json
import os
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "bench" / "libvpx_encode_compare.py"

REQUIRED_FIELDS = {
    "vp8uya_bits_per_pixel",
    "libvpx_bits_per_pixel",
    "vp8uya_psnr_all_db",
    "libvpx_psnr_all_db",
    "vp8uya_fps",
    "libvpx_fps",
}

REQUIRED_SUMMARY_FIELDS = {
    "vp8uya_bits_per_pixel",
    "libvpx_bits_per_pixel",
    "vp8uya_psnr_all_db",
    "libvpx_psnr_all_db",
    "vp8uya_fps",
    "libvpx_fps",
    "vpxenc_version",
    "vpxdec_version",
}


def load_module():
    spec = importlib.util.spec_from_file_location("libvpx_encode_compare", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError(f"failed to load {SCRIPT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def assert_contract(contract: dict[str, object]) -> None:
    fields = set(contract["required_result_fields"])
    missing = REQUIRED_FIELDS - fields
    if missing:
        raise AssertionError(f"missing required metric fields: {sorted(missing)}")

    summary_fields = set(contract["required_summary_fields"])
    missing_summary = REQUIRED_SUMMARY_FIELDS - summary_fields
    if missing_summary:
        raise AssertionError(f"missing required summary fields: {sorted(missing_summary)}")

    thresholds = contract["thresholds"]
    assert thresholds["max_bitrate_ratio"] == 1.10
    assert thresholds["min_psnr_all_delta_db"] == -0.50
    assert thresholds["min_fps_ratio"] == 0.80
    assert contract["libvpx_preset"] == "vpxenc --best"


def make_result(**overrides: object) -> dict[str, object]:
    result: dict[str, object] = {
        "sample": "unit",
        "width": 16,
        "height": 16,
        "frames": 1,
        "fps": "30/1",
        "vp8uya_bits_per_pixel": 1.0,
        "libvpx_bits_per_pixel": 1.0,
        "vp8uya_psnr_all_db": 40.0,
        "libvpx_psnr_all_db": 40.0,
        "vp8uya_ssim_all": 0.99,
        "libvpx_ssim_all": 0.99,
        "vp8uya_fps": 100.0,
        "libvpx_fps": 100.0,
    }
    result.update(overrides)
    return result


def assert_bitrate_threshold(module: object) -> None:
    passing = module.evaluate_thresholds(
        make_result(vp8uya_bits_per_pixel=1.10, libvpx_bits_per_pixel=1.0)
    )
    assert passing["passed"] is True
    assert passing["bitrate_ratio"] == 1.10
    assert passing["failure_reasons"] == []

    failing = module.evaluate_thresholds(
        make_result(vp8uya_bits_per_pixel=1.11, libvpx_bits_per_pixel=1.0)
    )
    assert failing["passed"] is False
    assert failing["bitrate_ratio"] == 1.11
    assert any("bitrate_ratio" in reason for reason in failing["failure_reasons"])


def assert_psnr_threshold(module: object) -> None:
    passing = module.evaluate_thresholds(
        make_result(vp8uya_psnr_all_db=39.50, libvpx_psnr_all_db=40.0)
    )
    assert passing["passed"] is True
    assert passing["psnr_all_delta_db"] == -0.50
    assert passing["failure_reasons"] == []

    failing = module.evaluate_thresholds(
        make_result(vp8uya_psnr_all_db=39.49, libvpx_psnr_all_db=40.0)
    )
    assert failing["passed"] is False
    assert failing["psnr_all_delta_db"] == -0.51
    assert any("psnr_all_delta_db" in reason for reason in failing["failure_reasons"])


def assert_fps_threshold(module: object) -> None:
    passing = module.evaluate_thresholds(
        make_result(vp8uya_fps=80.0, libvpx_fps=100.0)
    )
    assert passing["passed"] is True
    assert passing["fps_ratio"] == 0.80
    assert passing["failure_reasons"] == []

    failing = module.evaluate_thresholds(
        make_result(vp8uya_fps=79.0, libvpx_fps=100.0)
    )
    assert failing["passed"] is False
    assert failing["fps_ratio"] == 0.79
    assert any("fps_ratio" in reason for reason in failing["failure_reasons"])


def assert_threshold_cli_return_codes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        passing_path = tmp_path / "passing.json"
        failing_path = tmp_path / "failing.json"
        psnr_failing_path = tmp_path / "psnr_failing.json"
        fps_failing_path = tmp_path / "fps_failing.json"
        passing_path.write_text(json.dumps(make_result()), encoding="utf-8")
        failing_path.write_text(
            json.dumps(make_result(vp8uya_bits_per_pixel=1.11, libvpx_bits_per_pixel=1.0)),
            encoding="utf-8",
        )
        psnr_failing_path.write_text(
            json.dumps(make_result(vp8uya_psnr_all_db=39.49, libvpx_psnr_all_db=40.0)),
            encoding="utf-8",
        )
        fps_failing_path.write_text(
            json.dumps(make_result(vp8uya_fps=79.0, libvpx_fps=100.0)),
            encoding="utf-8",
        )

        passing = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--evaluate-result-json", str(passing_path)],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if passing.returncode != 0:
            raise AssertionError(passing.stdout)
        passing_report = json.loads(passing.stdout)
        assert passing_report["passed"] is True

        failing = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--evaluate-result-json", str(failing_path)],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert failing.returncode != 0
        failing_report = json.loads(failing.stdout)
        assert failing_report["passed"] is False
        assert failing_report["bitrate_ratio"] == 1.11
        assert any("bitrate_ratio" in reason for reason in failing_report["failure_reasons"])

        psnr_failing = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--evaluate-result-json", str(psnr_failing_path)],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert psnr_failing.returncode != 0
        psnr_report = json.loads(psnr_failing.stdout)
        assert psnr_report["passed"] is False
        assert psnr_report["psnr_all_delta_db"] == -0.51
        assert any("psnr_all_delta_db" in reason for reason in psnr_report["failure_reasons"])

        fps_failing = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--evaluate-result-json", str(fps_failing_path)],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert fps_failing.returncode != 0
        fps_report = json.loads(fps_failing.stdout)
        assert fps_report["passed"] is False
        assert fps_report["fps_ratio"] == 0.79
        assert any("fps_ratio" in reason for reason in fps_report["failure_reasons"])


def assert_vp8uya_bin_missing_cli_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        missing = Path(tmp) / "missing-vp8uya"
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--vp8uya-bin", str(missing)],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        assert completed.returncode != 0
        assert str(missing) in completed.stdout
        assert "unrecognized arguments" not in completed.stdout
        assert "vp8uya binary" in completed.stdout


def assert_group_dry_run_filters_qcif() -> None:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--group", "qcif", "--dry-run"],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stdout)
    report = json.loads(completed.stdout)
    sample_names = [sample["name"] for sample in report["samples"]]
    assert sample_names == ["akiyo_qcif", "foreman_qcif", "coastguard_qcif"]
    assert "mobile_cif" not in sample_names
    assert all("qcif" in sample["groups"] for sample in report["samples"])


def assert_ssim_is_record_only(module: object) -> None:
    contract = module.metric_contract()
    fields = set(contract["required_result_fields"])
    hard_threshold_fields = set(contract["hard_threshold_fields"])
    assert "vp8uya_ssim_all" in fields
    assert "libvpx_ssim_all" in fields
    assert "vp8uya_ssim_all" not in hard_threshold_fields
    assert "libvpx_ssim_all" not in hard_threshold_fields

    evaluated = module.evaluate_thresholds(
        make_result(vp8uya_ssim_all=0.10, libvpx_ssim_all=0.99)
    )
    assert evaluated["passed"] is True
    assert not any("ssim" in reason.lower() for reason in evaluated["failure_reasons"])


def write_fake_executable(path: Path) -> None:
    path.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    path.chmod(path.stat().st_mode | 0o111)


def write_fake_help_version_tool(path: Path, version_line: str) -> None:
    path.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = \"--version\" ]; then\n"
        "  echo unsupported >&2\n"
        "  exit 1\n"
        "fi\n"
        "if [ \"$1\" = \"--help\" ]; then\n"
        f"  echo '{version_line}'\n"
        "  exit 0\n"
        "fi\n"
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | 0o111)


def assert_vpxenc_env_lookup(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp) / "fake-vpxenc"
        write_fake_executable(fake)
        found = module.find_vpx_tool("vpxenc", "VPXENC", env={"VPXENC": str(fake)}, path="")
        assert found["path"] == str(fake)
        assert found["source"] == "VPXENC"
        assert found["error"] is None

        missing_path = str(Path(tmp) / "missing-vpxenc")
        missing = module.find_vpx_tool("vpxenc", "VPXENC", env={"VPXENC": missing_path}, path="")
        assert missing["path"] is None
        assert missing["source"] == "VPXENC"
        assert "VPXENC" in missing["error"]
        assert missing_path in missing["error"]


def assert_vpxdec_env_lookup(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        fake = Path(tmp) / "fake-vpxdec"
        write_fake_executable(fake)
        found = module.find_vpx_tool("vpxdec", "VPXDEC", env={"VPXDEC": str(fake)}, path="")
        assert found["path"] == str(fake)
        assert found["source"] == "VPXDEC"
        assert found["error"] is None

        missing_path = str(Path(tmp) / "missing-vpxdec")
        missing = module.find_vpx_tool("vpxdec", "VPXDEC", env={"VPXDEC": missing_path}, path="")
        assert missing["path"] is None
        assert missing["source"] == "VPXDEC"
        assert "VPXDEC" in missing["error"]
        assert missing_path in missing["error"]


def assert_probe_tools_path_lookup() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write_fake_executable(tmp_path / "vpxenc")
        write_fake_executable(tmp_path / "vpxdec")
        env = dict(os.environ)
        env["PATH"] = str(tmp_path)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--probe-tools"],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout)
        report = json.loads(completed.stdout)
        assert report["vpxenc"]["source"] == "PATH"
        assert report["vpxenc"]["path"] == str(tmp_path / "vpxenc")
        assert report["vpxenc"]["version_returncode"] == 0
        assert report["vpxenc"]["probe_returncode"] == 0
        assert report["vpxenc_probe_returncode"] == 0
        assert report["vpxdec"]["source"] == "PATH"
        assert report["vpxdec"]["path"] == str(tmp_path / "vpxdec")
        assert report["vpxdec"]["version_returncode"] == 0
        assert report["vpxdec"]["probe_returncode"] == 0
        assert report["vpxdec_probe_returncode"] == 0


def assert_probe_tools_help_version_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write_fake_help_version_tool(tmp_path / "vpxenc", "vp8 - WebM Project VP8 Encoder v9.8.7")
        write_fake_help_version_tool(tmp_path / "vpxdec", "vp8 - WebM Project VP8 Decoder v9.8.7")
        env = dict(os.environ)
        env["PATH"] = str(tmp_path)
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--probe-tools"],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout)
        report = json.loads(completed.stdout)
        assert report["vpxenc_version"] == "vp8 - WebM Project VP8 Encoder v9.8.7"
        assert report["vpxenc"]["version_source"] == "help"
        assert report["vpxdec_version"] == "vp8 - WebM Project VP8 Decoder v9.8.7"
        assert report["vpxdec"]["version_source"] == "help"


def assert_extracted_dir_lookup(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        write_fake_executable(tmp_path / "vpxenc")
        write_fake_executable(tmp_path / "vpxdec")

        vpxenc = module.find_vpx_tool("vpxenc", "VPXENC", env={}, path="", extracted_dir=tmp_path)
        assert vpxenc["path"] == str(tmp_path / "vpxenc")
        assert vpxenc["source"] == "extracted"
        assert vpxenc["error"] is None

        vpxdec = module.find_vpx_tool("vpxdec", "VPXDEC", env={}, path="", extracted_dir=tmp_path)
        assert vpxdec["path"] == str(tmp_path / "vpxdec")
        assert vpxdec["source"] == "extracted"
        assert vpxdec["error"] is None


def assert_missing_tool_error(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        missing = module.find_vpx_tool("vpxenc", "VPXENC", env={}, path="", extracted_dir=Path(tmp))
        assert missing["path"] is None
        assert "vpxenc" in missing["error"]
        assert "VPXENC" in missing["error"]
        assert "PATH" in missing["error"]
        assert "vpx-tools" in missing["error"]
        assert "--fetch-vpx-tools" in missing["error"]
        assert "--extract-vpx-tools" in missing["error"]


def assert_probe_tools_missing_cli_suggestion() -> None:
    extracted_root = REPO_ROOT / "build" / "deps" / "vpx-tools-root"
    backup_root = extracted_root.with_name("vpx-tools-root.contract-test-backup")
    moved_existing_root = False
    if backup_root.exists():
        raise AssertionError(f"stale test backup exists: {backup_root}")
    if extracted_root.exists():
        extracted_root.rename(backup_root)
        moved_existing_root = True

    try:
        env = dict(os.environ)
        env.pop("VPXENC", None)
        env.pop("VPXDEC", None)
        env["PATH"] = "/nonexistent"
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_PATH), "--probe-tools"],
            cwd=REPO_ROOT,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert completed.returncode != 0
        assert "VPXENC" in completed.stderr
        assert "VPXDEC" in completed.stderr
        assert "--fetch-vpx-tools" in completed.stderr
    finally:
        if moved_existing_root:
            backup_root.rename(extracted_root)


def assert_fetch_vpx_tools_download(module: object) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        if "sudo" in command:
            return subprocess.CompletedProcess(command, 1, "", "sudo must not be used")
        (cwd / "vpx-tools_1.0_test_amd64.deb").write_bytes(b"fake deb")
        return subprocess.CompletedProcess(command, 0, "downloaded\n", "")

    with tempfile.TemporaryDirectory() as tmp:
        report = module.fetch_vpx_tools(download_dir=Path(tmp), runner=fake_runner)
        assert report["ok"] is True
        assert calls == [(["apt-get", "download", "vpx-tools"], Path(tmp))]
        assert report["command"] == ["apt-get", "download", "vpx-tools"]
        assert report["deb_files"] == [str(Path(tmp) / "vpx-tools_1.0_test_amd64.deb")]


def assert_extract_vpx_tools(module: object) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        if "sudo" in command:
            return subprocess.CompletedProcess(command, 1, "", "sudo must not be used")
        root = Path(command[3])
        bin_dir = root / "usr" / "bin"
        bin_dir.mkdir(parents=True, exist_ok=True)
        write_fake_executable(bin_dir / "vpxenc")
        write_fake_executable(bin_dir / "vpxdec")
        return subprocess.CompletedProcess(command, 0, "extracted\n", "")

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        deb = tmp_path / "vpx-tools_1.0_test_amd64.deb"
        deb.write_bytes(b"fake deb")
        root = tmp_path / "vpx-tools-root"
        report = module.extract_vpx_tools(deps_dir=tmp_path, extract_root=root, runner=fake_runner)
        assert report["ok"] is True
        assert calls == [(["dpkg-deb", "-x", str(deb), str(root)], tmp_path)]
        assert report["command"] == ["dpkg-deb", "-x", str(deb), str(root)]
        assert report["vpxenc"] == str(root / "usr" / "bin" / "vpxenc")
        assert report["vpxdec"] == str(root / "usr" / "bin" / "vpxdec")


def assert_prepare_sample_dirs(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        y4m_dir = root / "real-y4m"
        i420_dir = root / "fixtures"
        report = module.prepare_sample_dirs(y4m_dir=y4m_dir, i420_dir=i420_dir)
        assert report["ok"] is True
        assert report["y4m_cache_dir"] == str(y4m_dir)
        assert report["i420_cache_dir"] == str(i420_dir)
        assert y4m_dir.is_dir()
        assert i420_dir.is_dir()

        completed = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_PATH),
                "--prepare-sample-dirs",
                "--y4m-cache-dir",
                str(root / "cli-real-y4m"),
                "--i420-cache-dir",
                str(root / "cli-fixtures"),
            ],
            cwd=REPO_ROOT,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if completed.returncode != 0:
            raise AssertionError(completed.stdout)
        cli_report = json.loads(completed.stdout)
        assert cli_report["ok"] is True
        assert (root / "cli-real-y4m").is_dir()
        assert (root / "cli-fixtures").is_dir()


def assert_download_y4m_sample(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        y4m_dir = Path(tmp)
        sample = {
            "name": "unit_sample",
            "url": "https://example.test/unit_sample.y4m",
        }

        def ok_downloader(url: str, dest: Path) -> None:
            assert url == sample["url"]
            assert dest == y4m_dir / "unit_sample.y4m.part"
            assert not (y4m_dir / "unit_sample.y4m").exists()
            dest.write_bytes(b"YUV4MPEG2\nFRAME\n")

        ok_report = module.download_y4m_sample(sample, y4m_dir=y4m_dir, downloader=ok_downloader)
        y4m_path = y4m_dir / "unit_sample.y4m"
        assert ok_report["ok"] is True
        assert ok_report["cached"] is False
        assert ok_report["path"] == str(y4m_path)
        assert y4m_path.read_bytes() == b"YUV4MPEG2\nFRAME\n"

    with tempfile.TemporaryDirectory() as tmp:
        y4m_dir = Path(tmp)
        sample = {
            "name": "broken_sample",
            "url": "https://example.test/broken_sample.y4m",
        }

        def failing_downloader(url: str, dest: Path) -> None:
            dest.write_bytes(b"partial")
            raise RuntimeError("network broke")

        failed = module.download_y4m_sample(sample, y4m_dir=y4m_dir, downloader=failing_downloader)
        assert failed["ok"] is False
        assert "network broke" in failed["error"]
        assert not (y4m_dir / "broken_sample.y4m").exists()
        assert not (y4m_dir / "broken_sample.y4m.part").exists()


def assert_verify_y4m_sha256(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        y4m_dir = Path(tmp)
        path = y4m_dir / "hash_ok.y4m"
        payload = b"YUV4MPEG2\nFRAME\nok"
        path.write_bytes(payload)
        sample = {
            "name": "hash_ok",
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        ok = module.verify_y4m_sample_sha256(sample, y4m_dir=y4m_dir)
        assert ok["ok"] is True
        assert ok["actual_sha256"] == sample["sha256"]
        assert path.exists()

    with tempfile.TemporaryDirectory() as tmp:
        y4m_dir = Path(tmp)
        path = y4m_dir / "hash_bad.y4m"
        path.write_bytes(b"bad payload")
        sample = {
            "name": "hash_bad",
            "sha256": "0" * 64,
        }
        bad = module.verify_y4m_sample_sha256(sample, y4m_dir=y4m_dir)
        bad_path = y4m_dir / "hash_bad.y4m.bad-sha256"
        assert bad["ok"] is False
        assert "sha256 mismatch" in bad["error"]
        assert not path.exists()
        assert bad_path.exists()


def assert_y4m_cache_reuse(module: object) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        y4m_dir = Path(tmp)
        payload = b"YUV4MPEG2\nFRAME\ncached"
        sample = {
            "name": "cache_sample",
            "url": "https://example.test/cache_sample.y4m",
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
        calls = 0

        def downloader(url: str, dest: Path) -> None:
            nonlocal calls
            calls += 1
            dest.write_bytes(payload)

        first = module.ensure_y4m_sample(sample, y4m_dir=y4m_dir, downloader=downloader)
        second = module.ensure_y4m_sample(sample, y4m_dir=y4m_dir, downloader=downloader)
        assert first["ok"] is True
        assert first["download"]["cached"] is False
        assert second["ok"] is True
        assert second["download"]["cached"] is True
        assert calls == 1


def assert_convert_y4m_to_i420(module: object) -> None:
    calls: list[tuple[list[str], Path]] = []

    def fake_runner(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        calls.append((command, cwd))
        Path(command[-1]).write_bytes(b"i420 payload")
        return subprocess.CompletedProcess(command, 0, "converted\n", "")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        y4m_dir = root / "real-y4m"
        i420_dir = root / "fixtures"
        y4m_dir.mkdir()
        (y4m_dir / "convert_sample.y4m").write_bytes(b"YUV4MPEG2\nFRAME\n")
        sample = {
            "name": "convert_sample",
            "frames": 60,
        }
        report = module.convert_y4m_to_i420(
            sample,
            y4m_dir=y4m_dir,
            i420_dir=i420_dir,
            runner=fake_runner,
        )
        output = i420_dir / "convert_sample.i420"
        assert report["ok"] is True
        assert report["output_path"] == str(output)
        assert output.read_bytes() == b"i420 payload"
        assert calls == [(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(y4m_dir / "convert_sample.y4m"),
                "-frames:v",
                "60",
                "-pix_fmt",
                "yuv420p",
                "-f",
                "rawvideo",
                str(output),
            ],
            module.REPO_ROOT,
        )]


def assert_i420_size_validation(module: object) -> None:
    assert module.i420_frame_size(16, 16) == 384
    assert module.i420_frame_size(17, 17) == 451

    with tempfile.TemporaryDirectory() as tmp:
        i420_dir = Path(tmp)
        sample = {
            "name": "size_ok",
            "width": 16,
            "height": 16,
            "frames": 3,
        }
        path = i420_dir / "size_ok.i420"
        path.write_bytes(bytes(384 * 3))
        ok = module.validate_i420_sample_size(sample, i420_dir=i420_dir)
        assert ok["ok"] is True
        assert ok["expected_bytes"] == 384 * 3
        assert ok["actual_bytes"] == 384 * 3

        sample_bad = {
            "name": "size_bad",
            "width": 16,
            "height": 16,
            "frames": 3,
        }
        bad_path = i420_dir / "size_bad.i420"
        bad_path.write_bytes(bytes(384 * 2))
        bad = module.validate_i420_sample_size(sample_bad, i420_dir=i420_dir)
        assert bad["ok"] is False
        assert bad["expected_bytes"] == 384 * 3
        assert bad["actual_bytes"] == 384 * 2
        assert "I420 size mismatch" in bad["error"]


def main() -> int:
    module = load_module()
    assert_contract(module.metric_contract())
    assert_bitrate_threshold(module)
    assert_psnr_threshold(module)
    assert_fps_threshold(module)
    assert_threshold_cli_return_codes()
    assert_vp8uya_bin_missing_cli_path()
    assert_group_dry_run_filters_qcif()
    assert_ssim_is_record_only(module)
    assert_vpxenc_env_lookup(module)
    assert_vpxdec_env_lookup(module)
    assert_probe_tools_path_lookup()
    assert_probe_tools_help_version_fallback()
    assert_extracted_dir_lookup(module)
    assert_missing_tool_error(module)
    assert_probe_tools_missing_cli_suggestion()
    assert_fetch_vpx_tools_download(module)
    assert_extract_vpx_tools(module)
    assert_prepare_sample_dirs(module)
    assert_download_y4m_sample(module)
    assert_verify_y4m_sha256(module)
    assert_y4m_cache_reuse(module)
    assert_convert_y4m_to_i420(module)
    assert_i420_size_validation(module)

    completed = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--print-metric-contract"],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise AssertionError(completed.stdout)
    assert_contract(json.loads(completed.stdout))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
