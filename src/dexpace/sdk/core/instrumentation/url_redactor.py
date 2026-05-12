"""Redact sensitive components from URLs before log emission."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Final

from ..http.common.url import QueryParams, Url

#: Default allow-list of query parameters that pass through unredacted.
#: Matches the dexpace/java-sdk default and is intentionally conservative.
DEFAULT_QUERY_ALLOWLIST: Final[frozenset[str]] = frozenset(
    {
        "api-version",
        "comp",
        "encoding",
        "fields",
        "filter",
        "include",
        "limit",
        "offset",
        "order",
        "orderby",
        "page",
        "page_size",
        "search",
        "select",
        "skip",
        "sort",
        "top",
        "view",
    }
)

_REDACTED: Final[str] = "REDACTED"


class UrlRedactor:
    """Strip userinfo and non-allowlisted query parameters from a URL.

    Used by logging policies to emit URLs without leaking credentials,
    tokens, or PII embedded in query strings. The redactor returns a
    ``str`` (not a ``Url``) so callers can format it directly.

    Attributes:
        allowed_query_keys: Query parameter names emitted unredacted.
    """

    __slots__ = ("allowed_query_keys",)

    def __init__(self, allowed_query_keys: Iterable[str] = DEFAULT_QUERY_ALLOWLIST) -> None:
        self.allowed_query_keys = frozenset(allowed_query_keys)

    def redact(self, url: str | Url) -> str:
        """Return a redacted wire-form string for ``url``.

        Args:
            url: Either a parsed ``Url`` or a wire-form string. Strings are
                parsed via ``Url.parse``; parse failures fall through to
                returning the input unchanged (so logging never silently
                drops a URL because it's malformed).

        Returns:
            A wire-form URL with userinfo stripped and non-allowlisted
            query values replaced by ``REDACTED``.
        """
        parsed = url if isinstance(url, Url) else _safe_parse(url)
        if parsed is None:
            return str(url)
        return str(self._redact_parsed(parsed))

    def _redact_parsed(self, parsed: Url) -> Url:
        redacted_query = QueryParams(
            [
                (key, value if key in self.allowed_query_keys else _REDACTED)
                for key, values in parsed.query.items()
                for value in values
            ]
        )
        return Url(
            scheme=parsed.scheme,
            host=parsed.host,
            path=parsed.path,
            port=parsed.port,
            query=redacted_query,
            fragment=parsed.fragment,
            userinfo=None,
        )


def _safe_parse(raw: str) -> Url | None:
    try:
        return Url.parse(raw)
    except ValueError:
        return None


__all__ = ["DEFAULT_QUERY_ALLOWLIST", "UrlRedactor"]
