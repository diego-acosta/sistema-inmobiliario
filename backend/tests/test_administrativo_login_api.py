from datetime import timedelta

from sqlalchemy import text

from app.application.administrativo.authentication import digest_access_token
from app.application.common.security.password_hashing import hash_password


def _credential(db_session, *, login="usr.adm.001", password="Valid-password-446"):
    user_id = db_session.execute(text("""
      INSERT INTO usuario(codigo_usuario,login,estado_usuario,usuario_sistema_interno,id_instalacion_origen,id_instalacion_ultima_modificacion)
      VALUES ('USR-446',:login,'ACTIVO',false,1,1) RETURNING id_usuario
    """), {"login": login}).scalar_one()
    credential_id = db_session.execute(text("""
      INSERT INTO credencial_usuario(id_usuario,tipo_credencial,hash_credencial,algoritmo_hash,
       estado_credencial,es_credencial_principal,fecha_alta,fecha_activacion,obliga_rotacion,
       intentos_fallidos_acumulados,requiere_reset,id_instalacion_origen,id_instalacion_ultima_modificacion)
      VALUES (:user,'PASSWORD',:phc,'argon2id:v1','ACTIVA',true,CURRENT_TIMESTAMP,
       CURRENT_TIMESTAMP,false,0,false,1,1) RETURNING id_credencial_usuario
    """), {"user": user_id, "phc": hash_password(password)}).scalar_one()
    db_session.flush()
    return user_id, credential_id


def test_login_persists_only_digest_and_logout_is_idempotent(client, db_session):
    _credential(db_session)
    response = client.post("/api/v1/administrativo/seguridad/login", json={"login": "usr.adm.001", "password": "Valid-password-446"})
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert set(response.json()) == {"ok", "data"}
    data = response.json()["data"]
    assert set(data) == {"access_token", "token_type", "expires_at", "session_id"}
    assert data["token_type"] == "bearer"
    row = db_session.execute(text("SELECT * FROM sesion_usuario WHERE uid_global=:uid"), {"uid": data["session_id"]}).mappings().one()
    assert row["token_sesion"] == digest_access_token(data["access_token"])
    assert row["token_sesion"] != data["access_token"]
    assert row["id_sucursal_operativa"] is None
    assert row["fecha_hora_ultima_actividad"] == row["fecha_hora_inicio"]
    assert row["expira_en"] - row["fecha_hora_inicio"] == timedelta(hours=8)
    assert row["version_registro"] == 1

    first = client.post("/api/v1/administrativo/seguridad/logout", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert first.status_code == 204
    closed = db_session.execute(text("SELECT estado_sesion,version_registro,fecha_hora_cierre FROM sesion_usuario WHERE uid_global=:uid"), {"uid": data["session_id"]}).mappings().one()
    assert closed["estado_sesion"] == "CERRADA"
    assert closed["version_registro"] == 2
    second = client.post("/api/v1/administrativo/seguridad/logout", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert second.status_code == 204
    repeated = db_session.execute(text("SELECT version_registro,fecha_hora_cierre FROM sesion_usuario WHERE uid_global=:uid"), {"uid": data["session_id"]}).mappings().one()
    assert repeated == {"version_registro": 2, "fecha_hora_cierre": closed["fecha_hora_cierre"]}


def test_login_anti_enumeration_and_request_validation(client, db_session):
    _credential(db_session)
    missing = client.post("/api/v1/administrativo/seguridad/login", json={"login": "missing", "password": "Valid-password-446"})
    wrong = client.post("/api/v1/administrativo/seguridad/login", json={"login": "usr.adm.001", "password": "wrong"})
    assert missing.status_code == wrong.status_code == 401
    assert missing.json() == wrong.json() == {"ok": False, "error_code": "INVALID_CREDENTIALS", "error_message": "Las credenciales no son válidas.", "details": {}}
    assert client.post("/api/v1/administrativo/seguridad/login", json={"login": "x"}).status_code == 422


def test_login_validation_never_reflects_credentials_or_complete_body(
    client, caplog, capsys
):
    password = "DO_NOT_LOG_PASSWORD_446_" + "x" * 1025
    login = "DO_NOT_REFLECT_LOGIN_446_" + "x" * 100
    body = {"login": login, "password": password, "marker": "COMPLETE_BODY_446"}

    response = client.post("/api/v1/administrativo/seguridad/login", json=body)

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    serialized = response.text
    assert password not in serialized
    assert login not in serialized
    assert "COMPLETE_BODY_446" not in serialized
    assert "DO_NOT_LOG_PASSWORD_446" not in serialized
    captured = capsys.readouterr()
    logs_and_streams = caplog.text + captured.out + captured.err
    assert password not in logs_and_streams
    assert login not in logs_and_streams
    assert "COMPLETE_BODY_446" not in logs_and_streams
    assert response.json() == {
        "ok": False,
        "error_code": "VALIDATION_ERROR",
        "error_message": "La solicitud de login no es válida.",
        "details": {},
    }


def test_login_empty_password_validation_is_sanitized_and_no_store(client):
    response = client.post(
        "/api/v1/administrativo/seguridad/login",
        json={"login": "DO_NOT_REFLECT_LOGIN_EMPTY_446", "password": ""},
    )

    assert response.status_code == 422
    assert response.headers["cache-control"] == "no-store"
    assert "DO_NOT_REFLECT_LOGIN_EMPTY_446" not in response.text
    assert '"input"' not in response.text


def test_logout_unknown_is_204_and_invalid_header_is_sanitized(client):
    unknown_token = "a" * 43
    assert client.post("/api/v1/administrativo/seguridad/logout", headers={"Authorization": f"Bearer {unknown_token}"}).status_code == 204
    response = client.post("/api/v1/administrativo/seguridad/logout")
    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_SESSION"
    assert response.headers["cache-control"] == "no-store"


def test_logout_rejects_non_urlsafe_bearer_before_lookup(client):
    response = client.post(
        "/api/v1/administrativo/seguridad/logout",
        headers={"Authorization": "Bearer abc!"},
    )

    assert response.status_code == 401
    assert response.json()["error_code"] == "INVALID_SESSION"
    assert response.headers["cache-control"] == "no-store"


def test_openapi_has_no_me_or_password_response(client):
    schema = client.get("/openapi.json").json()
    assert "/api/v1/administrativo/seguridad/me" not in schema["paths"]
    login = schema["paths"]["/api/v1/administrativo/seguridad/login"]["post"]
    assert "password" not in str(login["responses"])
