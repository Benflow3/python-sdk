# Copyright (c) 2026 dexpace and Omar Aljarrah.
# Licensed under the MIT License. See LICENSE.md in the repository root for details.

"""Challenge handler Protocol + simple built-ins (Basic, Composite).

A ``ChallengeHandler`` inspects a parsed list of ``AuthenticateChallenge``
values and, if it recognises a scheme it can satisfy, returns the header
name + value the caller should attach to the retried request. The Protocol
keeps the contract structural so transport adapters, tests, and the
``BearerTokenPolicy`` can all plug in interchangeably.

``BasicChallengeHandler`` wraps a static username/password pair and produces
``Authorization: Basic <base64>``. ``CompositeChallengeHandler`` walks an
ordered list of child handlers and returns the first non-``None`` result;
this is how callers typically combine Basic + Digest negotiation.
"""

from __future__ import annotations

import base64
from typing import Protocol, runtime_checkable

from ..common.url import Url
from ..request.method import Method
from .challenge import AuthenticateChallenge


@runtime_checkable
class ChallengeHandler(Protocol):
    """Negotiates a ``WWW-Authenticate`` / ``Proxy-Authenticate`` challenge.

    Implementations are stateful where the scheme requires it (e.g. Digest
    keeps a nonce counter) so callers should construct one per logical
    client, not per request.
    """

    def can_handle(self, challenges: list[AuthenticateChallenge]) -> bool:
        """Return True if at least one challenge can be satisfied."""
        ...

    def handle(
        self,
        method: Method,
        url: Url,
        challenges: list[AuthenticateChallenge],
        *,
        is_proxy: bool,
    ) -> tuple[str, str] | None:
        """Produce the auth header for the retry, or ``None``.

        Args:
            method: HTTP method that will be retried.
            url: Target URL.
            challenges: Parsed challenges from the 401/407 response.
            is_proxy: True when handling a 407 (``Proxy-Authenticate``).

        Returns:
            ``(header_name, header_value)`` to set on the next request, or
            ``None`` if no offered challenge is supported.
        """
        ...


class BasicChallengeHandler:
    """Satisfy a ``Basic`` challenge with a static username/password.

    The credentials are encoded once at construction time; the resulting
    base64 payload is reused for every request.
    """

    __slots__ = ("_encoded",)

    def __init__(self, username: str, password: str) -> None:
        if not isinstance(username, str) or not isinstance(password, str):
            raise TypeError("username and password must be strings")
        raw = f"{username}:{password}".encode()
        self._encoded = base64.b64encode(raw).decode("ascii")

    def can_handle(self, challenges: list[AuthenticateChallenge]) -> bool:
        return any(c.scheme.casefold() == "basic" for c in challenges)

    def handle(
        self,
        method: Method,
        url: Url,
        challenges: list[AuthenticateChallenge],
        *,
        is_proxy: bool,
    ) -> tuple[str, str] | None:
        del method, url  # Basic does not vary by request line.
        if not self.can_handle(challenges):
            return None
        header = "Proxy-Authorization" if is_proxy else "Authorization"
        return header, f"Basic {self._encoded}"


class CompositeChallengeHandler:
    """Walk an ordered list of handlers; first ``handle`` hit wins."""

    __slots__ = ("_handlers",)

    def __init__(self, *handlers: ChallengeHandler) -> None:
        if not handlers:
            raise ValueError("at least one handler is required")
        self._handlers: tuple[ChallengeHandler, ...] = handlers

    def can_handle(self, challenges: list[AuthenticateChallenge]) -> bool:
        return any(h.can_handle(challenges) for h in self._handlers)

    def handle(
        self,
        method: Method,
        url: Url,
        challenges: list[AuthenticateChallenge],
        *,
        is_proxy: bool,
    ) -> tuple[str, str] | None:
        for handler in self._handlers:
            result = handler.handle(method, url, challenges, is_proxy=is_proxy)
            if result is not None:
                return result
        return None


__all__ = [
    "BasicChallengeHandler",
    "ChallengeHandler",
    "CompositeChallengeHandler",
]
