"""``PipelineStep`` Protocol and shape-specialised aliases.

A ``PipelineStep`` is a SansIO transform: stateless, transport-agnostic,
``(value, ctx) -> value``. The pipeline runner wraps these in internal
``_SansIO*Runner`` policies so they participate in the linked-list chain
without each step needing to know about ``.next``.

For steps that need to wrap the downstream chain (retry, auth challenges,
span lifecycles), implement ``pipeline.Policy`` directly instead.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ...http.context import CallContext
    from ...http.request import Request
    from ...http.response import Response


@runtime_checkable
class PipelineStep[T_in, T_out](Protocol):
    """A single executable SansIO step in a pipeline workflow.

    Steps compose into chains: each takes the upstream's output plus the
    current promotion-chain ``CallContext`` (``DispatchContext``,
    ``RequestContext``, or ``ExchangeContext`` depending on tier) and emits
    the next stage's input. Returning ``None`` short-circuits the chain
    (the pipeline raises ``PipelineAbortedError``).

    Implementations can be classes, lambdas, or any callable with a
    matching signature — the Protocol is structural. Tag a step with a
    ``side`` attribute (``"request"`` or ``"response"``) to tell the
    pipeline runner whether to wrap it pre- or post-transport; untagged
    callables default to the request side.
    """

    def __call__(self, value: T_in, context: CallContext) -> T_out: ...


# Shape-specialised aliases. Prefer the parametrised form
# ``PipelineStep[Request, Request]`` when you need to pin both input and
# output types — these aliases exist for documentation only.
if TYPE_CHECKING:
    type RequestPipelineStep = PipelineStep[Request, Request | None]
    type ResponsePipelineStep = PipelineStep[Response, Response | None]
else:
    RequestPipelineStep = PipelineStep
    ResponsePipelineStep = PipelineStep


__all__ = [
    "PipelineStep",
    "RequestPipelineStep",
    "ResponsePipelineStep",
]
