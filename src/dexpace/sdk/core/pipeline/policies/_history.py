"""Per-attempt retry history record."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...http.request.request import Request
    from ...http.response.async_response import AsyncResponse
    from ...http.response.response import Response


@dataclass(frozen=True, slots=True)
class RequestHistory:
    """Snapshot of one retried attempt.

    Captured by ``RetryPolicy`` / ``AsyncRetryPolicy`` for every failed
    attempt so callers can inspect the full retry trail on the eventual
    error (via ``ctx.data["retry_history"]``) or for post-mortem logging.

    Attributes:
        request: The request as it was sent on this attempt (may differ
            from earlier attempts if policies mutated it between retries).
        response: The response received (``Response`` or ``AsyncResponse``),
            or ``None`` if the attempt failed before a response arrived.
        error: The exception raised by the attempt, or ``None`` on success.
    """

    request: Request
    response: Response | AsyncResponse | None = None
    error: BaseException | None = None


__all__ = ["RequestHistory"]
