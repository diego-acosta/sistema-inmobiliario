"""Auth central independiente de instalación, preservando el baseline oficial."""
import os
import re
from dataclasses import fields
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import event, text
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
    return PATCH.read_text(encoding="utf-8").replace("\nBEGIN;\n", "\n", 1).replace("\nCOMMIT;\n", "\n", 1)


# Bodies completos del contrato; no comparación parcial ni normalización interna.
def _normalize_body(body):
    return body.replace("\r\n", "\n").replace("\r", "\n").strip(" \t\n\r")


def _contract_functions():
    definitions = re.findall(
        r"CREATE OR REPLACE FUNCTION public\.(trg_\w+)\(\) RETURNS trigger LANGUAGE plpgsql AS \$\$(.*?)\$\$;",
        _patch(), re.S,
    )
    assert len(definitions) == 4
    return dict(definitions)


def _installed_bodies(db):
    return {
        name: db.execute(text("SELECT prosrc FROM pg_proc WHERE oid=to_regprocedure(:name)"),
                         {"name": "public." + name + "()"}).scalar_one()
        for name in _contract_functions()
    }


def _assert_contract_functions(db):
    assert {n: _normalize_body(b) for n, b in _installed_bodies(db).items()} == {
        n: _normalize_body(b) for n, b in _contract_functions().items()
    }


@pytest.fixture
def central_db(db_session, monkeypatch):
    monkeypatch.delenv("LOCAL_INSTALLATION_CODE", raising=False)
    assert "LOCAL_INSTALLATION_CODE" not in os.environ
    connection = db_session.connection()
    baseline = db_session.execute(
        text("SELECT * FROM public.instalacion ORDER BY id_instalacion")
    ).mappings().all()
    assert baseline, "El fixture conserva las instalaciones del baseline oficial"

    def forbidden_resolution(*args, **kwargs):
        pytest.fail("Auth/bootstrap central no debe resolver instalación")

    # Cubrir tanto imports por módulo como aliases directos en los consumidores.
    monkeypatch.setattr(
        "app.application.common.local_installation.resolve_local_installation",
        forbidden_resolution,
    )
    for module in (
        "app.application.administrativo.authentication",
        "app.application.administrativo.commands.bootstrap_credential",
    ):
        monkeypatch.setattr(
            module + ".resolve_local_installation", forbidden_resolution, raising=False
        )

    def forbid_installation_query(conn, cursor, statement, parameters, context, executemany):
        # Detectar también un lookup directo que eluda el resolver. No afecta
        # introspección pg_catalog ni validaciones FK internas de PostgreSQL.
        if re.search(r'\b(?:FROM|JOIN)\s+(?:"?public"?\.)?"?instalacion"?\b', statement, re.I):
            pytest.fail("Auth/bootstrap central no debe consultar instalación")

    event.listen(connection, "before_cursor_execute", forbid_installation_query)
    try:
        db_session.execute(text("SET LOCAL TIME ZONE 'Pacific/Auckland'"))
        yield db_session
    finally:
        event.remove(connection, "before_cursor_execute", forbid_installation_query)
    after = db_session.execute(
        text("SELECT * FROM public.instalacion ORDER BY id_instalacion")
    ).mappings().all()
    assert after == baseline


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


@pytest.mark.parametrize("zone", ["Pacific/Auckland", "America/Argentina/Buenos_Aires"])
def test_bootstrap_init_reset_replay_without_installation_utc(central_db, zone):
    db = central_db
    db.execute(text("SELECT set_config('TimeZone', :z, true)"), {"z": zone})
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


@pytest.mark.parametrize("zone", ["Pacific/Auckland", "America/Argentina/Buenos_Aires"])
def test_expired_session_utc_me_and_logout(central_db, client, zone):
    db = central_db
    db.execute(text("SELECT set_config('TimeZone', :z, true)"), {"z": zone})
    _, preview, secret, _ = _bootstrap(db)
    auth = AuthenticationService(db)
    result = auth.login(preview.login, secret)
    headers = {"Authorization": "Bearer " + result.access_token}
    path = "/api/v1/administrativo/seguridad/me"
    response = client.get(path, headers=headers)
    assert response.status_code == 200 and response.headers["cache-control"] == "no-store"
    assert set(response.json()["data"]) == {f.name for f in fields(AuthenticatedPrincipal)}
    db.execute(text("""UPDATE sesion_usuario SET
        fecha_hora_inicio=(clock_timestamp() AT TIME ZONE 'UTC')-interval '9 hours',
        fecha_hora_ultima_actividad=(clock_timestamp() AT TIME ZONE 'UTC')-interval '9 hours',
        expira_en=(clock_timestamp() AT TIME ZONE 'UTC')-interval '1 hour'
        WHERE uid_global=:u"""), {"u": result.session_id})
    assert client.get(path, headers=headers).status_code == 401
    auth.logout(result.access_token)
    assert db.execute(text("SELECT estado_sesion FROM sesion_usuario WHERE uid_global=:u"), {"u": result.session_id}).scalar_one() == "EXPIRADA"


@pytest.mark.parametrize("body_eol", ["\n", "\r\n", "\r"], ids=["body-LF", "body-CRLF", "body-CR"])
@pytest.mark.parametrize("patch_eol", ["\n", "\r\n", "\r"], ids=["patch-LF", "patch-CRLF", "patch-CR"])
def test_patch_reexecution_preserves_rows_fks_and_nullable_contract(central_db, body_eol, patch_eol):
    db = central_db
    with db.begin_nested():
        db.execute(text(_patch()))
    assert _marker(db) == CENTRAL_MARKER
    _, preview, secret, _ = _bootstrap(db)
    result = AuthenticationService(db).login(preview.login, secret)
    before = dict(db.execute(text("SELECT * FROM sesion_usuario WHERE uid_global=:u"), {"u": result.session_id}).mappings().one())
    _assert_contract_functions(db)
    credential_before = db.execute(text("SELECT * FROM credencial_usuario WHERE id_usuario=:u"),
                                   {"u": preview.id_usuario}).mappings().one()
    assert before["id_instalacion_origen"] is None
    assert credential_before["id_instalacion_origen"] is None
    assert credential_before["id_instalacion_ultima_modificacion"] is None
    # Reproducir prosrc de distintos checkouts/psql sin cambiar los statements.
    for name, body in _contract_functions().items():
        source = body.replace("\n", body_eol)
        db.execute(text(f"CREATE OR REPLACE FUNCTION public.{name}() RETURNS trigger "
                        f"LANGUAGE plpgsql AS $body${source}$body$"))
        assert _installed_bodies(db)[name] == source
    for _ in range(2):
        with db.begin_nested():
            db.execute(text(_patch().replace("\n", patch_eol)))
        _assert_contract_functions(db)
        assert _marker(db) == CENTRAL_MARKER
        assert AuthenticationService(db).resolve_principal(result.access_token).id_usuario == preview.id_usuario
    assert db.execute(text("SELECT * FROM credencial_usuario WHERE id_usuario=:u"),
                      {"u": preview.id_usuario}).mappings().one() == credential_before
    assert db.execute(text("""SELECT count(*) FROM pg_attribute
        WHERE attrelid='credencial_usuario'::regclass
          AND attname IN ('id_instalacion_origen','id_instalacion_ultima_modificacion')
          AND NOT attnotnull AND NOT attisdropped""")).scalar_one() == 2
    assert db.execute(text("""SELECT count(*) FROM pg_constraint
        WHERE conname IN ('fk_sesion_inst', 'fk_credencial_usuario_instalacion_origen',
                          'fk_credencial_usuario_instalacion_ultima_modificacion')
          AND conrelid IN ('sesion_usuario'::regclass, 'credencial_usuario'::regclass)
          AND contype='f' AND confrelid='instalacion'::regclass
          AND confdeltype='r' AND convalidated""")).scalar_one() == 3
    assert dict(db.execute(text("SELECT * FROM sesion_usuario WHERE uid_global=:u"), {"u": result.session_id}).mappings().one()) == before
    assert not db.execute(text("SELECT attnotnull FROM pg_attribute WHERE attrelid='sesion_usuario'::regclass AND attname='id_instalacion_origen'")).scalar_one()
    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(text("UPDATE sesion_usuario SET id_instalacion_origen=987654321 WHERE uid_global=:u"), {"u": result.session_id})
    with pytest.raises(DBAPIError), db.begin_nested():
        db.execute(text("UPDATE credencial_usuario SET id_instalacion_ultima_modificacion=987654321 WHERE id_usuario=:u"), {"u": preview.id_usuario})


@pytest.mark.parametrize("function_name", list(_contract_functions()))
def test_patch_rejects_material_function_change(central_db, function_name):
    db = central_db
    _assert_contract_functions(db)
    original = _contract_functions()[function_name]
    # Cambio material: la función dejaría de retornar NEW. Nunca ejecutar el trigger.
    altered = original.replace("RETURN NEW;", "RETURN NULL;")
    assert altered != original
    with pytest.raises(DBAPIError, match="Función incompatible: " + function_name), db.begin_nested():
        db.execute(text(f"CREATE OR REPLACE FUNCTION public.{function_name}() RETURNS trigger "
                        f"LANGUAGE plpgsql AS $body${altered}$body$"))
        db.execute(text(_patch()))
    # El rollback localizado restaura la función y mantiene utilizable el fixture.
    _assert_contract_functions(db)
    assert db.execute(text("SELECT 1")).scalar_one() == 1


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


def _marker(db):
    return db.execute(text("SELECT obj_description('public.sesion_usuario'::regclass, 'pg_class')")).scalar_one()


CENTRAL_MARKER = "AUTH_CENTRAL_EMPTY_INIT_V1: credencial_usuario y sesion_usuario vacias al inicializar."


def _auth_snapshot(db):
    return {
        table: db.execute(text(f"SELECT * FROM public.{table} ORDER BY 1")).mappings().all()
        for table in ("credencial_usuario", "sesion_usuario")
    }


def _schema_snapshot(db):
    return (
        _marker(db), _installed_bodies(db),
        db.execute(text("""SELECT a.attrelid, a.attname, a.attnotnull,
            pg_get_expr(d.adbin, d.adrelid)
            FROM pg_attribute a LEFT JOIN pg_attrdef d
              ON d.adrelid=a.attrelid AND d.adnum=a.attnum
            WHERE a.attrelid IN ('credencial_usuario'::regclass,'sesion_usuario'::regclass)
              AND a.attnum > 0 AND NOT a.attisdropped
            ORDER BY a.attrelid,a.attnum""")).all(),
        db.execute(text("""SELECT oid, pg_get_constraintdef(oid), convalidated
            FROM pg_constraint WHERE conrelid IN
            ('credencial_usuario'::regclass,'sesion_usuario'::regclass) ORDER BY oid""")).all(),
    )


def test_patch_first_initialization_requires_empty_auth(central_db):
    db = central_db
    assert _auth_snapshot(db) == {"credencial_usuario": [], "sesion_usuario": []}
    db.execute(text("COMMENT ON TABLE public.sesion_usuario IS NULL"))
    db.execute(text("ALTER TABLE sesion_usuario ALTER COLUMN id_instalacion_origen SET NOT NULL"))
    db.execute(text("ALTER TABLE sesion_usuario ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP"))
    constraints_before = _schema_snapshot(db)[3]
    with db.begin_nested():
        db.execute(text(_patch()))
    assert _marker(db) == CENTRAL_MARKER
    _assert_contract_functions(db)
    assert _auth_snapshot(db) == {"credencial_usuario": [], "sesion_usuario": []}
    assert _schema_snapshot(db)[3] == constraints_before
    assert not db.execute(text("SELECT attnotnull FROM pg_attribute WHERE attrelid='sesion_usuario'::regclass AND attname='id_instalacion_origen'")).scalar_one()
    defaults = db.execute(text("""SELECT pg_get_expr(adbin,adrelid) FROM pg_attrdef
        WHERE adrelid IN ('sesion_usuario'::regclass,'credencial_usuario'::regclass)
        AND adnum IN (SELECT attnum FROM pg_attribute WHERE attrelid=adrelid
            AND attname IN ('created_at','updated_at','fecha_alta'))""")).scalars().all()
    assert len(defaults) == 5 and all("UTC" in d for d in defaults)


@pytest.mark.parametrize("legacy_table", ["credencial_usuario", "sesion_usuario"])
@pytest.mark.parametrize("old_marker", [None, "Auth central: cutover pre-UTC v1 completado."])
def test_patch_rejects_unmarked_auth_atomically(central_db, legacy_table, old_marker):
    db = central_db
    if legacy_table == "credencial_usuario":
        _bootstrap(db)
    else:
        # Sesión independiente de credencial (FK nullable), sin borrar receipts.
        db.execute(text("""INSERT INTO sesion_usuario
            (id_usuario,token_sesion,fecha_hora_inicio,expira_en,estado_sesion)
            VALUES (1,:digest,timezone('UTC',CURRENT_TIMESTAMP),
                    timezone('UTC',CURRENT_TIMESTAMP)+interval '8 hours','ACTIVA')"""),
                   {"digest": digest_access_token(uuid4().hex)})
    db.execute(text("COMMENT ON TABLE public.sesion_usuario IS " +
                    ("NULL" if old_marker is None else "'" + old_marker + "'")))
    # Una semántica anterior reconocida tampoco autoriza migrar filas.
    db.execute(text("ALTER TABLE sesion_usuario ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP"))
    rows_before, schema_before = _auth_snapshot(db), _schema_snapshot(db)
    with pytest.raises(DBAPIError, match="Auth central requiere inicializacion limpia"), db.begin_nested():
        db.execute(text(_patch()))
    assert _auth_snapshot(db) == rows_before
    assert _schema_snapshot(db) == schema_before
    assert _marker(db) != CENTRAL_MARKER
    assert db.execute(text("SELECT 1")).scalar_one() == 1
