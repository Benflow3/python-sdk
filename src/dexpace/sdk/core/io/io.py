"""Holds the :class:`IoProvider` installed by the consuming application."""
from __future__ import annotations

import threading
from typing import Callable, Optional, TypeVar

from .io_provider import IoProvider

T = TypeVar("T")


class _Io:
    """Process-wide :class:`IoProvider` registry.

    Reads of :attr:`provider` are unsynchronized — the GIL guarantees that the
    field read is atomic, and there is no need to revalidate the installed
    instance on every call. Writes go through a :class:`threading.Lock` so two
    concurrent installs cannot race past the conflict check.
    """

    __slots__ = ("_lock", "_installed")

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._installed: Optional[IoProvider] = None

    @property
    def provider(self) -> IoProvider:
        """Return the installed provider, or raise if none was installed."""
        installed = self._installed
        if installed is None:
            raise RuntimeError(
                "No IoProvider installed. Call Io.install_provider(...) at "
                "application startup (e.g. Io.install_provider(DefaultIoProvider()))"
            )
        return installed

    def install_provider(self, provider: IoProvider) -> None:
        """Install ``provider`` as the global I/O provider.

        Idempotent when called with the same instance. Installing a different
        provider when one is already installed raises :class:`RuntimeError`; use
        :meth:`with_provider` for scoped overrides instead of double-installing.
        """
        with self._lock:
            existing = self._installed
            if existing is not None and existing is not provider:
                existing_name = f"{type(existing).__module__}.{type(existing).__name__}"
                provider_name = f"{type(provider).__module__}.{type(provider).__name__}"
                raise RuntimeError(
                    f"An IoProvider ({existing_name}) is already installed; "
                    f"refusing to overwrite with a different provider ({provider_name}). "
                    f"Use Io.with_provider(...) for scoped overrides."
                )
            self._installed = provider

    def with_provider(self, provider: IoProvider, block: Callable[[], T]) -> T:
        """Run ``block`` with ``provider`` installed, then restore the previous one.

        Intended for tests; not designed for concurrent use — the installed
        provider is a single process-wide field, so parallel scopes across
        threads will overwrite each other's overrides.
        """
        with self._lock:
            previous = self._installed
            self._installed = provider
        try:
            return block()
        finally:
            with self._lock:
                self._installed = previous


#: Process-wide :class:`IoProvider` registry. Install once at startup.
Io = _Io()

__all__ = ["Io"]
