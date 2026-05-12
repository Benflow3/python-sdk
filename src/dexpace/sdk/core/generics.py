"""Generic builder contract used by every SDK builder.

The SDK's public models use the immutable-data + private-constructor + mutable-builder
pattern. Builders that participate in generic pipeline composition implement this
interface so callers can write helpers that accept any builder.
"""
from __future__ import annotations

from typing import Generic, TypeVar

try:  # pragma: no cover - stdlib feature detection only
    from typing import Protocol, runtime_checkable
except ImportError:  # pragma: no cover - Protocol exists from 3.8 onward
    from typing_extensions import Protocol, runtime_checkable  # type: ignore[no-redef]

T_co = TypeVar("T_co", covariant=True)


@runtime_checkable
class Builder(Protocol, Generic[T_co]):
    """Materialize an immutable target value from the builder's current state."""

    def build(self) -> T_co: ...


__all__ = ["Builder"]
