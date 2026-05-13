"""Status-code → exception-type mapping helper."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from .http import HttpResponseError

if TYPE_CHECKING:
    from ..http.response.response import Response


def map_error(
    status_code: int,
    response: Response,
    error_map: Mapping[int, type[HttpResponseError]] | None,
) -> None:
    """Raise the mapped exception for ``status_code`` if one is registered.

    Pass any ``Mapping[int, type[HttpResponseError]]`` (a plain ``dict``
    is the typical choice).

    Args:
        status_code: HTTP status to look up.
        response: The response that triggered the error; forwarded to the
            raised exception's constructor.
        error_map: Caller-supplied mapping; ``None`` is a no-op.

    Raises:
        HttpResponseError: When ``status_code`` is in ``error_map``. The
            specific subclass is taken from the map.
    """
    if not error_map:
        return
    error_type = error_map.get(status_code)
    if error_type is None:
        return
    raise error_type(response=response)


__all__ = ["map_error"]
