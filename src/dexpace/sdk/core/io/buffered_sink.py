"""Typed write surface layered on top of :class:`Sink`."""
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, BinaryIO

from .sink import Sink

if TYPE_CHECKING:
    from .buffer import Buffer
    from .source import Source


class BufferedSink(Sink):
    """A :class:`Sink` that adds the typed write surface needed for HTTP body
    serialization and ``BinaryIO`` interop.

    Implementations are obtained from an :class:`IoProvider` — callers do not
    construct them directly.

    Instances are not safe for concurrent use; serialize external access if a
    sink is shared across threads.
    """

    @property
    @abstractmethod
    def buffer(self) -> "Buffer":
        """The adapter's internal buffer.

        When this sink IS a :class:`Buffer`, the property returns ``self``.
        Otherwise it returns the in-memory staging buffer used between typed write
        calls and the underlying transport. Mutating directly is undefined behavior.
        """

    @abstractmethod
    def write_bytes(self, data: bytes, offset: int = 0, byte_count: int = -1) -> "BufferedSink":
        """Write ``byte_count`` bytes from ``data`` starting at ``offset``.

        With the defaults, writes every byte of ``data``.

        Raises:
            IndexError: if ``offset`` or ``byte_count`` is out of range.
        """

    @abstractmethod
    def write_all(self, source: "Source") -> int:
        """Drain every remaining byte of ``source`` into this sink.

        Returns the number of bytes transferred.
        """

    @abstractmethod
    def write_utf8(
        self,
        string: str,
        begin_index: int = 0,
        end_index: int = -1,
    ) -> "BufferedSink":
        """UTF-8 encode (a slice of) ``string`` and write the resulting bytes.

        With the defaults, encodes and writes the whole string.
        """

    @abstractmethod
    def write_string(self, string: str, encoding: str) -> "BufferedSink":
        """Encode ``string`` using ``encoding`` and write the resulting bytes."""

    @abstractmethod
    def output_stream(self) -> BinaryIO:
        """Return a ``BinaryIO`` writing to this sink. Closing it closes ``self``."""

    @abstractmethod
    def emit(self) -> "BufferedSink":
        """Push buffered bytes one level toward their final destination.

        Use :meth:`flush` when system-level flush semantics are required.
        """


__all__ = ["BufferedSink"]
