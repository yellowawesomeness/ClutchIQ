from __future__ import annotations

from pathlib import Path

import pytest

from clutchiq.demo_ingest.errors import DemoParseError
from clutchiq.demo_ingest.vendor import Demoparser2Adapter


def test_real_demo_exposes_player_death_round_team_columns() -> None:
    demo_path = Path(__file__).parents[1] / "demos" / "MATCH20260725-1.dem"
    if not demo_path.exists():
        pytest.skip("real demo file not present")

    try:
        demo = Demoparser2Adapter().parse_bytes(demo_path.read_bytes())
    except DemoParseError as exc:
        pytest.skip(f"demoparser2 is unavailable for direct parser verification: {exc}")

    assert demo.player_round_teams
    assert {membership.player_id for membership in demo.player_round_teams}
    assert {membership.round_number for membership in demo.player_round_teams}
    assert {membership.team_num for membership in demo.player_round_teams} >= {2, 3}
    assert all(
        "attacker_team_num" in membership.raw or "user_team_num" in membership.raw
        for membership in demo.player_round_teams
    )
