"""Adapters from demo ingestion models into timeline import payloads."""

from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from clutchiq.demo_ingest.models import Cs2Demo, DemoKill, DemoPlayerRoundTeam, DemoRound
from clutchiq.timeline_engine.models import Participant, TimelineEvent, TimelineImport, TimelineMetadata


_ROUND_WINNER_TEAM_NUMBERS = {"T": 2, "CT": 3}


def cs2demo_to_timeline_import(demo: Cs2Demo) -> TimelineImport:
    metadata = TimelineMetadata(schema_version=1, source_name="cs2-demo", map_name=demo.header.map_name, tick_rate=demo.header.tick_rate, raw=_copy_raw(demo.header.raw))
    participants = tuple(Participant(participant_id=player.player_id, name=player.name, steam_id=player.steam_id, team=player.team, side=player.side, raw=_copy_raw(player.raw)) for player in demo.players)

    emitted: list[tuple[int, TimelineEvent]] = []
    per_tick_order: dict[int, int] = {}
    synchronized_kills = tuple(_synchronize_kill_round(kill, demo.rounds) for kill in demo.kills)
    membership_ticks = _membership_ticks(demo.rounds)
    round_outcomes = tuple(round_ for round_ in demo.rounds if _round_outcome_tick(round_) is not None and _winner_team_num(round_.winner_team) is not None)
    sources: tuple[tuple[str, tuple[object, ...]], ...] = (
        ("round.recorded", demo.rounds),
        ("round.outcome", round_outcomes),
        ("player.round_team", demo.player_round_teams),
        ("kill.recorded", synchronized_kills),
        ("event.recorded", demo.events),
    )
    for kind, items in sources:
        for item in items:
            if kind == "round.recorded":
                tick = _round_recorded_tick(item)
                if tick is None:
                    continue
            elif kind == "round.outcome":
                tick = _round_outcome_tick(item)
                assert tick is not None
            else:
                tick = membership_ticks.get(item.round_number, 0) if isinstance(item, DemoPlayerRoundTeam) else _source_tick(item)
            sequence = per_tick_order.get(tick, 0)
            per_tick_order[tick] = sequence + 1
            if isinstance(item, DemoKill):
                raw = _kill_raw(item)
            elif isinstance(item, DemoPlayerRoundTeam):
                raw = _membership_raw(item)
            elif kind == "round.outcome":
                raw = _round_outcome_raw(item)
            else:
                raw = _copy_raw(item.raw)
            event = TimelineEvent(event_id=_event_id(kind, tick, sequence, raw), tick=tick, sequence=sequence, kind=kind, round_number=getattr(item, "round_number", None), participant_id=getattr(item, "attacker_player_id", None) or getattr(item, "player_id", None), raw=raw)
            emitted.append((tick, event))

    events = tuple(event for _, event in sorted(emitted, key=lambda item: (item[0], item[1].sequence, item[1].event_id)))
    return TimelineImport(metadata=metadata, participants=participants, events=events, raw={"header": _copy_raw(demo.header.raw)})


def _round_outcome_tick(round_: DemoRound) -> int | None:
    if round_.round_number <= 0 or not isinstance(round_.end_tick, int) or isinstance(round_.end_tick, bool):
        return None
    return round_.end_tick


def _round_recorded_tick(round_: DemoRound) -> int | None:
    """Use a round's start tick, falling back to its end tick when needed."""
    if isinstance(round_.start_tick, int) and not isinstance(round_.start_tick, bool):
        return round_.start_tick
    if isinstance(round_.end_tick, int) and not isinstance(round_.end_tick, bool):
        return round_.end_tick
    return None


def _winner_team_num(winner_team: str | None) -> int | None:
    return _ROUND_WINNER_TEAM_NUMBERS.get(winner_team) if isinstance(winner_team, str) else None


def _round_outcome_raw(round_: DemoRound) -> dict[str, object]:
    winner_team_num = _winner_team_num(round_.winner_team)
    assert winner_team_num is not None
    raw = _copy_raw(round_.raw)
    raw.update({"round_number": round_.round_number, "winner_team_num": winner_team_num})
    return raw


def _membership_ticks(rounds: tuple[DemoRound, ...]) -> dict[int, int]:
    return {round_.round_number: round_.start_tick for round_ in rounds if isinstance(round_.start_tick, int) and not isinstance(round_.start_tick, bool)}


def _synchronize_kill_round(kill: DemoKill, rounds: tuple[DemoRound, ...]) -> DemoKill:
    """Assign a round from its inclusive tick interval when the parser omitted it."""
    if kill.round_number is not None:
        return kill
    for round_ in rounds:
        if round_.start_tick is None or round_.end_tick is None:
            continue
        start_tick, end_tick = sorted((round_.start_tick, round_.end_tick))
        if start_tick <= kill.tick <= end_tick:
            return DemoKill(tick=kill.tick, attacker_player_id=kill.attacker_player_id, victim_player_id=kill.victim_player_id, assister_player_id=kill.assister_player_id, weapon=kill.weapon, headshot=kill.headshot, round_number=round_.round_number, raw=_copy_raw(kill.raw))
    return kill


def _kill_raw(kill: DemoKill) -> dict[str, object]:
    raw = _copy_raw(kill.raw)
    raw.update({"attacker_player_id": kill.attacker_player_id, "victim_player_id": kill.victim_player_id, "assister_player_id": kill.assister_player_id, "weapon": kill.weapon, "headshot": kill.headshot, "round_number": kill.round_number})
    return raw


def _membership_raw(membership: DemoPlayerRoundTeam) -> dict[str, object]:
    raw = _copy_raw(membership.raw)
    raw.update({"player_id": membership.player_id, "round_number": membership.round_number, "team_num": membership.team_num})
    return raw


def _copy_raw(value: dict[str, object]) -> dict[str, object]:
    return dict(value)


def _source_tick(item: object) -> int:
    tick = getattr(item, "start_tick", None)
    if tick is not None:
        return tick
    tick = getattr(item, "tick", None)
    if tick is not None:
        return tick
    raise AttributeError("timeline source object does not expose a tick field")


def _event_id(kind: str, tick: int, sequence: int, raw: dict[str, object]) -> str:
    payload = f"{kind}|{tick}|{sequence}|{sorted(raw.items())!r}"
    return uuid5(NAMESPACE_URL, payload).hex
