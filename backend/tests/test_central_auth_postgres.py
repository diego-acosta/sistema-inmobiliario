"""Auth central sobre schema oficial, sin filas de instalación y con zona no UTC."""
from dataclasses import fields
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import sessionmaker

from app.application.administrativo.authentication import (
    AuthenticatedPrincipal, AuthenticationService, InvalidSession, digest_access_token,
)
from app.application.administrativo.commands.bootstrap_credential import (
    BootstrapCredentialCommand, CredentialBootstrapPreview, CredentialBootstrapResult,
    CredentialIdempotencyConflict,
)

PATCH = Path(__file__).resolve().parents[1] / "database/patch_auth_central_20260914.sql"


def _patch():
    return PATCH.read_text().replace("\nBEGIN;\n", "\n", 1).replace("\nCOMMIT;\n", "\n", 1)


@pytest.fixture
def central_db(db_session, monkeypatch):
    monkeypatch.delenv("LOCAL_INSTALLATION_CODE", raising=False)
    # Sólo dentro de la transacción externa revertida por db_session: no desactivar
    # constraints ni sustituir tablas. CASCADE vacía consumidores de seeds legacy.
    db_session.execute(text("TRUNCATE public.instalacion CASCADE"))
    assert db_session.execute(text("SELECT count(*) FROM instalacion")).scalar_one() == 0
    db_session.execute(text("SET LOCAL TIME ZONE 'Pacific/Auckland'"))
    return db_session


def _bootstrap(db):
    codigo = "CENTRAL-" + uuid4().hex[:12]
    db.execute(text("INSERT INTO usuario(codigo_usuario,login,estado_usuario) VALUES (:c,:c,'ACTIVO')"), {"c": codigo})
    factory = sessionmaker(bind=db.connection(), expire_on_commit=False, join_transaction_mode="create_savepoint")
    command = BootstrapCredentialCommand(factory)
    preview = command.preflight(codigo)
    secret, op = "Central-secret-123", uuid4()
    result = command.execute("init", preview, secret, op)
    assert result.result == "COMPLETADO"
    assert not any("instalacion" in f.name for dto in (CredentialBootstrapPreview, CredentialBootstrapResult) for f in fields(dto))
    return command, preview, secret, op


def test_bootstrap_init_reset_replay_without_installation_utc(central_db):
    db = central_db
    command, preview, secret, op = _bootstrap(db)
    before = dict(db.execute(text("SELECT * FROM credencial_usuario WHERE id_usuario=:u"), {"u": preview.id_usuario}).mappings().one())
    assert before["id_instalacion_origen"] is before["id_instalacion_ultima_modificacion"] is None
    now = db.execute(text("SELECT clock_timestamp() AT TIME ZONE 'UTC'")).scalar_one()
    for key in ("fecha_alta", "fecha_activacion", "ultimo_cambio_credencial", "created_at", "updated_at"):
        assert abs(now - before[key]) < timedelta(minutes=1)
    assert command.execute("init", preview, secret, op).result == "REPLAY_IDEMPOTENTE"
    with pytest.raises(CredentialIdempotencyConflict):
        command.execute("init", preview, "Different-secret-123", op)
    reset_op = uuid4()
    command.execute("reset", preview, "Different-secret-123", reset_op)
    assert command.execute("reset", preview, "Different-secret-123", reset_op).result == "REPLAY_IDEMPOTENTE"
    rows = db.execute(text("SELECT * FROM credencial_usuario WHERE id_usuario=:u ORDER BY id_credencial_usuario"), {"u": preview.id_usuario}).mappings().all()
    assert [r["estado_credencial"] for r in rows] == ["REVOCADA", "ACTIVA"]
    assert rows[0]["version_registro"] == before["version_registro"] + 1
    assert rows[0]["fecha_revocacion"] == rows[1]["fecha_alta"]
    assert all(r["id_instalacion_origen"] is r["id_instalacion_ultima_modificacion"] is None for r in rows)


@pytest.mark.parametrize("zone", ["Pacific/Auckland", "America/Argentina/Buenos_Aires"])
def test_login_principal_logout_utc_without_installation(central_db, zone):
    db = central_db
    db.execute(text("SELECT set_config('TimeZone', :z, true)"), {"z": zone})
    _, preview, secret, _ = _bootstrap(db)
    auth = AuthenticationService(db)
    result = auth.login(preview.login, secret)
    row = db.execute(text("SELECT * FROM sesion_usuario WHERE uid_global=:u"), {"u": result.session_id}).mappings().one()
    now = db.execute(text("SELECT clock_timestamp() AT TIME ZONE 'UTC'")).scalar_one()
    assert row["id_instalacion_origen"] is row["id_sucursal_operativa"] is None
    assert row["token_sesion"] == digest_access_token(result.access_token)
    assert row["expira_en"] - row["fecha_hora_inicio"] == timedelta(hours=8)
    for key in ("fecha_hora_inicio", "fecha_hora_ultima_actividad", "created_at", "updated_at"):
        assert abs(now - row[key]) < timedelta(minutes=1)
    principal = auth.resolve_principal(result.access_token)
    assert principal.id_usuario == preview.id_usuario
    assert {f.name for f in fields(AuthenticatedPrincipal)} == {"id_usuario", "codigo_usuario", "login", "id_sesion", "mecanismo_autenticacion", "autenticado_en"}
    auth.logout(result.access_token)
    closed = dict(db.execute(text("SELECT * FROM sesion_usuario WHERE uid_global=:u"), {"u": result.session_id}).mappings().one())
    assert closed["estado_sesion"] == "CERRADA"
    assert abs(now - closed["fecha_hora_cierre"]) < timedelta(minutes=1)
    assert abs(now - closed["updated_at"]) < timedelta(minutes=1)
    auth.logout(result.access_token)
    assert dict(db.execute(text("SELECT * FROM sesion_usuario WHERE uid_global=:u"), {"u": result.session_id}).mappings().one()) == closed
    with pytest.raises(InvalidSession):
        auth.resolve_principal(result.access_token)


def test_expired_session_utc_me_and_logout(central_db, client):
    db = central_db
    _, preview, secret, _ = _bootstrap(db)
    auth = AuthenticationService(db)
    result = auth.login(preview.login, secret)
    headers = {"Authorization": "Bearer " + result.access_token}
    path = "/api/v1/administrativo/seguridad/me"
    response = client.get(path, headers=headers)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    db.execute(text("""UPDATE sesion_usuario SET
        fecha_hora_inicio=(clock_timestamp() AT TIME ZONE 'UTC')-interval '9 hours',
        fecha_hora_ultima_actividad=(clock_timestamp() AT TIME ZONE 'UTC')-interval '9 hours',
        expira_en=(clock_timestamp() AT TIME ZONE 'UTC')-interval '1 hour'
        WHERE uid_global=:u"""), {"u": result.session_id})
    assert client.get(path, headers=headers).status_code == 401
    auth.logout(result.access_token)
    assert db.execute(text("SELECT estado_sesion FROM sesion_usuario WHERE uid_global=:u"), {"u": result.session_id}).scalar_one() == "EXPIRADA"


def test_patch_reexecution_preserves_rows_fks_and_nullable_contract(central_db):
    db = central_db
    _, preview, secret, _ = _bootstrap(db)
    result = AuthenticationService(db).login(preview.login, secret)
    before = dict(db.execute(text("SELECT * FROM sesion_usuario WHERE uid_global=:u"), {"u": result.session_id}).mappings().one())
    db.execute(text(_patch()))
    db.execute(text(_patch()))
    assert dict(db.execute(text("SELECT * FROM sesion_usuario WHERE uid_global=:u"), {"u": result.session_id}).mappings().one()) == before
    assert not db.execute(text("SELECT attnotnull FROM pg_attribute WHERE attrelid='sesion_usuario'::regclass AND attname='id_instalacion_origen'")).scalar_one()
    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(text("UPDATE sesion_usuario SET id_instalacion_origen=987654321 WHERE uid_global=:u"), {"u": result.session_id})
    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(text("UPDATE credencial_usuario SET id_instalacion_ultima_modificacion=987654321 WHERE id_usuario=:u"), {"u": preview.id_usuario})


def test_patch_rejects_incompatible_structure(db_session):
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("ALTER TABLE sesion_usuario DROP CONSTRAINT fk_sesion_inst"))
        db_session.execute(text(_patch()))


@pytest.mark.parametrize("assignment", [
    "token_sesion='bearer-completo-invalido'",
    "expira_en=fecha_hora_inicio",
    "estado_sesion='CERRADA',fecha_hora_cierre=NULL",
])
def test_session_invariants_remain_enforced(central_db, assignment):
    db = central_db
    _, preview, secret, _ = _bootstrap(db)
    result = AuthenticationService(db).login(preview.login, secret)
    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(text(f"UPDATE sesion_usuario SET {assignment} WHERE uid_global=:u"), {"u": result.session_id})


def test_session_trigger_preserves_uid_created_and_increments_once(central_db):
    db = central_db
    _, preview, secret, _ = _bootstrap(db)
    result = AuthenticationService(db).login(preview.login, secret)
    before = db.execute(text("SELECT * FROM sesion_usuario WHERE uid_global=:u"), {"u": result.session_id}).mappings().one()
    after = db.execute(text("""UPDATE sesion_usuario SET uid_global=gen_random_uuid(),
        created_at=created_at+interval '1 day', version_registro=999
        WHERE uid_global=:u RETURNING *"""), {"u": result.session_id}).mappings().one()
    assert after["uid_global"] == before["uid_global"]
    assert after["created_at"] == before["created_at"]
    assert after["version_registro"] == before["version_registro"] + 1
