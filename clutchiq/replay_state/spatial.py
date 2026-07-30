"""Spatial replay data built from demoparser2 tick parsing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd

SPATIAL_COLUMNS = (
    "tick",
    "steamid",
    "name",
    "team_name",
    "X",
    "Y",
    "Z",
    "yaw",
    "pitch",
    "is_alive",
)


@dataclass(frozen=True, slots=True)
class SpatialReplayData:
    frame: pd.DataFrame
    _tick_index: dict[int, slice]

    @classmethod
    def from_parse_ticks(cls, rows: pd.DataFrame) -> SpatialReplayData:
        frame = _normalize_frame(rows)
        tick_index = _build_tick_index(frame["tick"].to_numpy())
        return cls(frame=frame, _tick_index=tick_index)

    def rows_at_tick(self, tick: int) -> pd.DataFrame:
        tick_slice = self._tick_index.get(int(tick))
        if tick_slice is None:
            return self.frame.iloc[0:0].copy()
        return self.frame.iloc[tick_slice]


def _normalize_frame(rows: pd.DataFrame) -> pd.DataFrame:
    required = set(SPATIAL_COLUMNS)
    missing = required.difference(rows.columns)
    if missing:
        raise ValueError(f"parse_ticks output missing columns: {sorted(missing)!r}")

    frame = rows.loc[:, SPATIAL_COLUMNS].copy()
    frame["tick"] = pd.to_numeric(frame["tick"], downcast=None).astype("uint32")
    for column in ("X", "Y", "Z", "yaw", "pitch"):
        frame[column] = pd.to_numeric(frame[column], errors="raise").astype("float32")
    frame["is_alive"] = frame["is_alive"].astype(bool)
    for column in ("steamid", "name", "team_name"):
        frame[column] = frame[column].astype("category")
    frame = frame.sort_values(["tick", "steamid", "name"], kind="mergesort").reset_index(drop=True)
    return frame


def _build_tick_index(ticks: Iterable[int]) -> dict[int, slice]:
    tick_index: dict[int, slice] = {}
    start = 0
    tick_list = list(int(tick) for tick in ticks)
    if not tick_list:
        return tick_index
    current = tick_list[0]
    for idx, tick in enumerate(tick_list):
        if tick != current:
            tick_index[current] = slice(start, idx)
            current = tick
            start = idx
    tick_index[current] = slice(start, len(tick_list))
    return tick_index
