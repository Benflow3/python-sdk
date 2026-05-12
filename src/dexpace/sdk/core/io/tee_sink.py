""":class:`BufferedSink` that mirrors writes into a tap buffer for body logging."""
from __future__ import annotations

from typing import BinaryIO

from .buffer import Buffer
from .buffered_sink import BufferedSink
from .io_provider import IoProvider
from .source import Source

_SCRATCH_BYTES = 8 * 1024


class TeeSink(BufferedSink):
    """A :class:`BufferedSink` that mirrors every byte written through it into a
    tap :class:`Buffer` while still forwarding to a primary sink.

    Used by request body-logging to capture bytes for diagnostic output without
    breaking the streaming write to the transport sink.

    Not thread-safe — a single in-flight request writes through one ``TeeSink``
    from one thread.
    """

    __slots__ = ("_primary", "_tap", "_scratch")

    def __init__(self, primary: BufferedSink, tap: Buffer, provider: IoProvider) -> None:
        self._primary = primary
        self._tap = tap
        self._scratch: Buffer = provider.buffer()

    @property
    def buffer(self) -> Buffer:
        return self._tap

    def write(self, source: Buffer, byte_count: int) -> None:
        # Mirror the prefix into tap (non-destructive), then drain into primary.
        source.copy_to(self._tap, 0, byte_count)
        self._primary.write(source, byte_count)

    def flush(self) -> None:
        self._primary.flush()

    def close(self) -> None:
        self._primary.close()

    def write_bytes(self, data: bytes, offset: int = 0, byte_count: int = -1) -> "BufferedSink":
        self._scratch.write_bytes(data, offset, byte_count)
        self._drain_scratch()
        return self

    def write_all(self, source: Source) -> int:
        total = 0
        while True:
            read = source.read(self._scratch, _SCRATCH_BYTES)
            # A zero-byte read on a non-zero request means the source is broken —
            # treat it the same as end-of-stream rather than spinning forever.
            if read <= 0:
                break
            self._drain_scratch()
            total += read
        return total

    def write_utf8(self, string: str, begin_index: int = 0, end_index: int = -1) -> "BufferedSink":
        self._scratch.write_utf8(string, begin_index, end_index)
        self._drain_scratch()
        return self

    def write_string(self, string: str, encoding: str) -> "BufferedSink":
        self._scratch.write_string(string, encoding)
        self._drain_scratch()
        return self

    def output_stream(self) -> BinaryIO:
        primary_stream = self._primary.output_stream()
        tap_stream = self._tap.output_stream()

        class _TeeStream:
            def write(self, data: bytes) -> int:
                primary_stream.write(data)
                tap_stream.write(data)
                return len(data)

            def flush(self) -> None:
                primary_stream.flush()
                tap_stream.flush()

            def close(self) -> None:
                try:
                    primary_stream.close()
                finally:
                    tap_stream.close()

        return _TeeStream()  # type: ignore[return-value]

    def emit(self) -> "BufferedSink":
        self._primary.emit()
        return self

    def _drain_scratch(self) -> None:
        staged = self._scratch.size
        if staged == 0:
            return
        try:
            self._scratch.copy_to(self._tap, 0, staged)
            self._primary.write(self._scratch, staged)
        finally:
            # Ensure scratch is empty even on failure paths so a subsequent typed
            # write doesn't prepend leftover bytes from a failed attempt.
            if self._scratch.size > 0:
                self._scratch.clear()


__all__ = ["TeeSink"]
