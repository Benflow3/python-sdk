"""Typed read surface layered on top of :class:`Source`."""
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, BinaryIO, Optional

from .source import Source

if TYPE_CHECKING:
    from .buffer import Buffer


class BufferedSource(Source):
    """A :class:`Source` that adds the typed read surface needed for HTTP body
    deserialization, body-logging snapshots, and ``BinaryIO`` interop.

    Implementations are obtained from an :class:`IoProvider` — callers do not
    construct them directly.

    Instances are not safe for concurrent use; serialize external access if a
    source is shared across threads.
    """

    @property
    @abstractmethod
    def buffer(self) -> "Buffer":
        """The adapter's internal buffer.

        When this source IS a :class:`Buffer`, the property returns ``self``.
        Otherwise it returns whatever in-memory storage the adapter uses to stage
        bytes between the underlying transport and typed read calls. Mutating the
        returned buffer directly is undefined behavior.
        """

    @abstractmethod
    def exhausted(self) -> bool:
        """Return ``True`` when no more bytes are available. May block."""

    @abstractmethod
    def read_byte(self) -> int:
        """Read a single byte as an ``int`` in ``[0, 255]``.

        Raises:
            EOFError: if the source is exhausted.
        """

    @abstractmethod
    def read_bytes(self, byte_count: Optional[int] = None) -> bytes:
        """Read bytes.

        Without an argument, reads every remaining byte. With ``byte_count``,
        reads exactly that many bytes and raises :class:`EOFError` if the source is
        exhausted before the count is satisfied.
        """

    @abstractmethod
    def read_utf8(self, byte_count: Optional[int] = None) -> str:
        """Read every remaining byte (or exactly ``byte_count``) and decode as UTF-8."""

    @abstractmethod
    def read_utf8_line(self) -> Optional[str]:
        """Read bytes up to (and consume) the next ``\\n`` or ``\\r\\n`` terminator.

        Returns the preceding bytes decoded as UTF-8. Returns ``None`` if the source
        is exhausted before any bytes are read. A final line without a terminator
        is returned as-is.
        """

    @abstractmethod
    def read_string(self, encoding: str) -> str:
        """Read every remaining byte and decode using ``encoding``."""

    @abstractmethod
    def peek(self) -> "BufferedSource":
        """Return a non-consuming view of this source.

        Reads from the returned source do not advance the position of this source.
        """

    @abstractmethod
    def input_stream(self) -> BinaryIO:
        """Return a ``BinaryIO`` reading from this source. Closing it closes ``self``."""

    @abstractmethod
    def skip(self, byte_count: int) -> None:
        """Skip ``byte_count`` bytes.

        Raises:
            EOFError: if exhausted before the count is met.
        """

    @abstractmethod
    def slice(self, offset: int, byte_count: int) -> "BufferedSource":
        """Return a non-consuming, length-bounded view starting at ``offset``.

        Reads from the returned source do not advance ``self``. Closing the slice
        does NOT close ``self``; closing ``self`` invalidates the slice — subsequent
        reads raise :class:`OSError`. Multiple slices are independent.
        """


__all__ = ["BufferedSource"]
