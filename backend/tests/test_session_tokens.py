import re

from app.application.administrativo.authentication import (
    ACCESS_TOKEN_LENGTH,
    InvalidSession,
    TOKEN_RANDOM_BYTES,
    digest_access_token,
    generate_access_token,
    parse_bearer_header,
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
    first = generate_access_token()
    second = generate_access_token()
    assert first != second
    assert len(first) == len(second) == ACCESS_TOKEN_LENGTH == 43


@pytest.mark.parametrize(
    "header",
    [
        None,
        "",
        "Basic abc",
        "Bearer",
        "Bearer ",
        "bearer abc",
        "Bearer a b",
        "Bearer a\tb",
        "Bearer a\nb",
        "Bearer a\rb",
        "Bearer abc!",
        "Bearer abc/",
        "Bearer abc+",
        "Bearer short",
        f"Bearer {'a' * 44}",
    ],
)
def test_bearer_parser_rejects_missing_or_malformed(header):
    with pytest.raises(InvalidSession):
        parse_bearer_header(header)


def test_bearer_parser_accepts_generated_token():
    token = generate_access_token()
    assert parse_bearer_header(f"Bearer {token}") == token
