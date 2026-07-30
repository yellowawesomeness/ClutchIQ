"""Configuration-driven CS2 radar map registry."""
from __future__ import annotations

from dataclasses import dataclass
import json
from importlib import resources
from typing import Any

from PySide6.QtGui import QPixmap


@dataclass(frozen=True, slots=True)
class RadarLevelSpec:
    name: str
    asset_name: str
    min_z: float | None = None
    max_z: float | None = None

    def contains(self, z: float) -> bool:
        return (self.min_z is None or z >= self.min_z) and (self.max_z is None or z < self.max_z)


@dataclass(frozen=True, slots=True)
class RadarMapSpec:
    map_name: str
    asset_name: str
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    invert_y: bool = True
    asset_svg: str | None = None
    levels: tuple[RadarLevelSpec, ...] = ()

    def normalized(self, x: float, y: float) -> tuple[float, float] | None:
        if self.max_x <= self.min_x or self.max_y <= self.min_y:
            return None
        nx = (x - self.min_x) / (self.max_x - self.min_x)
        ny = (y - self.min_y) / (self.max_y - self.min_y)
        if not 0.0 <= nx <= 1.0 or not 0.0 <= ny <= 1.0:
            return None
        return nx, 1.0 - ny if self.invert_y else ny

    def level_for_z(self, z: float | None) -> RadarLevelSpec | None:
        if z is None:
            return None
        return next((level for level in self.levels if level.contains(z)), None)


class RadarMapRegistry:
    def __init__(self, specs: dict[str, RadarMapSpec] | None = None) -> None:
        self._specs = specs if specs is not None else self._load_specs()

    def resolve(self, map_name: str | None) -> RadarMapSpec | None:
        return self._specs.get((map_name or "").strip().lower())

    def load_pixmap(self, spec: RadarMapSpec) -> QPixmap | None:
        pixmap = QPixmap()
        if spec.asset_svg:
            pixmap.loadFromData(spec.asset_svg.encode("utf-8"), "SVG")
        else:
            try:
                asset = resources.files("clutchiq").joinpath("assets", "radar", spec.asset_name)
                with resources.as_file(asset) as path:
                    pixmap = QPixmap(str(path))
            except (FileNotFoundError, ModuleNotFoundError, OSError):
                return None
        return pixmap if not pixmap.isNull() else None

    @staticmethod
    def _load_specs() -> dict[str, RadarMapSpec]:
        try:
            config = resources.files("clutchiq").joinpath("assets", "radar", "maps.json")
            raw: Any = json.loads(config.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return {}
            specs: dict[str, RadarMapSpec] = {}
            fields = {"asset_name", "min_x", "max_x", "min_y", "max_y", "invert_y", "asset_svg"}
            for name, values in raw.items():
                if not isinstance(name, str) or not isinstance(values, dict):
                    continue
                normalized_name = name.strip().lower()
                if not normalized_name:
                    continue
                raw_levels = values.get("levels", ())
                levels = tuple(RadarLevelSpec(**level) for level in raw_levels if isinstance(level, dict)) if isinstance(raw_levels, list) else ()
                specs[normalized_name] = RadarMapSpec(map_name=normalized_name, levels=levels, **{key: value for key, value in values.items() if key in fields})
            return specs
        except (FileNotFoundError, ModuleNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return {}


DEFAULT_RADAR_REGISTRY = RadarMapRegistry()
