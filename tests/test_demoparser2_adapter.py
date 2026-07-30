from __future__ import annotations

import builtins
import sys
from pathlib import Path

import pytest

from clutchiq.demo_ingest.errors import DemoParseError
from clutchiq.demo_ingest.vendor import Demoparser2Adapter


class _FakeFrame:
    def __init__(self, rows: list[dict[str, object]]):
        self._rows = rows

    def to_dicts(self) -> list[dict[str, object]]:
        return self._rows


class _VendorParser:
    def __init__(self, path: str):
        self.path = path

    def parse_header(self) -> dict[str, object]:
        return {"map_name": "de_anubis", "server_name": "server-a", "client_name": "client-b"}

    def parse_player_info(self) -> _FakeFrame:
        return _FakeFrame([{"id": 3, "name": "carol", "steamid": 123, "team_name": "CT", "side": "ct"}])

    def parse_events(self, event_names: list[str], player=None, other=None):
        assert event_names in (
            ["round_start", "round_end", "round_freeze_end"],
            ["round_start", "round_end", "round_freeze_end", "player_death"],
        )
        return [
            ("round_start", _FakeFrame([{"tick": 2, "round": 1}])),
            ("round_end", _FakeFrame([{"tick": 4, "round": 1, "winner_team": "CT"}])),
            ("player_death", _FakeFrame([{"tick": 99, "round": 1}])),
        ]

    def parse_event(self, name: str, player=None, other=None) -> _FakeFrame:
        assert name == "player_death"
        assert player == ["team_num"]
        assert other == ["total_rounds_played"]
        return _FakeFrame([
            {"tick": 99, "event_type": "player_death", "attacker_steamid": 3,
             "user_steamid": 4, "assister_steamid": 5, "weapon": "ak47",
             "headshot": True, "total_rounds_played": 1,
             "attacker_team_num": 3, "user_team_num": 2}
        ])


class _ParserModule:
    DemoParser = _VendorParser


@pytest.fixture(autouse=True)
def clean_demoparser2() -> None:
    sys.modules.pop("demoparser2", None)


def test_adapter_normalizes_query_payload_and_round_scoped_team_columns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "demoparser2", _ParserModule())

    demo = Demoparser2Adapter().parse_bytes(b"demo-bytes")

    assert demo.header.map_name == "de_anubis"
    assert demo.players[0].name == "carol"
    assert demo.rounds[0].round_number == 1
    assert demo.rounds[0].winner_team == "CT"
    assert demo.rounds[0].end_tick == 4
    assert demo.kills[0].round_number == 1
    assert demo.kills[0].attacker_player_id == 3
    assert demo.kills[0].victim_player_id == 4
    assert [(item.player_id, item.round_number, item.team_num) for item in demo.player_round_teams] == [
        (3, 1, 3), (4, 1, 2)
    ]


def test_adapter_uses_winner_fallback_when_winner_team_is_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    class WinnerFallbackParser(_VendorParser):
        def parse_events(self, event_names: list[str], player=None, other=None):
            return [
                ("round_start", _FakeFrame([{"tick": 2, "round": 1}])),
                ("round_end", _FakeFrame([{"tick": 4, "round": 1, "winner": "T"}])),
                ("player_death", _FakeFrame([{"tick": 99, "round": 1}])),
            ]

    class WinnerFallbackModule:
        DemoParser = WinnerFallbackParser

    monkeypatch.setitem(sys.modules, "demoparser2", WinnerFallbackModule())

    demo = Demoparser2Adapter().parse_bytes(b"demo-bytes")

    assert demo.rounds[0].winner_team == "T"
    assert demo.rounds[0].end_tick == 4


def test_adapter_prefers_winner_team_over_winner(monkeypatch: pytest.MonkeyPatch) -> None:
    class BothWinnersParser(_VendorParser):
        def parse_events(self, event_names: list[str], player=None, other=None):
            return [
                ("round_start", _FakeFrame([{"tick": 2, "round": 1}])),
                ("round_end", _FakeFrame([{"tick": 4, "round": 1, "winner_team": "CT", "winner": "T"}])),
                ("player_death", _FakeFrame([{"tick": 99, "round": 1}])),
            ]

    class BothWinnersModule:
        DemoParser = BothWinnersParser

    monkeypatch.setitem(sys.modules, "demoparser2", BothWinnersModule())

    demo = Demoparser2Adapter().parse_bytes(b"demo-bytes")

    assert demo.rounds[0].winner_team == "CT"


def test_adapter_does_not_fall_back_to_static_player_team(monkeypatch: pytest.MonkeyPatch) -> None:
    class MissingTeamColumnsParser(_VendorParser):
        def parse_event(self, name: str, player=None, other=None) -> _FakeFrame:
            return _FakeFrame([
                {"tick": 99, "event_type": "player_death", "attacker_steamid": 3,
                 "user_steamid": 4, "total_rounds_played": 1}
            ])

    class MissingTeamColumnsModule:
        DemoParser = MissingTeamColumnsParser

    monkeypatch.setitem(sys.modules, "demoparser2", MissingTeamColumnsModule())
    demo = Demoparser2Adapter().parse_bytes(b"demo-bytes")

    assert demo.players[0].team == "CT"
    assert demo.player_round_teams == ()


def test_adapter_rejects_conflicting_round_team_values() -> None:
    adapter = Demoparser2Adapter()
    from clutchiq.demo_ingest.models import DemoKill

    kills = [
        DemoKill(tick=1, attacker_player_id=3, round_number=1, raw={"attacker_team_num": 2}),
        DemoKill(tick=2, attacker_player_id=3, round_number=1, raw={"attacker_team_num": 3}),
    ]

    with pytest.raises(DemoParseError, match="Conflicting team_num"):
        adapter._parse_player_round_teams(kills)


def test_adapter_rejects_unknown_vendor_api(monkeypatch: pytest.MonkeyPatch) -> None:
    class UnsupportedModule:
        pass

    monkeypatch.setitem(sys.modules, "demoparser2", UnsupportedModule())
    with pytest.raises(DemoParseError, match="Unsupported demoparser2 API"):
        Demoparser2Adapter().parse_bytes(b"demo-bytes")


def test_adapter_raises_when_dependency_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "demoparser2":
            raise ImportError("No module named demoparser2")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(DemoParseError, match="demoparser2 is required"):
        Demoparser2Adapter().parse_bytes(b"demo-bytes")


def test_adapter_cleans_temp_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    created: list[Path] = []

    class DummyTempFile:
        def __init__(self, suffix: str, delete: bool):
            self.name = str(tmp_path / "temp.dem")
            self._path = Path(self.name)
            created.append(self._path)

        def __enter__(self):
            self._path.write_bytes(b"x")
            return self

        def write(self, data: bytes) -> None:
            self._path.write_bytes(data)

        def flush(self) -> None:
            return None

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("clutchiq.demo_ingest.vendor.demoparser2_adapter.tempfile.NamedTemporaryFile", DummyTempFile)
    monkeypatch.setitem(sys.modules, "demoparser2", _ParserModule())
    Demoparser2Adapter().parse_bytes(b"demo-bytes")
    assert created and not created[0].exists()
