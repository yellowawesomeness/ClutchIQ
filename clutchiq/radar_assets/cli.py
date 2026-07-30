"""Command line interface for user-owned CS2 radar generation."""
from __future__ import annotations

import argparse
from datetime import datetime
import itertools
import os
from pathlib import Path
import tempfile

from .images import install_png
from .manifest import RadarLevel, RadarManifestEntry, write_manifest
from .overview import parse_overview
from .source2viewer import Source2ViewerError, extract_targeted, resolve_source2viewer
from .steam import SteamDiscoveryError, find_cs2, find_vpks

EXTRACTION_TIMEOUT_SECONDS = 90


class BuildReporter:
    """Write durable diagnostic records while reporting build progress."""
    def __init__(self, output: Path) -> None:
        output.mkdir(parents=True, exist_ok=True)
        self.path = output / f"radar-assets-{datetime.now():%Y%m%d-%H%M%S-%f}-{os.getpid()}.log"
        self._stream = self.path.open("x", encoding="utf-8")
    def report(self, message: str) -> None:
        self._stream.write(f"[{datetime.now().isoformat(timespec='milliseconds')}] {message}\n"); self._stream.flush(); print(message, flush=True)
    def close(self) -> None: self._stream.close()
    def __enter__(self) -> BuildReporter: return self
    def __exit__(self, *_: object) -> None: self.close()


class BuildLock:
    """An exclusive lock preventing simultaneous radar extraction builds."""
    def __init__(self, output: Path) -> None: self.path = output / ".radar-assets-build.lock"; self._acquired = False
    def __enter__(self) -> BuildLock:
        try: descriptor = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error: raise RuntimeError(f"A radar-assets build is already running ({self.path}).") from error
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream: stream.write(f"pid={os.getpid()} started={datetime.now().isoformat(timespec='seconds')}\n"); stream.flush()
        self._acquired = True; return self
    def __exit__(self, *_: object) -> None:
        if self._acquired: self.path.unlink(missing_ok=True)


def _map_name(path: Path) -> tuple[str, str]:
    name = path.stem.lower()
    for suffix in ("_radar", "_overview"):
        if name.endswith(suffix): name = name[:-len(suffix)]
    level = "lower" if name.endswith("_lower") else "upper"
    if level == "lower": name = name[:-6]
    return name, level


def _decoded_radar_key(path: Path) -> tuple[str, str] | None:
    name = path.stem.lower()
    for suffix in ("_radar_psd", "_radar_tga"):
        if name.endswith(suffix):
            map_name = name[:-len(suffix)]
            level = "lower" if map_name.endswith("_lower") else "upper"
            return (map_name[:-6] if level == "lower" else map_name), level
    return None


def _image_priority(path: Path) -> tuple[int, str]:
    name = path.stem.lower()
    return (0 if name.endswith("_radar_psd") else 1, name)


def build(cs2_root: Path | None, steam_root: Path | None, source2viewer: Path | None, output: Path, *, diagnostic: bool = False, limit: int | None = None) -> None:
    if limit is not None and limit <= 0: raise ValueError("--limit must be a positive integer.")
    if diagnostic and limit != 1: raise ValueError("--diagnostic requires --limit 1.")
    with BuildReporter(output) as reporter:
        reporter.report("Radar assets build starting."); reporter.report("Acquiring single-build lock.")
        with BuildLock(output):
            reporter.report("Detecting Counter-Strike 2 installation."); cs2 = find_cs2(cs2_root, steam_root)
            reporter.report("Resolving Source2Viewer."); tool = resolve_source2viewer(source2viewer)
            reporter.report("Creating temporary extraction directory.")
            with tempfile.TemporaryDirectory(prefix="clutchiq-radar-") as temporary_name:
                staging = Path(temporary_name); vpks = find_vpks(cs2)
                if limit is not None: vpks = itertools.islice(vpks, limit)
                for vpk in vpks:
                    reporter.report(f"Targeted extraction from {vpk.name} (timeout {EXTRACTION_TIMEOUT_SECONDS}s).")
                    extract_targeted(tool, vpk, staging, timeout=EXTRACTION_TIMEOUT_SECONDS, reporter=reporter.report)
                reporter.report("Scanning extracted overview metadata.")
                images: dict[tuple[str, str], list[Path]] = {}
                for image in staging.rglob("*.png"):
                    key = _decoded_radar_key(image)
                    if key is not None: images.setdefault(key, []).append(image)
                entries: dict[str, RadarManifestEntry] = {}
                for overview_file in staging.rglob("*.txt"):
                    if "overview" not in overview_file.as_posix().lower(): continue
                    reporter.report(f"Processing {overview_file.name}."); map_name, level_name = _map_name(overview_file)
                    candidates = images.get((map_name, level_name), ())
                    image = min(candidates, key=_image_priority, default=None)
                    if image is None: continue
                    overview = parse_overview(overview_file.read_text(encoding="utf-8", errors="replace")); destination_name = f"{map_name}_{level_name}.png"
                    width, height = install_png(image, output / destination_name); min_x, max_x, min_y, max_y = overview.bounds(width, height); level = RadarLevel(level_name, destination_name)
                    current = entries.get(map_name)
                    if current is None: entries[map_name] = RadarManifestEntry(destination_name, min_x, max_x, min_y, max_y, levels=(level,))
                    else: entries[map_name] = RadarManifestEntry(current.asset_name, current.min_x, current.max_x, current.max_y, current.max_y, levels=tuple(sorted((*current.levels, level), key=lambda item: item.name)))
                if not entries: raise RuntimeError("Source2Viewer produced no overview PNG/metadata pairs.")
                reporter.report("Writing radar manifest."); write_manifest(entries, output / "maps.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clutchiq-radar-assets"); parser.add_argument("command", choices=("detect", "build", "verify")); parser.add_argument("--steam-root", type=Path); parser.add_argument("--cs2-root", type=Path); parser.add_argument("--source2viewer", type=Path); parser.add_argument("--output", type=Path, default=Path("clutchiq/assets/radar")); parser.add_argument("--diagnostic", action="store_true"); parser.add_argument("--limit", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "detect": print(find_cs2(args.cs2_root, args.steam_root), flush=True)
        elif args.command == "verify":
            import json
            json.loads((args.output / "maps.json").read_text(encoding="utf-8")); print("Radar assets verified.", flush=True)
        else: build(args.cs2_root, args.steam_root, args.source2viewer, args.output, diagnostic=args.diagnostic, limit=args.limit); print("Radar assets generated.", flush=True)
    except (SteamDiscoveryError, Source2ViewerError, RuntimeError, ValueError) as error: parser.error(str(error))
    return 0

if __name__ == "__main__": raise SystemExit(main())
