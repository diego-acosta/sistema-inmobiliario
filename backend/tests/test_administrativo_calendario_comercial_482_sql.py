from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError


PATCH_NAME = "patch_calendario_comercial_482_20260814.sql"
BACKEND = Path(__file__).resolve().parents[1]
PATCH = BACKEND / "database" / PATCH_NAME
SH = BACKEND / "scripts/reset_db.sh"
BAT = BACKEND / "scripts/reset_db.bat"

CODES = ("DIA_CIERRE_COMERCIAL", "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS")
EXPECTED = [
    (
        CODES[0],
        "Día de cierre comercial",
        "Día del mes, entre 1 y 31, utilizado para determinar el período base sugerido de una venta según su fecha de negocio.",
        "ENTERO", "GLOBAL", True, False, True,
    ),
    (
        CODES[1],
        "Día de vencimiento predeterminado de cuotas",
        "Día del mes, entre 1 y 31, utilizado para sugerir el vencimiento de las cuotas; la fecha sugerida puede ser modificada antes de confirmar la venta.",
        "ENTERO", "GLOBAL", True, False, True,
    ),
]


def _sql() -> str:
    content = PATCH.read_text(encoding="utf-8")
    return content.replace("BEGIN;", "", 1).rsplit("COMMIT;", 1)[0]


def _definitions(db):
    return db.execute(text("""
      SELECT p.codigo_parametro,p.nombre_parametro,p.descripcion,t.codigo_tipo_dato,
             a.codigo_alcance,p.exponible_api_administrativa,p.es_sensible,
             p.editable_administrativamente
        FROM parametro_sistema p JOIN tipo_dato_parametro t USING(id_tipo_dato_parametro)
        JOIN alcance_parametro a USING(id_alcance_parametro)
       WHERE p.codigo_parametro IN ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
       ORDER BY p.codigo_parametro
    """)).all()


def test_reset_deja_definiciones_sin_valores_ni_raiz(db_session):
    assert _definitions(db_session) == EXPECTED
    assert db_session.execute(text("""
      SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p USING(id_parametro_sistema)
       WHERE p.codigo_parametro IN ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
    """)).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM configuracion_calendario_comercial")).scalar_one() == 0


def test_patch_transaccional_simetrico_idempotente_y_sin_duplicados(db_session):
    upper = PATCH.read_text(encoding="utf-8").upper()
    assert upper.count("BEGIN;") == upper.count("COMMIT;") == 1
    assert SH.read_text(encoding="utf-8").count(f'"{PATCH_NAME}"') == 2
    assert BAT.read_text(encoding="utf-8").count("PATCH_CALENDARIO_COMERCIAL_482_FILE") == 5
    before = db_session.execute(text("""
      SELECT (SELECT count(*) FROM parametro_sistema WHERE codigo_parametro IN ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')),
             (SELECT count(*) FROM permiso WHERE codigo_permiso='ADMIN.CONFIG.CALENDARIO_COMERCIAL.ADMINISTRAR'),
             (SELECT count(*) FROM rol_seguridad_permiso rsp JOIN rol_seguridad r USING(id_rol_seguridad)
               JOIN permiso p USING(id_permiso) WHERE r.codigo_rol='ADMINISTRADOR_SISTEMA'
               AND p.codigo_permiso='ADMIN.CONFIG.CALENDARIO_COMERCIAL.ADMINISTRAR')
    """)).one()
    db_session.execute(text(_sql()))
    assert before == (2, 1, 1)
    assert _definitions(db_session) == EXPECTED


@pytest.mark.parametrize(
    ("mutation", "evidence"),
    [
        (
            "ALTER TABLE configuracion_calendario_comercial ALTER COLUMN version_registro SET DEFAULT 2",
            "SELECT column_default='2' FROM information_schema.columns WHERE table_schema='public' AND table_name='configuracion_calendario_comercial' AND column_name='version_registro'",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial DROP CONSTRAINT uq_configuracion_calendario_comercial_uid",
            "SELECT NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='configuracion_calendario_comercial'::regclass AND contype='u')",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial DROP CONSTRAINT chk_configuracion_calendario_comercial_version",
            "SELECT NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='configuracion_calendario_comercial'::regclass AND conname='chk_configuracion_calendario_comercial_version')",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial DROP CONSTRAINT fk_configuracion_calendario_comercial_instalacion_origen",
            "SELECT NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='configuracion_calendario_comercial'::regclass AND conname='fk_configuracion_calendario_comercial_instalacion_origen')",
        ),
        (
            "ALTER TABLE configuracion_calendario_comercial ALTER COLUMN id_configuracion_calendario_comercial DROP IDENTITY",
            "SELECT attidentity='' FROM pg_attribute WHERE attrelid='configuracion_calendario_comercial'::regclass AND attname='id_configuracion_calendario_comercial'",
        ),
    ],
)
def test_tabla_raiz_incompatible_falla_sin_sanear(db_session, mutation, evidence):
    with db_session.begin_nested():
        db_session.execute(text(mutation))
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        assert db_session.execute(text(evidence)).scalar_one() is True


@pytest.mark.parametrize(
    "function_name",
    [
        "trg_configuracion_calendario_comercial_core_ef",
        "trg_valor_parametro_calendario_comercial",
    ],
)
def test_funcion_homonima_incompatible_falla_sin_reemplazar(db_session, function_name):
    marker = "BODY_INCOMPATIBLE_482"
    with db_session.begin_nested():
        db_session.execute(text(f"""
          CREATE OR REPLACE FUNCTION public.{function_name}() RETURNS trigger
          LANGUAGE plpgsql AS $function$
          BEGIN
            RAISE EXCEPTION '{marker}';
          END $function$
        """))
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))
        definition = db_session.execute(
            text("SELECT pg_get_functiondef(to_regprocedure(:signature))"),
            {"signature": f"public.{function_name}()"},
        ).scalar_one()
        assert marker in definition


@pytest.mark.parametrize("column,value", [
    ("id_tipo_dato_parametro", 999999), ("id_alcance_parametro", 999999),
    ("exponible_api_administrativa", False), ("es_sensible", True),
    ("editable_administrativamente", False), ("nombre_parametro", "incompatible"),
])
def test_definicion_incompatible_falla_sin_sanear(db_session, column, value):
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text(f"UPDATE parametro_sistema SET {column}=:value WHERE codigo_parametro=:code"),
                           {"value": value, "code": CODES[0]})
        db_session.execute(text(_sql()))
    assert _definitions(db_session) == EXPECTED


def test_permiso_y_receptor_canonico_sin_roles_ni_asignaciones_nuevas(db_session):
    assert db_session.execute(text("""
      SELECT p.nombre_permiso,p.descripcion,p.estado_permiso,r.codigo_rol
        FROM permiso p JOIN rol_seguridad_permiso rsp USING(id_permiso)
        JOIN rol_seguridad r USING(id_rol_seguridad)
       WHERE p.codigo_permiso='ADMIN.CONFIG.CALENDARIO_COMERCIAL.ADMINISTRAR'
    """)).one() == (
        "Administrar calendario comercial",
        "Permite crear y programar configuraciones del calendario comercial global, incluyendo día de cierre comercial y día de vencimiento predeterminado de cuotas.",
        "ACTIVO", "ADMINISTRADOR_SISTEMA",
    )
    assert db_session.execute(text("SELECT count(*) FROM rol_seguridad WHERE codigo_rol='ADMIN'")).scalar_one() == 0
    assert db_session.execute(text("""
      SELECT count(*) FROM usuario_rol_seguridad ur JOIN rol_seguridad r USING(id_rol_seguridad)
       WHERE r.codigo_rol='ADMINISTRADOR_SISTEMA'
    """)).scalar_one() == 0


def test_raiz_core_ef_permite_cero_o_una_activa_y_versiona(db_session):
    columns = db_session.execute(text("""
      SELECT column_name FROM information_schema.columns
       WHERE table_schema='public' AND table_name='configuracion_calendario_comercial'
       ORDER BY ordinal_position
    """)).scalars().all()
    assert columns == ["id_configuracion_calendario_comercial", "uid_global", "version_registro",
                       "created_at", "updated_at", "deleted_at", "id_instalacion_origen",
                       "id_instalacion_ultima_modificacion", "op_id_alta", "op_id_ultima_modificacion"]
    assert db_session.execute(text("SELECT count(*) FROM configuracion_calendario_comercial")).scalar_one() == 0
    with db_session.begin_nested():
        root_id = db_session.execute(text("INSERT INTO configuracion_calendario_comercial DEFAULT VALUES RETURNING id_configuracion_calendario_comercial")).scalar_one()
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text("INSERT INTO configuracion_calendario_comercial DEFAULT VALUES"))
        before = db_session.execute(text("SELECT uid_global,created_at,version_registro FROM configuracion_calendario_comercial WHERE id_configuracion_calendario_comercial=:id"), {"id": root_id}).one()
        db_session.execute(text("UPDATE configuracion_calendario_comercial SET uid_global=gen_random_uuid() WHERE id_configuracion_calendario_comercial=:id"), {"id": root_id})
        after = db_session.execute(text("SELECT uid_global,created_at,version_registro FROM configuracion_calendario_comercial WHERE id_configuracion_calendario_comercial=:id"), {"id": root_id}).one()
        assert after[:2] == before[:2]
        assert after.version_registro == 2


@pytest.mark.parametrize("raw,accepted", [("1", True), ("31", True), ("0", False), ("32", False), ("abc", False)])
def test_rango_exclusivo_calendario(db_session, raw, accepted):
    statement = text("""
      INSERT INTO valor_parametro(id_parametro_sistema,valor_parametro,es_valor_vigente)
      SELECT id_parametro_sistema,:raw,false FROM parametro_sistema WHERE codigo_parametro=:code
    """)
    if accepted:
        with db_session.begin_nested():
            db_session.execute(statement, {"raw": raw, "code": CODES[0]})
    else:
        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(statement, {"raw": raw, "code": CODES[0]})


def test_otro_entero_no_queda_limitado_y_global_rechaza_contexto(db_session):
    with db_session.begin_nested():
        db_session.execute(text("""
          INSERT INTO valor_parametro(id_parametro_sistema,valor_parametro,es_valor_vigente)
          SELECT id_parametro_sistema,'999',false FROM parametro_sistema
           WHERE codigo_parametro='PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'
        """))
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("""
          INSERT INTO valor_parametro(id_parametro_sistema,id_instalacion,valor_parametro,es_valor_vigente)
          SELECT id_parametro_sistema,1,'15',false FROM parametro_sistema WHERE codigo_parametro=:code
        """), {"code": CODES[0]})
