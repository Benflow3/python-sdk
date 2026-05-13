"""Terminal link in the context promotion chain."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from ...instrumentation import InstrumentationContext
from .call_context import CallContext

if TYPE_CHECKING:
    from ..request.request import Request
    from ..response.async_response import AsyncResponse
    from ..response.response import Response


@dataclass(frozen=True)
class ExchangeContext(CallContext):
    """Terminal link in the context promotion chain.

    Bundles the ``Request`` / ``Response`` pair with the call's
    ``InstrumentationContext`` so post-exchange observers (metrics, log
    sinks, span finalisers) can correlate every artifact of a completed
    call. The ``response`` field accepts either a sync ``Response`` or
    an ``AsyncResponse`` — the immutable snapshot is recorded regardless
    of which pipeline produced it.

    Note: ``slots=True`` is intentionally omitted here. Mixing a slotted
    dataclass into a non-slotted ABC base (``CallContext``) produces a
    layout that still allocates ``__dict__``, so the slots flag would not
    save memory and would only add fragility to the inheritance.
    """

    instrumentation_context: InstrumentationContext
    request: Request
    response: Response | AsyncResponse


__all__ = ["ExchangeContext"]
