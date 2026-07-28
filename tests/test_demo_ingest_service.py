from __future__ import annotations

from pathlib import Path
import sys

import pytest

from clutchiq.demo_ingest import (
    BinaryDemoSource,
    Cs2DemoParser,
    DemoIngestService,
    DemoParseError,
    DemoReadError,
)


class FakeSource:
    def __init__(self, path: Path, payload: bytes | Exception):
        self._path = path
        self._payload = payload

    @property
    def path(self) -> Path:
        return self._path

    @property
    def size_bytes(self) -> int:
        return 0 if isinstance(self._payload, Exception) else len(self._payload)

    def read_bytes(self) -> bytes:
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


class EchoParser:
    def parse(self, data: bytes) -> bytes:
        return data


class DomainParseFailureParser:
    def parse(self, data: bytes) -> bytes:
        raise DemoParseError("invalid demo content")


class BuggyParser:
    def parse(self, data: bytes) -> bytes:
        raise ValueError("unexpected bug")


class _FakeFrame:
    def __init__(self, rows: list[dict[str, object]]):
        self._rows = rows

    def to_dicts(self) -> list[dict[str, object]]:
        return self._rows


class _VendorParser:
    def __init__(self, path: str):
        self.path = path

    def parse_header(self) -> dict[str, object]:
        return {"map_name": "de_dust2"}

    def parse_player_info(self) -> _FakeFrame:
        return _FakeFrame([{"id": 1, "name": "alice"}])

    def parse_events(self, event_names: list[str], player=None, other=None):
        return [("round_start", _FakeFrame([{"tick": 1, "round": 1}]))]

    def parse_event(self, name: str, player=None, other=None) -> _FakeFrame:
        return _FakeFrame([])


class _ParserModule:
    DemoParser = _VendorParser


@pytest.fixture(autouse=True)
def clean_demoparser2() -> None:
    sys.modules.pop("demoparser2", None)


def test_ingest_returns_parsed_payload(tmp_path: Path) -> None:
    service = DemoIngestService(parser=EchoParser())
    source = FakeSource(tmp_path / "demo.bin", b"abc")

    assert service.ingest(source) == b"abc"


def test_ingest_path_returns_parsed_payload(tmp_path: Path) -> None:
    path = tmp_path / "demo.bin"
    path.write_bytes(b"abc")

    service = DemoIngestService(parser=EchoParser())

    assert service.ingest_path(path) == b"abc"


def test_ingest_propagates_read_error(tmp_path: Path) -> None:
    service = DemoIngestService(parser=EchoParser())
    source = FakeSource(tmp_path / "demo.bin", DemoReadError("boom"))

    with pytest.raises(DemoReadError):
        service.ingest(source)


def test_ingest_propagates_domain_parse_error(tmp_path: Path) -> None:
    service = DemoIngestService(parser=DomainParseFailureParser())
    source = FakeSource(tmp_path / "demo.bin", b"abc")

    with pytest.raises(DemoParseError):
        service.ingest(source)


def test_ingest_preserves_unexpected_parser_exception(tmp_path: Path) -> None:
    service = DemoIngestService(parser=BuggyParser())
    source = FakeSource(tmp_path / "demo.bin", b"abc")

    with pytest.raises(ValueError):
        service.ingest(source)


def test_binary_demo_source_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "demo.bin"
    path.write_bytes(b"abc")

    service = DemoIngestService(parser=EchoParser())
    source = BinaryDemoSource(path)

    assert service.ingest(source) == b"abc"


def test_service_can_use_cs2_parser_adapter(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "demoparser2", _ParserModule())
    path = Path("demo.dem")
    service = DemoIngestService(parser=Cs2DemoParser())

    result = service.ingest(FakeSource(path, b"demo-bytes"))

    assert result.header.map_name == "de_dust2"
    assert result.rounds[0].round_number == 1
