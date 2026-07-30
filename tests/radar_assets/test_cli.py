from __future__ import annotations
from pathlib import Path
import subprocess
import pytest
from clutchiq.radar_assets import cli, source2viewer
from clutchiq.radar_assets.source2viewer import Source2ViewerError


def test_build_reports_and_logs_before_detection(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    events: list[str] = []
    def find_cs2(*_args: object) -> Path: events.append("detect"); return tmp_path
    monkeypatch.setattr(cli, "find_cs2", find_cs2); monkeypatch.setattr(cli, "resolve_source2viewer", lambda *_: tmp_path / "tool"); monkeypatch.setattr(cli, "find_vpks", lambda _: [])
    with pytest.raises(RuntimeError, match="no overview"): cli.build(None, None, None, tmp_path / "output")
    assert events == ["detect"]
    assert capsys.readouterr().out.splitlines()[0] == "Radar assets build starting."
    assert next((tmp_path / "output").glob("radar-assets-*.log")).read_text(encoding="utf-8").splitlines()[0].endswith("Radar assets build starting.")


def test_diagnostic_limit_one_extracts_once_with_strict_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    extracted: list[tuple[Path, int]] = []
    monkeypatch.setattr(cli, "find_cs2", lambda *_: tmp_path); monkeypatch.setattr(cli, "resolve_source2viewer", lambda *_: tmp_path / "tool"); monkeypatch.setattr(cli, "find_vpks", lambda _: iter((tmp_path / "one.vpk", tmp_path / "two.vpk"))); monkeypatch.setattr(cli, "extract_targeted", lambda _tool, vpk, _destination, *, timeout, reporter: extracted.append((vpk, timeout)))
    with pytest.raises(RuntimeError, match="no overview"): cli.build(None, None, None, tmp_path / "output", diagnostic=True, limit=1)
    assert extracted == [(tmp_path / "one.vpk", cli.EXTRACTION_TIMEOUT_SECONDS)]


def test_diagnostic_requires_limit_one(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="requires --limit 1"): cli.build(None, None, None, tmp_path / "output", diagnostic=True)


def test_existing_build_lock_is_rejected(tmp_path: Path) -> None:
    output = tmp_path / "output"; output.mkdir(); (output / ".radar-assets-build.lock").write_text("other build", encoding="utf-8")
    with pytest.raises(RuntimeError, match="already running"): cli.build(None, None, None, output, diagnostic=True, limit=1)


def test_extract_rejects_non_positive_timeout(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="timeout must be positive"): source2viewer.extract(tmp_path / "tool", tmp_path / "input.vpk", tmp_path / "output", timeout=0)


def test_targeted_extraction_uses_two_source2viewer_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[list[str], int, source2viewer.Report | None]] = []
    def run(command: list[str], *, timeout: int, reporter: source2viewer.Report | None = None) -> subprocess.CompletedProcess[str]:
        calls.append((command, timeout, reporter))
        listing = "resource/overviews/de_dust2.txt CRC:123 size:456\n" if "resource/overviews/" in command else '"panorama\\images\\overheadmaps\\de_dust2_radar_psd.vtex_c" CRC:789 size:012\n'
        return subprocess.CompletedProcess(command, 0, listing, "")
    monkeypatch.setattr(source2viewer, "_run", run)
    reports: list[str] = []; tool = tmp_path / "Source2Viewer-CLI.exe"; vpk = tmp_path / "pak01_dir.vpk"; staging = tmp_path / "staging"
    source2viewer.extract_targeted(tool, vpk, staging, timeout=31, reporter=reports.append)
    assert [call[0] for call in calls] == [
        [str(tool), "-i", str(vpk), "--vpk_list", "--vpk_filepath", "resource/overviews/", "--vpk_extensions", "txt"],
        [str(tool), "-i", str(vpk), "--vpk_list", "--vpk_filepath", "panorama/images/overheadmaps/", "--vpk_extensions", "vtex_c"],
        [str(tool), "-i", str(vpk), "-o", str(staging), "--vpk_decompile", "--vpk_filepath", "resource/overviews/", "--vpk_extensions", "txt", "--threads", "1"],
        [str(tool), "-i", str(vpk), "-o", str(staging), "--vpk_decompile", "--vpk_filepath", "panorama/images/overheadmaps/", "--vpk_extensions", "vtex_c", "--threads", "1"],
    ]
    assert [call[1] for call in calls] == [31, 31, 31, 31]
    assert reports == []


def test_targeted_extraction_refuses_empty_successful_overheadmap_listing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    def run(command: list[str], *, timeout: int, reporter: source2viewer.Report | None = None) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        output = "resource/overviews/de_dust2.txt CRC:123 size:456\n" if "resource/overviews/" in command else ""
        return subprocess.CompletedProcess(command, 0, output, "")
    monkeypatch.setattr(source2viewer, "_run", run)
    with pytest.raises(Source2ViewerError, match="no vtex_c assets"):
        source2viewer.extract_targeted(tmp_path / "tool", tmp_path / "pak01_dir.vpk", tmp_path / "staging")
    assert len(calls) == 2


def test_parse_targeted_vpk_list_accepts_metadata_and_quoted_backslash_paths() -> None:
    assert source2viewer.parse_targeted_vpk_list('"panorama\\images\\overheadmaps\\de_mirage_radar_psd.vtex_c" CRC:789 size:012\n', vpk_path="panorama/images/overheadmaps/", extensions="vtex_c") == ("panorama/images/overheadmaps/de_mirage_radar_psd.vtex_c",)


def test_decoded_radar_filename_normalization_and_primary_preference(tmp_path: Path) -> None:
    primary = tmp_path / "de_dust2_radar_psd.png"; alternate = tmp_path / "de_dust2_radar_tga.png"; lower = tmp_path / "de_dust2_lower_radar_psd.png"
    assert cli._decoded_radar_key(primary) == ("de_dust2", "upper")
    assert cli._decoded_radar_key(lower) == ("de_dust2", "lower")
    assert min((alternate, primary), key=cli._image_priority) == primary


def test_targeted_extraction_stops_after_listing_failure(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    def run(command: list[str], *, timeout: int, reporter: source2viewer.Report | None = None) -> subprocess.CompletedProcess[str]: calls.append(command); return subprocess.CompletedProcess(command, 1, "", "listing failed")
    monkeypatch.setattr(source2viewer, "_run", run)
    with pytest.raises(Source2ViewerError, match="targeted listing failed"): source2viewer.extract_targeted(tmp_path / "tool", tmp_path / "pak01_dir.vpk", tmp_path / "staging")
    assert len(calls) == 1
