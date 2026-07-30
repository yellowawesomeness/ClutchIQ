from __future__ import annotations

import pytest

from clutchiq.timeline_engine import ClutchDetectionConfig, ClutchQuery, InMemoryTimelineRepository, TimelineEngine, TimelineEvent, TimelineImport, TimelineMetadata


def _membership(event_id: str, player: object, team: object, round_number: object = 1) -> TimelineEvent:
    return TimelineEvent(event_id, 0, 0, "player.round_team", round_number if isinstance(round_number, int) else None, raw={"player_id": player, "team_num": team, "round_number": round_number})


def _kill(event_id: str, tick: object, sequence: object, attacker: object, victim: object, round_number: object = 1) -> TimelineEvent:
    return TimelineEvent(event_id, tick, sequence, "kill.recorded", round_number if isinstance(round_number, int) else None, raw={"attacker_player_id": attacker, "victim_player_id": victim, "round_number": round_number})


def _outcome(event_id: str, tick: object, sequence: object, winner: object, round_number: object = 1) -> TimelineEvent:
    return TimelineEvent(event_id, tick, sequence, "round.outcome", round_number if isinstance(round_number, int) else None, raw={"winner_team_num": winner, "round_number": round_number})


def _result(events: tuple[TimelineEvent, ...]):
    engine = TimelineEngine(InMemoryTimelineRepository())
    timeline_id = engine.import_timeline(TimelineImport(TimelineMetadata(), events=events))
    return engine.detect_clutches(ClutchQuery(timeline_id))


def _teams() -> tuple[TimelineEvent, ...]:
    return (_membership("m1", 1, 2), _membership("m2", 2, 2), _membership("m3", 3, 3), _membership("m4", 4, 3), _membership("m5", 5, 3))


def test_detects_successful_one_vs_n_clutch() -> None:
    result = _result(_teams() + (_kill("entry", 10, 0, 3, 2), _outcome("win", 20, 0, 2)))
    assert [(clutch.survivor_player_id, clutch.survivor_team, clutch.opponents_at_start, clutch.start_event_id, clutch.outcome_event_id) for clutch in result.clutches] == [(1, 2, 3, "entry", "win")]


def test_requires_matching_winner_and_survivor_alive_at_outcome() -> None:
    losing = _result(_teams() + (_kill("entry", 10, 0, 3, 2), _outcome("loss", 20, 0, 3)))
    dead = _result(_teams() + (_kill("entry", 10, 0, 3, 2), _kill("death", 15, 0, 3, 1), _outcome("win", 20, 0, 2)))
    assert not losing.clutches
    assert not dead.clutches


def test_skips_invalid_alive_transitions_without_mutating_alive_state() -> None:
    events = _teams() + (_kill("entry", 10, 0, 3, 2), _kill("repeat-death", 11, 0, 3, 2), _kill("dead-attacker", 12, 0, 2, 4), _outcome("win", 20, 0, 2))
    result = _result(events)
    assert len(result.clutches) == 1
    assert result.skipped_unknown == 2


def test_orders_events_and_rejects_conflicting_outcomes() -> None:
    ordered = _result(_teams() + (_outcome("win", 20, 0, 2), _kill("entry", 10, 0, 3, 2)))
    conflict = _result(_teams() + (_kill("entry", 10, 0, 3, 2), _outcome("win", 20, 0, 2), _outcome("conflict", 21, 0, 3)))
    assert len(ordered.clutches) == 1
    assert not conflict.clutches
    assert conflict.skipped_conflicting == 1


def test_skips_malformed_duplicate_and_conflicting_sources_and_filters_rounds() -> None:
    events = _teams() + (_membership("duplicate", 1, 2), _membership("conflict", 3, 2), _kill("bad", 5, 0, "x", 2), _kill("entry", 10, 0, 3, 2), _outcome("bad-outcome", 15, 0, "T"), _outcome("win", 20, 0, 2))
    engine = TimelineEngine(InMemoryTimelineRepository())
    timeline_id = engine.import_timeline(TimelineImport(TimelineMetadata(), events=events))
    result = engine.detect_clutches(ClutchQuery(timeline_id, round_numbers=(2,)))
    assert not result.clutches
    assert result.skipped_duplicate >= 1
    assert result.skipped_conflicting >= 1
    assert result.skipped_malformed >= 2


def test_config_rejects_invalid_minimum_opponents() -> None:
    with pytest.raises(ValueError, match="positive"):
        ClutchDetectionConfig(0)
