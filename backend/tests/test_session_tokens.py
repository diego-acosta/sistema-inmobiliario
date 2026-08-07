import re

from app.application.administrativo.authentication import (
    TOKEN_RANDOM_BYTES,
    digest_access_token,
    generate_access_token,
    parse_bearer_header,
    InvalidSession,
)
import pytest


def test_token_uses_32_random_bytes_and_digest_is_lowercase_hex(monkeypatch):
    calls = []
    monkeypatch.setattr("app.application.administrativo.authentication.secrets.token_urlsafe", lambda size: calls.append(size) or "opaque-token")
    token = generate_access_token()
    assert token == "opaque-token"
    assert calls == [TOKEN_RANDOM_BYTES] == [32]
    assert digest_access_token(token) == digest_access_token(token)
    assert re.fullmatch(r"[0-9a-f]{64}", digest_access_token(token))


def test_generated_tokens_are_different():
    assert generate_access_token() != generate_access_token()


@pytest.mark.parametrize("header", [None, "", "Basic abc", "Bearer", "Bearer ", "Bearer a b", "bearer abc"])
def test_bearer_parser_rejects_missing_or_malformed(header):
    with pytest.raises(InvalidSession):
        parse_bearer_header(header)


def test_bearer_parser_accepts_standard_form():
    assert parse_bearer_header("Bearer opaque") == "opaque"
