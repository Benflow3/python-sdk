"""Multipart/form-data ``RequestBody`` builder.

Generates a deterministic-boundary ``multipart/form-data`` payload from a
list of fields. Each field has a name, value (bytes or string), optional
filename, optional media type, and optional extra headers.

The resulting body is replayable (the boundary and field bytes are
captured once at construction), so retries are safe.
"""

from __future__ import annotations

import secrets
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

from ..common.media_type import MediaType
from .request_body import RequestBody, _check_chunk_size


@dataclass(frozen=True, slots=True)
class MultipartField:
    """One part of a ``multipart/form-data`` body.

    Attributes:
        name: Form field name (mandatory).
        value: Field content as bytes or string. Strings are UTF-8 encoded.
        filename: Optional filename for file parts; included in
            ``Content-Disposition``.
        media_type: Optional content type for the part.
        headers: Optional extra headers as ``(name, value)`` pairs.
    """

    name: str
    value: bytes | str
    filename: str | None = None
    media_type: MediaType | None = None
    headers: Sequence[tuple[str, str]] = field(default_factory=tuple)


def _generate_boundary() -> str:
    """Return a random RFC 2046 multipart boundary."""
    return "----dexpace-" + secrets.token_hex(16)


def _build_part(part: MultipartField, boundary: str) -> bytes:
    """Render one part as bytes (terminating CRLF included).

    Header lines are encoded as Latin-1 (the HTTP/1.1 wire-form charset);
    non-ASCII characters in ``name`` / ``filename`` are tolerated as
    best-effort Latin-1 rather than raising. Callers needing RFC 5987
    compliance (``filename*=UTF-8''…``) should provide that header
    explicitly via ``MultipartField.headers``.
    """
    disposition = f'form-data; name="{_escape_quoted(part.name)}"'
    if part.filename is not None:
        disposition += f'; filename="{_escape_quoted(part.filename)}"'
    lines: list[bytes] = [f"--{boundary}".encode("latin-1")]
    lines.append(f"Content-Disposition: {disposition}".encode("latin-1"))
    if part.media_type is not None:
        lines.append(f"Content-Type: {part.media_type}".encode("latin-1"))
    for header_name, header_value in part.headers:
        lines.append(f"{header_name}: {header_value}".encode("latin-1"))
    lines.append(b"")
    if isinstance(part.value, str):
        lines.append(part.value.encode("utf-8"))
    else:
        lines.append(part.value)
    return b"\r\n".join(lines) + b"\r\n"


def _escape_quoted(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


class MultipartRequestBody(RequestBody):
    """Replayable ``multipart/form-data`` body.

    Build via ``RequestBody.from_multipart(fields)`` or instantiate directly.
    The boundary is generated once at construction so retries see identical
    bytes (and so loggable wrappers can capture the payload deterministically).
    """

    __slots__ = ("_boundary", "_payload")

    def __init__(
        self,
        fields: Sequence[MultipartField],
        *,
        boundary: str | None = None,
    ) -> None:
        if not fields:
            raise ValueError("at least one field is required")
        self._boundary = boundary or _generate_boundary()
        parts: list[bytes] = [_build_part(f, self._boundary) for f in fields]
        parts.append(f"--{self._boundary}--\r\n".encode("ascii"))
        self._payload = b"".join(parts)

    @property
    def boundary(self) -> str:
        return self._boundary

    def media_type(self) -> MediaType | None:
        return MediaType.of("multipart", "form-data", {"boundary": self._boundary})

    def content_length(self) -> int:
        return len(self._payload)

    def is_replayable(self) -> bool:
        return True

    def to_replayable(self) -> RequestBody:
        return self

    def iter_bytes(self, chunk_size: int = 64 * 1024) -> Iterator[bytes]:
        _check_chunk_size(chunk_size)
        view = memoryview(self._payload)
        for start in range(0, len(view), chunk_size):
            yield bytes(view[start : start + chunk_size])


def _from_multipart(
    cls: type[RequestBody],
    fields: Sequence[MultipartField],
    *,
    boundary: str | None = None,
) -> RequestBody:
    del cls
    return MultipartRequestBody(fields, boundary=boundary)


RequestBody.from_multipart = classmethod(_from_multipart)  # type: ignore[attr-defined]


__all__ = ["MultipartField", "MultipartRequestBody"]
