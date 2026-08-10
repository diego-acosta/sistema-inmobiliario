import json
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

BACKEND = Path(__file__).resolve().parents[1]
PATCH_NAME = "patch_operacion_idempotente_20260810.sql"
PATCH = BACKEND / "database" / PATCH_NAME
EXPECTED_COLUMNS = {
    "id_operacion_idempotente", "op_id", "command_code", "target_type",
    "target_uid", "target_key", "payload_hash", "canonicalization_version",
    "result_code", "result_http_status", "result_target_uid", "result_version",
    "response_snapshot", "id_usuario", "id_sucursal", "id_instalacion", "created_at",
}
PROHIBITED_COLUMNS = {
    "uid_global", "version_registro", "updated_at", "deleted_at", "op_id_alta",
    "op_id_ultima_modificacion", "id_instalacion_origen",
    "id_instalacion_ultima_modificacion", "status", "completed_at",
}


def _patch_body() -> str:
    sql = PATCH.read_text(encoding="utf-8")
    return sql.replace("BEGIN;", "", 1).rsplit("COMMIT;", 1)[0]


def _installation(db) -> int:
    return db.execute(text("SELECT id_instalacion FROM instalacion ORDER BY id_instalacion LIMIT 1")).scalar_one()


def _insert(db, **changes):
    values = {
        "op_id": uuid4(), "command_code": "TEST.COMMAND", "target_type": "TEST",
        "target_uid": None, "target_key": None, "payload_hash": "a" * 64,
        "canonicalization_version": 1, "result_code": "COMPLETED",
        "result_http_status": None, "result_target_uid": None, "result_version": None,
        "response_snapshot": json.dumps({"ok": True}), "id_usuario": None,
        "id_sucursal": None, "id_instalacion": _installation(db),
    }
    values.update(changes)
    columns = list(values)
    return db.execute(text(
        f"INSERT INTO operacion_idempotente ({','.join(columns)}) "
        f"VALUES ({','.join(':'+column for column in columns)}) RETURNING *"
    ), values).mappings().one()


def test_schema_fisico_exacto(db_session):
    columns = db_session.execute(text("""
      SELECT column_name,data_type,character_maximum_length,is_nullable,column_default,
             identity_generation
        FROM information_schema.columns
       WHERE table_schema='public' AND table_name='operacion_idempotente'
    """)).mappings().all()
    by_name = {row["column_name"]: row for row in columns}
    assert set(by_name) == EXPECTED_COLUMNS
    assert not PROHIBITED_COLUMNS & set(by_name)
    expected_types = {
        "id_operacion_idempotente": ("bigint", None), "op_id": ("uuid", None),
        "command_code": ("character varying", 100), "target_type": ("character varying", 100),
        "target_uid": ("uuid", None), "target_key": ("character varying", 200),
        "payload_hash": ("character", 64), "canonicalization_version": ("integer", None),
        "result_code": ("character varying", 100), "result_http_status": ("integer", None),
        "result_target_uid": ("uuid", None), "result_version": ("integer", None),
        "response_snapshot": ("jsonb", None), "id_usuario": ("bigint", None),
        "id_sucursal": ("bigint", None), "id_instalacion": ("bigint", None),
        "created_at": ("timestamp without time zone", None),
    }
    for name, expected in expected_types.items():
        assert (by_name[name]["data_type"], by_name[name]["character_maximum_length"]) == expected
    nullable = {"target_uid", "target_key", "result_http_status", "result_target_uid", "result_version", "id_usuario", "id_sucursal"}
    assert {name for name, row in by_name.items() if row["is_nullable"] == "YES"} == nullable
    assert by_name["id_operacion_idempotente"]["identity_generation"] == "BY DEFAULT"
    assert by_name["created_at"]["column_default"] == "CURRENT_TIMESTAMP"
    assert all(row["column_default"] is None for name, row in by_name.items() if name not in {"created_at", "id_operacion_idempotente"})

    constraints = dict(db_session.execute(text("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='operacion_idempotente'::regclass")).all())
    assert set(constraints) == {
        "operacion_idempotente_pkey", "uq_operacion_idempotente_op_id",
        "chk_operacion_idempotente_command_code", "chk_operacion_idempotente_target_type",
        "chk_operacion_idempotente_target_key", "chk_operacion_idempotente_payload_hash",
        "chk_operacion_idempotente_canonicalization_version", "chk_operacion_idempotente_result_code",
        "chk_operacion_idempotente_result_http_status", "chk_operacion_idempotente_result_version",
        "fk_operacion_idempotente_usuario", "fk_operacion_idempotente_sucursal",
        "fk_operacion_idempotente_instalacion",
    }
    assert all("ON DELETE RESTRICT" in constraints[name] for name in constraints if name.startswith("fk_"))
    indexes = db_session.execute(text("SELECT indexname FROM pg_indexes WHERE schemaname='public' AND tablename='operacion_idempotente'")).scalars().all()
    assert set(indexes) == {"operacion_idempotente_pkey", "uq_operacion_idempotente_op_id"}
    triggers = db_session.execute(text("SELECT tgname FROM pg_trigger WHERE tgrelid='operacion_idempotente'::regclass AND NOT tgisinternal")).scalars().all()
    assert triggers == ["trg_bud_operacion_idempotente_inmutable"]


def test_unicidad_global_op_id_y_target_no_unico(db_session):
    op_id, target_uid = uuid4(), uuid4()
    _insert(db_session, op_id=op_id, target_uid=target_uid)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        _insert(db_session, op_id=op_id, command_code="OTHER")
    _insert(db_session, target_uid=target_uid)


@pytest.mark.parametrize(("changes", "valid"), [
    ({"command_code": " "}, False), ({"target_type": ""}, False), ({"target_key": "  "}, False),
    ({"target_uid": None, "target_key": None}, True), ({"payload_hash": "a" * 64}, True),
    ({"payload_hash": "a" * 63}, False), ({"payload_hash": "a" * 65}, False),
    ({"payload_hash": "A" * 64}, False), ({"payload_hash": "g" * 64}, False),
    ({"canonicalization_version": 0}, False), ({"canonicalization_version": -1}, False),
    ({"canonicalization_version": 2}, True), ({"result_code": " "}, False),
    ({"result_http_status": None}, True), ({"result_http_status": 100}, True),
    ({"result_http_status": 599}, True), ({"result_http_status": 99}, False),
    ({"result_http_status": 600}, False), ({"result_version": None}, True),
    ({"result_version": 1}, True), ({"result_version": 0}, False), ({"result_version": -1}, False),
    ({"id_usuario": None, "id_sucursal": None}, True), ({"id_instalacion": None}, False),
    ({"id_usuario": 999999999}, False), ({"id_sucursal": 999999999}, False),
    ({"id_instalacion": 999999999}, False),
])
def test_checks_contexto_y_fks(db_session, changes, valid):
    if valid:
        _insert(db_session, **changes)
    else:
        with pytest.raises(DBAPIError), db_session.begin_nested():
            _insert(db_session, **changes)


def test_canonicalization_version_sin_default(db_session):
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("""
          INSERT INTO operacion_idempotente
            (op_id,command_code,target_type,payload_hash,result_code,response_snapshot,id_instalacion)
          VALUES (:op,'C','T',:hash,'OK','{}',:installation)
        """), {"op": uuid4(), "hash": "a" * 64, "installation": _installation(db_session)})


def test_jsonb_timestamp_e_inmutabilidad(db_session):
    snapshot = {"nested": {"array": [True, None, "áé漢字"]}}
    row = _insert(db_session, response_snapshot=json.dumps(snapshot, ensure_ascii=False))
    assert row["response_snapshot"] == snapshot
    assert row["created_at"] is not None
    for statement in (
        "UPDATE operacion_idempotente SET result_code='OTHER' WHERE id_operacion_idempotente=:id",
        "DELETE FROM operacion_idempotente WHERE id_operacion_idempotente=:id",
    ):
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(statement), {"id": row["id_operacion_idempotente"]})
    current = db_session.execute(text("SELECT result_code FROM operacion_idempotente WHERE id_operacion_idempotente=:id"), {"id": row["id_operacion_idempotente"]}).scalar_one()
    assert current == "COMPLETED"


def test_reejecucion_compatible_no_reemplaza_objetos_ni_filas(db_session):
    row = _insert(db_session)
    function_oid = db_session.execute(text("SELECT 'trg_operacion_idempotente_inmutable()'::regprocedure::oid")).scalar_one()
    trigger_oid = db_session.execute(text("SELECT oid FROM pg_trigger WHERE tgname='trg_bud_operacion_idempotente_inmutable'")).scalar_one()
    db_session.execute(text(_patch_body()))
    assert db_session.execute(text("SELECT 'trg_operacion_idempotente_inmutable()'::regprocedure::oid")).scalar_one() == function_oid
    assert db_session.execute(text("SELECT oid FROM pg_trigger WHERE tgname='trg_bud_operacion_idempotente_inmutable'")).scalar_one() == trigger_oid
    assert db_session.execute(text("SELECT count(*) FROM operacion_idempotente WHERE id_operacion_idempotente=:id"), {"id": row["id_operacion_idempotente"]}).scalar_one() == 1


@pytest.mark.parametrize("mutation", [
    "ALTER TABLE operacion_idempotente DROP COLUMN target_key",
    "ALTER TABLE operacion_idempotente ALTER COLUMN target_key TYPE text",
    "ALTER TABLE operacion_idempotente ALTER COLUMN target_uid SET NOT NULL",
    "ALTER TABLE operacion_idempotente ALTER COLUMN canonicalization_version SET DEFAULT 1",
    "ALTER TABLE operacion_idempotente DROP CONSTRAINT uq_operacion_idempotente_op_id; ALTER TABLE operacion_idempotente ADD UNIQUE(op_id,command_code)",
    "DROP TRIGGER trg_bud_operacion_idempotente_inmutable ON operacion_idempotente; CREATE TRIGGER trg_bud_operacion_idempotente_inmutable BEFORE UPDATE ON operacion_idempotente FOR EACH ROW EXECUTE FUNCTION trg_operacion_idempotente_inmutable()",
    "DROP TRIGGER trg_bud_operacion_idempotente_inmutable ON operacion_idempotente; DROP FUNCTION trg_operacion_idempotente_inmutable(); CREATE FUNCTION trg_operacion_idempotente_inmutable() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RETURN OLD; END $$; CREATE TRIGGER trg_bud_operacion_idempotente_inmutable BEFORE UPDATE OR DELETE ON operacion_idempotente FOR EACH ROW EXECUTE FUNCTION trg_operacion_idempotente_inmutable()",
])
def test_fail_fast_estructura_incompatible_y_rollback(db_session, mutation):
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(mutation))
        db_session.execute(text(_patch_body()))
    assert set(db_session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='operacion_idempotente'")).scalars()) == EXPECTED_COLUMNS


def test_reset_simetrico_ordenado_y_no_sync():
    sh = (BACKEND / "scripts/reset_db.sh").read_text(encoding="utf-8")
    bat = (BACKEND / "scripts/reset_db.bat").read_text(encoding="utf-8")
    assert sh.count(f'"{PATCH_NAME}"') == 2
    assert bat.count('-f "%PATCH_OPERACION_IDEMPOTENTE_FILE%"') == 2
    assert sh.index("patch_sesion_usuario_runtime_20260807.sql") < sh.index(PATCH_NAME) < sh.index("seed_minimo.sql")
    assert bat.index("PATCH_SESION_USUARIO_RUNTIME_FILE") < bat.index("PATCH_OPERACION_IDEMPOTENTE_FILE") < bat.index("%SEED_FILE%")
    assert all("ON_ERROR_STOP=1" in line for line in bat.splitlines() if '-f "%PATCH_OPERACION_IDEMPOTENTE_FILE%"' in line)
    policy_files = list((BACKEND / "app").rglob("*.py"))
    assert not any("operacion_idempotente" in path.read_text(encoding="utf-8") for path in policy_files)


def test_insert_no_modifica_outbox_inbox(db_session):
    before = tuple(db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() for table in ("outbox_event", "inbox_event"))
    _insert(db_session)
    after = tuple(db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one() for table in ("outbox_event", "inbox_event"))
    assert after == before
