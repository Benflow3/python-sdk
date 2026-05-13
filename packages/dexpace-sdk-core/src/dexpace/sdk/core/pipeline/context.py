"""Mutable per-request scratchpad carried through the pipeline.

The promotion-chain contexts (``DispatchContext`` / ``RequestContext`` /
``ExchangeContext``) are immutable telemetry snapshots. A pipeline needs a
*mutable* container as well — for policy bookkeeping (retry counters, auth
challenge state) and caller-supplied per-call overrides. That container is
``PipelineContext``.

Modelled on Azure's ``corehttp.runtime.pipeline.PipelineContext`` but without
the dict-subclass gymnastics: ``options`` and ``data`` are plain dicts on a
slotted dataclass, with a typed ``call`` field linking back to the immutable
telemetry context.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..http.context.request_context import RequestContext


@dataclass(slots=True)
class PipelineContext:
    """Mutable state carried alongside the request through the pipeline.

    Policies read and write ``options`` (caller-supplied per-call kwargs) and
    ``data`` (their own bookkeeping); both are plain dicts. ``call`` is the
    immutable promotion-chain context for trace correlation.

    Attributes:
        call: The active immutable promotion-chain context.
        options: Caller-supplied per-call overrides. Forwarded into
            ``Pipeline.run(**kwargs)``.
        data: Per-policy scratchpad (e.g. ``data["retry_count"]``).
    """

    call: RequestContext
    options: dict[str, Any] = field(default_factory=dict)
    data: dict[str, Any] = field(default_factory=dict)


__all__ = ["PipelineContext"]
