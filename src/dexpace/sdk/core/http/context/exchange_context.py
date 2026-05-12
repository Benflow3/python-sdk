"""Terminal link in the context promotion chain."""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...instrumentation import InstrumentationContext
from .call_context import CallContext

if TYPE_CHECKING:
    from ..request.request import Request
    from ..response.response import Response


@dataclass(frozen=True)
class ExchangeContext(CallContext):
    """Terminal link in the context promotion chain.

    Bundles the :class:`Request` / :class:`Response` pair with the call's
    :class:`InstrumentationContext` so post-exchange observers (metrics, log
    sinks, span finalizers) can correlate every artifact of a completed call.
    """

    instrumentation_context: InstrumentationContext
    request: "Request"
    response: "Response"


__all__ = ["ExchangeContext"]
