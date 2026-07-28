"""CS2 demo parser adapter."""

from __future__ import annotations

from dataclasses import dataclass

from clutchiq.demo_ingest.errors import DemoParseError
from clutchiq.demo_ingest.models import Cs2Demo
from clutchiq.demo_ingest.parser import DemoParser
from clutchiq.demo_ingest.vendor import Demoparser2Adapter


@dataclass(frozen=True, slots=True)
class Cs2DemoParser(DemoParser[Cs2Demo]):
    """Parse CS2 demo bytes via the production parser library."""

    adapter: Demoparser2Adapter = Demoparser2Adapter()

    def parse(self, data: bytes) -> Cs2Demo:
        try:
            return self.adapter.parse_bytes(data)
        except DemoParseError:
            raise
        except Exception as exc:  # pragma: no cover - adapter guard
            raise DemoParseError(str(exc)) from exc
