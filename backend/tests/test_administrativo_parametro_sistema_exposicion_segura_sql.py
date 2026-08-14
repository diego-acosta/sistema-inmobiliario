from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

PATCH_NAME = "patch_parametro_sistema_exposicion_segura_20260804.sql"
BACKEND = Path(__file__).resolve().parents[1]
PATCH = BACKEND / "database" / PATCH_NAME
SH = BACKEND / "scripts/reset_db.sh"
BAT = BACKEND / "scripts/reset_db.bat"
ENDPOINT_PREFIX = "/api/v1/administrativo/configuracion/parametros"


def _patch_without_transaction():
    sql = PATCH.read_text(encoding="utf-8")
    return sql.replace("\nBEGIN;\n", "\n", 1).replace("\nCOMMIT;\n", "\n", 1)


def _ids(db):
    return db.execute(text("""
        SELECT t.id_tipo_dato_parametro, a.id_alcance_parametro
        FROM tipo_dato_parametro t, alcance_parametro a
        WHERE t.codigo_tipo_dato='ENTERO' AND a.codigo_alcance='GLOBAL'
    """)).one()


def _insert_param(db, code=None):
    tipo_id, alcance_id = _ids(db)
    return db.execute(text("""
        INSERT INTO parametro_sistema (
            id_tipo_dato_parametro, id_alcance_parametro, codigo_parametro, nombre_parametro
        ) VALUES (:tipo, :alcance, :codigo, :codigo)
        RETURNING id_parametro_sistema
    """), {"tipo": tipo_id, "alcance": alcance_id, "codigo": code or f"TEST_438_{uuid4().hex}"}).scalar_one()


def _snapshot_values(db):
    return db.execute(text("SELECT * FROM valor_parametro ORDER BY id_valor_parametro")).mappings().all()


def test_patch_transaccional_resets_y_sin_runtime_nuevo():
    sql = PATCH.read_text(encoding="utf-8")
    normalized = sql.upper()
    sh = SH.read_text(encoding="utf-8")
    bat = BAT.read_text(encoding="utf-8")

    assert normalized.count("BEGIN;") == 1
    assert normalized.count("COMMIT;") == 1
    assert sh.count(f'"{PATCH_NAME}"') == 2
    assert bat.count("PATCH_PARAMETRO_SISTEMA_EXPOSICION_SEGURA_FILE") >= 6
    assert sh.index("patch_valor_parametro_core_ef_20260803.sql") < sh.index(PATCH_NAME)
    assert bat.index("PATCH_VALOR_PARAMETRO_CORE_EF_FILE") < bat.index("PATCH_PARAMETRO_SISTEMA_EXPOSICION_SEGURA_FILE")
    assert "ON_ERROR_STOP=1" in sh and "ON_ERROR_STOP=1" in bat
    for forbidden in (
        "INSERT INTO PARAMETRO_SISTEMA", "INSERT INTO VALOR_PARAMETRO", "OUTBOX_EVENT",
        "HISTORIAL_PARAMETRO", "CREATE TRIGGER", "CREATE INDEX", "DO UPDATE",
        "DIA_CIERRE_COMERCIAL", "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS",
    ):
        assert forbidden not in normalized


def test_estructura_exacta_default_deny_sin_indices_ni_triggers(db_session):
    rows = db_session.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name='parametro_sistema'
          AND column_name IN ('exponible_api_administrativa','es_sensible')
    """)).mappings().all()
    by_name = {r["column_name"]: r for r in rows}
    assert set(by_name) == {"exponible_api_administrativa", "es_sensible"}
    assert by_name["exponible_api_administrativa"]["data_type"] == "boolean"
    assert by_name["exponible_api_administrativa"]["is_nullable"] == "NO"
    assert by_name["exponible_api_administrativa"]["column_default"] == "false"
    assert by_name["es_sensible"]["data_type"] == "boolean"
    assert by_name["es_sensible"]["is_nullable"] == "NO"
    assert by_name["es_sensible"]["column_default"] == "true"

    constraints = dict(db_session.execute(text("""
        SELECT conname, pg_get_constraintdef(oid)
        FROM pg_constraint WHERE conrelid='parametro_sistema'::regclass
    """)).all())
    assert "chk_parametro_sistema_exposicion_no_sensible" in constraints
    assert "NOT (exponible_api_administrativa AND es_sensible)" in constraints["chk_parametro_sistema_exposicion_no_sensible"]
    assert db_session.execute(text("""
        SELECT count(*) FROM pg_indexes
        WHERE schemaname='public' AND tablename='parametro_sistema'
          AND (indexname LIKE '%exponible%' OR indexname LIKE '%sensible%')
    """)).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM pg_trigger WHERE tgrelid='parametro_sistema'::regclass AND NOT tgisinternal")).scalar_one() == 0


def test_reset_baseline_y_endpoint_407_no_expone_metadata(client, db_session):
    assert db_session.execute(text("SELECT count(*) FROM tipo_dato_parametro WHERE codigo_tipo_dato='ENTERO'")).scalar_one() == 1
    assert db_session.execute(text("SELECT count(*) FROM alcance_parametro WHERE codigo_alcance='GLOBAL'")).scalar_one() == 1
    assert db_session.execute(text("SELECT count(*) FROM parametro_sistema WHERE codigo_parametro <> 'PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'")).scalar_one() == 0

    pid = _insert_param(db_session)
    response = client.get(ENDPOINT_PREFIX)
    assert response.status_code == 200
    item = next(i for i in response.json()["data"]["items"] if i["id_parametro_sistema"] == pid)
    assert "exponible_api_administrativa" not in item
    assert "es_sensible" not in item
    assert "valor_parametro" not in response.text


def test_migra_tabla_vacia_definicion_heredada_y_varias_sin_valores(db_session):
    before_values = _snapshot_values(db_session)
    with db_session.begin_nested():
        db_session.execute(text("ALTER TABLE parametro_sistema DROP CONSTRAINT chk_parametro_sistema_exposicion_no_sensible"))
        db_session.execute(text("ALTER TABLE parametro_sistema DROP COLUMN exponible_api_administrativa"))
        db_session.execute(text("ALTER TABLE parametro_sistema DROP COLUMN es_sensible"))
        ids = [_insert_param(db_session), _insert_param(db_session), _insert_param(db_session)]
        db_session.execute(text(_patch_without_transaction()))
        rows = db_session.execute(text("""
            SELECT exponible_api_administrativa, es_sensible
            FROM parametro_sistema WHERE id_parametro_sistema = ANY(:ids)
        """), {"ids": ids}).all()
        assert rows == [(False, True), (False, True), (False, True)]
        db_session.execute(text(_patch_without_transaction()))
        assert _snapshot_values(db_session) == before_values


def test_constraint_rechaza_estado_sensible_y_exponible(db_session):
    pid = _insert_param(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("""
            UPDATE parametro_sistema
            SET exponible_api_administrativa=true, es_sensible=true
            WHERE id_parametro_sistema=:pid
        """), {"pid": pid})


@pytest.mark.parametrize("ddl", [
    "ALTER TABLE parametro_sistema ALTER COLUMN exponible_api_administrativa DROP NOT NULL",
    "ALTER TABLE parametro_sistema ALTER COLUMN es_sensible DROP NOT NULL",
    "ALTER TABLE parametro_sistema ALTER COLUMN exponible_api_administrativa SET DEFAULT true",
    "ALTER TABLE parametro_sistema ALTER COLUMN es_sensible SET DEFAULT false",
    "ALTER TABLE parametro_sistema DROP COLUMN exponible_api_administrativa; ALTER TABLE parametro_sistema ADD COLUMN exponible_api_administrativa text NOT NULL DEFAULT 'false'",
])
def test_reejecucion_rechaza_estructura_parcial_incompatible_y_revierte(db_session, ddl):
    before = db_session.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name='parametro_sistema'
          AND column_name IN ('exponible_api_administrativa','es_sensible')
        ORDER BY column_name
    """)).all()
    with pytest.raises(DBAPIError), db_session.begin_nested():
        for statement in ddl.split(";"):
            if statement.strip():
                db_session.execute(text(statement))
        db_session.execute(text(_patch_without_transaction()))
    after = db_session.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name='parametro_sistema'
          AND column_name IN ('exponible_api_administrativa','es_sensible')
        ORDER BY column_name
    """)).all()
    assert after == before


def test_rechaza_constraint_homonima_incompatible_y_estado_contradictorio_preexistente(db_session):
    pid = _insert_param(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("ALTER TABLE parametro_sistema DROP CONSTRAINT chk_parametro_sistema_exposicion_no_sensible"))
        db_session.execute(text("ALTER TABLE parametro_sistema ADD CONSTRAINT chk_parametro_sistema_exposicion_no_sensible CHECK (es_sensible OR NOT es_sensible)"))
        db_session.execute(text(_patch_without_transaction()))

    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("ALTER TABLE parametro_sistema DROP CONSTRAINT chk_parametro_sistema_exposicion_no_sensible"))
        db_session.execute(text("UPDATE parametro_sistema SET exponible_api_administrativa=true, es_sensible=true WHERE id_parametro_sistema=:pid"), {"pid": pid})
        db_session.execute(text(_patch_without_transaction()))


def test_no_infiere_ni_habilita_por_codigo_tipo_alcance_nombre_o_descripcion(db_session):
    suspicious = "DIA_CIERRE_COMERCIAL"
    pid = _insert_param(db_session, suspicious)
    db_session.execute(text("""
        UPDATE parametro_sistema
        SET nombre_parametro='Público no sensible', descripcion='Global entero visible'
        WHERE id_parametro_sistema=:pid
    """), {"pid": pid})
    db_session.execute(text(_patch_without_transaction()))
    assert db_session.execute(text("""
        SELECT exponible_api_administrativa, es_sensible
        FROM parametro_sistema WHERE id_parametro_sistema=:pid
    """), {"pid": pid}).one() == (False, True)


def test_no_endpoints_nuevos_no_outbox_no_historial_no_valores(db_session):
    before = {t: db_session.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in ("valor_parametro", "outbox_event", "historial_parametro")}
    db_session.execute(text(_patch_without_transaction()))
    after = {t: db_session.execute(text(f"SELECT count(*) FROM {t}")).scalar_one() for t in ("valor_parametro", "outbox_event", "historial_parametro")}
    assert after == before
    router = (BACKEND / "app/api/routers/administrativo_router.py").read_text(encoding="utf-8")
    assert router.count(ENDPOINT_PREFIX) == 3
    inventario_pos = router.find(f'"{ENDPOINT_PREFIX}"')
    assert "valor_parametro" not in router[inventario_pos: inventario_pos + 1200]
