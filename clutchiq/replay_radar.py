"""Configuration-driven CS2 radar map registry."""
from __future__ import annotations

from dataclasses import dataclass
import json
from importlib import resources
from typing import Any

from PySide6.QtGui import QPixmap


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

    def normalized(self, x: float, y: float) -> tuple[float, float] | None:
        if self.max_x <= self.min_x or self.max_y <= self.min_y:
            return None
        nx = (x - self.min_x) / (self.max_x - self.min_x)
        ny = (y - self.min_y) / (self.max_y - self.min_y)
        if not 0.0 <= nx <= 1.0 or not 0.0 <= ny <= 1.0:
            return None
        return nx, 1.0 - ny if self.invert_y else ny


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
            for name, values in raw.items():
                if not isinstance(name, str) or not isinstance(values, dict):
                    continue
                normalized_name = name.strip().lower()
                if not normalized_name:
                    continue
                specs[normalized_name] = RadarMapSpec(map_name=normalized_name, **values)
            return specs
        except (FileNotFoundError, ModuleNotFoundError, OSError, TypeError, ValueError, json.JSONDecodeError):
            return {}


DEFAULT_RADAR_REGISTRY = RadarMapRegistry()
