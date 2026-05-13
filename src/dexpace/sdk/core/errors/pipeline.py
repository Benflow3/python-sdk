"""Pipeline-flow exceptions."""

from __future__ import annotations

from .base import SdkError


class PipelineAbortedError(SdkError):
    """A pipeline step short-circuited the chain.

    Raised when a SansIO step returns ``None`` from its callable signature
    (indicating "do not forward to the next step"). The pipeline runner
    converts that signal into this exception so callers can distinguish a
    deliberate abort from a transport error.
    """


__all__ = ["PipelineAbortedError"]
