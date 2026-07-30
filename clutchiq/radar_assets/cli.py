"""Command line interface for user-owned CS2 radar generation."""
from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import tempfile

from .images import install_png
from .manifest import RadarLevel, RadarManifestEntry, write_manifest
from .overview import parse_overview
from .source2viewer import Source2ViewerError, extract, resolve_source2viewer
from .steam import SteamDiscoveryError, find_cs2, find_vpks


def _map_name(path: Path) -> tuple[str, str]:
    name = path.stem.lower()
    for suffix in ("_radar", "_overview"):
        if name.endswith(suffix):
            name = name[: -len(suffix)]
    level = "lower" if name.endswith("_lower") else "upper"
    if level == "lower":
        name = name[:-6]
    return name, level


def build(cs2_root: Path | None, steam_root: Path | None, source2viewer: Path | None, output: Path) -> None:
    cs2 = find_cs2(cs2_root, steam_root)
    tool = resolve_source2viewer(source2viewer)
    with tempfile.TemporaryDirectory(prefix="clutchiq-radar-") as temporary_name:
        staging = Path(temporary_name)
        for vpk in find_vpks(cs2):
            extract(tool, vpk, staging)
        entries: dict[str, RadarManifestEntry] = {}
        for overview_file in staging.rglob("*.txt"):
            if "overview" not in overview_file.as_posix().lower():
                continue
            map_name, level_name = _map_name(overview_file)
            image = next((candidate for candidate in overview_file.parent.glob(overview_file.stem + "*.png")), None)
            if image is None:
                continue
            overview = parse_overview(overview_file.read_text(encoding="utf-8", errors="replace"))
            destination_name = f"{map_name}_{level_name}.png"
            width, height = install_png(image, output / destination_name)
            min_x, max_x, min_y, max_y = overview.bounds(width, height)
            level = RadarLevel(level_name, destination_name)
            current = entries.get(map_name)
            if current is None:
                entries[map_name] = RadarManifestEntry(destination_name, min_x, max_x, min_y, max_y, levels=(level,))
            else:
                entries[map_name] = RadarManifestEntry(current.asset_name, current.min_x, current.max_x, current.min_y, current.max_y, levels=tuple(sorted((*current.levels, level), key=lambda item: item.name)))
        if not entries:
            raise RuntimeError("Source2Viewer produced no overview PNG/metadata pairs.")
        write_manifest(entries, output / "maps.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="clutchiq-radar-assets")
    parser.add_argument("command", choices=("detect", "build", "verify"))
    parser.add_argument("--steam-root", type=Path)
    parser.add_argument("--cs2-root", type=Path)
    parser.add_argument("--source2viewer", type=Path)
    parser.add_argument("--output", type=Path, default=Path("clutchiq/assets/radar"))
    args = parser.parse_args(argv)
    try:
        if args.command == "detect":
            print(find_cs2(args.cs2_root, args.steam_root))
        elif args.command == "verify":
            import json
            json.loads((args.output / "maps.json").read_text(encoding="utf-8"))
            print("Radar assets verified.")
        else:
            build(args.cs2_root, args.steam_root, args.source2viewer, args.output)
            print("Radar assets generated.")
    except (SteamDiscoveryError, Source2ViewerError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
