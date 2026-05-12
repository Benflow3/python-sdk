"""Tests for ``MultipartRequestBody``."""
from __future__ import annotations

import pytest

from dexpace.sdk.core.http.common import MediaType
from dexpace.sdk.core.http.request import (
    MultipartField,
    MultipartRequestBody,
    RequestBody,
)


def _drain(body: RequestBody) -> bytes:
    return b"".join(body.iter_bytes())


def test_simple_field() -> None:
    body = MultipartRequestBody([MultipartField(name="key", value="value")])
    drained = _drain(body)
    assert b'name="key"' in drained
    assert b"value" in drained


def test_filename_in_disposition() -> None:
    body = MultipartRequestBody(
        [
            MultipartField(
                name="file",
                value=b"<<bytes>>",
                filename="upload.bin",
                media_type=MediaType.of("application", "octet-stream"),
            )
        ]
    )
    drained = _drain(body)
    assert b'filename="upload.bin"' in drained
    assert b"Content-Type: application/octet-stream" in drained


def test_media_type_includes_boundary() -> None:
    body = MultipartRequestBody([MultipartField(name="a", value="b")])
    media = body.media_type()
    assert media is not None and media.full_type == "multipart/form-data"
    assert dict(media.parameters)["boundary"] == body.boundary


def test_replayable() -> None:
    body = MultipartRequestBody([MultipartField(name="a", value="b")])
    assert body.is_replayable()
    assert _drain(body) == _drain(body)


def test_factory() -> None:
    body = RequestBody.from_multipart(  # type: ignore[attr-defined]
        [MultipartField(name="a", value="b")]
    )
    assert isinstance(body, MultipartRequestBody)


def test_empty_fields_raises() -> None:
    with pytest.raises(ValueError):
        MultipartRequestBody([])


def test_explicit_boundary() -> None:
    body = MultipartRequestBody(
        [MultipartField(name="a", value="b")],
        boundary="my-boundary",
    )
    drained = _drain(body)
    assert b"--my-boundary" in drained
    assert b"--my-boundary--" in drained


def test_quotes_in_name_escaped() -> None:
    body = MultipartRequestBody(
        [MultipartField(name='odd"name', value="x")],
    )
    drained = _drain(body)
    assert b'\\"name' in drained
