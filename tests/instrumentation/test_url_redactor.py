"""Tests for ``UrlRedactor``."""

from __future__ import annotations

from dexpace.sdk.core.http.common import Url
from dexpace.sdk.core.instrumentation import UrlRedactor


def test_strips_userinfo() -> None:
    redactor = UrlRedactor()
    redacted = redactor.redact("https://user:secret@api.example.com/path")
    assert "user" not in redacted
    assert "secret" not in redacted
    assert "api.example.com" in redacted


def test_allowlisted_query_unredacted() -> None:
    redactor = UrlRedactor()
    redacted = redactor.redact("https://api.example.com/v1?api-version=1.0&token=hunter2")
    assert "api-version=1.0" in redacted
    assert "token=REDACTED" in redacted
    assert "hunter2" not in redacted


def test_accepts_parsed_url() -> None:
    redactor = UrlRedactor()
    parsed = Url.parse("https://api.example.com/v1?secret=value")
    out = redactor.redact(parsed)
    assert "secret=REDACTED" in out


def test_unparseable_input_returns_input_unchanged() -> None:
    redactor = UrlRedactor()
    assert redactor.redact("not a url") == "not a url"


def test_custom_allowlist() -> None:
    redactor = UrlRedactor(allowed_query_keys={"plain"})
    out = redactor.redact("https://example.com/?plain=ok&api-version=1.0")
    assert "plain=ok" in out
    # api-version was not in the custom allow-list; should be redacted.
    assert "api-version=REDACTED" in out


def test_multiple_values_per_key() -> None:
    redactor = UrlRedactor(allowed_query_keys=set())
    out = redactor.redact("https://example.com/?a=1&a=2")
    assert out.count("a=REDACTED") == 2


def test_redactor_redacts_fragment_by_default() -> None:
    redactor = UrlRedactor()
    out = redactor.redact("https://x/api?api-version=1#token=abc")
    assert "abc" not in out


def test_redactor_redacts_path_when_enabled() -> None:
    redactor = UrlRedactor(redact_path=True)
    out = redactor.redact("https://x/users/123/secret/abc")
    assert "abc" not in out and "123" not in out


def test_fragment_preserved_when_redact_fragment_false() -> None:
    redactor = UrlRedactor(redact_fragment=False)
    out = redactor.redact("https://x/api?api-version=1#token=abc")
    assert "token=abc" in out


def test_path_preserved_by_default() -> None:
    redactor = UrlRedactor()
    out = redactor.redact("https://x/users/123/secret/abc")
    assert "/users/123/secret/abc" in out
