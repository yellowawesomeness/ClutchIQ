"""Deterministic radar manifest generation."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import tempfile


@dataclass(frozen=True, slots=True)
class RadarLevel:
    name: str
    asset_name: str
    min_z: float | None = None
    max_z: float | None = None


@dataclass(frozen=True, slots=True)
class RadarManifestEntry:
    asset_name: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    invert_y: bool = True
    levels: tuple[RadarLevel, ...] = ()

    def validate(self) -> None:
        if not self.asset_name.endswith(".png") or Path(self.asset_name).name != self.asset_name:
            raise ValueError("asset_name must be a PNG filename")
        if self.max_x <= self.min_x or self.max_y <= self.min_y:
            raise ValueError("invalid radar coordinate bounds")


def write_manifest(entries: dict[str, RadarManifestEntry], destination: Path) -> None:
    payload: dict[str, dict[str, object]] = {}
    for name, entry in sorted(entries.items()):
        if not name or name != name.strip().lower():
            raise ValueError(f"invalid map name: {name!r}")
        entry.validate()
        value = asdict(entry)
        if not entry.levels:
            value.pop("levels")
        payload[name] = value
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False, dir=destination.parent, suffix=".tmp") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")
        temporary = Path(stream.name)
    temporary.replace(destination)
