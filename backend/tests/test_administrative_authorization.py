from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from app.api.administrative_authorization import (
    ADMINISTRATIVE_AUTHORIZATION_RESPONSES,
    require_administrative_permission,
)
from app.api.authentication import get_authenticated_principal
from app.api.dependencies import get_db
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
    AdministrativeAuthorizationService,
    AdministrativeAuthorizationTechnicalError,
    InsufficientAdministrativeAuthorization,
)
from app.infrastructure.persistence.repositories.administrative_authorization_repository import (
    AdministrativeAuthorizationProjection,
    AdministrativeAuthorizationRepository,
)
from app.main import (
    administrative_authorization_technical_error_handler,
    insufficient_administrative_authorization_handler,
)
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient


def _principal(id_usuario=42):
    return AuthenticatedPrincipal(
        id_usuario=id_usuario,
        codigo_usuario="USR-42",
        login="admin",
        id_sesion=uuid4(),
        mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=datetime(2026, 8, 10),
        id_instalacion_origen_sesion=1,
        id_sucursal_operativa=None,
    )


def test_dependency_uses_principal_identity_and_returns_same_instance():
    principal = _principal()
    dependency = require_administrative_permission("permiso.opaco")
    with patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService"
    ) as service:
        service.return_value.authorize.return_value = (
            AdministrativeAuthorizationDecision.GRANTED
        )
        assert dependency(principal, Mock()) is principal
    service.return_value.authorize.assert_called_once_with(42, "permiso.opaco")


def test_dependency_default_denies_every_non_granted_decision():
    dependency = require_administrative_permission("permiso.opaco")
    with patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService"
    ) as service:
        service.return_value.authorize.return_value = (
            AdministrativeAuthorizationDecision.DENIED
        )
        with pytest.raises(InsufficientAdministrativeAuthorization):
            dependency(_principal(), Mock())


@pytest.mark.parametrize("permission_code", ["", "   ", None])
def test_dependency_rejects_empty_permission_as_technical_error(permission_code):
    with pytest.raises(AdministrativeAuthorizationTechnicalError):
        require_administrative_permission(permission_code)


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            AdministrativeAuthorizationProjection(True, True),
            AdministrativeAuthorizationDecision.GRANTED,
        ),
        (
            AdministrativeAuthorizationProjection(True, False),
            AdministrativeAuthorizationDecision.DENIED,
        ),
    ],
)
def test_service_resolves_granted_and_all_ordinary_denials(projection, expected):
    db = Mock()
    with patch(
        "app.application.administrativo.authorization."
        "AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_global_permission.return_value = projection
        assert AdministrativeAuthorizationService(db).authorize(42, "p") is expected
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
    db.flush.assert_not_called()


def test_service_classifies_undefined_permission_as_technical_error():
    with patch(
        "app.application.administrativo.authorization."
        "AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_global_permission.return_value = (
            AdministrativeAuthorizationProjection(False, False)
        )
        with pytest.raises(AdministrativeAuthorizationTechnicalError):
            AdministrativeAuthorizationService(Mock()).authorize(42, "missing")


@pytest.mark.parametrize("result", [None, object()])
def test_service_default_denies_impossible_internal_results(result):
    with patch(
        "app.application.administrativo.authorization."
        "AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_global_permission.return_value = result
        with pytest.raises(AdministrativeAuthorizationTechnicalError):
            AdministrativeAuthorizationService(Mock()).authorize(42, "p")


def test_service_sanitizes_repository_error_without_transaction_side_effects():
    db = Mock()
    with patch(
        "app.application.administrativo.authorization."
        "AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_global_permission.side_effect = RuntimeError(
            "SQL driver DSN permiso.opaco"
        )
        with pytest.raises(AdministrativeAuthorizationTechnicalError) as error:
            AdministrativeAuthorizationService(db).authorize(42, "permiso.opaco")
    assert str(error.value) == "No fue posible resolver la autorización administrativa."
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
    db.flush.assert_not_called()


def test_repository_query_is_global_read_only_and_uses_postgresql_wall_clock():
    db = Mock()
    result = Mock()
    mappings = Mock()
    db.execute.return_value = result
    result.mappings.return_value = mappings
    mappings.one.return_value = {"permission_defined": True, "granted": False}

    projection = AdministrativeAuthorizationRepository(db).resolve_global_permission(
        42, "Case.Sensitive"
    )

    sql = str(db.execute.call_args.args[0]).lower()
    assert projection == AdministrativeAuthorizationProjection(True, False)
    assert "clock_timestamp()::timestamp without time zone" in sql
    assert "fecha_desde <=" in sql
    assert "fecha_hasta >" in sql
    assert "usuario_rol_sucursal" not in sql
    assert "usuario_sucursal" not in sql
    assert "for update" not in sql
    assert not any(word in sql for word in ("insert ", "update ", "delete "))
    assert db.execute.call_args.args[1] == {
        "id_usuario": 42,
        "permission_code": "Case.Sensitive",
    }


def _isolated_client(principal, decision):
    app = FastAPI()
    app.add_exception_handler(
        InsufficientAdministrativeAuthorization,
        insufficient_administrative_authorization_handler,
    )
    app.add_exception_handler(
        AdministrativeAuthorizationTechnicalError,
        administrative_authorization_technical_error_handler,
    )
    dependency = require_administrative_permission("test.permission.443")

    @app.get(
        "/protected",
        responses=ADMINISTRATIVE_AUTHORIZATION_RESPONSES,
    )
    def protected(authenticated=Depends(dependency)):
        return {"id_usuario": authenticated.id_usuario}

    app.dependency_overrides[get_authenticated_principal] = lambda: principal
    app.dependency_overrides[get_db] = lambda: Mock()
    service = patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService"
    )
    service_mock = service.start()
    if isinstance(decision, Exception):
        service_mock.return_value.authorize.side_effect = decision
    else:
        service_mock.return_value.authorize.return_value = decision
    return TestClient(app), service


def test_isolated_api_exact_403_is_sanitized_and_ignores_spoofed_headers():
    client, service = _isolated_client(
        _principal(42), AdministrativeAuthorizationDecision.DENIED
    )
    try:
        response = client.get(
            "/protected",
            headers={
                "Authorization": "Bearer never-read-by-authorization",
                "X-Usuario-Id": "999",
                "X-Op-Id": str(uuid4()),
                "X-Sucursal-Id": "99",
                "X-Instalacion-Id": "99",
            },
        )
    finally:
        service.stop()
    assert response.status_code == 403
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "ok": False,
        "error_code": "autorizacion_insuficiente",
        "error_message": (
            "La autorización efectiva es insuficiente para ejecutar la operación."
        ),
        "details": {},
    }
    assert "test.permission.443" not in response.text
    assert "roles" not in response.text
    assert "permisos" not in response.text


def test_isolated_api_exact_500_is_sanitized():
    client, service = _isolated_client(
        _principal(), AdministrativeAuthorizationTechnicalError("SQL driver DSN")
    )
    try:
        response = client.get("/protected")
    finally:
        service.stop()
    assert response.status_code == 500
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "ok": False,
        "error_code": "inconsistencia_roles_permisos",
        "error_message": "No fue posible resolver la autorización administrativa.",
        "details": {},
    }
    assert "SQL" not in response.text
    assert "driver" not in response.text
    assert "DSN" not in response.text
    assert "test.permission.443" not in response.text


def test_isolated_openapi_reuses_bearer_once_without_raw_header_or_scopes():
    app = FastAPI()
    dependency = require_administrative_permission("test.permission.443")

    @app.get(
        "/protected",
        responses=ADMINISTRATIVE_AUTHORIZATION_RESPONSES,
    )
    def protected(_principal=Depends(dependency)):
        return {}

    operation = app.openapi()["paths"]["/protected"]["get"]
    assert app.openapi()["components"]["securitySchemes"]["BearerAuth"] == {
        "type": "http",
        "scheme": "bearer",
    }
    assert operation["security"] == [{"BearerAuth": []}]
    assert set(operation["responses"]) >= {"401", "403", "500"}
    assert not any(
        parameter.get("in") == "header"
        and parameter.get("name", "").lower() == "authorization"
        for parameter in operation.get("parameters", [])
    )
