from sqlalchemy import text
from unittest.mock import patch

from tests.test_administrativo_login_api import _credential


PATH = "/api/v1/administrativo/seguridad/me"
INVALID = {
    "ok": False,
    "error_code": "INVALID_SESSION",
    "error_message": "La sesión no es válida.",
    "details": {},
}


def _login(client, db_session):
    _credential(db_session)
    response = client.post(
        "/api/v1/administrativo/seguridad/login",
        json={"login": "usr.adm.001", "password": "Valid-password-446"},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_me_returns_exact_principal_without_core_ef_headers(client, db_session):
    login = _login(client, db_session)
    before = db_session.execute(text("""
        SELECT version_registro, updated_at, fecha_hora_ultima_actividad, estado_sesion
        FROM sesion_usuario WHERE uid_global=:uid
    """), {"uid": login["session_id"]}).mappings().one()

    response = client.get(PATH, headers={"Authorization": f"Bearer {login['access_token']}"})

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "ok": True,
        "data": {
            "id_usuario": db_session.execute(text("SELECT id_usuario FROM usuario WHERE login='usr.adm.001'")).scalar_one(),
            "codigo_usuario": "USR-446",
            "login": "usr.adm.001",
            "id_sesion": login["session_id"],
            "mecanismo_autenticacion": "SESION_SERVIDOR",
            "autenticado_en": response.json()["data"]["autenticado_en"],
            "id_instalacion_origen_sesion": 1,
            "id_sucursal_operativa": None,
        },
    }
    after = db_session.execute(text("""
        SELECT version_registro, updated_at, fecha_hora_ultima_actividad, estado_sesion
        FROM sesion_usuario WHERE uid_global=:uid
    """), {"uid": login["session_id"]}).mappings().one()
    assert after == before
    assert "access_token" not in response.text
    assert "roles" not in response.text
    assert "permisos" not in response.text
    assert "scopes" not in response.text


def test_me_without_bearer_rejects_spoofed_human_and_technical_context(client):
    headers = {
        "X-Usuario-Id": "1",
        "X-Op-Id": "00000000-0000-4000-8000-000000000001",
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
        "X-Client-Type": "desktop",
        "X-Forwarded-For": "127.0.0.1",
    }
    response = client.get(PATH, headers=headers)
    assert response.status_code == 401
    assert response.json() == INVALID
    assert response.headers["cache-control"] == "no-store"


def test_me_collapses_invalid_headers_and_unknown_token(client):
    for authorization in ("Basic abc", "Bearer abc!", f"Bearer {'a' * 43}"):
        response = client.get(PATH, headers={"Authorization": authorization})
        assert response.status_code == 401
        assert response.json() == INVALID
        assert response.headers["cache-control"] == "no-store"


def test_me_declares_bearer_security_scheme_in_openapi(client):
    schema = client.get("/openapi.json").json()
    bearer = schema["components"]["securitySchemes"]["BearerAuth"]
    operation = schema["paths"][PATH]["get"]

    assert bearer == {"type": "http", "scheme": "bearer"}
    assert operation["security"] == [{"BearerAuth": []}]
    assert not any(
        parameter.get("in") == "header"
        and parameter.get("name", "").lower() == "authorization"
        for parameter in operation.get("parameters", [])
    )


def test_openapi_bearer_declaration_preserves_strict_runtime_errors(client):
    for headers in ({}, {"Authorization": "bearer " + "a" * 43}, {"Authorization": "Bearer  " + "a" * 43}):
        response = client.get(PATH, headers=headers)
        assert response.status_code == 401
        assert response.json() == INVALID
        assert response.headers["cache-control"] == "no-store"


def test_me_sanitizes_database_error_and_never_logs_secrets(client, caplog, capsys):
    token = "SENSITIVE_BEARER_447" + "x" * 23
    assert len(token) == 43
    with patch(
        "app.infrastructure.persistence.repositories.sesion_usuario_repository."
        "SesionUsuarioRepository.get_principal_projection_by_digest",
        side_effect=RuntimeError("SQL driver DSN digest"),
    ):
        response = client.get(PATH, headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 500
    assert response.json() == {
        "ok": False,
        "error_code": "SESSION_TECHNICAL_ERROR",
        "error_message": "No fue posible validar la sesión.",
        "details": {},
    }
    assert response.headers["cache-control"] == "no-store"
    captured = capsys.readouterr()
    public_and_logs = response.text + caplog.text + captured.out + captured.err
    assert token not in public_and_logs
    assert "digest" not in public_and_logs
    assert "DSN" not in public_and_logs


def test_me_collapses_closed_expired_and_ineligible_user(client, db_session):
    login = _login(client, db_session)
    cases = [
        "UPDATE sesion_usuario SET estado_sesion='CERRADA', fecha_hora_cierre=clock_timestamp() WHERE uid_global=:uid",
        "UPDATE sesion_usuario SET estado_sesion='EXPIRADA' WHERE uid_global=:uid",
        "UPDATE sesion_usuario SET estado_sesion='ACTIVA', fecha_hora_cierre=NULL, expira_en=clock_timestamp() WHERE uid_global=:uid",
        "UPDATE sesion_usuario SET expira_en=clock_timestamp()+interval '1 hour', requiere_reautenticacion=true WHERE uid_global=:uid",
    ]
    for statement in cases:
        db_session.execute(text(statement), {"uid": login["session_id"]})
        db_session.flush()
        response = client.get(PATH, headers={"Authorization": f"Bearer {login['access_token']}"})
        assert response.status_code == 401
        assert response.json() == INVALID

    db_session.execute(text("""
        UPDATE sesion_usuario SET requiere_reautenticacion=false, estado_sesion='ACTIVA',
          fecha_hora_cierre=NULL, expira_en=clock_timestamp()+interval '1 hour'
        WHERE uid_global=:uid
    """), {"uid": login["session_id"]})
    user_id = db_session.execute(text("SELECT id_usuario FROM usuario WHERE login='usr.adm.001'")).scalar_one()
    for column, value in (
        ("estado_usuario", "'INACTIVO'"),
        ("deleted_at", "clock_timestamp()"),
        ("fecha_baja", "CURRENT_DATE"),
    ):
        db_session.execute(text("UPDATE usuario SET estado_usuario='ACTIVO', deleted_at=NULL, fecha_baja=NULL WHERE id_usuario=:id"), {"id": user_id})
        db_session.execute(text(f"UPDATE usuario SET {column}={value} WHERE id_usuario=:id"), {"id": user_id})
        db_session.flush()
        response = client.get(PATH, headers={"Authorization": f"Bearer {login['access_token']}"})
        assert response.status_code == 401
        assert response.json() == INVALID
