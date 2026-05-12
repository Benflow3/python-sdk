"""Transport SPI: the seam between SDK models and a concrete HTTP transport."""
from __future__ import annotations

from .http_client import HttpClient

__all__ = ["HttpClient"]
