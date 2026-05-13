"""Serialisation / deserialisation exceptions.

These inherit from ``ValueError`` so existing ``except ValueError`` handlers
continue to work. They also inherit from ``SdkError`` so callers that catch
the SDK root see them.
"""

from __future__ import annotations

from .base import SdkError


class SerializationError(SdkError, ValueError):
    """A value could not be serialised to the target format."""


class DeserializationError(SdkError, ValueError):
    """A payload could not be deserialised."""


__all__ = ["DeserializationError", "SerializationError"]
