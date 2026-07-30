"""Deterministic, defensive trade detection for timeline events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from clutchiq.timeline_engine.models import TimelineEvent, Trade
from clutchiq.timeline_engine.query import TradeQuery, TradeResult

_KILL_KIND = "kill.recorded"
_MEMBERSHIP_KIND = "player.round_team"
_KNOWN_TEAM_NUMBERS = frozenset((2, 3))


@dataclass(frozen=True, slots=True)
class _Kill:
    event: TimelineEvent
    attacker_id: int
    victim_id: int
    round_number: int
    attacker_team: int
    victim_team: int


def detect_trades(events: Iterable[TimelineEvent], query: TradeQuery) -> TradeResult:
    """Detect valid trades without trusting malformed timeline payloads.

    Membership is deliberately read only from ``player.round_team`` events, which
    are the timeline representation of ``DemoPlayerRoundTeam``.
    """
    membership: dict[tuple[int, int], int] = {}
    conflicts: set[tuple[int, int]] = set()
    seen_memberships: set[tuple[int, int, int]] = set()
    seen_kills: set[tuple[int, int, int, int]] = set()
    kills: list[_Kill] = []
    skipped_unknown = skipped_conflicting = skipped_duplicate = skipped_malformed = 0

    ordered = sorted(events, key=lambda event: (event.tick, event.sequence, event.event_id) if _valid_order(event) else (0, 0, ""))
    for event in ordered:
        if event.kind == _MEMBERSHIP_KIND:
            parsed = _membership(event)
            if parsed is None:
                skipped_malformed += 1
                continue
            key, team = parsed
            source_key = (*key, team)
            if source_key in seen_memberships:
                skipped_duplicate += 1
                continue
            seen_memberships.add(source_key)
            previous = membership.get(key)
            if previous is None:
                membership[key] = team
            elif previous != team:
                conflicts.add(key)
                skipped_conflicting += 1
            else:
                skipped_duplicate += 1

    for event in ordered:
        if event.kind != _KILL_KIND:
            continue
        parsed = _kill_identity(event)
        if parsed is None:
            skipped_malformed += 1
            continue
        round_number, attacker_id, victim_id = parsed
        duplicate_key = (round_number, event.tick, attacker_id, victim_id)
        if duplicate_key in seen_kills:
            skipped_duplicate += 1
            continue
        seen_kills.add(duplicate_key)
        attacker_key = (round_number, attacker_id)
        victim_key = (round_number, victim_id)
        if attacker_key in conflicts or victim_key in conflicts:
            skipped_conflicting += 1
            continue
        attacker_team = membership.get(attacker_key)
        victim_team = membership.get(victim_key)
        if attacker_team is None or victim_team is None:
            skipped_unknown += 1
            continue
        if attacker_team == victim_team:
            skipped_unknown += 1
            continue
        if query.round_numbers is not None and round_number not in query.round_numbers:
            continue
        kills.append(_Kill(event, attacker_id, victim_id, round_number, attacker_team, victim_team))

    pending: list[_Kill] = []
    trades: list[Trade] = []
    for kill in kills:
        match_index = _newest_match_index(pending, kill, query.config.window_ticks)
        if match_index is None:
            pending.append(kill)
            continue
        death = pending.pop(match_index)
        trades.append(
            Trade(
                death_event_id=death.event.event_id,
                retaliation_event_id=kill.event.event_id,
                round_number=death.round_number,
                original_killer_player_id=death.attacker_id,
                original_victim_player_id=death.victim_id,
                death_tick=death.event.tick,
                retaliation_tick=kill.event.tick,
            )
        )
    return TradeResult(tuple(trades), skipped_unknown, skipped_conflicting, skipped_duplicate, skipped_malformed)


def _newest_match_index(pending: list[_Kill], retaliation: _Kill, window_ticks: int) -> int | None:
    for index in range(len(pending) - 1, -1, -1):
        death = pending[index]
        elapsed = retaliation.event.tick - death.event.tick
        if elapsed < 0 or elapsed > window_ticks:
            continue
        if death.round_number != retaliation.round_number:
            continue
        if death.attacker_id != retaliation.victim_id or death.victim_id != retaliation.attacker_id:
            continue
        if death.attacker_team == retaliation.attacker_team or death.victim_team == retaliation.victim_team:
            continue
        return index
    return None


def _membership(event: TimelineEvent) -> tuple[tuple[int, int], int] | None:
    raw = event.raw
    player_id = raw.get("player_id")
    team_num = raw.get("team_num")
    round_number = event.round_number if event.round_number is not None else raw.get("round_number")
    if not _positive_int(player_id) or not _positive_int(round_number) or team_num not in _KNOWN_TEAM_NUMBERS:
        return None
    return (round_number, player_id), team_num


def _kill_identity(event: TimelineEvent) -> tuple[int, int, int] | None:
    if not _valid_order(event):
        return None
    raw = event.raw
    round_number = event.round_number if event.round_number is not None else raw.get("round_number")
    attacker_id = raw.get("attacker_player_id")
    victim_id = raw.get("victim_player_id")
    if not _positive_int(round_number) or not _positive_int(attacker_id) or not _positive_int(victim_id) or attacker_id == victim_id:
        return None
    return round_number, attacker_id, victim_id


def _valid_order(event: TimelineEvent) -> bool:
    return (
        isinstance(event.tick, int)
        and not isinstance(event.tick, bool)
        and isinstance(event.sequence, int)
        and not isinstance(event.sequence, bool)
        and isinstance(event.event_id, str)
    )


def _positive_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0
