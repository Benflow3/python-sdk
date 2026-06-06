# Copyright (c) 2026 dexpace and Omar Aljarrah.
# Licensed under the MIT License. See LICENSE.md in the repository root for details.

"""Proxy configuration value type.

``ProxyOptions`` describes an outbound HTTP / SOCKS proxy together with the
list of hosts that should bypass it. Instances are immutable and the bypass
globs (``*.internal.example.com`` style) are compiled exactly once at
construction time so per-request matching is a plain regex check.

The :meth:`ProxyOptions.from_configuration` factory bridges the proxy value
type to the layered :class:`Configuration` lookup: it reads ``HTTPS_PROXY``
(preferred) or ``HTTP_PROXY`` as full URLs and ``NO_PROXY`` as a
comma-separated bypass list. Parse failures degrade to ``None`` rather than
raising — bad proxy configuration should never bring down the caller.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Self
from urllib.parse import urlsplit

from ..config.configuration import Configuration

__all__ = ["ProxyOptions", "ProxyType"]


_LOG = logging.getLogger(__name__)


class ProxyType(StrEnum):
    """Supported proxy transport flavours.

    The SDK core only models the *type* — concrete transports decide which
    flavours they actually support. ``SOCKS4`` / ``SOCKS5`` are included for
    API parity with the Java SDK even though the stdlib HTTP adapter only
    speaks ``HTTP``.
    """

    HTTP = "HTTP"
    SOCKS4 = "SOCKS4"
    SOCKS5 = "SOCKS5"


@dataclass(frozen=True, slots=True)
class ProxyOptions:
    """Immutable proxy configuration with pre-compiled bypass globs.

    Attributes:
        type: Proxy transport flavour (HTTP / SOCKS4 / SOCKS5).
        host: Proxy host. Must be non-empty.
        port: Proxy port in the range ``0..65535``.
        non_proxy_hosts: Glob patterns (``fnmatch`` syntax) that bypass the
            proxy. Compiled once in ``__post_init__``.
        username: Optional username for proxy auth. Masked in ``repr``.
        password: Optional password for proxy auth. Masked in ``repr``.
    """

    type: ProxyType
    host: str
    port: int
    non_proxy_hosts: tuple[str, ...] = ()
    username: str | None = None
    password: str | None = None
    # Compiled bypass globs. Excluded from ``repr`` / equality / hashing so
    # two ``ProxyOptions`` with the same logical fields compare equal even
    # though their compiled patterns are distinct objects.
    _bypass_patterns: tuple[re.Pattern[str], ...] = field(
        init=False, repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        """Validate inputs and pre-compile bypass globs.

        Raises:
            ValueError: If ``host`` is empty or ``port`` is outside 0..65535.
        """
        if not self.host:
            raise ValueError("host must not be empty")
        if not (0 <= self.port <= 65535):
            raise ValueError(f"port must be in 0..65535, got {self.port}")
        compiled = tuple(
            re.compile(fnmatch.translate(pattern), re.IGNORECASE)
            for pattern in self.non_proxy_hosts
        )
        object.__setattr__(self, "_bypass_patterns", compiled)

    def bypasses_proxy(self, host: str) -> bool:
        """Return ``True`` when ``host`` matches any bypass glob.

        Matching is case-insensitive — hostnames in the wire are
        case-insensitive per RFC 3986.

        Args:
            host: Candidate hostname (no scheme, no port).

        Returns:
            ``True`` if at least one bypass pattern matches; ``False``
            otherwise (including when there are no bypass patterns).
        """
        return any(pattern.match(host) for pattern in self._bypass_patterns)

    def __repr__(self) -> str:
        """Render the proxy options with credentials masked.

        Username and password (when present) are rendered as ``'***'`` so
        accidental logging of the proxy configuration never leaks creds.

        Returns:
            A ``ProxyOptions(...)`` repr suitable for logs.
        """
        username = "'***'" if self.username is not None else "None"
        password = "'***'" if self.password is not None else "None"
        return (
            f"ProxyOptions(type={self.type!r}, host={self.host!r}, "
            f"port={self.port!r}, non_proxy_hosts={self.non_proxy_hosts!r}, "
            f"username={username}, password={password})"
        )

    @classmethod
    def from_configuration(cls, config: Configuration) -> Self | None:
        """Build a ``ProxyOptions`` from layered configuration env vars.

        Reads ``HTTPS_PROXY`` (preferred) or ``HTTP_PROXY`` as full proxy
        URLs (``http://user:pass@proxy.corp:8080``). Reads ``NO_PROXY`` as
        a comma-separated bypass list. A ``NO_PROXY`` value of ``"*"``
        bypasses everything and short-circuits to ``None``.

        Args:
            config: Layered configuration to read from.

        Returns:
            A populated ``ProxyOptions``, or ``None`` when no proxy is
            configured, when ``NO_PROXY=*``, or when the proxy URL fails to
            parse (a debug-level log line records the failure).
        """
        no_proxy_raw = config.get(Configuration.NO_PROXY)
        if no_proxy_raw is not None and no_proxy_raw.strip() == "*":
            return None
        proxy_url = config.get(Configuration.HTTPS_PROXY) or config.get(Configuration.HTTP_PROXY)
        if proxy_url is None or proxy_url == "":
            return None
        try:
            parsed = urlsplit(proxy_url)
        except ValueError:
            _LOG.debug("failed to parse proxy URL %r", proxy_url)
            return None
        if not parsed.hostname:
            _LOG.debug("proxy URL %r missing hostname", proxy_url)
            return None
        try:
            port = parsed.port
        except ValueError:
            _LOG.debug("proxy URL %r has invalid port", proxy_url)
            return None
        if port is None:
            _LOG.debug("proxy URL %r missing port", proxy_url)
            return None
        non_proxy_hosts: tuple[str, ...] = ()
        if no_proxy_raw is not None and no_proxy_raw.strip():
            non_proxy_hosts = tuple(
                entry.strip() for entry in no_proxy_raw.split(",") if entry.strip()
            )
        try:
            return cls(
                type=ProxyType.HTTP,
                host=parsed.hostname,
                port=port,
                non_proxy_hosts=non_proxy_hosts,
                username=parsed.username,
                password=parsed.password,
            )
        except ValueError:
            _LOG.debug("proxy URL %r failed ProxyOptions validation", proxy_url)
            return None
