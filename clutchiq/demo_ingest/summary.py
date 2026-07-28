"""Match summary helpers for demo ingestion."""

from __future__ import annotations

from dataclasses import dataclass

from clutchiq.demo_ingest.models import Cs2Demo


@dataclass(frozen=True, slots=True)
class MatchSummary:
    map_name: str | None
    demo_id: str | None
    rounds: int
    players: int
    kills: int
    winner_team: str | None


def build_match_summary(demo: Cs2Demo) -> MatchSummary:
    winner_team = demo.rounds[-1].winner_team if demo.rounds else None
    return MatchSummary(
        map_name=demo.header.map_name,
        demo_id=demo.header.demo_id,
        rounds=len(demo.rounds),
        players=len(demo.players),
        kills=len(demo.kills),
        winner_team=winner_team,
    )


def format_match_summary(summary: MatchSummary) -> str:
    parts = []
    if summary.map_name:
        parts.append(f"map={summary.map_name}")
    if summary.demo_id:
        parts.append(f"demo={summary.demo_id}")
    parts.append(f"rounds={summary.rounds}")
    parts.append(f"players={summary.players}")
    parts.append(f"kills={summary.kills}")
    if summary.winner_team:
        parts.append(f"winner={summary.winner_team}")
    return " ".join(parts)
