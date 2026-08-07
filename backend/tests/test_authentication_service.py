from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.application.administrativo.authentication import (
    AuthenticationService,
    InvalidCredentials,
)


def _credential(expires_at):
    return {
        "id_credencial_usuario": 9,
        "id_usuario": 7,
        "tipo_credencial": "PASSWORD",
        "hash_credencial": "$argon2id$test-phc",
        "algoritmo_hash": "argon2id:v1",
        "estado_credencial": "ACTIVA",
        "es_credencial_principal": True,
        "fecha_activacion": None,
        "fecha_vencimiento": expires_at,
        "bloqueo_hasta": None,
        "requiere_reset": False,
        "obliga_rotacion": False,
        "deleted_at": None,
    }


def test_revalidation_uses_later_wall_clock_and_rejects_expired_credential(
    monkeypatch,
):
    before_verify = datetime(2026, 8, 7, 10, 0, 0)
    after_verify = before_verify + timedelta(seconds=2)
    credential = _credential(before_verify + timedelta(seconds=1))
    user = {
        "id_usuario": 7,
        "estado_usuario": "ACTIVO",
        "fecha_baja": None,
        "deleted_at": None,
    }
    auth_repo = MagicMock()
    auth_repo.get_user_by_login_exact.return_value = user
    auth_repo.list_password_credentials.return_value = [credential]
    auth_repo.get_user_for_update.return_value = user
    auth_repo.get_credential_for_update.return_value = credential
    session_repo = MagicMock()
    session_repo.get_wall_clock_timestamp.side_effect = [before_verify, after_verify]

    monkeypatch.setattr(
        "app.application.administrativo.authentication.AuthenticationRepository",
        lambda _db: auth_repo,
    )
    monkeypatch.setattr(
        "app.application.administrativo.authentication.SesionUsuarioRepository",
        lambda _db: session_repo,
    )
    monkeypatch.setattr(
        "app.application.administrativo.authentication.resolve_local_installation",
        lambda *_args: SimpleNamespace(id_instalacion=1),
    )
    monkeypatch.setattr(
        "app.application.administrativo.authentication.verify_password",
        lambda *_args: True,
    )
    db = MagicMock()

    with pytest.raises(InvalidCredentials):
        AuthenticationService(db, object()).login("exact.login", "secret")

    assert session_repo.get_wall_clock_timestamp.call_count == 2
    auth_repo.get_user_for_update.assert_called_once_with(7)
    auth_repo.get_credential_for_update.assert_called_once_with(9)
    session_repo.insert.assert_not_called()
    db.rollback.assert_called_once()
