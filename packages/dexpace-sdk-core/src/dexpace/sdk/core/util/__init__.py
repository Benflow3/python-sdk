"""Cross-cutting utilities used throughout the SDK core.

Exports the :class:`Clock` / :class:`AsyncClock` abstractions that let
time-dependent code (retry backoff, token expiry) be driven deterministically
in tests, and the :class:`ProxyOptions` value type used to describe outbound
HTTP / SOCKS proxies in a transport-agnostic way.
"""

from __future__ import annotations

from .clock import ASYNC_SYSTEM_CLOCK, SYSTEM_CLOCK, AsyncClock, Clock
from .proxy import ProxyOptions, ProxyType

__all__ = [
    "ASYNC_SYSTEM_CLOCK",
    "SYSTEM_CLOCK",
    "AsyncClock",
    "Clock",
    "ProxyOptions",
    "ProxyType",
]
