"""Pre-constructed :class:`MediaType` constants for the most common content types.

Exposed as module-level constants. Reusing these avoids re-parsing the same
media-type string on hot paths.
"""
from __future__ import annotations

from .media_type import MediaType

TEXT_PLAIN = MediaType.of("text", "plain")
TEXT_HTML = MediaType.of("text", "html")
TEXT_CSS = MediaType.of("text", "css")
TEXT_JAVASCRIPT = MediaType.of("text", "javascript")
TEXT_CSV = MediaType.of("text", "csv")

APPLICATION_JSON = MediaType.of("application", "json")
APPLICATION_XML = MediaType.of("application", "xml")
APPLICATION_FORM_URLENCODED = MediaType.of("application", "x-www-form-urlencoded")
APPLICATION_OCTET_STREAM = MediaType.of("application", "octet-stream")
APPLICATION_PDF = MediaType.of("application", "pdf")
APPLICATION_ZIP = MediaType.of("application", "zip")
APPLICATION_VND_API_JSON = MediaType.of("application", "vnd.api+json")
APPLICATION_HAL_JSON = MediaType.of("application", "hal+json")
APPLICATION_PROBLEM_JSON = MediaType.of("application", "problem+json")

IMAGE_JPEG = MediaType.of("image", "jpeg")
IMAGE_PNG = MediaType.of("image", "png")
IMAGE_GIF = MediaType.of("image", "gif")
IMAGE_SVG_XML = MediaType.of("image", "svg+xml")

AUDIO_MPEG = MediaType.of("audio", "mpeg")
VIDEO_MP4 = MediaType.of("video", "mp4")

MULTIPART_FORM_DATA = MediaType.of("multipart", "form-data")
MULTIPART_BYTERANGES = MediaType.of("multipart", "byteranges")

__all__ = [
    "TEXT_PLAIN",
    "TEXT_HTML",
    "TEXT_CSS",
    "TEXT_JAVASCRIPT",
    "TEXT_CSV",
    "APPLICATION_JSON",
    "APPLICATION_XML",
    "APPLICATION_FORM_URLENCODED",
    "APPLICATION_OCTET_STREAM",
    "APPLICATION_PDF",
    "APPLICATION_ZIP",
    "APPLICATION_VND_API_JSON",
    "APPLICATION_HAL_JSON",
    "APPLICATION_PROBLEM_JSON",
    "IMAGE_JPEG",
    "IMAGE_PNG",
    "IMAGE_GIF",
    "IMAGE_SVG_XML",
    "AUDIO_MPEG",
    "VIDEO_MP4",
    "MULTIPART_FORM_DATA",
    "MULTIPART_BYTERANGES",
]
