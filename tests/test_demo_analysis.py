from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from clutchiq.demo_analysis import AnalysisEngine
from clutchiq.demo_ingest import Cs2Demo, DemoHeader, DemoKill, DemoPlayer, DemoRound


@pytest.fixture()
def engine() -> AnalysisEngine:
    return AnalysisEngine()


def _demo(
    *,
    players: tuple[DemoPlayer, ...] = (),
    rounds: tuple[DemoRound, ...] = (),
    kills: tuple[DemoKill, ...] = (),
):
    return Cs2Demo(
        header=DemoHeader(),
        players=players,
        rounds=rounds,
        kills=kills,
    )


def test_analysis_entry_kills_entry_deaths_and_survival_rate(engine: AnalysisEngine) -> None:
    demo = _demo(
        players=(DemoPlayer(player_id=1, name="alpha"), DemoPlayer(player_id=2, name="bravo")),
        rounds=(
            DemoRound(round_number=1, winner_team="CT"),
            DemoRound(round_number=2, winner_team="T"),
            DemoRound(round_number=3, winner_team="CT"),
        ),
        kills=(
            DemoKill(tick=10, attacker_player_id=1, victim_player_id=2, round_number=1),
            DemoKill(tick=20, attacker_player_id=2, victim_player_id=1, round_number=2),
            DemoKill(tick=30, attacker_player_id=1, victim_player_id=2, round_number=2),
        ),
    )

    result = engine.analyze(demo)
    alpha, bravo = result.players

    assert alpha.entry_kills == 1
    assert alpha.entry_deaths == 1
    assert alpha.survival_rate == pytest.approx(2 / 3)
    assert bravo.entry_kills == 1
    assert bravo.entry_deaths == 1
    assert bravo.survival_rate == pytest.approx(1 / 3)


def test_analysis_opening_kill_uses_tick_then_input_order(engine: AnalysisEngine) -> None:
    demo = _demo(
        rounds=(DemoRound(round_number=1, winner_team="CT"),),
        kills=(
            DemoKill(tick=100, attacker_player_id=2, victim_player_id=3, round_number=1),
            DemoKill(tick=100, attacker_player_id=1, victim_player_id=4, round_number=1),
        ),
    )

    result = engine.analyze(demo)

    assert result.rounds[0].opening_kill is not None
    assert result.rounds[0].opening_kill.attacker_player_id == 2


def test_analysis_multi_kill_records_preserve_2k_3k_4k_ace_detail(engine: AnalysisEngine) -> None:
    demo = _demo(
        rounds=(DemoRound(round_number=1, winner_team="CT"),),
        kills=(
            DemoKill(tick=1, attacker_player_id=10, victim_player_id=1, round_number=1),
            DemoKill(tick=2, attacker_player_id=10, victim_player_id=2, round_number=1),
            DemoKill(tick=3, attacker_player_id=10, victim_player_id=3, round_number=1),
            DemoKill(tick=4, attacker_player_id=10, victim_player_id=4, round_number=1),
            DemoKill(tick=5, attacker_player_id=11, victim_player_id=5, round_number=1),
            DemoKill(tick=6, attacker_player_id=11, victim_player_id=6, round_number=1),
        ),
    )

    result = engine.analyze(demo)

    assert result.rounds[0].multi_kills == (
        result.rounds[0].multi_kills[0].__class__(player_id=10, kill_count=4),
        result.rounds[0].multi_kills[1].__class__(player_id=11, kill_count=2),
    )


def test_analysis_ignores_missing_round_number_for_round_buckets_but_counts_global_stats(engine: AnalysisEngine) -> None:
    demo = _demo(
        players=(DemoPlayer(player_id=1, name="alpha"), DemoPlayer(player_id=2, name="bravo")),
        rounds=(DemoRound(round_number=1, winner_team="CT"),),
        kills=(
            DemoKill(tick=1, attacker_player_id=1, victim_player_id=2, round_number=None),
            DemoKill(tick=2, attacker_player_id=1, victim_player_id=2, round_number=1),
        ),
    )

    result = engine.analyze(demo)

    alpha, bravo = result.players
    assert alpha.kills == 2
    assert bravo.deaths == 2
    assert result.rounds[0].opening_kill.tick == 2
    assert alpha.entry_kills == 1
    assert alpha.survival_rate == pytest.approx(1.0)


def test_analysis_missing_attacker_counts_death_only(engine: AnalysisEngine) -> None:
    demo = _demo(
        players=(DemoPlayer(player_id=1, name="alpha"),),
        rounds=(DemoRound(round_number=1, winner_team="CT"),),
        kills=(DemoKill(tick=1, attacker_player_id=None, victim_player_id=1, round_number=1),),
    )

    result = engine.analyze(demo)
    player = result.players[0]

    assert player.kills == 0
    assert player.deaths == 1


def test_analysis_missing_victim_counts_kill_only(engine: AnalysisEngine) -> None:
    demo = _demo(
        players=(DemoPlayer(player_id=1, name="alpha"),),
        rounds=(DemoRound(round_number=1, winner_team="CT"),),
        kills=(DemoKill(tick=1, attacker_player_id=1, victim_player_id=None, round_number=1),),
    )

    result = engine.analyze(demo)
    player = result.players[0]

    assert player.kills == 1
    assert player.deaths == 0


def test_analysis_team_kills_and_suicides_are_counted_normally(engine: AnalysisEngine) -> None:
    demo = _demo(
        players=(DemoPlayer(player_id=1, name="alpha"), DemoPlayer(player_id=2, name="bravo")),
        rounds=(DemoRound(round_number=1, winner_team="CT"),),
        kills=(
            DemoKill(tick=1, attacker_player_id=1, victim_player_id=1, round_number=1),
            DemoKill(tick=2, attacker_player_id=1, victim_player_id=2, round_number=1),
        ),
    )

    result = engine.analyze(demo)
    alpha, bravo = result.players

    assert alpha.kills == 2
    assert alpha.deaths == 1
    assert bravo.deaths == 1


def test_analysis_output_is_immutable(engine: AnalysisEngine) -> None:
    demo = _demo(
        players=(DemoPlayer(player_id=1, name="alpha"),),
        rounds=(DemoRound(round_number=1, winner_team="CT"),),
        kills=(DemoKill(tick=1, attacker_player_id=1, victim_player_id=2, round_number=1),),
    )

    result = engine.analyze(demo)

    with pytest.raises(FrozenInstanceError):
        result.match.total_rounds = 2  # type: ignore[misc]
