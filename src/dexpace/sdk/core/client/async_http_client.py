"""Async ``HttpClient`` Protocol."""
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ..http.request.request import Request
    from ..http.response.async_response import AsyncResponse


@runtime_checkable
class AsyncHttpClient(Protocol):
    """Async transport seam.

    Mirrors ``HttpClient`` but with ``async def execute`` returning an
    ``AsyncResponse``. Implementations must be safe for concurrent calls
    sharing the same event loop. Per-request state is confined to local
    variables or the returned ``AsyncResponse`` graph; the response body
    is not pre-buffered.
    """

    async def execute(self, request: Request) -> AsyncResponse: ...


async def asyncio_sleep(duration: float) -> None:
    """Default async sleep — wraps ``asyncio.sleep`` for use in retry policies."""
    await asyncio.sleep(duration)


__all__ = ["AsyncHttpClient", "asyncio_sleep"]
