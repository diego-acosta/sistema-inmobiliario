from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

PATCH = (
    Path(__file__).parents[1] / "database" / "patch_admin_valor_global_412_20260813.sql"
)


def _sql():
    content = PATCH.read_text(encoding="utf-8")
    return content.replace("BEGIN;", "", 1).rsplit("COMMIT;", 1)[0]


def _counts(db):
    return db.execute(
        text("""
      SELECT
       (SELECT count(*) FROM permiso WHERE codigo_permiso='ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR'),
       (SELECT count(*) FROM rol_seguridad_permiso rsp JOIN rol_seguridad r USING(id_rol_seguridad)
         JOIN permiso p USING(id_permiso) WHERE r.codigo_rol='ADMINISTRADOR_SISTEMA'
          AND p.codigo_permiso='ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR'),
       (SELECT count(*) FROM parametro_sistema WHERE codigo_parametro='PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'),
       (SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p USING(id_parametro_sistema)
         WHERE p.codigo_parametro='PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO' AND v.es_valor_vigente
           AND v.deleted_at IS NULL AND v.id_sucursal IS NULL AND v.id_instalacion IS NULL)
    """)
    ).one()


def test_patch_exact_contract_and_compatible_reexecution(db_session):
    role = db_session.execute(
        text(
            "SELECT nombre_rol,descripcion,estado_rol FROM rol_seguridad WHERE codigo_rol='ADMINISTRADOR_SISTEMA'"
        )
    ).one()
    assert role == (
        "Administrador del sistema",
        "Rol administrativo global para la gestión y configuración del sistema.",
        "ACTIVO",
    )
    permission = db_session.execute(
        text(
            "SELECT nombre_permiso,descripcion,estado_permiso FROM permiso WHERE codigo_permiso='ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR'"
        )
    ).one()
    assert permission == (
        "Modificar valor global de parámetro",
        "Permite modificar un valor GLOBAL administrativo existente y elegible.",
        "ACTIVO",
    )
    parameter = db_session.execute(
        text("""
      SELECT t.codigo_tipo_dato,a.codigo_alcance,p.exponible_api_administrativa,
             p.es_sensible,p.editable_administrativamente,v.valor_parametro
      FROM parametro_sistema p JOIN tipo_dato_parametro t USING(id_tipo_dato_parametro)
      JOIN alcance_parametro a USING(id_alcance_parametro)
      JOIN valor_parametro v USING(id_parametro_sistema)
      WHERE p.codigo_parametro='PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'
        AND v.es_valor_vigente AND v.deleted_at IS NULL
        AND v.id_sucursal IS NULL AND v.id_instalacion IS NULL
    """)
    ).one()
    assert parameter == ("ENTERO", "GLOBAL", True, False, True, "15")
    before = _counts(db_session)
    db_session.execute(text(_sql()))
    assert _counts(db_session) == before == (1, 1, 1, 1)


@pytest.mark.parametrize("mode", ["missing", "inactive"])
def test_patch_requires_exactly_one_active_role_and_creates_nothing_on_failure(
    db_session, mode
):
    before = _counts(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        if mode == "missing":
            db_session.execute(
                text(
                    "DELETE FROM rol_seguridad_permiso WHERE id_rol_seguridad IN (SELECT id_rol_seguridad FROM rol_seguridad WHERE codigo_rol='ADMINISTRADOR_SISTEMA')"
                )
            )
            db_session.execute(
                text(
                    "DELETE FROM rol_seguridad WHERE codigo_rol='ADMINISTRADOR_SISTEMA'"
                )
            )
        else:
            db_session.execute(
                text(
                    "UPDATE rol_seguridad SET estado_rol='INACTIVO' WHERE codigo_rol='ADMINISTRADOR_SISTEMA'"
                )
            )
        db_session.execute(text(_sql()))
    assert _counts(db_session) == before


def test_incompatible_permission_aborts_without_partial_seed(db_session):
    before = _counts(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(
            text(
                "UPDATE permiso SET descripcion='incompatible' WHERE codigo_permiso='ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR'"
            )
        )
        db_session.execute(
            text(
                "DELETE FROM valor_parametro WHERE id_parametro_sistema IN (SELECT id_parametro_sistema FROM parametro_sistema WHERE codigo_parametro='PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO')"
            )
        )
        db_session.execute(
            text(
                "DELETE FROM parametro_sistema WHERE codigo_parametro='PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO'"
            )
        )
        db_session.execute(text(_sql()))
    assert _counts(db_session) == before
