# Copyright (c) 2026 dexpace and Omar Aljarrah.
# Licensed under the MIT License. See LICENSE.md in the repository root for details.

"""``requests``-backed synchronous HTTP transport for ``dexpace-sdk-core``."""

from __future__ import annotations

from .client import RequestsHttpClient

__all__ = ["RequestsHttpClient"]
