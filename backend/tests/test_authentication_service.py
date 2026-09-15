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
        "app.application.administrativo.authentication.verify_password",
        lambda *_args: True,
    )
    db = MagicMock()

    with pytest.raises(InvalidCredentials):
        AuthenticationService(db).login("exact.login", "secret")

    assert session_repo.get_wall_clock_timestamp.call_count == 2
    auth_repo.get_user_for_update.assert_called_once_with(7)
    auth_repo.get_credential_for_update.assert_called_once_with(9)
    session_repo.insert.assert_not_called()
    db.rollback.assert_called_once()


@pytest.fixture
def central_auth(monkeypatch):
    from uuid import uuid4
    now = datetime(2026, 9, 14, 12)
    user = {"id_usuario": 7, "estado_usuario": "ACTIVO", "fecha_baja": None, "deleted_at": None}
    credential = _credential(None)
    auth, sessions, db = MagicMock(), MagicMock(), MagicMock()
    auth.get_user_by_login_exact.return_value = user
    auth.list_password_credentials.return_value = [credential]
    auth.get_user_for_update.return_value = user
    auth.get_credential_for_update.return_value = credential
    sessions.get_wall_clock_timestamp.return_value = now
    sessions.insert.return_value = uuid4()
    monkeypatch.setattr("app.application.administrativo.authentication.AuthenticationRepository", lambda _: auth)
    monkeypatch.setattr("app.application.administrativo.authentication.SesionUsuarioRepository", lambda _: sessions)
    verify = MagicMock(return_value=True)
    monkeypatch.setattr("app.application.administrativo.authentication.verify_password", verify)
    monkeypatch.setattr("app.application.common.local_installation.resolve_local_installation", MagicMock(side_effect=AssertionError("legacy resolver called")))
    monkeypatch.delenv("LOCAL_INSTALLATION_CODE", raising=False)
    return AuthenticationService(db), db, auth, sessions, verify


def test_login_central_digest_ttl_without_settings(central_auth):
    from app.application.administrativo.authentication import digest_access_token
    service, db, _, sessions, _ = central_auth
    result = service.login("login", "password")
    args = sessions.insert.call_args.kwargs
    assert "id_instalacion_origen" not in args
    assert args["token_digest"] == digest_access_token(result.access_token)
    assert result.access_token not in args.values()
    assert args["expires_at"] - args["started_at"] == timedelta(hours=8)
    db.commit.assert_called_once()


@pytest.mark.parametrize("change", ["missing", "inactive", "baja", "deleted", "credential"])
def test_invalid_user_or_credential_uses_dummy_and_rolls_back(central_auth, change):
    from app.application.administrativo.authentication import AUTHENTICATION_DUMMY_ARGON2ID_PHC
    service, db, auth, sessions, verify = central_auth
    if change == "missing":
        auth.get_user_by_login_exact.return_value = None
    elif change == "credential":
        auth.list_password_credentials.return_value[0]["requiere_reset"] = True
    else:
        key = {"inactive": "estado_usuario", "baja": "fecha_baja", "deleted": "deleted_at"}[change]
        auth.get_user_by_login_exact.return_value[key] = "INACTIVO" if change == "inactive" else datetime(2026, 1, 1)
    with pytest.raises(InvalidCredentials):
        service.login("login", "secret")
    verify.assert_called_once_with("secret", AUTHENTICATION_DUMMY_ARGON2ID_PHC)
    sessions.insert.assert_not_called()
    db.rollback.assert_called_once()


def test_inconsistent_credentials_fail_closed(central_auth):
    from app.application.administrativo.authentication import AuthenticationTechnicalError
    service, db, auth, sessions, _ = central_auth
    auth.list_password_credentials.return_value *= 2
    with pytest.raises(AuthenticationTechnicalError):
        service.login("login", "secret")
    sessions.insert.assert_not_called()
    db.rollback.assert_called_once()


@pytest.mark.parametrize("collisions,success", [(1, True), (3, False)])
def test_token_collision_retry_and_exhaustion(central_auth, collisions, success):
    from sqlalchemy.exc import IntegrityError
    from uuid import uuid4
    from app.application.administrativo.authentication import AuthenticationTechnicalError
    service, db, _, sessions, _ = central_auth
    error = IntegrityError("hidden SQL", {}, SimpleNamespace(diag=SimpleNamespace(constraint_name="uq_sesion_token")))
    sessions.insert.side_effect = [error] * collisions + [uuid4()]
    if success:
        service.login("login", "secret")
        db.commit.assert_called_once()
    else:
        with pytest.raises(AuthenticationTechnicalError):
            service.login("login", "secret")
        db.rollback.assert_called_once()
    assert sessions.insert.call_count == min(collisions + 1, 3)


def test_commit_failure_sanitized_and_rollback(central_auth):
    from app.application.administrativo.authentication import AuthenticationTechnicalError
    service, db, *_ = central_auth
    db.commit.side_effect = RuntimeError("DSN secret")
    with pytest.raises(AuthenticationTechnicalError) as exc:
        service.login("login", "secret")
    assert "secret" not in str(exc.value)
    db.rollback.assert_called_once()
