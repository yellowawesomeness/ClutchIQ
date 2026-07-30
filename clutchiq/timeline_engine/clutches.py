"""Deterministic, defensive clutch detection for timeline events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from clutchiq.timeline_engine.models import Clutch, TimelineEvent
from clutchiq.timeline_engine.query import ClutchQuery, ClutchResult

_KILL_KIND = "kill.recorded"
_MEMBERSHIP_KIND = "player.round_team"
_OUTCOME_KIND = "round.outcome"
_KNOWN_TEAM_NUMBERS = frozenset((2, 3))


@dataclass(frozen=True, slots=True)
class _Candidate:
    round_number: int
    survivor_player_id: int
    survivor_team: int
    opponents_at_start: int
    start_event_id: str
    start_tick: int


def detect_clutches(events: Iterable[TimelineEvent], query: ClutchQuery) -> ClutchResult:
    """Detect successful clutches from membership, kill, and outcome timeline events only."""
    membership: dict[tuple[int, int], int] = {}
    membership_conflicts: set[tuple[int, int]] = set()
    seen_memberships: set[tuple[int, int, int]] = set()
    seen_kills: set[tuple[int, int, int, int]] = set()
    outcomes: dict[int, TimelineEvent] = {}
    outcome_winners: dict[int, int] = {}
    outcome_alive: dict[int, frozenset[int]] = {}
    outcome_conflicts: set[int] = set()
    alive: dict[int, set[int]] = {}
    candidates: dict[tuple[int, int], _Candidate] = {}
    skipped_unknown = skipped_conflicting = skipped_duplicate = skipped_malformed = 0

    ordered = sorted(events, key=lambda event: (event.tick, event.sequence, event.event_id) if _valid_order(event) else (0, 0, ""))
    for event in ordered:
        if event.kind != _MEMBERSHIP_KIND:
            continue
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
            membership_conflicts.add(key)
            skipped_conflicting += 1
        else:
            skipped_duplicate += 1

    for (round_number, player_id), team in membership.items():
        if (round_number, player_id) not in membership_conflicts:
            alive.setdefault(round_number, set()).add(player_id)

    for event in ordered:
        if event.kind == _KILL_KIND:
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
            if attacker_key in membership_conflicts or victim_key in membership_conflicts:
                skipped_conflicting += 1
                continue
            attacker_team = membership.get(attacker_key)
            victim_team = membership.get(victim_key)
            round_alive = alive.get(round_number)
            if attacker_team is None or victim_team is None or round_alive is None or attacker_team == victim_team:
                skipped_unknown += 1
                continue
            if attacker_id not in round_alive or victim_id not in round_alive:
                skipped_unknown += 1
                continue
            round_alive.remove(victim_id)
            if query.round_numbers is not None and round_number not in query.round_numbers:
                continue
            team_alive = [player_id for player_id in round_alive if membership[(round_number, player_id)] == victim_team]
            opponents_alive = sum(1 for player_id in round_alive if membership[(round_number, player_id)] == attacker_team)
            if len(team_alive) == 1 and opponents_alive >= query.config.minimum_opponents:
                survivor_id = team_alive[0]
                candidates.setdefault(
                    (round_number, victim_team),
                    _Candidate(round_number, survivor_id, victim_team, opponents_alive, event.event_id, event.tick),
                )
        elif event.kind == _OUTCOME_KIND:
            parsed = _outcome(event)
            if parsed is None:
                skipped_malformed += 1
                continue
            round_number, winner_team = parsed
            previous = outcome_winners.get(round_number)
            if previous is None:
                outcome_winners[round_number] = winner_team
                outcomes[round_number] = event
                outcome_alive[round_number] = frozenset(alive.get(round_number, set()))
            elif previous != winner_team:
                outcome_conflicts.add(round_number)
                skipped_conflicting += 1
            else:
                skipped_duplicate += 1

    clutches: list[Clutch] = []
    for candidate in candidates.values():
        outcome = outcomes.get(candidate.round_number)
        if outcome is None or candidate.round_number in outcome_conflicts:
            continue
        if outcome_winners[candidate.round_number] != candidate.survivor_team or outcome.tick < candidate.start_tick:
            continue
        if candidate.survivor_player_id not in outcome_alive[candidate.round_number]:
            continue
        clutches.append(Clutch(candidate.round_number, candidate.survivor_player_id, candidate.survivor_team, candidate.opponents_at_start, candidate.start_event_id, candidate.start_tick, outcome.event_id, outcome.tick))
    clutches.sort(key=lambda clutch: (clutch.start_tick, clutch.round_number, clutch.survivor_player_id))
    return ClutchResult(tuple(clutches), skipped_unknown, skipped_conflicting, skipped_duplicate, skipped_malformed)


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


def _outcome(event: TimelineEvent) -> tuple[int, int] | None:
    if not _valid_order(event):
        return None
    round_number = event.round_number if event.round_number is not None else event.raw.get("round_number")
    winner_team = event.raw.get("winner_team_num")
    if not _positive_int(round_number) or winner_team not in _KNOWN_TEAM_NUMBERS:
        return None
    return round_number, winner_team


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
