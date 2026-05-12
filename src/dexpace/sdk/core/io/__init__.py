"""I/O contracts: ``Source``, ``Sink``, ``Buffer``, ``IoProvider``, ``Io``.

This subpackage exposes contracts only; install a concrete provider once at startup::

    from dexpace.sdk.core.io import Io
    from dexpace.sdk.core.io.default import DefaultIoProvider

    Io.install_provider(DefaultIoProvider())
"""
from __future__ import annotations

from .buffer import Buffer
from .buffered_sink import BufferedSink
from .buffered_source import BufferedSource
from .io import Io
from .io_provider import IoProvider
from .sink import Sink
from .source import Source
from .tee_sink import TeeSink

__all__ = [
    "Buffer",
    "BufferedSink",
    "BufferedSource",
    "Io",
    "IoProvider",
    "Sink",
    "Source",
    "TeeSink",
]
