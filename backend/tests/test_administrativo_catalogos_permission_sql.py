from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
    AdministrativeAuthorizationService,
)


BACKEND = Path(__file__).parents[1]
PATCH = BACKEND / "database/patch_admin_catalogos_permission_20260924.sql"
RESET_SH = BACKEND / "scripts/reset_db.sh"
RESET_BAT = BACKEND / "scripts/reset_db.bat"
PERMISSION_CODE = "ADMIN.CONFIG.CATALOGO.ADMINISTRAR"
PERMISSION_NAME = "Administrar catálogos"
PERMISSION_DESCRIPTION = (
    "Permite crear, modificar, cambiar estado y dar de baja catálogos maestros "
    "y sus ítems configurables."
)


def _sql() -> str:
    content = PATCH.read_text(encoding="utf-8")
    return content.replace("BEGIN;", "", 1).rsplit("COMMIT;", 1)[0]


def _counts(db_session) -> tuple[int, int]:
    return db_session.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM permiso WHERE codigo_permiso=:permission_code),
              (SELECT count(*)
                 FROM rol_seguridad_permiso rsp
                 JOIN rol_seguridad r USING(id_rol_seguridad)
                 JOIN permiso p USING(id_permiso)
                WHERE r.codigo_rol='ADMINISTRADOR_SISTEMA'
                  AND p.codigo_permiso=:permission_code)
            """
        ),
        {"permission_code": PERMISSION_CODE},
    ).one()


def _delete_permission(db_session) -> None:
    db_session.execute(
        text(
            """
            DELETE FROM rol_seguridad_permiso
             WHERE id_permiso IN (
               SELECT id_permiso FROM permiso WHERE codigo_permiso=:permission_code
             )
            """
        ),
        {"permission_code": PERMISSION_CODE},
    )
    db_session.execute(
        text("DELETE FROM permiso WHERE codigo_permiso=:permission_code"),
        {"permission_code": PERMISSION_CODE},
    )


def test_reset_scripts_include_patch_in_symmetric_deterministic_order():
    sh = RESET_SH.read_text(encoding="utf-8")
    bat = RESET_BAT.read_text(encoding="utf-8")

    assert sh.count(PATCH.name) == 2
    assert bat.count("PATCH_ADMIN_CATALOGOS_PERMISSION_FILE") == 5
    assert sh.index("patch_auth_central_20260914.sql") < sh.index(PATCH.name)
    assert bat.index("PATCH_AUTH_CENTRAL_FILE") < bat.index(
        "PATCH_ADMIN_CATALOGOS_PERMISSION_FILE"
    )
    assert bat.count(
        '-f "%PATCH_ADMIN_CATALOGOS_PERMISSION_FILE%"'
    ) == 2
    assert all(
        "ON_ERROR_STOP=1" in line
        for line in bat.splitlines()
        if '-f "%PATCH_ADMIN_CATALOGOS_PERMISSION_FILE%"' in line
    )


def test_first_application_creates_exact_permission_and_grant(db_session):
    with db_session.begin_nested():
        _delete_permission(db_session)
        assert _counts(db_session) == (0, 0)

        db_session.execute(text(_sql()))

        permission = db_session.execute(
            text(
                """
                SELECT nombre_permiso, descripcion, estado_permiso
                  FROM permiso
                 WHERE codigo_permiso=:permission_code
                """
            ),
            {"permission_code": PERMISSION_CODE},
        ).one()
        assert permission == (
            PERMISSION_NAME,
            PERMISSION_DESCRIPTION,
            "ACTIVO",
        )
        assert _counts(db_session) == (1, 1)


def test_compatible_reexecution_does_not_duplicate_permission_or_grant(db_session):
    before = _counts(db_session)
    db_session.execute(text(_sql()))
    assert _counts(db_session) == before == (1, 1)


@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("nombre_permiso", "Nombre incompatible"),
        ("descripcion", "Descripción incompatible"),
        ("estado_permiso", "INACTIVO"),
    ],
)
def test_permission_contract_drift_is_rejected(db_session, column, value):
    before = _counts(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(
            text(
                f"UPDATE permiso SET {column}=:value "
                "WHERE codigo_permiso=:permission_code"
            ),
            {"value": value, "permission_code": PERMISSION_CODE},
        )
        db_session.execute(text(_sql()))
    assert _counts(db_session) == before


@pytest.mark.parametrize("mode", ["missing", "inactive"])
def test_patch_requires_exactly_one_active_canonical_role(db_session, mode):
    before = _counts(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        if mode == "missing":
            db_session.execute(
                text(
                    "UPDATE rol_seguridad SET codigo_rol='ADMINISTRADOR_SISTEMA_AUSENTE' "
                    "WHERE codigo_rol='ADMINISTRADOR_SISTEMA'"
                )
            )
        else:
            db_session.execute(
                text(
                    "UPDATE rol_seguridad SET estado_rol='INACTIVO' "
                    "WHERE codigo_rol='ADMINISTRADOR_SISTEMA'"
                )
            )
        db_session.execute(text(_sql()))
    assert _counts(db_session) == before


def test_duplicate_permission_is_rejected(db_session):
    before = _counts(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("ALTER TABLE permiso DROP CONSTRAINT uq_permiso_codigo"))
        db_session.execute(
            text(
                """
                INSERT INTO permiso (
                  codigo_permiso, nombre_permiso, descripcion, estado_permiso
                ) VALUES (
                  :permission_code, :name, :description, 'ACTIVO'
                )
                """
            ),
            {
                "permission_code": PERMISSION_CODE,
                "name": PERMISSION_NAME,
                "description": PERMISSION_DESCRIPTION,
            },
        )
        db_session.execute(text(_sql()))
    assert _counts(db_session) == before


def test_duplicate_role_permission_grant_is_rejected(db_session):
    before = _counts(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(
            text(
                """
                INSERT INTO rol_seguridad_permiso (id_rol_seguridad, id_permiso)
                SELECT r.id_rol_seguridad, p.id_permiso
                  FROM rol_seguridad r
                  JOIN permiso p ON p.codigo_permiso=:permission_code
                 WHERE r.codigo_rol='ADMINISTRADOR_SISTEMA'
                """
            ),
            {"permission_code": PERMISSION_CODE},
        )
        db_session.execute(text(_sql()))
    assert _counts(db_session) == before


def test_patch_rolls_back_permission_when_grant_insert_fails(db_session):
    with db_session.begin_nested():
        _delete_permission(db_session)
        db_session.execute(
            text(
                """
                CREATE FUNCTION pg_temp.reject_catalog_permission_grant()
                RETURNS trigger LANGUAGE plpgsql AS $function$
                BEGIN
                  IF EXISTS (
                    SELECT 1 FROM permiso p
                     WHERE p.id_permiso=NEW.id_permiso
                       AND p.codigo_permiso='ADMIN.CONFIG.CATALOGO.ADMINISTRAR'
                  ) THEN
                    RAISE EXCEPTION 'grant rechazado para probar atomicidad';
                  END IF;
                  RETURN NEW;
                END
                $function$
                """
            )
        )
        db_session.execute(
            text(
                """
                CREATE TRIGGER reject_catalog_permission_grant
                BEFORE INSERT ON rol_seguridad_permiso
                FOR EACH ROW EXECUTE FUNCTION pg_temp.reject_catalog_permission_grant()
                """
            )
        )

        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))

        assert _counts(db_session) == (0, 0)


def test_materialized_permission_is_resolvable_by_existing_d1(db_session):
    suffix = uuid4().hex
    user_id = db_session.execute(
        text(
            """
            INSERT INTO usuario (codigo_usuario, login, estado_usuario)
            VALUES (:code, :login, 'ACTIVO')
            RETURNING id_usuario
            """
        ),
        {"code": f"USR-CAT-{suffix}", "login": f"usr-cat-{suffix}"},
    ).scalar_one()
    role_id = db_session.execute(
        text(
            "SELECT id_rol_seguridad FROM rol_seguridad "
            "WHERE codigo_rol='ADMINISTRADOR_SISTEMA'"
        )
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO usuario_rol_seguridad (
              id_usuario, id_rol_seguridad, fecha_desde
            ) VALUES (
              :user_id, :role_id,
              clock_timestamp() AT TIME ZONE 'UTC' - interval '1 minute'
            )
            """
        ),
        {"user_id": user_id, "role_id": role_id},
    )

    decision = AdministrativeAuthorizationService(db_session).authorize(
        user_id,
        PERMISSION_CODE,
    )

    assert decision is AdministrativeAuthorizationDecision.GRANTED
