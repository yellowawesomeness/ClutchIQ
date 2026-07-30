"""Source overview metadata parsing and world-coordinate conversion."""
from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class Overview:
    pos_x: float
    pos_y: float
    scale: float
    rotate: bool = False

    def bounds(self, width: int, height: int) -> tuple[float, float, float, float]:
        if width <= 0 or height <= 0 or self.scale <= 0:
            raise ValueError("overview scale and image dimensions must be positive")
        return (self.pos_x, self.pos_x + self.scale * width, self.pos_y - self.scale * height, self.pos_y)


def parse_overview(text: str) -> Overview:
    values: dict[str, str] = {}
    for key, value in re.findall(r'"?([A-Za-z_]+)"?\s+"?([^"\s{}]+)"?', text):
        values[key.lower()] = value
    try:
        return Overview(float(values["pos_x"]), float(values["pos_y"]), float(values["scale"]), values.get("rotate", "0") in {"1", "true"})
    except (KeyError, ValueError) as error:
        raise ValueError("overview metadata requires numeric pos_x, pos_y, and scale") from error
