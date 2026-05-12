"""Default in-memory :class:`IoProvider` backed by :class:`bytearray` and ``BinaryIO``.

Ships inside ``core`` so consuming applications have a working provider without
importing an external adapter. Install once at startup::

    from dexpace.sdk.core.io import Io
    from dexpace.sdk.core.io.default import DefaultIoProvider

    Io.install_provider(DefaultIoProvider())

The implementation is allocation-friendly rather than allocation-optimal: each
buffer holds its bytes in a single :class:`bytearray`, and head-side consumption
uses ``del data[:n]`` which copies the tail. For most HTTP body sizes that's
cheap; for multi-MB bodies, consider streaming via :meth:`BufferedSource.input_stream`
instead of draining into a buffer.
"""
from __future__ import annotations

import io
from typing import BinaryIO, Optional

from .buffer import Buffer
from .buffered_sink import BufferedSink
from .buffered_source import BufferedSource
from .io_provider import IoProvider
from .sink import Sink
from .source import Source

_READ_CHUNK = 8 * 1024


class _DefaultBuffer(Buffer):
    """In-memory :class:`Buffer` implementation backed by a :class:`bytearray`.

    The bytearray's head (index 0) is the consumer end; its tail is the producer
    end. Reads consume from the head with ``del data[:n]``; writes append to the
    tail with ``data.extend(...)``.
    """

    __slots__ = ("_data",)

    def __init__(self) -> None:
        self._data = bytearray()

    # ----- Buffer ---------------------------------------------------------

    @property
    def size(self) -> int:
        return len(self._data)

    def snapshot(self) -> bytes:
        if len(self._data) > Buffer.MAX_BYTE_ARRAY_SIZE:
            raise OverflowError("Buffer size exceeds MAX_BYTE_ARRAY_SIZE")
        return bytes(self._data)

    def clear(self) -> None:
        self._data.clear()

    def copy_to(self, out: Buffer, offset: int = 0, byte_count: Optional[int] = None) -> Buffer:
        if byte_count is None:
            byte_count = len(self._data) - offset
        if offset < 0 or byte_count < 0 or offset + byte_count > len(self._data):
            raise IndexError(
                f"copy_to out of range: offset={offset}, byte_count={byte_count}, size={len(self._data)}"
            )
        if byte_count == 0:
            return out
        out.write_bytes(bytes(memoryview(self._data)[offset : offset + byte_count]))
        return out

    # ----- Source ---------------------------------------------------------

    def read(self, sink: Buffer, byte_count: int) -> int:
        if byte_count < 0:
            raise ValueError("byte_count must be non-negative")
        if byte_count == 0:
            return 0
        if not self._data:
            return -1
        n = min(byte_count, len(self._data))
        sink.write_bytes(bytes(memoryview(self._data)[:n]))
        del self._data[:n]
        return n

    def close(self) -> None:
        # In-memory buffers hold no transport resources; close is a no-op.
        return None

    # ----- BufferedSource -------------------------------------------------

    def exhausted(self) -> bool:
        return not self._data

    def read_byte(self) -> int:
        if not self._data:
            raise EOFError("buffer exhausted")
        b = self._data[0]
        del self._data[0]
        return b

    def read_bytes(self, byte_count: Optional[int] = None) -> bytes:
        if byte_count is None:
            result = bytes(self._data)
            self._data.clear()
            return result
        if byte_count < 0:
            raise ValueError("byte_count must be non-negative")
        if byte_count > len(self._data):
            raise EOFError(f"requested {byte_count} bytes, only {len(self._data)} available")
        result = bytes(memoryview(self._data)[:byte_count])
        del self._data[:byte_count]
        return result

    def read_utf8(self, byte_count: Optional[int] = None) -> str:
        return self.read_bytes(byte_count).decode("utf-8")

    def read_utf8_line(self) -> Optional[str]:
        if not self._data:
            return None
        nl = self._data.find(b"\n")
        if nl < 0:
            result = bytes(self._data).decode("utf-8")
            self._data.clear()
            return result
        # CRLF: strip the trailing CR from the returned text but still consume the LF.
        end = nl - 1 if nl > 0 and self._data[nl - 1] == 0x0D else nl
        result = bytes(memoryview(self._data)[:end]).decode("utf-8")
        del self._data[: nl + 1]
        return result

    def read_string(self, encoding: str) -> str:
        result = bytes(self._data).decode(encoding)
        self._data.clear()
        return result

    def peek(self) -> BufferedSource:
        # Returning a fresh snapshot detaches the peek view from subsequent mutations.
        view = _DefaultBuffer()
        view._data = bytearray(self._data)
        return view

    def input_stream(self) -> BinaryIO:
        return _BufferReadStream(self)

    def skip(self, byte_count: int) -> None:
        if byte_count < 0:
            raise ValueError("byte_count must be non-negative")
        if byte_count > len(self._data):
            raise EOFError(f"cannot skip {byte_count} bytes; only {len(self._data)} available")
        del self._data[:byte_count]

    def slice(self, offset: int, byte_count: int) -> BufferedSource:
        if offset < 0 or byte_count < 0:
            raise ValueError("offset and byte_count must be non-negative")
        end = min(offset + byte_count, len(self._data))
        start = min(offset, len(self._data))
        view = _DefaultBuffer()
        view._data = bytearray(memoryview(self._data)[start:end])
        return view

    # ----- BufferedSink ---------------------------------------------------

    def write_bytes(self, data: bytes, offset: int = 0, byte_count: int = -1) -> BufferedSink:
        if byte_count == -1:
            byte_count = len(data) - offset
        if offset < 0 or byte_count < 0 or offset + byte_count > len(data):
            raise IndexError(
                f"write_bytes out of range: offset={offset}, byte_count={byte_count}, len={len(data)}"
            )
        if byte_count == 0:
            return self
        self._data.extend(memoryview(data)[offset : offset + byte_count])
        return self

    def write_all(self, source: Source) -> int:
        # Pump through a scratch buffer so the source's contract (write into a Buffer)
        # is honoured without the source needing to know about bytearray internals.
        scratch = _DefaultBuffer()
        total = 0
        while True:
            read = source.read(scratch, _READ_CHUNK)
            if read <= 0:
                break
            staged = scratch.size
            self._data.extend(scratch._data)
            scratch._data.clear()
            total += staged
        return total

    def write_utf8(self, string: str, begin_index: int = 0, end_index: int = -1) -> BufferedSink:
        if end_index == -1:
            end_index = len(string)
        if begin_index < 0 or end_index < begin_index or end_index > len(string):
            raise IndexError(
                f"write_utf8 out of range: begin={begin_index}, end={end_index}, len={len(string)}"
            )
        self._data.extend(string[begin_index:end_index].encode("utf-8"))
        return self

    def write_string(self, string: str, encoding: str) -> BufferedSink:
        self._data.extend(string.encode(encoding))
        return self

    def output_stream(self) -> BinaryIO:
        return _BufferWriteStream(self)

    def emit(self) -> BufferedSink:
        # Nothing to push downstream for an in-memory buffer.
        return self

    def flush(self) -> None:
        return None


class _StreamBufferedSource(BufferedSource):
    """:class:`BufferedSource` that reads from a ``BinaryIO`` through a staging buffer."""

    __slots__ = ("_stream", "_buffer")

    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self._buffer: _DefaultBuffer = _DefaultBuffer()

    @property
    def buffer(self) -> Buffer:
        return self._buffer

    def read(self, sink: Buffer, byte_count: int) -> int:
        if byte_count < 0:
            raise ValueError("byte_count must be non-negative")
        if byte_count == 0:
            return 0
        self._fill(byte_count)
        if self._buffer.size == 0:
            return -1
        return self._buffer.read(sink, byte_count)

    def close(self) -> None:
        self._stream.close()
        self._buffer.clear()

    def exhausted(self) -> bool:
        if self._buffer.size > 0:
            return False
        self._fill(_READ_CHUNK)
        return self._buffer.size == 0

    def read_byte(self) -> int:
        self._require(1)
        return self._buffer.read_byte()

    def read_bytes(self, byte_count: Optional[int] = None) -> bytes:
        if byte_count is None:
            self._drain()
            return self._buffer.read_bytes()
        self._require(byte_count)
        return self._buffer.read_bytes(byte_count)

    def read_utf8(self, byte_count: Optional[int] = None) -> str:
        return self.read_bytes(byte_count).decode("utf-8")

    def read_utf8_line(self) -> Optional[str]:
        while b"\n" not in self._buffer._data:
            chunk = self._stream.read(_READ_CHUNK)
            if not chunk:
                break
            self._buffer._data.extend(chunk)
        return self._buffer.read_utf8_line()

    def read_string(self, encoding: str) -> str:
        self._drain()
        return self._buffer.read_string(encoding)

    def peek(self) -> BufferedSource:
        # Drain the entire stream so the peek view is independent.
        self._drain()
        return self._buffer.peek()

    def input_stream(self) -> BinaryIO:
        return _SourceReadStream(self)

    def skip(self, byte_count: int) -> None:
        self._require(byte_count)
        self._buffer.skip(byte_count)

    def slice(self, offset: int, byte_count: int) -> BufferedSource:
        self._require(offset + byte_count)
        return self._buffer.slice(offset, byte_count)

    def _require(self, byte_count: int) -> None:
        if byte_count < 0:
            raise ValueError("byte_count must be non-negative")
        while self._buffer.size < byte_count:
            chunk = self._stream.read(max(_READ_CHUNK, byte_count - self._buffer.size))
            if not chunk:
                raise EOFError(
                    f"requested {byte_count} bytes, only {self._buffer.size} available before EOF"
                )
            self._buffer._data.extend(chunk)

    def _fill(self, hint: int) -> None:
        if self._buffer.size >= hint:
            return
        chunk = self._stream.read(max(_READ_CHUNK, hint))
        if chunk:
            self._buffer._data.extend(chunk)

    def _drain(self) -> None:
        while True:
            chunk = self._stream.read(_READ_CHUNK)
            if not chunk:
                return
            self._buffer._data.extend(chunk)


class _StreamBufferedSink(BufferedSink):
    """:class:`BufferedSink` that writes through a staging buffer to a ``BinaryIO``."""

    __slots__ = ("_stream", "_buffer")

    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self._buffer: _DefaultBuffer = _DefaultBuffer()

    @property
    def buffer(self) -> Buffer:
        return self._buffer

    def write(self, source: Buffer, byte_count: int) -> None:
        source.copy_to(self._buffer, 0, byte_count)
        # Drop the same prefix from source so its read cursor advances.
        source.skip(byte_count)
        self.emit()

    def write_bytes(self, data: bytes, offset: int = 0, byte_count: int = -1) -> BufferedSink:
        self._buffer.write_bytes(data, offset, byte_count)
        self.emit()
        return self

    def write_all(self, source: Source) -> int:
        total = self._buffer.write_all(source)
        self.emit()
        return total

    def write_utf8(self, string: str, begin_index: int = 0, end_index: int = -1) -> BufferedSink:
        self._buffer.write_utf8(string, begin_index, end_index)
        self.emit()
        return self

    def write_string(self, string: str, encoding: str) -> BufferedSink:
        self._buffer.write_string(string, encoding)
        self.emit()
        return self

    def output_stream(self) -> BinaryIO:
        return _SinkWriteStream(self)

    def emit(self) -> BufferedSink:
        if self._buffer.size > 0:
            self._stream.write(bytes(self._buffer._data))
            self._buffer._data.clear()
        return self

    def flush(self) -> None:
        self.emit()
        self._stream.flush()

    def close(self) -> None:
        try:
            self.emit()
        finally:
            self._stream.close()


class _BufferReadStream(io.RawIOBase):
    """BinaryIO view over a :class:`_DefaultBuffer` for caller-driven reading."""

    def __init__(self, buffer: _DefaultBuffer) -> None:
        super().__init__()
        self._buffer = buffer

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:  # type: ignore[override]
        if self._buffer.size == 0:
            return 0
        n = min(len(b), self._buffer.size)
        b[:n] = memoryview(self._buffer._data)[:n]
        del self._buffer._data[:n]
        return n


class _BufferWriteStream(io.RawIOBase):
    """BinaryIO view over a :class:`_DefaultBuffer` for caller-driven writing."""

    def __init__(self, buffer: _DefaultBuffer) -> None:
        super().__init__()
        self._buffer = buffer

    def writable(self) -> bool:
        return True

    def write(self, b) -> int:  # type: ignore[override]
        self._buffer._data.extend(b)
        return len(b)


class _SourceReadStream(io.RawIOBase):
    """BinaryIO view over a :class:`BufferedSource` (stream-backed)."""

    def __init__(self, source: BufferedSource) -> None:
        super().__init__()
        self._source = source

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:  # type: ignore[override]
        scratch = _DefaultBuffer()
        n = self._source.read(scratch, len(b))
        if n <= 0:
            return 0
        b[:n] = memoryview(scratch._data)[:n]
        return n

    def close(self) -> None:
        super().close()
        self._source.close()


class _SinkWriteStream(io.RawIOBase):
    """BinaryIO view over a :class:`BufferedSink` (stream-backed)."""

    def __init__(self, sink: BufferedSink) -> None:
        super().__init__()
        self._sink = sink

    def writable(self) -> bool:
        return True

    def write(self, b) -> int:  # type: ignore[override]
        self._sink.write_bytes(bytes(b))
        return len(b)

    def flush(self) -> None:
        self._sink.flush()

    def close(self) -> None:
        super().close()
        self._sink.close()


class DefaultIoProvider(IoProvider):
    """In-memory :class:`IoProvider` backed by :class:`bytearray` and ``BinaryIO``.

    The reference implementation. Suitable for production for typical HTTP body
    sizes; bring your own provider if you need segment-pooled zero-copy semantics
    or share-by-reference buffer slicing.
    """

    def buffer(self) -> Buffer:
        return _DefaultBuffer()

    def source_from_stream(self, stream: BinaryIO) -> BufferedSource:
        return _StreamBufferedSource(stream)

    def source_from_bytes(self, data: bytes) -> BufferedSource:
        buf = _DefaultBuffer()
        buf._data = bytearray(data)
        return buf

    def sink_to_stream(self, stream: BinaryIO) -> BufferedSink:
        return _StreamBufferedSink(stream)

    def buffered_source(self, source: Source) -> BufferedSource:
        if isinstance(source, BufferedSource):
            return source
        return _PrimitiveSourceWrapper(source)

    def buffered_sink(self, sink: Sink) -> BufferedSink:
        if isinstance(sink, BufferedSink):
            return sink
        return _PrimitiveSinkWrapper(sink)


class _PrimitiveSourceWrapper(_StreamBufferedSource):
    """Wraps a primitive :class:`Source` with the typed read surface."""

    def __init__(self, source: Source) -> None:
        # The parent expects a BinaryIO; we adapt the primitive Source to that shape
        # via a tiny stream that pumps through a scratch buffer.
        super().__init__(_PrimitiveSourceStream(source))


class _PrimitiveSinkWrapper(_StreamBufferedSink):
    """Wraps a primitive :class:`Sink` with the typed write surface."""

    def __init__(self, sink: Sink) -> None:
        super().__init__(_PrimitiveSinkStream(sink))


class _PrimitiveSourceStream(io.RawIOBase):
    def __init__(self, source: Source) -> None:
        super().__init__()
        self._source = source

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:  # type: ignore[override]
        scratch = _DefaultBuffer()
        n = self._source.read(scratch, len(b))
        if n <= 0:
            return 0
        b[:n] = memoryview(scratch._data)[:n]
        return n

    def close(self) -> None:
        super().close()
        self._source.close()


class _PrimitiveSinkStream(io.RawIOBase):
    def __init__(self, sink: Sink) -> None:
        super().__init__()
        self._sink = sink

    def writable(self) -> bool:
        return True

    def write(self, b) -> int:  # type: ignore[override]
        scratch = _DefaultBuffer()
        scratch._data.extend(b)
        self._sink.write(scratch, len(b))
        return len(b)

    def flush(self) -> None:
        self._sink.flush()

    def close(self) -> None:
        super().close()
        self._sink.close()


__all__ = ["DefaultIoProvider"]
