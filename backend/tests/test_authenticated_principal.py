from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest

from app.api.authentication import get_authenticated_principal
from app.application.administrativo.authentication import (
    AuthenticatedPrincipal,
    AuthenticationService,
    InvalidSession,
    SessionTechnicalError,
)


def _projection(**overrides):
    now = datetime(2026, 8, 7, 12)
    values = {
        "uid_global": uuid4(),
        "id_usuario_sesion": 10,
        "estado_sesion": "ACTIVA",
        "fecha_hora_inicio": now - timedelta(hours=1),
        "fecha_hora_cierre": None,
        "expira_en": now + timedelta(hours=7),
        "requiere_reautenticacion": False,
        "id_instalacion_origen": 1,
        "id_sucursal_operativa": None,
        "id_usuario_usuario": 10,
        "codigo_usuario": "USR-001",
        "login": "operador",
        "estado_usuario": "ACTIVO",
        "usuario_deleted_at": None,
        "fecha_baja": None,
        "ahora": now,
    }
    values.update(overrides)
    return values


def test_authenticated_principal_is_immutable_typed_and_nullable():
    principal = AuthenticatedPrincipal(
        10, "USR-001", "operador", uuid4(), "SESION_SERVIDOR",
        datetime(2026, 8, 7, 12), 1, None,
    )
    assert isinstance(principal.id_sesion, UUID)
    assert principal.id_sucursal_operativa is None
    with pytest.raises((FrozenInstanceError, AttributeError)):
        principal.login = "otro"


def test_dependency_reuses_canonical_parser_and_service():
    db = Mock()
    request = Mock()
    request.headers.get.return_value = "Bearer token"
    expected = Mock(spec=AuthenticatedPrincipal)
    with patch("app.api.authentication.parse_bearer_header", return_value="token") as parser, patch(
        "app.api.authentication.AuthenticationService"
    ) as service:
        service.return_value.resolve_principal.return_value = expected
        assert get_authenticated_principal(request, None, db) is expected
    parser.assert_called_once_with("Bearer token")
    service.return_value.resolve_principal.assert_called_once_with("token")


@pytest.mark.parametrize(
    ("changes"),
    [
        {"estado_sesion": "CERRADA"},
        {"estado_sesion": "EXPIRADA"},
        {"fecha_hora_cierre": datetime(2026, 8, 7, 12)},
        {"expira_en": datetime(2026, 8, 7, 12)},
        {"requiere_reautenticacion": True},
        {"estado_usuario": "INACTIVO"},
        {"usuario_deleted_at": datetime(2026, 8, 7, 12)},
        {"fecha_baja": datetime(2026, 8, 7, 12)},
        {"id_usuario_usuario": None},
    ],
)
def test_principal_rejects_every_unusable_session_or_user(changes):
    db = Mock()
    with patch(
        "app.application.administrativo.authentication.SesionUsuarioRepository"
    ) as repository:
        repository.return_value.get_principal_projection_by_digest.return_value = _projection(**changes)
        with pytest.raises(InvalidSession):
            AuthenticationService(db, None).resolve_principal("a" * 43)
    db.commit.assert_not_called()


def test_principal_builds_from_projection_and_reuses_digest():
    row = _projection()
    db = Mock()
    with patch(
        "app.application.administrativo.authentication.SesionUsuarioRepository"
    ) as repository, patch(
        "app.application.administrativo.authentication.digest_access_token",
        return_value="digest",
    ) as digest:
        repository.return_value.get_principal_projection_by_digest.return_value = row
        principal = AuthenticationService(db, None).resolve_principal("a" * 43)
    digest.assert_called_with("a" * 43)
    assert principal.id_sesion == UUID(str(row["uid_global"]))
    assert principal.id_instalacion_origen_sesion == 1
    assert principal.id_sucursal_operativa is None
    db.commit.assert_not_called()


def test_principal_collapses_database_failure_without_secrets():
    db = Mock()
    with patch(
        "app.application.administrativo.authentication.SesionUsuarioRepository"
    ) as repository:
        repository.return_value.get_principal_projection_by_digest.side_effect = RuntimeError("SQL token digest")
        with pytest.raises(SessionTechnicalError) as error:
            AuthenticationService(db, None).resolve_principal("a" * 43)
    assert str(error.value) == "No fue posible validar la sesión."
