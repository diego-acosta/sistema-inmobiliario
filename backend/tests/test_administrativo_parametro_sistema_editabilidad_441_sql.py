from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

PATCH_NAME = "patch_parametro_sistema_editabilidad_administrativa_20260805.sql"
BACKEND = Path(__file__).resolve().parents[1]
PATCH = BACKEND / "database" / PATCH_NAME
SH = BACKEND / "scripts/reset_db.sh"
BAT = BACKEND / "scripts/reset_db.bat"
ROUTER = BACKEND / "app/api/routers/administrativo_router.py"
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


def _insert_param(db, code=None, exposed=False, sensitive=True):
    tipo_id, alcance_id = _ids(db)
    return db.execute(text("""
        INSERT INTO parametro_sistema (
            id_tipo_dato_parametro, id_alcance_parametro, codigo_parametro,
            nombre_parametro, descripcion, exponible_api_administrativa, es_sensible
        ) VALUES (:tipo, :alcance, :codigo, :codigo, :descripcion, :expuesta, :sensible)
        RETURNING id_parametro_sistema
    """), {
        "tipo": tipo_id,
        "alcance": alcance_id,
        "codigo": code or f"TEST_441_{uuid4().hex}",
        "descripcion": "Parametro global entero administrativo",
        "expuesta": exposed,
        "sensible": sensitive,
    }).scalar_one()


def _snapshot(table, db):
    return db.execute(text(f"SELECT * FROM {table} ORDER BY 1")).mappings().all()


def test_patch_transaccional_resets_y_sin_runtime_nuevo():
    sql = PATCH.read_text(encoding="utf-8")
    normalized = sql.upper()
    sh = SH.read_text(encoding="utf-8")
    bat = BAT.read_text(encoding="utf-8")

    assert normalized.count("BEGIN;") == 1
    assert normalized.count("COMMIT;") == 1
    assert sh.count(f'"{PATCH_NAME}"') == 2
    assert bat.count("PATCH_PARAMETRO_SISTEMA_EDITABILIDAD_ADMINISTRATIVA_FILE") >= 6
    assert sh.index("patch_parametro_sistema_exposicion_segura_20260804.sql") < sh.index(PATCH_NAME)
    assert bat.index("PATCH_PARAMETRO_SISTEMA_EXPOSICION_SEGURA_FILE") < bat.index("PATCH_PARAMETRO_SISTEMA_EDITABILIDAD_ADMINISTRATIVA_FILE")
    assert "ON_ERROR_STOP=1" in sh and "ON_ERROR_STOP=1" in bat
    for forbidden in (
        "INSERT INTO PARAMETRO_SISTEMA", "INSERT INTO VALOR_PARAMETRO", "OUTBOX_EVENT",
        "HISTORIAL_PARAMETRO", "CREATE TRIGGER", "CREATE INDEX", "CREATE FUNCTION",
        "DO UPDATE", "DIA_CIERRE_COMERCIAL", "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS",
        "CODIGO_PARAMETRO =", "CODIGO_TIPO_DATO", "CODIGO_ALCANCE", "NOMBRE_PARAMETRO LIKE",
        "DESCRIPCION LIKE", "PERMITE_MODIFICACION", "MODO_GESTION", "ES_EDITABLE",
    ):
        assert forbidden not in normalized


def test_estructura_exacta_default_deny_sin_indices_triggers_ni_endpoint(db_session):
    row = db_session.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_schema='public' AND table_name='parametro_sistema'
          AND column_name='editable_administrativamente'
    """)).mappings().one()
    assert row["data_type"] == "boolean"
    assert row["is_nullable"] == "NO"
    assert row["column_default"] == "false"
    assert db_session.execute(text("""
        SELECT count(*) FROM pg_indexes
        WHERE schemaname='public' AND tablename='parametro_sistema'
          AND indexdef ILIKE '%editable_administrativamente%'
    """)).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM pg_trigger WHERE tgrelid='parametro_sistema'::regclass AND NOT tgisinternal")).scalar_one() == 0
    assert ROUTER.read_text(encoding="utf-8").count(ENDPOINT_PREFIX) == 3


@pytest.mark.parametrize("count", [0, 1, 3])
def test_migra_filas_heredadas_a_no_editables_y_reejecucion_preserva_valores(db_session, count):
    before_values = _snapshot("valor_parametro", db_session)
    with db_session.begin_nested():
        db_session.execute(text("ALTER TABLE parametro_sistema DROP COLUMN editable_administrativamente"))
        ids = [_insert_param(db_session, sensitive=False) for _ in range(count)]
        db_session.execute(text(_patch_without_transaction()))
        if ids:
            assert db_session.execute(text("""
                SELECT bool_or(editable_administrativamente) FROM parametro_sistema
                WHERE id_parametro_sistema = ANY(:ids)
            """), {"ids": ids}).scalar_one() is False
        db_session.execute(text(_patch_without_transaction()))
        assert _snapshot("valor_parametro", db_session) == before_values


@pytest.mark.parametrize("ddl", [
    "ALTER TABLE parametro_sistema DROP COLUMN editable_administrativamente; ALTER TABLE parametro_sistema ADD COLUMN editable_administrativamente text NOT NULL DEFAULT 'false'",
    "ALTER TABLE parametro_sistema ALTER COLUMN editable_administrativamente DROP NOT NULL",
    "ALTER TABLE parametro_sistema ALTER COLUMN editable_administrativamente SET DEFAULT true",
    "ALTER TABLE parametro_sistema ALTER COLUMN editable_administrativamente DROP DEFAULT",
])
def test_rechaza_estructura_parcial_incompatible_y_rollback(db_session, ddl):
    before = db_session.execute(text("""
        SELECT data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name='parametro_sistema' AND column_name='editable_administrativamente'
    """)).one()
    with pytest.raises(DBAPIError), db_session.begin_nested():
        for statement in ddl.split(";"):
            if statement.strip():
                db_session.execute(text(statement))
        db_session.execute(text(_patch_without_transaction()))
    after = db_session.execute(text("""
        SELECT data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name='parametro_sistema' AND column_name='editable_administrativamente'
    """)).one()
    assert after == before


def test_rechaza_filas_nulas_sin_saneamiento_silencioso(db_session):
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("ALTER TABLE parametro_sistema ALTER COLUMN editable_administrativamente DROP NOT NULL"))
        pid = _insert_param(db_session, sensitive=False)
        db_session.execute(text("UPDATE parametro_sistema SET editable_administrativamente=NULL WHERE id_parametro_sistema=:pid"), {"pid": pid})
        db_session.execute(text(_patch_without_transaction()))


def test_no_infiere_por_codigo_tipo_alcance_exposicion_sensibilidad_nombre_descripcion_o_valor(db_session):
    pid = _insert_param(db_session, code="DIA_CIERRE_COMERCIAL_SIMULADO", exposed=True, sensitive=False)
    db_session.execute(text("""
        INSERT INTO valor_parametro (id_parametro_sistema, valor_parametro, fecha_desde)
        VALUES (:pid, '10', CURRENT_DATE)
    """), {"pid": pid})
    db_session.execute(text(_patch_without_transaction()))
    assert db_session.execute(text("""
        SELECT editable_administrativamente FROM parametro_sistema WHERE id_parametro_sistema=:pid
    """), {"pid": pid}).scalar_one() is False


def test_independencia_conceptual_sin_constraints_automaticas(db_session):
    combos = [
        (True, False, False),
        (False, True, False),
        (False, False, True),
        (False, True, True),
    ]
    ids = [_insert_param(db_session, exposed=e, sensitive=s) for e, _editable, s in combos]
    for pid, (_e, editable, _s) in zip(ids, combos):
        db_session.execute(text("""
            UPDATE parametro_sistema SET editable_administrativamente=:editable
            WHERE id_parametro_sistema=:pid
        """), {"pid": pid, "editable": editable})
    rows = db_session.execute(text("""
        SELECT exponible_api_administrativa, editable_administrativamente, es_sensible
        FROM parametro_sistema WHERE id_parametro_sistema = ANY(:ids)
        ORDER BY id_parametro_sistema
    """), {"ids": ids}).all()
    assert rows == combos


def test_reset_baseline_sin_definiciones_funcionales_425_ni_valores(db_session):
    assert db_session.execute(text("SELECT count(*) FROM tipo_dato_parametro WHERE codigo_tipo_dato='ENTERO'")).scalar_one() == 1
    assert db_session.execute(text("SELECT count(*) FROM alcance_parametro WHERE codigo_alcance='GLOBAL'")).scalar_one() == 1
    assert db_session.execute(text("""
        SELECT count(*) FROM parametro_sistema
        WHERE codigo_parametro IN ('DIA_CIERRE_COMERCIAL', 'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
    """)).scalar_one() == 2
    assert db_session.execute(text("SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p USING(id_parametro_sistema) WHERE p.codigo_parametro <> 'PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'")).scalar_one() == 0
