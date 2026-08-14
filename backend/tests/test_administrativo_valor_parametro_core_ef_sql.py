from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import sleep
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.config.database import engine

PATCH_NAME = "patch_valor_parametro_core_ef_20260803.sql"
BACKEND = Path(__file__).resolve().parents[1]
PATCH = BACKEND / "database" / PATCH_NAME
SH = BACKEND / "scripts/reset_db.sh"
BAT = BACKEND / "scripts/reset_db.bat"


def _parameter(db, scope="GLOBAL"):
    if scope != "GLOBAL":
        db.execute(text("INSERT INTO alcance_parametro (codigo_alcance,nombre_alcance) VALUES (:c,:c)"), {"c": scope})
    return db.execute(text("""
        INSERT INTO parametro_sistema(id_tipo_dato_parametro,id_alcance_parametro,codigo_parametro,nombre_parametro)
        SELECT t.id_tipo_dato_parametro,a.id_alcance_parametro,:code,:code
        FROM tipo_dato_parametro t, alcance_parametro a
        WHERE t.codigo_tipo_dato='ENTERO' AND a.codigo_alcance=:scope
        RETURNING id_parametro_sistema
    """), {"code": f"TEST_410_{uuid4().hex}", "scope": scope}).scalar_one()


def _insert(db, parameter, **values):
    columns = ["id_parametro_sistema", *values]
    params = {"parameter": parameter, **values}
    placeholders = [":parameter", *(f":{name}" for name in values)]
    return db.execute(text(f"INSERT INTO valor_parametro ({','.join(columns)}) VALUES ({','.join(placeholders)}) RETURNING *"), params).mappings().one()


def _patch_without_transaction():
    sql = PATCH.read_text()
    return sql.replace("\nBEGIN;\n", "\n", 1).replace("\nCOMMIT;\n", "\n", 1)


def _snapshot(db, ids):
    return db.execute(text("""
        SELECT id_valor_parametro, uid_global, version_registro, created_at, updated_at,
               deleted_at, id_instalacion_origen, id_instalacion_ultima_modificacion,
               op_id_alta, op_id_ultima_modificacion, es_valor_vigente
          FROM valor_parametro WHERE id_valor_parametro = ANY(:ids)
          ORDER BY id_valor_parametro
    """), {"ids": ids}).mappings().all()


def test_patch_transaccional_acotado_y_resets_simétricos():
    sql = PATCH.read_text()
    sh, bat = SH.read_text(), BAT.read_text()
    assert sql.upper().count("BEGIN;") == 1
    assert sql.upper().count("COMMIT;") == 1
    for forbidden in ("INSERT INTO PARAMETRO_SISTEMA", "INSERT INTO OUTBOX_EVENT", "HISTORIAL_PARAMETRO"):
        assert forbidden not in sql.upper()
    assert sh.count(f'"{PATCH_NAME}"') == 2
    assert bat.count('-f "%PATCH_VALOR_PARAMETRO_CORE_EF_FILE%"') == 2
    assert sh.index("patch_parametrizacion_estructural_20260802.sql") < sh.index(PATCH_NAME)
    assert bat.index("PATCH_PARAMETRIZACION_ESTRUCTURAL_FILE") < bat.index("PATCH_VALOR_PARAMETRO_CORE_EF_FILE")
    assert "ON_ERROR_STOP=1" in sh and bat.count("ON_ERROR_STOP=1") >= 4


def test_estructura_core_ef_exacta(db_session):
    rows = db_session.execute(text("""
      SELECT column_name, data_type, is_nullable, column_default
      FROM information_schema.columns WHERE table_schema='public' AND table_name='valor_parametro'
      AND column_name IN ('uid_global','version_registro','created_at','updated_at','deleted_at','id_instalacion_origen','id_instalacion_ultima_modificacion','op_id_alta','op_id_ultima_modificacion')
    """)).mappings().all()
    by_name = {r["column_name"]: r for r in rows}
    assert set(by_name) == {"uid_global","version_registro","created_at","updated_at","deleted_at","id_instalacion_origen","id_instalacion_ultima_modificacion","op_id_alta","op_id_ultima_modificacion"}
    assert by_name["uid_global"]["data_type"] == "uuid" and by_name["uid_global"]["is_nullable"] == "NO"
    assert by_name["version_registro"]["column_default"] == "1"
    assert by_name["created_at"]["is_nullable"] == by_name["updated_at"]["is_nullable"] == "NO"
    for name in ("deleted_at","id_instalacion_origen","id_instalacion_ultima_modificacion","op_id_alta","op_id_ultima_modificacion"):
        assert by_name[name]["is_nullable"] == "YES"
    constraints = dict(db_session.execute(text("SELECT conname,pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid='valor_parametro'::regclass")).all())
    assert "UNIQUE (uid_global)" in constraints["uq_valor_parametro_uid_global"]
    assert "version_registro >= 1" in constraints["chk_valor_parametro_version_registro"]
    assert "ON DELETE RESTRICT" in constraints["fk_valor_parametro_instalacion_origen"]
    indexes = dict(db_session.execute(text("SELECT indexname,indexdef FROM pg_indexes WHERE tablename='valor_parametro'")).all())
    assert "op_id_alta IS NOT NULL" in indexes["ux_valor_parametro_op_id_alta"]
    assert "ux_valor_parametro_global_vigente" not in indexes


def test_triggers_presentes_y_sin_outbox(db_session):
    triggers = dict(db_session.execute(text("SELECT tgname,pg_get_triggerdef(oid) FROM pg_trigger WHERE tgrelid='valor_parametro'::regclass AND NOT tgisinternal")).all())
    assert set(triggers) == {"trg_bi_valor_parametro_core_ef","trg_bu_valor_parametro_core_ef","trg_biu_valor_parametro_validar_alcance"}
    assert all("outbox" not in definition.lower() for definition in triggers.values())


def test_insert_defaults_copias_y_version_inicial(db_session):
    pid = _parameter(db_session)
    op = uuid4()
    row = _insert(db_session, pid, valor_parametro="1", id_instalacion_origen=1, op_id_alta=op)
    assert row["uid_global"] and row["version_registro"] == 1
    assert row["created_at"] and row["updated_at"]
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert row["op_id_ultima_modificacion"] == op


@pytest.mark.parametrize("version", [0, -1, 2])
def test_insert_rechaza_version_inicial_distinta_de_uno(db_session, version):
    pid = _parameter(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        _insert(db_session, pid, version_registro=version)


def test_update_incrementa_una_vez_y_preserva_metadata(db_session):
    pid = _parameter(db_session)
    op = uuid4()
    original = _insert(db_session, pid, valor_parametro="1", id_instalacion_origen=1, op_id_alta=op)
    db_session.execute(text("""UPDATE valor_parametro SET valor_parametro='2', version_registro=version_registro+99,
      uid_global=gen_random_uuid(), created_at=created_at + interval '1 day', id_instalacion_origen=NULL, op_id_alta=gen_random_uuid()
      WHERE id_valor_parametro=:id"""), {"id": original["id_valor_parametro"]})
    changed = db_session.execute(text("SELECT * FROM valor_parametro WHERE id_valor_parametro=:id"), {"id": original["id_valor_parametro"]}).mappings().one()
    assert changed["version_registro"] == 2
    assert changed["uid_global"] == original["uid_global"] and changed["created_at"] == original["created_at"]
    assert changed["id_instalacion_origen"] == 1 and changed["op_id_alta"] == op
    before = changed["version_registro"]
    assert db_session.execute(text("SELECT version_registro FROM valor_parametro WHERE id_valor_parametro=:id"), {"id": original["id_valor_parametro"]}).scalar_one() == before
    db_session.execute(text("UPDATE valor_parametro SET deleted_at=CURRENT_TIMESTAMP WHERE id_valor_parametro=:id"), {"id": original["id_valor_parametro"]})
    assert db_session.execute(text("SELECT version_registro FROM valor_parametro WHERE id_valor_parametro=:id"), {"id": original["id_valor_parametro"]}).scalar_one() == 3


@pytest.mark.parametrize("context", [{"id_sucursal": 1},{"id_instalacion": 1},{"id_sucursal": 1,"id_instalacion": 1}])
def test_global_rechaza_contexto(db_session, context):
    pid = _parameter(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested(): _insert(db_session, pid, **context)


def test_no_global_no_recibe_reglas_contextuales_inventadas(db_session):
    pid = _parameter(db_session, "TEST_NO_GLOBAL")
    first = _insert(db_session, pid, valor_parametro="uno")
    second = _insert(db_session, pid, valor_parametro="dos")
    assert first["es_valor_vigente"] and second["es_valor_vigente"]
    assert first["id_sucursal"] is second["id_sucursal"] is None
    assert first["id_instalacion"] is second["id_instalacion"] is None
    before = _snapshot(db_session, [first["id_valor_parametro"], second["id_valor_parametro"]])
    db_session.execute(text(_patch_without_transaction()))
    assert _snapshot(db_session, [first["id_valor_parametro"], second["id_valor_parametro"]]) == before


def test_unicidad_global_vigente_e_historico_y_eliminado(db_session):
    pid = _parameter(db_session)
    _insert(db_session, pid, valor_parametro="1")
    with pytest.raises(DBAPIError), db_session.begin_nested(): _insert(db_session, pid, valor_parametro="2")
    _insert(db_session, pid, valor_parametro="hist", es_valor_vigente=False)
    db_session.execute(text("UPDATE valor_parametro SET deleted_at=CURRENT_TIMESTAMP WHERE id_parametro_sistema=:p AND es_valor_vigente"), {"p":pid})
    _insert(db_session, pid, valor_parametro="nuevo")


@pytest.mark.parametrize("start,end,valid", [(None,None,True),("2026-01-01","2026-01-02",True),("2026-01-01","2026-01-01",False),("2026-01-02","2026-01-01",False)])
def test_vigencia_minima_estricta(db_session,start,end,valid):
    pid = _parameter(db_session)
    context = db_session.begin_nested() if not valid else __import__('contextlib').nullcontext()
    if valid:
        with context: _insert(db_session,pid,fecha_desde=start,fecha_hasta=end)
    else:
        with pytest.raises(DBAPIError), context: _insert(db_session,pid,fecha_desde=start,fecha_hasta=end)


def test_reejecucion_preserva_metadata_con_version_mayor_a_uno(db_session):
    pid = _parameter(db_session)
    row = _insert(db_session, pid, valor_parametro="1", id_instalacion_origen=1, op_id_alta=uuid4())
    for value in ("2", "3"):
        db_session.execute(text("UPDATE valor_parametro SET valor_parametro=:value WHERE id_valor_parametro=:id"), {"value": value, "id": row["id_valor_parametro"]})
    before = _snapshot(db_session, [row["id_valor_parametro"]])
    outbox_before = db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one()

    db_session.execute(text(_patch_without_transaction()))

    assert _snapshot(db_session, [row["id_valor_parametro"]]) == before
    assert before[0]["version_registro"] == 3
    assert db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one() == outbox_before
    assert db_session.execute(text("SELECT count(*) FROM pg_trigger WHERE tgrelid='valor_parametro'::regclass AND NOT tgisinternal")).scalar_one() == 3


def test_reejecucion_acepta_soft_delete_y_reemplazo_sin_mutarlos(db_session):
    pid = _parameter(db_session)
    deleted = _insert(db_session, pid, valor_parametro="anterior", op_id_alta=uuid4())
    db_session.execute(text("UPDATE valor_parametro SET deleted_at=CURRENT_TIMESTAMP WHERE id_valor_parametro=:id"), {"id": deleted["id_valor_parametro"]})
    replacement = _insert(db_session, pid, valor_parametro="actual", op_id_alta=uuid4())
    ids = [deleted["id_valor_parametro"], replacement["id_valor_parametro"]]
    before = _snapshot(db_session, ids)
    outbox_before = db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one()

    db_session.execute(text(_patch_without_transaction()))

    assert _snapshot(db_session, ids) == before
    assert before[0]["deleted_at"] is not None and before[1]["deleted_at"] is None
    assert db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one() == outbox_before


def test_garantia_global_cubre_updates_y_excluye_la_misma_fila(db_session):
    first_pid = _parameter(db_session)
    second_pid = _parameter(db_session)
    current = _insert(db_session, first_pid, valor_parametro="actual")
    historical = _insert(db_session, first_pid, valor_parametro="histórico", es_valor_vigente=False)
    other = _insert(db_session, second_pid, valor_parametro="otro")

    db_session.execute(text("UPDATE valor_parametro SET valor_parametro='actualizado' WHERE id_valor_parametro=:id"), {"id": current["id_valor_parametro"]})
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("UPDATE valor_parametro SET es_valor_vigente=true WHERE id_valor_parametro=:id"), {"id": historical["id_valor_parametro"]})
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("UPDATE valor_parametro SET id_parametro_sistema=:target WHERE id_valor_parametro=:id"), {"target": first_pid, "id": other["id_valor_parametro"]})


def test_migra_indice_defectuoso_previo_y_datos_usados(db_session):
    pid = _parameter(db_session)
    deleted = _insert(db_session, pid, valor_parametro="anterior")
    db_session.execute(text("UPDATE valor_parametro SET deleted_at=CURRENT_TIMESTAMP WHERE id_valor_parametro=:id"), {"id": deleted["id_valor_parametro"]})
    replacement = _insert(db_session, pid, valor_parametro="actual")
    ids = [deleted["id_valor_parametro"], replacement["id_valor_parametro"]]
    before = _snapshot(db_session, ids)
    db_session.execute(text("""CREATE UNIQUE INDEX ux_valor_parametro_global_vigente
        ON valor_parametro(id_parametro_sistema)
        WHERE id_sucursal IS NULL AND id_instalacion IS NULL AND es_valor_vigente AND deleted_at IS NULL"""))

    db_session.execute(text(_patch_without_transaction()))
    db_session.execute(text(_patch_without_transaction()))

    assert _snapshot(db_session, ids) == before
    assert db_session.execute(text("SELECT to_regclass('public.ux_valor_parametro_global_vigente')")).scalar_one() is None


def test_primera_migracion_sin_deleted_at_rechaza_duplicados_y_revierte(db_session):
    pid = _parameter(db_session)
    before_columns = db_session.execute(text("SELECT count(*) FROM information_schema.columns WHERE table_name='valor_parametro'")).scalar_one()
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("DROP TRIGGER trg_biu_valor_parametro_validar_alcance ON valor_parametro"))
        db_session.execute(text("DROP TRIGGER trg_bi_valor_parametro_core_ef ON valor_parametro"))
        db_session.execute(text("DROP TRIGGER trg_bu_valor_parametro_core_ef ON valor_parametro"))
        db_session.execute(text("ALTER TABLE valor_parametro DROP COLUMN deleted_at CASCADE"))
        db_session.execute(text("INSERT INTO valor_parametro(id_parametro_sistema,valor_parametro) VALUES (:p,'uno'),(:p,'dos')"), {"p": pid})
        db_session.execute(text(_patch_without_transaction()))
    assert db_session.execute(text("SELECT count(*) FROM information_schema.columns WHERE table_name='valor_parametro'")).scalar_one() == before_columns
    assert db_session.execute(text("SELECT count(*) FROM valor_parametro WHERE id_parametro_sistema=:p"), {"p": pid}).scalar_one() == 0


def test_concurrencia_global_se_serializa_en_definicion():
    code = f"TEST_410_CONCURRENT_{uuid4().hex}"
    with engine.begin() as setup:
        pid = setup.execute(text("""INSERT INTO parametro_sistema(
          id_tipo_dato_parametro,id_alcance_parametro,codigo_parametro,nombre_parametro)
          SELECT t.id_tipo_dato_parametro,a.id_alcance_parametro,:code,:code
          FROM tipo_dato_parametro t, alcance_parametro a
          WHERE t.codigo_tipo_dato='ENTERO' AND a.codigo_alcance='GLOBAL'
          RETURNING id_parametro_sistema"""), {"code": code}).scalar_one()

    first = engine.connect()
    first_tx = first.begin()
    try:
        first.execute(text("INSERT INTO valor_parametro(id_parametro_sistema,valor_parametro) VALUES (:p,'primero')"), {"p": pid})

        def competing_insert():
            with engine.connect() as second:
                tx = second.begin()
                try:
                    second.execute(text("INSERT INTO valor_parametro(id_parametro_sistema,valor_parametro) VALUES (:p,'segundo')"), {"p": pid})
                    tx.commit()
                    return True
                except DBAPIError:
                    tx.rollback()
                    return False

        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(competing_insert)
            sleep(0.25)
            assert not future.done()
            first_tx.commit()
            assert future.result(timeout=5) is False

        with engine.connect() as check:
            assert check.execute(text("SELECT count(*) FROM valor_parametro WHERE id_parametro_sistema=:p AND es_valor_vigente AND deleted_at IS NULL"), {"p": pid}).scalar_one() == 1
    finally:
        if first_tx.is_active:
            first_tx.rollback()
        first.close()
        with engine.begin() as cleanup:
            cleanup.execute(text("DELETE FROM valor_parametro WHERE id_parametro_sistema=:p"), {"p": pid})
            cleanup.execute(text("DELETE FROM parametro_sistema WHERE id_parametro_sistema=:p"), {"p": pid})


def test_baseline_sin_datos_funcionales_425_ni_outbox(db_session):
    assert db_session.execute(text("SELECT count(*) FROM parametro_sistema WHERE codigo_parametro <> 'PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'")).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p USING(id_parametro_sistema) WHERE p.codigo_parametro <> 'PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'")).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM tipo_dato_parametro WHERE codigo_tipo_dato='ENTERO'")).scalar_one() == 1
    assert db_session.execute(text("SELECT count(*) FROM alcance_parametro WHERE codigo_alcance='GLOBAL'")).scalar_one() == 1
