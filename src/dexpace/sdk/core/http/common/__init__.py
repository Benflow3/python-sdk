"""Shared HTTP value objects: headers, media types, protocol versions."""
from __future__ import annotations

from . import common_media_types
from .headers import Headers
from .media_type import MediaType
from .protocol import Protocol

__all__ = ["Headers", "MediaType", "Protocol", "common_media_types"]
