"""Async twin of ``Policy``."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..http.request.request import Request
    from ..http.response.async_response import AsyncResponse
    from .context import PipelineContext


class AsyncPolicy(ABC):
    """Async pipeline step that can decide whether (and how) to invoke ``self.next``.

    Mirrors ``Policy`` but with ``async def send`` and ``AsyncResponse``
    semantics. ``.next`` is wired up by ``AsyncPipeline`` at construction.
    """

    next: AsyncPolicy

    @abstractmethod
    async def send(self, request: Request, ctx: PipelineContext) -> AsyncResponse:
        """Process ``request`` and return its async response."""


__all__ = ["AsyncPolicy"]
