from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


PATCH_NAME = "patch_rol_administrador_sistema_20260813.sql"
BACKEND = Path(__file__).resolve().parents[1]
PATCH = BACKEND / "database" / PATCH_NAME
SH = BACKEND / "scripts/reset_db.sh"
BAT = BACKEND / "scripts/reset_db.bat"

EXPECTED = (
    "ADMINISTRADOR_SISTEMA",
    "Administrador del sistema",
    "Rol administrativo global para la gestión y configuración del sistema.",
    "ACTIVO",
)


def _patch_without_transaction() -> str:
    sql = PATCH.read_text(encoding="utf-8")
    return sql.replace("\nBEGIN;\n", "\n", 1).replace("\nCOMMIT;\n", "\n", 1)


def _canonical_rows(db):
    return db.execute(text("""
        SELECT codigo_rol, nombre_rol, descripcion, estado_rol
          FROM rol_seguridad
         WHERE codigo_rol = 'ADMINISTRADOR_SISTEMA'
    """)).all()


def _scope_counts(db):
    return tuple(db.execute(text(statement)).scalar_one() for statement in (
        "SELECT count(*) FROM permiso",
        "SELECT count(*) FROM rol_seguridad_permiso",
        "SELECT count(*) FROM usuario_rol_seguridad",
        "SELECT count(*) FROM parametro_sistema",
        "SELECT count(*) FROM valor_parametro",
    ))


def test_reset_test_contiene_contrato_canonico_exacto(db_session):
    assert _canonical_rows(db_session) == [EXPECTED]


def test_patch_es_transaccional_comun_a_dev_y_test_y_anterior_a_consumidores():
    sql = PATCH.read_text(encoding="utf-8").upper()
    sh = SH.read_text(encoding="utf-8")
    bat = BAT.read_text(encoding="utf-8")

    assert sql.count("BEGIN;") == 1
    assert sql.count("COMMIT;") == 1
    assert "ON CONFLICT" not in sql
    assert "UPDATE PUBLIC.ROL_SEGURIDAD" not in sql
    assert sh.count(f'"{PATCH_NAME}"') == 2
    assert sh.index(PATCH_NAME) < sh.index("DEV_SEEDS=(")
    assert bat.count("PATCH_ROL_ADMINISTRADOR_SISTEMA_FILE") == 5
    assert bat.index("PATCH_OPERACION_IDEMPOTENTE_FILE") < bat.index(
        "PATCH_ROL_ADMINISTRADOR_SISTEMA_FILE"
    )


def test_primera_ejecucion_crea_una_fila_y_reejecucion_no_duplica(db_session):
    with db_session.begin_nested():
        db_session.execute(text("DELETE FROM rol_seguridad_permiso WHERE id_rol_seguridad IN (SELECT id_rol_seguridad FROM rol_seguridad WHERE codigo_rol='ADMINISTRADOR_SISTEMA')"))
        db_session.execute(text("""
            DELETE FROM rol_seguridad
             WHERE codigo_rol = 'ADMINISTRADOR_SISTEMA'
        """))
        db_session.execute(text(_patch_without_transaction()))
        assert _canonical_rows(db_session) == [EXPECTED]
        db_session.execute(text(_patch_without_transaction()))
        assert _canonical_rows(db_session) == [EXPECTED]


@pytest.mark.parametrize(
    ("column", "incompatible"),
    [
        ("nombre_rol", "Administrador"),
        ("descripcion", "Otra descripción"),
        ("estado_rol", "INACTIVO"),
    ],
)
def test_reejecucion_incompatible_falla_sin_mutacion_parcial(
    db_session, column, incompatible
):
    before_scope = _scope_counts(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(f"""
            UPDATE rol_seguridad SET {column} = :value
             WHERE codigo_rol = 'ADMINISTRADOR_SISTEMA'
        """), {"value": incompatible})
        incompatible_row = _canonical_rows(db_session)
        db_session.execute(text(_patch_without_transaction()))

    assert _canonical_rows(db_session) == [EXPECTED]
    assert _scope_counts(db_session) == before_scope
    assert incompatible_row != [EXPECTED]


def test_patch_no_crea_permiso_asignaciones_ni_parametro_412(db_session):
    before = _scope_counts(db_session)
    db_session.execute(text(_patch_without_transaction()))
    assert _scope_counts(db_session) == before
    assert db_session.execute(text("""
        SELECT count(*) FROM permiso
         WHERE codigo_permiso = 'ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR'
    """)).scalar_one() == 1
    assert db_session.execute(text("""
        SELECT count(*) FROM parametro_sistema
         WHERE codigo_parametro = 'PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'
    """)).scalar_one() == 1
