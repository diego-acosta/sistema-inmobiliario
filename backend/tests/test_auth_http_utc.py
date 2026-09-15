"""Frontera HTTP real con aplicación sustituida; no requiere PostgreSQL."""
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routers import administrativo_router as routes
from app.api.temporal import utc_naive_to_aware
from app.application.administrativo.authentication import AuthenticatedPrincipal, LoginResult


def test_http_auth_serializes_same_utc_instants(monkeypatch):
    start = datetime(2026, 9, 15, 12, 0)
    expires = start + timedelta(hours=8)
    uid = UUID("00000000-0000-4000-8000-000000000001")
    token = "a" * 43
    result = LoginResult(token, expires, uid)
    principal = AuthenticatedPrincipal(1, "USR", "usr", uid, "SESION_SERVIDOR", start)
    monkeypatch.setattr(routes.AuthenticationService, "login", lambda self, login, password: result)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[routes.get_db] = lambda: object()
    app.dependency_overrides[routes.get_authenticated_principal] = lambda: principal
    with TestClient(app) as client:
        login = client.post("/api/v1/administrativo/seguridad/login",
                            json={"login": "usr", "password": "valid-password"})
        me = client.get("/api/v1/administrativo/seguridad/me",
                        headers={"Authorization": "Bearer " + token})
        for response, field, expected in ((login, "expires_at", expires), (me, "autenticado_en", start)):
            assert response.status_code == 200
            assert response.headers["cache-control"] == "no-store"
            actual = datetime.fromisoformat(response.json()["data"][field])
            assert actual.tzinfo is not None and actual.utcoffset() == timedelta(0)
            assert actual.replace(tzinfo=None) == expected
        assert login.json()["data"]["access_token"] == token
        assert login.json()["data"]["session_id"] == me.json()["data"]["id_sesion"] == str(uid)
        assert result.expires_at == expires and result.expires_at.tzinfo is None
        assert principal.autenticado_en == start and principal.autenticado_en.tzinfo is None
        schemas = client.get("/openapi.json").json()["components"]["schemas"]
        for model, field in (("LoginData", "expires_at"), ("AuthenticatedPrincipalData", "autenticado_en")):
            assert schemas[model]["properties"][field]["type"] == "string"
            assert schemas[model]["properties"][field]["format"] == "date-time"


@pytest.mark.parametrize("zone", [UTC, timezone(timedelta(hours=-3))])
def test_utc_naive_boundary_rejects_aware_input(zone):
    with pytest.raises(ValueError, match="UTC-naive"):
        utc_naive_to_aware(datetime(2026, 9, 15, 12, tzinfo=zone))
