# Copyright (c) 2026 dexpace and Omar Aljarrah.
# Licensed under the MIT License. See LICENSE.md in the repository root for details.

"""Tests for the ``WWW-Authenticate`` challenge parser."""

from __future__ import annotations

from dexpace.sdk.core.http.auth import AuthenticateChallenge, parse_challenges


class TestParseChallenges:
    def test_parse_single_basic_challenge(self) -> None:
        challenges = parse_challenges('Basic realm="example"')
        assert len(challenges) == 1
        assert challenges[0].scheme == "Basic"
        assert challenges[0].parameters == {"realm": "example"}

    def test_parse_multiple_challenges(self) -> None:
        challenges = parse_challenges('Basic realm="r1", Digest realm="r2", qop="auth"')
        assert len(challenges) == 2
        assert challenges[0].scheme == "Basic"
        assert challenges[0].parameters == {"realm": "r1"}
        assert challenges[1].scheme == "Digest"
        assert challenges[1].parameters == {"realm": "r2", "qop": "auth"}

    def test_parse_quoted_pair(self) -> None:
        # quoted-pair: backslash followed by a char decodes to the bare char
        challenges = parse_challenges(r'Digest realm="he said \"hi\"", nonce="a\\b"')
        assert len(challenges) == 1
        assert challenges[0].parameters["realm"] == 'he said "hi"'
        assert challenges[0].parameters["nonce"] == "a\\b"

    def test_parse_case_insensitive_param_names(self) -> None:
        challenges = parse_challenges('Digest REALM="x", QoP="auth"')
        assert challenges[0].parameters["realm"] == "x"
        assert challenges[0].parameters["qop"] == "auth"

    def test_parse_malformed_skips_gracefully(self) -> None:
        # Garbage between two valid challenges should not break parsing.
        challenges = parse_challenges('Basic realm="ok", =badtoken, Digest realm="d"')
        schemes = [c.scheme for c in challenges]
        assert "Basic" in schemes
        assert "Digest" in schemes

    def test_parse_empty_returns_empty(self) -> None:
        assert parse_challenges("") == []
        assert parse_challenges("   ") == []

    def test_parse_unquoted_token_value(self) -> None:
        challenges = parse_challenges("Digest algorithm=SHA-256, qop=auth")
        assert challenges[0].parameters == {"algorithm": "SHA-256", "qop": "auth"}

    def test_parse_comma_inside_quoted_string(self) -> None:
        challenges = parse_challenges('Digest realm="a, b", qop="auth"')
        assert len(challenges) == 1
        assert challenges[0].parameters["realm"] == "a, b"
        assert challenges[0].parameters["qop"] == "auth"

    def test_authenticate_challenge_is_frozen(self) -> None:
        c = AuthenticateChallenge(scheme="Basic", parameters={"realm": "x"})
        import dataclasses

        try:
            c.scheme = "Digest"  # type: ignore[misc]
        except dataclasses.FrozenInstanceError:
            pass
        else:  # pragma: no cover
            raise AssertionError("expected FrozenInstanceError")
