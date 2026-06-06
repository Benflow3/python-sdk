# Copyright (c) 2026 dexpace and Omar Aljarrah.
# Licensed under the MIT License. See LICENSE.md in the repository root for details.

"""Reference stdlib HTTP transports for dexpace-sdk-core.

`UrllibHttpClient` and `AsyncioHttpClient` implement the `HttpClient` and
`AsyncHttpClient` Protocols from `dexpace-sdk-core`. Both depend only on the
Python stdlib — useful for tests, examples, and demonstrating the pipeline
shape.

For production traffic, prefer the third-party-backed adapters
(`dexpace-sdk-http-httpx`, `dexpace-sdk-http-aiohttp`,
`dexpace-sdk-http-requests`).
"""

from __future__ import annotations

from .asyncio_http_client import AsyncioHttpClient
from .urllib_http_client import UrllibHttpClient

__all__ = ["AsyncioHttpClient", "UrllibHttpClient"]
