"""Immutable analysis domain models for ClutchIQ."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WinningSide(str, Enum):
    """Winning side classification for matches and rounds."""

    CT = "CT"
    T = "T"
    TIE = "TIE"


@dataclass(frozen=True, slots=True)
class FinalScore:
    ct_rounds: int
    t_rounds: int


@dataclass(frozen=True, slots=True)
class OpeningKill:
    round_number: int | None
    tick: int
    attacker_player_id: int | None
    victim_player_id: int | None
    headshot: bool | None
    weapon: str | None


@dataclass(frozen=True, slots=True)
class MultiKillRecord:
    player_id: int
    kill_count: int


@dataclass(frozen=True, slots=True)
class RoundMetrics:
    round_number: int | None
    winner: WinningSide
    opening_kill: OpeningKill | None
    multi_kills: tuple[MultiKillRecord, ...]


@dataclass(frozen=True, slots=True)
class PlayerMetrics:
    player_id: int
    name: str | None
    steam_id: int | None
    team: str | None
    side: str | None
    kills: int
    deaths: int
    assists: int
    k_d: float
    headshot_percentage: float
    entry_kills: int
    entry_deaths: int
    survival_rate: float


@dataclass(frozen=True, slots=True)
class MatchMetrics:
    total_rounds: int
    final_score: FinalScore
    winning_side: WinningSide
    rounds_with_known_winner: int


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    match: MatchMetrics
    players: tuple[PlayerMetrics, ...]
    rounds: tuple[RoundMetrics, ...]
