"""Transport SPI: the seam between SDK models and a concrete HTTP transport.

The `HttpClient` / `AsyncHttpClient` Protocols live here. Concrete transports
ship in separate packages (`dexpace-sdk-http-stdlib`,
`dexpace-sdk-http-httpx`, etc.) — `core` deliberately knows nothing about
specific HTTP libraries.
"""

from __future__ import annotations

from .async_http_client import AsyncHttpClient, asyncio_sleep
from .http_client import HttpClient

__all__ = [
    "AsyncHttpClient",
    "HttpClient",
    "asyncio_sleep",
]
