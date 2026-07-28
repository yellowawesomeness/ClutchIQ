"""Parser boundary for demo ingestion."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

ParsedT = TypeVar("ParsedT", covariant=True)


@runtime_checkable
class DemoParser(Protocol[ParsedT]):
    """Parse raw demo bytes into a domain object."""

    def parse(self, data: bytes) -> ParsedT:
        """Parse the given demo payload."""
        ...
