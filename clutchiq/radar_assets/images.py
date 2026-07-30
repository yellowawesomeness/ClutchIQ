"""Safe PNG validation and deterministic radar asset installation."""
from __future__ import annotations

from pathlib import Path
import shutil
import struct

_PNG = b"\x89PNG\r\n\x1a\n"


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as stream:
        header = stream.read(24)
    if len(header) != 24 or not header.startswith(_PNG) or header[12:16] != b"IHDR":
        raise ValueError(f"not a PNG image: {path}")
    width, height = struct.unpack(">II", header[16:24])
    if width <= 0 or height <= 0 or width > 16384 or height > 16384:
        raise ValueError(f"unsupported PNG dimensions: {path}")
    return width, height


def install_png(source: Path, destination: Path) -> tuple[int, int]:
    """Validate an extracted PNG and copy it under its normalized manifest name."""
    dimensions = png_dimensions(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, destination)
    return dimensions
