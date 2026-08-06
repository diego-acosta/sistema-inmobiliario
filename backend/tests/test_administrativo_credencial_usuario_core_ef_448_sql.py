from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

PATCH_NAME = "patch_credencial_usuario_core_ef_20260805.sql"
BACKEND = Path(__file__).resolve().parents[1]
PATCH = BACKEND / "database" / PATCH_NAME
SH = BACKEND / "scripts/reset_db.sh"
BAT = BACKEND / "scripts/reset_db.bat"
HISTORICAL_COLUMNS = {
    "id_credencial_usuario", "id_usuario", "tipo_credencial", "identificador_credencial",
    "hash_credencial", "algoritmo_hash", "estado_credencial", "es_credencial_principal",
    "fecha_alta", "fecha_activacion", "fecha_vencimiento", "fecha_revocacion",
    "motivo_revocacion", "obliga_rotacion", "ultimo_cambio_credencial",
    "intentos_fallidos_acumulados", "ultimo_intento_fallido", "bloqueo_hasta",
    "requiere_reset", "observaciones",
}
META_COLUMNS = {
    "uid_global", "version_registro", "created_at", "updated_at", "deleted_at",
    "id_instalacion_origen", "id_instalacion_ultima_modificacion", "op_id_alta",
    "op_id_ultima_modificacion",
}


def _patch_without_transaction() -> str:
    return PATCH.read_text(encoding="utf-8").replace("\nBEGIN;\n", "\n", 1).replace("\nCOMMIT;\n", "\n", 1)


def _user(db, suffix=None):
    suffix = suffix or uuid4().hex
    return db.execute(text("""
        INSERT INTO usuario (codigo_usuario, login, email, estado_usuario)
        VALUES (:c, :l, :e, 'ACTIVO') RETURNING id_usuario
    """), {"c": f"USR_448_{suffix}", "l": f"usr_448_{suffix}", "e": f"u{suffix}@example.invalid"}).scalar_one()


def _cred(db, user_id, **values):
    base = {
        "id_usuario": user_id,
        "tipo_credencial": "PASSWORD",
        "hash_credencial": "hash-no-real-448",
        "algoritmo_hash": "HISTORICO",
        "estado_credencial": "ACTIVA",
    }
    base.update(values)
    cols = list(base)
    return db.execute(text(f"INSERT INTO credencial_usuario ({','.join(cols)}) VALUES ({','.join(':'+c for c in cols)}) RETURNING *"), base).mappings().one()


def _snapshot(db, user_id):
    return [dict(row) for row in db.execute(text("""
        SELECT id_credencial_usuario, id_usuario, tipo_credencial, identificador_credencial,
               hash_credencial, algoritmo_hash, estado_credencial, es_credencial_principal,
               fecha_alta, fecha_activacion, fecha_vencimiento, fecha_revocacion,
               motivo_revocacion, obliga_rotacion, ultimo_cambio_credencial,
               intentos_fallidos_acumulados, ultimo_intento_fallido, bloqueo_hasta,
               requiere_reset, observaciones, uid_global, version_registro, created_at,
               updated_at, deleted_at, id_instalacion_origen,
               id_instalacion_ultima_modificacion, op_id_alta, op_id_ultima_modificacion
          FROM credencial_usuario
         WHERE id_usuario=:u
         ORDER BY id_credencial_usuario
    """), {"u": user_id}).mappings().all()]


def test_patch_transaccional_con_lock_y_resets_simmetricos():
    sql = PATCH.read_text(encoding="utf-8")
    sh, bat = SH.read_text(encoding="utf-8"), BAT.read_text(encoding="utf-8")
    assert sql.upper().count("BEGIN;") == 1
    assert sql.upper().count("COMMIT;") == 1
    assert "LOCK TABLE public.credencial_usuario IN ACCESS EXCLUSIVE MODE" in sql
    for forbidden in ("CREATE TABLE public.credencial_usuario", "INSERT INTO public.credencial_usuario", "INSERT INTO outbox_event", "INSERT INTO historial", "sesion_usuario"):
        assert forbidden not in sql.upper()
    assert sh.count(f'"{PATCH_NAME}"') == 2
    assert bat.count('-f "%PATCH_CREDENCIAL_USUARIO_CORE_EF_FILE%"') == 2
    assert sh.index("patch_parametro_sistema_editabilidad_administrativa_20260805.sql") < sh.index(PATCH_NAME) < sh.index("seed_minimo.sql")
    assert bat.index("PATCH_PARAMETRO_SISTEMA_EDITABILIDAD_ADMINISTRATIVA_FILE") < bat.index("PATCH_CREDENCIAL_USUARIO_CORE_EF_FILE") < bat.index("%SEED_FILE%")


def test_estructura_metadata_constraints_indices_y_triggers(db_session):
    rows = db_session.execute(text("""
      SELECT column_name, data_type, character_maximum_length, is_nullable, column_default
      FROM information_schema.columns WHERE table_schema='public' AND table_name='credencial_usuario'
    """)).mappings().all()
    by = {r["column_name"]: r for r in rows}
    assert HISTORICAL_COLUMNS <= set(by)
    assert META_COLUMNS <= set(by)
    assert by["hash_credencial"]["data_type"] == "text" and by["hash_credencial"]["is_nullable"] == "NO"
    assert by["algoritmo_hash"]["data_type"] == "character varying" and by["algoritmo_hash"]["character_maximum_length"] == 100 and by["algoritmo_hash"]["is_nullable"] == "NO"
    assert by["uid_global"]["data_type"] == "uuid" and by["uid_global"]["is_nullable"] == "NO" and "gen_random_uuid" in by["uid_global"]["column_default"]
    assert by["version_registro"]["column_default"] == "1"
    assert by["created_at"]["is_nullable"] == by["updated_at"]["is_nullable"] == "NO"
    for name in (META_COLUMNS - {"uid_global", "version_registro", "created_at", "updated_at"}):
        assert by[name]["is_nullable"] == "YES"

    constraints = dict(db_session.execute(text("SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='credencial_usuario'::regclass")).all())
    for name in ["credencial_usuario_pkey", "fk_cred_usuario", "uq_credencial_usuario_uid_global", "fk_credencial_usuario_instalacion_origen", "fk_credencial_usuario_instalacion_ultima_modificacion"]:
        assert name in constraints
    for fragment in ["tipo_credencial", "PASSWORD", "estado_credencial", "ACTIVA", "REVOCADA", "btrim(hash_credencial)", "btrim((algoritmo_hash)", "version_registro >= 1", "intentos_fallidos_acumulados >= 0", "fecha_vencimiento", "fecha_revocacion", "bloqueo_hasta"]:
        assert any(fragment in definition for definition in constraints.values())

    indexes = dict(db_session.execute(text("SELECT indexname,indexdef FROM pg_indexes WHERE tablename='credencial_usuario'")).all())
    for name in ["idx_cred_usuario", "ix_credencial_usuario_estado", "ux_credencial_usuario_op_id_alta", "ux_credencial_usuario_password_activa", "ux_credencial_usuario_principal_activa"]:
        assert name in indexes
    assert "op_id_alta IS NOT NULL" in indexes["ux_credencial_usuario_op_id_alta"]
    assert "deleted_at IS NULL" in indexes["ux_credencial_usuario_password_activa"]
    assert "es_credencial_principal IS TRUE" in indexes["ux_credencial_usuario_principal_activa"]

    triggers = dict(db_session.execute(text("SELECT tgname,pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid='credencial_usuario'::regclass AND NOT tgisinternal")).all())
    assert triggers.keys() == {"trg_bi_credencial_usuario_core_ef", "trg_bu_credencial_usuario_core_ef"}
    assert all("outbox" not in t.lower() and "historial" not in t.lower() for t in triggers.values())


def test_insert_update_metadata_e_idempotencia_sin_outbox(db_session):
    uid = _user(db_session)
    op = uuid4()
    row = _cred(db_session, uid, id_instalacion_origen=1, op_id_alta=op)
    assert row["version_registro"] == 1 and row["uid_global"]
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert row["op_id_ultima_modificacion"] == op
    before_outbox = db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one()
    db_session.execute(text("""
      UPDATE credencial_usuario
         SET hash_credencial='hash-rotado-no-real', version_registro=99, uid_global=gen_random_uuid(),
             created_at=created_at + interval '1 day', id_instalacion_origen=NULL, op_id_alta=gen_random_uuid()
       WHERE id_credencial_usuario=:id
    """), {"id": row["id_credencial_usuario"]})
    changed = db_session.execute(text("SELECT * FROM credencial_usuario WHERE id_credencial_usuario=:id"), {"id": row["id_credencial_usuario"]}).mappings().one()
    assert changed["version_registro"] == 2
    assert changed["uid_global"] == row["uid_global"]
    assert changed["created_at"] == row["created_at"]
    assert changed["id_instalacion_origen"] == 1 and changed["op_id_alta"] == op
    snapshot = dict(changed)
    db_session.execute(text(_patch_without_transaction()))
    after = dict(db_session.execute(text("SELECT * FROM credencial_usuario WHERE id_credencial_usuario=:id"), {"id": row["id_credencial_usuario"]}).mappings().one())
    assert after == snapshot
    assert db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one() == before_outbox


@pytest.mark.parametrize("values", [
    {"hash_credencial": "   "}, {"algoritmo_hash": ""}, {"tipo_credencial": "API_KEY"},
    {"estado_credencial": "BLOQUEADA"}, {"intentos_fallidos_acumulados": -1},
    {"estado_credencial": "REVOCADA"}, {"fecha_revocacion": "2026-01-01"},
    {"fecha_activacion": "2026-01-02", "fecha_vencimiento": "2026-01-02"},
])
def test_invariantes_rechazan_datos_incompatibles(db_session, values):
    with pytest.raises(DBAPIError), db_session.begin_nested():
        _cred(db_session, _user(db_session), **values)


def test_unicidad_activa_principal_y_revocadas_eliminadas(db_session):
    uid = _user(db_session)
    _cred(db_session, uid, es_credencial_principal=True)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        _cred(db_session, uid)
    db_session.execute(text("UPDATE credencial_usuario SET deleted_at=CURRENT_TIMESTAMP WHERE id_usuario=:u"), {"u": uid})
    active = _cred(db_session, uid, es_credencial_principal=True)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        _cred(db_session, uid, es_credencial_principal=True)
    _cred(
        db_session,
        uid,
        estado_credencial="REVOCADA",
        fecha_alta="2026-08-06 00:00:00",
        fecha_revocacion="2026-08-06 00:00:01",
        es_credencial_principal=True,
    )
    db_session.execute(text("UPDATE credencial_usuario SET deleted_at=CURRENT_TIMESTAMP WHERE id_credencial_usuario=:id"), {"id": active["id_credencial_usuario"]})
    _cred(db_session, uid, es_credencial_principal=True)


def test_reejecucion_permite_credencial_eliminada_y_reemplazo_activo(db_session):
    uid = _user(db_session)
    before_outbox = db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one()
    before_historial = db_session.execute(text("SELECT count(*) FROM historial_acceso")).scalar_one()
    first = _cred(db_session, uid, es_credencial_principal=True, op_id_alta=uuid4())
    db_session.execute(text("UPDATE credencial_usuario SET deleted_at=CURRENT_TIMESTAMP WHERE id_credencial_usuario=:id"), {"id": first["id_credencial_usuario"]})
    _cred(db_session, uid, es_credencial_principal=True, op_id_alta=uuid4())
    snapshot = _snapshot(db_session, uid)

    db_session.execute(text(_patch_without_transaction()))

    assert _snapshot(db_session, uid) == snapshot
    assert db_session.execute(text("SELECT count(*) FROM credencial_usuario WHERE id_usuario=:u"), {"u": uid}).scalar_one() == 2
    assert db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one() == before_outbox
    assert db_session.execute(text("SELECT count(*) FROM historial_acceso")).scalar_one() == before_historial


def test_reejecucion_rechaza_dos_password_activas_no_eliminadas(db_session):
    uid = _user(db_session)
    first = _cred(db_session, uid, es_credencial_principal=False)
    db_session.execute(text("UPDATE credencial_usuario SET deleted_at=CURRENT_TIMESTAMP WHERE id_credencial_usuario=:id"), {"id": first["id_credencial_usuario"]})
    _cred(db_session, uid, es_credencial_principal=False)
    db_session.execute(text("DROP INDEX ux_credencial_usuario_password_activa"))
    db_session.execute(text("UPDATE credencial_usuario SET deleted_at=NULL WHERE id_credencial_usuario=:id"), {"id": first["id_credencial_usuario"]})

    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_without_transaction()))


def test_reejecucion_rechaza_dos_principales_activas_no_eliminadas(db_session):
    uid = _user(db_session)
    first = _cred(db_session, uid, es_credencial_principal=True)
    db_session.execute(text("UPDATE credencial_usuario SET deleted_at=CURRENT_TIMESTAMP WHERE id_credencial_usuario=:id"), {"id": first["id_credencial_usuario"]})
    _cred(db_session, uid, es_credencial_principal=True)
    db_session.execute(text("DROP INDEX ux_credencial_usuario_password_activa"))
    db_session.execute(text("DROP INDEX ux_credencial_usuario_principal_activa"))
    db_session.execute(text("UPDATE credencial_usuario SET deleted_at=NULL WHERE id_credencial_usuario=:id"), {"id": first["id_credencial_usuario"]})

    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(_patch_without_transaction()))


def test_seguridad_sin_runtime_ni_credenciales_en_seeds():
    columns = PATCH.read_text(encoding="utf-8").lower()
    assert " salt" not in columns and "password en claro" not in columns
    for path in BACKEND.glob("database/seed*.sql"):
        assert "credencial_usuario" not in path.read_text(encoding="utf-8").lower()
    runtime_files = list((BACKEND / "app").rglob("*.py"))
    assert not any("credencial_usuario" in p.read_text(encoding="utf-8").lower() for p in runtime_files)
