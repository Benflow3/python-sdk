"""In-memory byte queue — both :class:`BufferedSource` and :class:`BufferedSink`."""
from __future__ import annotations

from abc import abstractmethod
from typing import Optional

from .buffered_sink import BufferedSink
from .buffered_source import BufferedSource


class Buffer(BufferedSource, BufferedSink):
    """An in-memory queue of bytes that is simultaneously a :class:`BufferedSource`
    and a :class:`BufferedSink`.

    Bytes written through the sink end come out the source end in FIFO order.
    Buffers are the canonical staging area for body-logging snapshots and for
    adapter-internal staging between transport streams and typed read/write calls.

    Instances are obtained from :meth:`IoProvider.buffer` — implementations live
    in adapter modules.

    Buffers are not thread-safe; serialize external access if shared.
    """

    #: Maximum number of bytes that can be safely returned as a single ``bytes``
    #: object. Matches CPython's effective limit for very large byte objects.
    MAX_BYTE_ARRAY_SIZE: int = (1 << 31) - 9

    @property
    @abstractmethod
    def size(self) -> int:
        """The number of bytes currently held."""

    @abstractmethod
    def snapshot(self) -> bytes:
        """Return an immutable copy of the buffer's contents. The buffer is unchanged.

        Raises:
            OverflowError: when :attr:`size` exceeds :attr:`MAX_BYTE_ARRAY_SIZE`.
        """

    @abstractmethod
    def clear(self) -> None:
        """Discard every byte."""

    @abstractmethod
    def copy_to(
        self,
        out: "Buffer",
        offset: int = 0,
        byte_count: Optional[int] = None,
    ) -> "Buffer":
        """Copy ``byte_count`` bytes starting at ``offset`` into ``out``.

        With ``byte_count`` unset, copies from ``offset`` to the end of the buffer.
        ``self`` is unchanged.

        Raises:
            IndexError: if the range is out of bounds.
        """

    @property
    def buffer(self) -> "Buffer":
        """A :class:`Buffer` IS its own buffer."""
        return self


__all__ = ["Buffer"]
