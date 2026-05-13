"""Tests for ``AsyncRequestBody`` / ``AsyncResponseBody``."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable

import pytest

from dexpace.sdk.core.http.common import common_media_types
from dexpace.sdk.core.http.request import AsyncRequestBody
from dexpace.sdk.core.http.response import AsyncResponseBody


async def _adrain(body: AsyncRequestBody) -> bytes:
    chunks: list[bytes] = []
    async for chunk in body.aiter_bytes():
        chunks.append(chunk)
    return b"".join(chunks)


async def test_from_bytes_replayable() -> None:
    body = AsyncRequestBody.from_bytes(b"hello")
    assert body.is_replayable()
    assert await _adrain(body) == b"hello"
    assert await _adrain(body) == b"hello"


async def test_from_string() -> None:
    body = AsyncRequestBody.from_string("hello")
    assert await _adrain(body) == b"hello"


async def test_from_form() -> None:
    body = AsyncRequestBody.from_form({"a": "1"})
    text = (await _adrain(body)).decode()
    assert text == "a=1"
    assert body.media_type() == common_media_types.APPLICATION_FORM_URLENCODED


async def test_from_async_iter_single_use() -> None:
    async def chunks() -> AsyncIterator[bytes]:
        yield b"ab"
        yield b"c"

    body = AsyncRequestBody.from_async_iter(chunks())
    assert await _adrain(body) == b"abc"
    with pytest.raises(RuntimeError):
        await _adrain(body)


async def test_to_replayable_buffers_async_iter() -> None:
    async def chunks() -> AsyncIterator[bytes]:
        yield b"ab"
        yield b"c"

    body = await AsyncRequestBody.from_async_iter(chunks()).to_replayable()
    assert body.is_replayable()
    assert await _adrain(body) == b"abc"
    assert await _adrain(body) == b"abc"


async def test_async_response_body_bytes() -> None:
    body = AsyncResponseBody.from_bytes(b"hello")
    assert await body.bytes() == b"hello"


async def test_async_response_body_string() -> None:
    body = AsyncResponseBody.from_bytes("héllo".encode())
    assert await body.string() == "héllo"


async def test_async_response_body_chunks() -> None:
    body = AsyncResponseBody.from_bytes(b"abcdef")
    chunks = [chunk async for chunk in body.aiter_bytes(chunk_size=2)]
    assert chunks == [b"ab", b"cd", b"ef"]


async def test_async_context_manager_closes() -> None:
    body = AsyncResponseBody.from_bytes(b"x")
    async with body as b:
        assert b is body


class _StubAsyncStream:
    """Minimal ``SupportsAsyncRead`` stub for the chunk-size guard test."""

    async def read(self, size: int = -1) -> bytes:
        del size
        return b""

    async def close(self) -> object:  # pragma: no cover - never reached
        return None


@pytest.mark.parametrize(
    "factory",
    [
        lambda: AsyncResponseBody.from_bytes(b"hi"),
        lambda: AsyncResponseBody.from_async_stream(_StubAsyncStream()),
    ],
)
@pytest.mark.parametrize("size", [0, -1])
async def test_aiter_bytes_rejects_invalid_chunk_size(
    factory: Callable[[], AsyncResponseBody],
    size: int,
) -> None:
    body = factory()
    with pytest.raises(ValueError, match="chunk_size"):
        async for _ in body.aiter_bytes(size):
            pass
