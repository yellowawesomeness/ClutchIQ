"""Steam and Counter-Strike 2 installation discovery."""
from __future__ import annotations

from pathlib import Path
import os
import re
import sys


class SteamDiscoveryError(FileNotFoundError):
    """Raised when Counter-Strike 2 cannot be located."""


def default_steam_roots() -> tuple[Path, ...]:
    if sys.platform == "win32":
        roots = [Path(os.environ.get("PROGRAMFILES(X86)", r"C:\\Program Files (x86)")) / "Steam"]
    elif sys.platform == "darwin":
        roots = [Path.home() / "Library/Application Support/Steam"]
    else:
        roots = [Path.home() / ".steam/steam", Path.home() / ".local/share/Steam"]
    return tuple(root for root in roots if root.exists())


def steam_libraries(steam_root: Path) -> tuple[Path, ...]:
    libraries = [steam_root]
    vdf = steam_root / "steamapps" / "libraryfolders.vdf"
    if vdf.is_file():
        text = vdf.read_text(encoding="utf-8", errors="replace")
        for value in re.findall(r'"path"\s+"([^"]+)"', text, flags=re.IGNORECASE):
            path = Path(value.replace("\\\\", "\\"))
            if path not in libraries:
                libraries.append(path)
    return tuple(libraries)


def find_cs2(cs2_root: Path | None = None, steam_root: Path | None = None) -> Path:
    if cs2_root is not None:
        root = Path(cs2_root)
        if (root / "game" / "csgo").is_dir():
            return root
        raise SteamDiscoveryError(f"CS2 root does not contain game/csgo: {root}")
    roots = (Path(steam_root),) if steam_root is not None else default_steam_roots()
    for root in roots:
        for library in steam_libraries(root):
            candidate = library / "steamapps" / "common" / "Counter-Strike Global Offensive"
            if (candidate / "game" / "csgo").is_dir():
                return candidate
    raise SteamDiscoveryError("Counter-Strike 2 was not found. Supply --cs2-root <path> or --steam-root <path>.")


def find_vpks(cs2_root: Path) -> tuple[Path, ...]:
    search_root = cs2_root / "game" / "csgo"
    vpks = tuple(sorted(search_root.rglob("*_dir.vpk")))
    if not vpks:
        raise SteamDiscoveryError(f"No CS2 VPKs found below {search_root}")
    return vpks
