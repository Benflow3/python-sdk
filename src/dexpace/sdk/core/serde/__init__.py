"""Format-agnostic serialization / deserialization contracts.

Concrete implementations live outside ``core`` — ``core`` deliberately ships
no embedded serializer. Pick an adapter (or write your own) and inject it
wherever a :class:`Serde` is required.
"""
from __future__ import annotations

from .serde import Deserializer, Serde, Serializer

__all__ = ["Deserializer", "Serde", "Serializer"]
