from __future__ import annotations

import builtins
import sys

import pytest

from clutchiq.demo_ingest import Cs2Demo, Cs2DemoParser, DemoParseError


class _FakeFrame:
    def __init__(self, rows: list[dict[str, object]]):
        self._rows = rows

    def to_dicts(self) -> list[dict[str, object]]:
        return self._rows


class _VendorParser:
    def __init__(self, path: str):
        self.path = path

    def parse_header(self) -> dict[str, object]:
        return {"map_name": "de_dust2", "server_name": "ClutchIQ Test Server", "client_name": "clutchiq"}

    def parse_player_info(self) -> _FakeFrame:
        return _FakeFrame([{"id": 1, "name": "alice", "team": "T"}, {"id": 2, "name": "bob", "team": "CT"}])

    def parse_events(self, event_names: list[str], player=None, other=None):
        assert event_names in (["round_start", "round_end", "round_freeze_end"], ["round_start", "round_end", "round_freeze_end", "player_death"])
        return [("round_start", _FakeFrame([{"tick": 1, "round": 1}])), ("round_end", _FakeFrame([{"tick": 120, "round": 1, "winner_team": "T"}]))]

    def parse_event(self, name: str, player=None, other=None) -> _FakeFrame:
        assert name == "player_death"
        return _FakeFrame([{"tick": 42, "event_type": "player_death", "attacker_player_id": 1, "victim_player_id": 2, "weapon": "ak47", "headshot": True, "round": 1}])


class _ParserModule:
    DemoParser = _VendorParser


def test_parser_converts_vendor_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "demoparser2", _ParserModule())
    result = Cs2DemoParser().parse(b"demo-bytes")
    assert isinstance(result, Cs2Demo)
    assert result.header.map_name == "de_dust2"
    assert [r.round_number for r in result.rounds] == [1]
    assert [p.name for p in result.players] == ["alice", "bob"]
    assert result.kills[0].weapon == "ak47"
    assert [e.event_type for e in result.events] == ["round_start", "round_end"]


def test_parser_raises_when_dependency_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "demoparser2":
            raise ImportError("No module named demoparser2")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(DemoParseError, match="demoparser2 is required"):
        Cs2DemoParser().parse(b"demo-bytes")


def test_parser_rejects_unsupported_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    class UnsupportedParser:
        def __init__(self, path: str):
            self.path = path

    class UnsupportedModule:
        DemoParser = UnsupportedParser

    monkeypatch.setitem(sys.modules, "demoparser2", UnsupportedModule())
    with pytest.raises(DemoParseError, match="Unsupported demoparser2 API: parse_header not available"):
        Cs2DemoParser().parse(b"demo-bytes")
