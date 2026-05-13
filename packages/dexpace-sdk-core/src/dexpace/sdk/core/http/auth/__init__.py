"""Credential types and built-in authentication policies."""

from __future__ import annotations

from .access_token import AccessTokenInfo, TokenRequestOptions
from .challenge import AuthenticateChallenge, parse_challenges
from .challenge_handler import (
    BasicChallengeHandler,
    ChallengeHandler,
    CompositeChallengeHandler,
)
from .credentials import (
    AsyncTokenCredential,
    BasicAuthCredential,
    KeyCredential,
    NamedKeyCredential,
    TokenCredential,
)
from .digest import DigestAlgorithm, DigestChallengeHandler
from .policies import (
    AsyncBearerTokenPolicy,
    BasicAuthPolicy,
    BearerTokenPolicy,
    KeyCredentialPolicy,
)
from .token_cache import InMemoryTokenCache, TokenCache

__all__ = [
    "AccessTokenInfo",
    "AsyncBearerTokenPolicy",
    "AsyncTokenCredential",
    "AuthenticateChallenge",
    "BasicAuthCredential",
    "BasicAuthPolicy",
    "BasicChallengeHandler",
    "BearerTokenPolicy",
    "ChallengeHandler",
    "CompositeChallengeHandler",
    "DigestAlgorithm",
    "DigestChallengeHandler",
    "InMemoryTokenCache",
    "KeyCredential",
    "KeyCredentialPolicy",
    "NamedKeyCredential",
    "TokenCache",
    "TokenCredential",
    "TokenRequestOptions",
    "parse_challenges",
]
