# ruff: noqa: E402
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


from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from sqlalchemy.exc import IntegrityError

from app.application.administrativo.commands.bootstrap_credential import (
    BootstrapCredentialCommand,
    CredentialBootstrapPreview,
    CredentialBootstrapResult,
    CredentialBootstrapTechnicalError,
    CredentialIdempotencyConflict,
    CredentialStateConflict,
    _translate_integrity_error,
)


def test_revalidates_policy_against_locked_user_before_credentials(monkeypatch):
    session = MagicMock()
    session.__enter__.return_value = session
    session.begin.return_value.__enter__.return_value = None
    locked = {
        "id_usuario": 7,
        "codigo_usuario": "USER",
        "login": "NuevaClaveSegura123",
        "estado_usuario": "ACTIVO",
        "deleted_at": None,
        "fecha_baja": None,
    }
    user_repo = MagicMock()
    user_repo.get_by_codigo_exact_for_update.return_value = locked
    credential_repo = MagicMock()
    monkeypatch.setattr(
        "app.application.administrativo.commands.bootstrap_credential.hash_password",
        lambda value: "unused-phc",
    )
    monkeypatch.setattr(
        "app.application.administrativo.commands.bootstrap_credential.resolve_local_installation",
        lambda *a: SimpleNamespace(
            codigo_instalacion="I", nombre_instalacion="Inst", id_instalacion=1
        ),
    )
    monkeypatch.setattr(
        "app.application.administrativo.commands.bootstrap_credential.UsuarioSistemaRepository",
        lambda *_: user_repo,
    )
    monkeypatch.setattr(
        "app.application.administrativo.commands.bootstrap_credential.CredencialUsuarioRepository",
        lambda *_: credential_repo,
    )
    preview = CredentialBootstrapPreview(7, "USER", "login-anterior", "I", "Inst")
    with pytest.raises(InvalidCredentialInput):
        BootstrapCredentialCommand(lambda: session, object()).execute(
            "init", preview, locked["login"], uuid4()
        )
    credential_repo.find_created_by_op_id.assert_not_called()
    credential_repo.list_password_credentials_for_update.assert_not_called()
    credential_repo.revoke_password.assert_not_called()
    credential_repo.insert_active_password.assert_not_called()


def _integrity(constraint):
    original = SimpleNamespace(diag=SimpleNamespace(constraint_name=constraint))
    return IntegrityError("sanitized-test", {}, original)


@pytest.mark.parametrize(
    "constraint",
    ["ux_credencial_usuario_password_activa", "ux_credencial_usuario_principal_activa"],
)
def test_active_integrity_constraints_are_state_conflicts(constraint):
    assert isinstance(
        _translate_integrity_error(_integrity(constraint)), CredentialStateConflict
    )


def test_op_id_integrity_constraint_is_idempotency_conflict():
    error = _translate_integrity_error(_integrity("ux_credencial_usuario_op_id_alta"))
    assert isinstance(error, CredentialIdempotencyConflict)
    assert "constraint" not in str(error).lower()


def test_unknown_integrity_constraint_is_technical():
    assert isinstance(
        _translate_integrity_error(_integrity("unknown")),
        CredentialBootstrapTechnicalError,
    )


def test_public_results_do_not_expose_hash():
    assert "hash" not in CredentialBootstrapPreview.__dataclass_fields__
    assert "hash" not in CredentialBootstrapResult.__dataclass_fields__


def test_invalid_operation_is_rejected_before_hashing(monkeypatch):
    called = MagicMock()
    monkeypatch.setattr(
        "app.application.administrativo.commands.bootstrap_credential.hash_password",
        called,
    )
    preview = CredentialBootstrapPreview(1, "USER", "login", "I", "Inst")
    with pytest.raises(InvalidCredentialInput):
        BootstrapCredentialCommand(MagicMock(), object()).execute(
            "delete", preview, "Valid-secret-123", uuid4()
        )
    called.assert_not_called()
