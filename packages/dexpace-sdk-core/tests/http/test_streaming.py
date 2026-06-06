# Copyright (c) 2026 dexpace and Omar Aljarrah.
# Licensed under the MIT License. See LICENSE.md in the repository root for details.

"""Tests for ``iter_jsonl`` / ``chunked_frame`` helpers."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest

from dexpace.sdk.core.errors import DeserializationError
from dexpace.sdk.core.http.common import (
    aiter_chunked_frame,
    aiter_jsonl,
    chunked_frame,
    iter_jsonl,
)


def _chunks(data: bytes, size: int) -> list[bytes]:
    return [data[i : i + size] for i in range(0, len(data), size)]


class TestIterJsonl:
    def test_single_line(self) -> None:
        result = list(iter_jsonl([b'{"a": 1}\n']))
        assert result == [{"a": 1}]

    def test_multiple_lines(self) -> None:
        stream = b'{"a": 1}\n{"b": 2}\n'
        result = list(iter_jsonl([stream]))
        assert result == [{"a": 1}, {"b": 2}]

    def test_chunk_boundary_splits_line(self) -> None:
        stream = b'{"a": 1}\n{"b": 2}\n'
        result = list(iter_jsonl(_chunks(stream, 4)))
        assert result == [{"a": 1}, {"b": 2}]

    def test_empty_lines_skipped(self) -> None:
        stream = b'{"a": 1}\n\n{"b": 2}\n'
        result = list(iter_jsonl([stream]))
        assert result == [{"a": 1}, {"b": 2}]

    def test_trailing_line_without_newline(self) -> None:
        stream = b'{"a": 1}'
        result = list(iter_jsonl([stream]))
        assert result == [{"a": 1}]

    def test_malformed_line_raises(self) -> None:
        with pytest.raises(DeserializationError):
            list(iter_jsonl([b"{not json}\n"]))


class TestChunkedFrame:
    def test_simple_chunks(self) -> None:
        framed = b"".join(chunked_frame([b"hello", b"world"]))
        assert b"5\r\nhello\r\n" in framed
        assert b"5\r\nworld\r\n" in framed
        assert framed.endswith(b"0\r\n\r\n")

    def test_empty_chunks_skipped(self) -> None:
        framed = b"".join(chunked_frame([b"", b"data", b""]))
        assert framed == b"4\r\ndata\r\n0\r\n\r\n"

    def test_empty_input_emits_terminator_only(self) -> None:
        framed = b"".join(chunked_frame([]))
        assert framed == b"0\r\n\r\n"


async def test_aiter_jsonl() -> None:
    async def stream() -> AsyncIterator[bytes]:
        yield b'{"a": 1}\n'
        yield b'{"b": 2}\n'

    items: list[object] = []
    async for value in aiter_jsonl(stream()):
        items.append(value)
    assert items == [{"a": 1}, {"b": 2}]


async def test_aiter_chunked_frame() -> None:
    async def chunks() -> AsyncIterator[bytes]:
        yield b"hello"
        yield b"world"

    parts: list[bytes] = []
    async for piece in aiter_chunked_frame(chunks()):
        parts.append(piece)
    assert b"".join(parts).endswith(b"0\r\n\r\n")
