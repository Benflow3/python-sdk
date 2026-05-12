"""Single seam between ``core`` and a concrete I/O implementation."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, BinaryIO

if TYPE_CHECKING:
    from .buffer import Buffer
    from .buffered_sink import BufferedSink
    from .buffered_source import BufferedSource
    from .sink import Sink
    from .source import Source


class IoProvider(ABC):
    """Single seam between ``core`` and a concrete I/O implementation.

    A consuming library installs one implementation at startup::

        Io.install_provider(DefaultIoProvider())

    After installation, every part of the SDK that needs to create a stream calls
    :attr:`Io.provider` and obtains the right factory method here — without ever
    importing a concrete implementation.

    Factory methods are invoked concurrently from request-processing threads and
    must be safe to call from any thread. Individual buffers / sources / sinks
    returned from them are not required to be thread-safe.
    """

    @abstractmethod
    def buffer(self) -> "Buffer":
        """Return a new, empty in-memory :class:`Buffer`."""

    @abstractmethod
    def source_from_stream(self, stream: BinaryIO) -> "BufferedSource":
        """Return a :class:`BufferedSource` reading from ``stream``.

        The returned source takes ownership of ``stream`` — closing the source
        closes the stream.
        """

    @abstractmethod
    def source_from_bytes(self, data: bytes) -> "BufferedSource":
        """Return a :class:`BufferedSource` reading from the given bytes."""

    @abstractmethod
    def sink_to_stream(self, stream: BinaryIO) -> "BufferedSink":
        """Return a :class:`BufferedSink` writing to ``stream``.

        The returned sink takes ownership of ``stream`` — closing the sink closes
        the stream.
        """

    @abstractmethod
    def buffered_source(self, source: "Source") -> "BufferedSource":
        """Wrap an existing primitive :class:`Source` with the typed read surface."""

    @abstractmethod
    def buffered_sink(self, sink: "Sink") -> "BufferedSink":
        """Wrap an existing primitive :class:`Sink` with the typed write surface."""


__all__ = ["IoProvider"]
