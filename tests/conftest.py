"""Shared pytest fixtures."""
from __future__ import annotations

from collections.abc import Iterator

import pytest

from dexpace.sdk.core.http.context import ContextStore


@pytest.fixture(autouse=True)
def _clean_context_store() -> Iterator[None]:
    """Reset the process-wide ``ContextStore`` around every test.

    Multiple tests across the suite write into ``ContextStore`` through the
    promotion chain; leaving entries in place between tests turns
    ``ContextStore.put`` collision checks into flaky failures depending on
    test ordering.
    """
    yield
    # Clear by iterating the internal dict — ContextStore exposes ``remove``
    # but no ``clear``. Touching the private attribute here is acceptable
    # for tests; production code uses the proper API.
    ContextStore._contexts.clear()
