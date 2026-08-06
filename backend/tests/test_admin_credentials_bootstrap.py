import pytest

from app.application.administrativo.commands.bootstrap_credential import (
    InvalidCredentialInput,
    validate_password_policy,
)


@pytest.mark.parametrize("size", [12, 1024])
def test_password_policy_accepts_limits_and_preserves_secret(size):
    secret = " ü " + "x" * (size - 3)
    assert len(secret) == size
    assert (
        validate_password_policy(secret, codigo_usuario="user", login="login") is None
    )


@pytest.mark.parametrize("secret", ["", "   ", "x" * 11, "x" * 1025, "user", "login"])
def test_password_policy_rejects_invalid_values(secret):
    with pytest.raises(InvalidCredentialInput):
        validate_password_policy(secret, codigo_usuario="user", login="login")
