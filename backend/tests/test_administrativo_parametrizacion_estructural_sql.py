from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


PATCH_NAME = "patch_parametrizacion_estructural_20260802.sql"
BACKEND_DIR = Path(__file__).resolve().parents[1]
PATCH_PATH = BACKEND_DIR / "database" / PATCH_NAME
RESET_SH = BACKEND_DIR / "scripts/reset_db.sh"
RESET_BAT = BACKEND_DIR / "scripts/reset_db.bat"
ENDPOINT = "/api/v1/administrativo/configuracion/parametros"

EXPECTED_TYPE = (
    "ENTERO",
    "Entero",
    "Valor numérico entero sin componente decimal.",
)
EXPECTED_SCOPE = (
    "GLOBAL",
    "Global",
    "Aplicable sin contexto de sucursal o instalación.",
)


def _patch_without_transaction() -> str:
    sql = PATCH_PATH.read_text(encoding="utf-8")
    return sql.replace("\nBEGIN;\n", "\n", 1).replace("\nCOMMIT;\n", "\n", 1)


def test_patch_presente_en_resets_dev_test_y_en_el_mismo_orden():
    sh = RESET_SH.read_text(encoding="utf-8")
    bat = RESET_BAT.read_text(encoding="utf-8")

    previous = "patch_item_catalogo_estado_20260724.sql"
    assert sh.count(f'"{PATCH_NAME}"') == 2
    assert sh.index(previous) < sh.index(PATCH_NAME)
    assert bat.count(f'-f "%PATCH_PARAMETRIZACION_ESTRUCTURAL_FILE%"') == 2
    assert bat.index("PATCH_ITEM_CATALOGO_ESTADO_FILE") < bat.index(
        "PATCH_PARAMETRIZACION_ESTRUCTURAL_FILE"
    )


def test_patch_es_incremental_transaccional_y_no_siembra_425():
    sql = PATCH_PATH.read_text(encoding="utf-8")
    normalized = sql.upper()

    assert normalized.count("BEGIN;") == 1
    assert normalized.count("COMMIT;") == 1
    assert "INSERT INTO PARAMETRO_SISTEMA" not in normalized
    assert "INSERT INTO VALOR_PARAMETRO" not in normalized
    assert "DO UPDATE" not in normalized
    assert "SCHEMA_INMOBILIARIA_20260418.SQL" not in sql


def test_reset_deja_datos_exactos_unicos_y_lookup_por_codigo(db_session):
    type_rows = db_session.execute(text("""
        SELECT codigo_tipo_dato, nombre_tipo_dato, descripcion_tipo_dato
        FROM tipo_dato_parametro
        WHERE codigo_tipo_dato = :codigo
    """), {"codigo": "ENTERO"}).all()
    scope_rows = db_session.execute(text("""
        SELECT codigo_alcance, nombre_alcance, descripcion_alcance
        FROM alcance_parametro
        WHERE codigo_alcance = :codigo
    """), {"codigo": "GLOBAL"}).all()

    assert type_rows == [EXPECTED_TYPE]
    assert scope_rows == [EXPECTED_SCOPE]
    assert db_session.execute(text("""
        SELECT COUNT(*) FROM tipo_dato_parametro
        WHERE upper(codigo_tipo_dato) = 'ENTERO'
    """)).scalar_one() == 1
    assert db_session.execute(text("""
        SELECT COUNT(*) FROM alcance_parametro
        WHERE upper(codigo_alcance) = 'GLOBAL'
    """)).scalar_one() == 1


def test_patch_se_puede_reejecutar_sin_duplicar(db_session):
    db_session.execute(text(_patch_without_transaction()))
    db_session.execute(text(_patch_without_transaction()))

    assert db_session.execute(text("""
        SELECT COUNT(*) FROM tipo_dato_parametro
        WHERE codigo_tipo_dato = 'ENTERO'
    """)).scalar_one() == 1
    assert db_session.execute(text("""
        SELECT COUNT(*) FROM alcance_parametro
        WHERE codigo_alcance = 'GLOBAL'
    """)).scalar_one() == 1


@pytest.mark.parametrize(
    ("statement", "params"),
    (
        (
            "UPDATE tipo_dato_parametro SET nombre_tipo_dato = :value "
            "WHERE codigo_tipo_dato = 'ENTERO'",
            {"value": "Número"},
        ),
        (
            "UPDATE alcance_parametro SET descripcion_alcance = :value "
            "WHERE codigo_alcance = 'GLOBAL'",
            {"value": "General"},
        ),
        (
            "INSERT INTO tipo_dato_parametro "
            "(codigo_tipo_dato, nombre_tipo_dato) VALUES (:value, 'Variante')",
            {"value": "entero"},
        ),
        (
            "INSERT INTO tipo_dato_parametro "
            "(codigo_tipo_dato, nombre_tipo_dato) VALUES (:value, 'Sinónimo')",
            {"value": "NUMERO"},
        ),
        (
            "INSERT INTO alcance_parametro "
            "(codigo_alcance, nombre_alcance) VALUES (:value, 'Sinónimo')",
            {"value": "GENERAL"},
        ),
        (
            "INSERT INTO alcance_parametro "
            "(codigo_alcance, nombre_alcance) VALUES (:value, 'Sinónimo')",
            {"value": "LOCAL"},
        ),
    ),
)
def test_patch_rechaza_incompatibilidades_y_revierte(db_session, statement, params):
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(statement), params)
        db_session.execute(text(_patch_without_transaction()))

    assert db_session.execute(text("""
        SELECT codigo_tipo_dato, nombre_tipo_dato, descripcion_tipo_dato
        FROM tipo_dato_parametro WHERE codigo_tipo_dato = 'ENTERO'
    """)).one() == EXPECTED_TYPE
    assert db_session.execute(text("""
        SELECT codigo_alcance, nombre_alcance, descripcion_alcance
        FROM alcance_parametro WHERE codigo_alcance = 'GLOBAL'
    """)).one() == EXPECTED_SCOPE


def test_get_407_es_compatible_con_lookup_estructural_por_codigo(
    client, db_session
):
    type_id = db_session.execute(text("""
        SELECT id_tipo_dato_parametro FROM tipo_dato_parametro
        WHERE codigo_tipo_dato = 'ENTERO'
    """)).scalar_one()
    scope_id = db_session.execute(text("""
        SELECT id_alcance_parametro FROM alcance_parametro
        WHERE codigo_alcance = 'GLOBAL'
    """)).scalar_one()
    parameter_id = db_session.execute(text("""
        INSERT INTO parametro_sistema (
            id_tipo_dato_parametro, id_alcance_parametro,
            codigo_parametro, nombre_parametro
        ) VALUES (:type_id, :scope_id, 'TEST_409_GET_407', 'Integración 409/407')
        RETURNING id_parametro_sistema
    """), {"type_id": type_id, "scope_id": scope_id}).scalar_one()

    response = client.get(ENDPOINT)

    assert response.status_code == 200
    item = next(
        row for row in response.json()["data"]["items"]
        if row["id_parametro_sistema"] == parameter_id
    )
    assert item["tipo"]["codigo_tipo_dato"] == "ENTERO"
    assert item["alcance"]["codigo_alcance"] == "GLOBAL"


def test_409_no_crea_definiciones_ni_valores_funcionales_425(db_session):
    assert db_session.execute(text("SELECT COUNT(*) FROM parametro_sistema")).scalar_one() == 0
    assert db_session.execute(text("SELECT COUNT(*) FROM valor_parametro")).scalar_one() == 0
