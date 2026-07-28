"""Domain models for demo ingestion."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from clutchiq.demo_ingest.errors import DemoReadError


@dataclass(frozen=True, slots=True)
class BinaryDemoSource:
    """File-backed binary demo source."""

    _path: Path

    @property
    def path(self) -> Path:
        """Return the demo file path."""
        return self._path

    @property
    def size_bytes(self) -> int:
        """Return the current file size in bytes."""
        try:
            return self._path.stat().st_size
        except OSError as exc:
            raise DemoReadError(
                f"Could not read file metadata for: {self._path}"
            ) from exc

    def read_bytes(self) -> bytes:
        """Eagerly load and return the complete demo file."""
        try:
            return self._path.read_bytes()
        except OSError as exc:
            raise DemoReadError(
                f"Could not read demo file: {self._path}"
            ) from exc


@dataclass(frozen=True, slots=True)
class DemoHeader:
    demo_id: str | None = None
    map_name: str | None = None
    server_name: str | None = None
    tick_rate: int | None = None
    client_name: str | None = None
    playback_time: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DemoPlayer:
    player_id: int
    name: str | None = None
    steam_id: int | None = None
    team: str | None = None
    side: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DemoRound:
    round_number: int
    winner_team: str | None = None
    start_tick: int | None = None
    end_tick: int | None = None
    score_ct: int | None = None
    score_t: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DemoKill:
    tick: int
    attacker_player_id: int | None = None
    victim_player_id: int | None = None
    assister_player_id: int | None = None
    weapon: str | None = None
    headshot: bool | None = None
    round_number: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DemoEvent:
    tick: int
    event_type: str
    round_number: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Cs2Demo:
    header: DemoHeader
    rounds: tuple[DemoRound, ...] = ()
    players: tuple[DemoPlayer, ...] = ()
    kills: tuple[DemoKill, ...] = ()
    events: tuple[DemoEvent, ...] = ()
    raw: dict[str, Any] = field(default_factory=dict)
