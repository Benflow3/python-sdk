"""Primitive write contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .buffer import Buffer


class Sink(ABC):
    """Primitive write contract — consumes bytes from the head of a :class:`Buffer`.

    Adapters implement this interface; callers usually do not interact with ``Sink``
    directly — they obtain a :class:`BufferedSink` from an :class:`IoProvider` which
    adds the typed write surface.
    """

    @abstractmethod
    def write(self, source: "Buffer", byte_count: int) -> None:
        """Remove ``byte_count`` bytes from the head of ``source`` and append them here.

        Raises:
            ValueError: if ``byte_count`` is negative.
            OSError: on underlying I/O failure (including when ``source`` has fewer
                than ``byte_count`` bytes).
        """

    @abstractmethod
    def flush(self) -> None:
        """Push buffered bytes to their final destination."""

    @abstractmethod
    def close(self) -> None:
        """Release any underlying resources. Idempotent."""

    def __enter__(self) -> "Sink":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


__all__ = ["Sink"]
