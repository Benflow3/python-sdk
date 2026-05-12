"""``Policy`` ABC — pipeline steps that wrap the downstream chain."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..http.request.request import Request
    from ..http.response.response import Response
    from .context import PipelineContext


class Policy(ABC):
    """Pipeline step that can decide whether (and how) to invoke ``self.next``.

    Use ``Policy`` when a step needs to wrap the downstream chain — for
    retry, authentication challenges, span lifecycles, etc. Stateless,
    transport-agnostic transforms should be a ``PipelineStep`` Protocol
    instead; the pipeline runner wraps those in an internal SansIO runner
    that calls ``self.next`` after the transform.

    Modelled on Azure's ``corehttp.runtime.policies.HTTPPolicy``: ``.next``
    is a per-instance attribute wired up by the pipeline constructor; the
    terminal node is a transport runner. Subclasses implement ``send``.
    """

    next: Policy

    @abstractmethod
    def send(self, request: Request, ctx: PipelineContext) -> Response:
        """Process ``request`` and return its response.

        Implementations typically mutate the request, call
        ``self.next.send(request, ctx)``, and post-process the response (or
        loop, in the retry case).

        Args:
            request: The HTTP request to process.
            ctx: Mutable pipeline state for this exchange.

        Returns:
            The response from the downstream chain.
        """


__all__ = ["Policy"]
