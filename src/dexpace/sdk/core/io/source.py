"""Primitive read contract."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .buffer import Buffer


class Source(ABC):
    """Primitive read contract — reads bytes into the tail of a :class:`Buffer`.

    Adapters implement this interface; callers usually do not interact with ``Source``
    directly — they obtain a :class:`BufferedSource` from an :class:`IoProvider` which
    adds the typed read surface.
    """

    @abstractmethod
    def read(self, sink: "Buffer", byte_count: int) -> int:
        """Read up to ``byte_count`` bytes from this source and append them to ``sink``.

        Returns the number of bytes read (at least 1 when ``byte_count`` > 0 and the
        source is not exhausted), ``0`` when ``byte_count`` is ``0``, or ``-1`` when
        the source is exhausted before any bytes are read.

        Raises:
            ValueError: if ``byte_count`` is negative.
            OSError: on underlying I/O failure.
        """

    @abstractmethod
    def close(self) -> None:
        """Release any underlying resources. Idempotent."""

    def __enter__(self) -> "Source":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


__all__ = ["Source"]
