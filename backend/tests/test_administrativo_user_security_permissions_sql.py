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
PATCH = BACKEND / "database/patch_admin_user_security_permissions_20260926.sql"
RESET_SH = BACKEND / "scripts/reset_db.sh"
RESET_BAT = BACKEND / "scripts/reset_db.bat"
PERMISSIONS = (
    (
        "ADMIN.USUARIO.ADMINISTRAR",
        "Administrar usuarios",
        "Permite crear y dar de baja usuarios del sistema.",
    ),
    (
        "ADMIN.SEGURIDAD.GRANTS.ADMINISTRAR",
        "Administrar grants de seguridad",
        "Permite asignar y revocar roles de seguridad de usuarios.",
    ),
    (
        "ADMIN.USUARIO_SUCURSAL.ADMINISTRAR",
        "Administrar alcance de usuarios por sucursal",
        "Permite asignar sucursales y capacidades operativas a usuarios.",
    ),
)
PERMISSION_CODES = tuple(permission[0] for permission in PERMISSIONS)


def _sql() -> str:
    content = PATCH.read_text(encoding="utf-8")
    return content.replace("BEGIN;", "", 1).rsplit("COMMIT;", 1)[0]


def _counts(db_session) -> tuple[int, int]:
    return db_session.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM permiso WHERE codigo_permiso = ANY(:codes)),
              (SELECT count(*)
                 FROM rol_seguridad_permiso rsp
                 JOIN rol_seguridad r USING(id_rol_seguridad)
                 JOIN permiso p USING(id_permiso)
                WHERE r.codigo_rol='ADMINISTRADOR_SISTEMA'
                  AND p.codigo_permiso = ANY(:codes))
            """
        ),
        {"codes": list(PERMISSION_CODES)},
    ).one()


def _delete_permissions(db_session) -> None:
    db_session.execute(
        text(
            """
            DELETE FROM rol_seguridad_permiso
             WHERE id_permiso IN (
               SELECT id_permiso FROM permiso WHERE codigo_permiso = ANY(:codes)
             )
            """
        ),
        {"codes": list(PERMISSION_CODES)},
    )
    db_session.execute(
        text("DELETE FROM permiso WHERE codigo_permiso = ANY(:codes)"),
        {"codes": list(PERMISSION_CODES)},
    )


def _materialize_permissions(db_session) -> None:
    db_session.execute(text(_sql()))
    assert _counts(db_session) == (3, 3)


def test_reset_scripts_include_patch_in_symmetric_deterministic_order():
    sh = RESET_SH.read_text(encoding="utf-8")
    bat = RESET_BAT.read_text(encoding="utf-8")

    assert sh.count(PATCH.name) == 2
    assert bat.count("PATCH_ADMIN_USER_SECURITY_PERMISSIONS_FILE") == 5
    assert sh.index("patch_admin_catalogos_permission_20260924.sql") < sh.index(
        PATCH.name
    )
    assert bat.index("PATCH_ADMIN_CATALOGOS_PERMISSION_FILE") < bat.index(
        "PATCH_ADMIN_USER_SECURITY_PERMISSIONS_FILE"
    )
    assert bat.count(
        '-f "%PATCH_ADMIN_USER_SECURITY_PERMISSIONS_FILE%"'
    ) == 2
    assert all(
        "ON_ERROR_STOP=1" in line
        for line in bat.splitlines()
        if '-f "%PATCH_ADMIN_USER_SECURITY_PERMISSIONS_FILE%"' in line
    )


def test_first_application_creates_exact_permissions_and_grants(db_session):
    with db_session.begin_nested():
        _delete_permissions(db_session)
        assert _counts(db_session) == (0, 0)

        db_session.execute(text(_sql()))

        permissions = db_session.execute(
            text(
                """
                SELECT codigo_permiso, nombre_permiso, descripcion, estado_permiso
                  FROM permiso
                 WHERE codigo_permiso = ANY(:codes)
                 ORDER BY codigo_permiso
                """
            ),
            {"codes": list(PERMISSION_CODES)},
        ).all()
        expected = sorted(
            (code, name, description, "ACTIVO")
            for code, name, description in PERMISSIONS
        )
        assert permissions == expected
        assert _counts(db_session) == (3, 3)


def test_compatible_reexecution_does_not_duplicate_permissions_or_grants(db_session):
    _materialize_permissions(db_session)
    before = _counts(db_session)
    db_session.execute(text(_sql()))
    assert _counts(db_session) == before == (3, 3)


@pytest.mark.parametrize("permission_code", PERMISSION_CODES)
@pytest.mark.parametrize(
    ("column", "value"),
    [
        ("nombre_permiso", "Nombre incompatible"),
        ("descripcion", "Descripción incompatible"),
        ("estado_permiso", "INACTIVO"),
    ],
)
def test_permission_contract_drift_is_rejected(
    db_session, permission_code, column, value
):
    _materialize_permissions(db_session)
    before = _counts(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        result = db_session.execute(
            text(
                f"UPDATE permiso SET {column}=:value "
                "WHERE codigo_permiso=:permission_code"
            ),
            {"value": value, "permission_code": permission_code},
        )
        assert result.rowcount == 1
        db_session.execute(text(_sql()))
    assert _counts(db_session) == before


@pytest.mark.parametrize("mode", ["missing", "inactive"])
def test_patch_requires_exactly_one_active_canonical_role(db_session, mode):
    before = _counts(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        if mode == "missing":
            db_session.execute(
                text(
                    "UPDATE rol_seguridad "
                    "SET codigo_rol='ADMINISTRADOR_SISTEMA_AUSENTE' "
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


@pytest.mark.parametrize("permission_code", PERMISSION_CODES)
def test_duplicate_permission_is_rejected(db_session, permission_code):
    _materialize_permissions(db_session)
    before = _counts(db_session)
    contract = next(item for item in PERMISSIONS if item[0] == permission_code)
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
                "permission_code": contract[0],
                "name": contract[1],
                "description": contract[2],
            },
        )
        db_session.execute(text(_sql()))
    assert _counts(db_session) == before


@pytest.mark.parametrize("permission_code", PERMISSION_CODES)
def test_duplicate_role_permission_grant_is_rejected(db_session, permission_code):
    _materialize_permissions(db_session)
    before = _counts(db_session)
    with pytest.raises(DBAPIError), db_session.begin_nested():
        db_session.execute(text("DROP INDEX ux_rol_seguridad_permiso"))
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
            {"permission_code": permission_code},
        )
        db_session.execute(text(_sql()))
    assert _counts(db_session) == before


def test_patch_rolls_back_all_permissions_when_a_grant_insert_fails(db_session):
    with db_session.begin_nested():
        _delete_permissions(db_session)
        db_session.execute(
            text(
                """
                CREATE FUNCTION pg_temp.reject_user_scope_permission_grant()
                RETURNS trigger LANGUAGE plpgsql AS $function$
                BEGIN
                  IF EXISTS (
                    SELECT 1 FROM permiso p
                     WHERE p.id_permiso=NEW.id_permiso
                       AND p.codigo_permiso='ADMIN.USUARIO_SUCURSAL.ADMINISTRAR'
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
                CREATE TRIGGER reject_user_scope_permission_grant
                BEFORE INSERT ON rol_seguridad_permiso
                FOR EACH ROW EXECUTE FUNCTION
                  pg_temp.reject_user_scope_permission_grant()
                """
            )
        )

        with pytest.raises(DBAPIError), db_session.begin_nested():
            db_session.execute(text(_sql()))

        assert _counts(db_session) == (0, 0)


def test_materialized_permissions_are_resolvable_by_existing_d1(db_session):
    _materialize_permissions(db_session)
    suffix = uuid4().hex
    user_id = db_session.execute(
        text(
            """
            INSERT INTO usuario (codigo_usuario, login, estado_usuario)
            VALUES (:code, :login, 'ACTIVO')
            RETURNING id_usuario
            """
        ),
        {"code": f"USR-SEC-{suffix}", "login": f"usr-sec-{suffix}"},
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

    service = AdministrativeAuthorizationService(db_session)
    for permission_code in PERMISSION_CODES:
        assert service.authorize(
            user_id,
            permission_code,
        ) is AdministrativeAuthorizationDecision.GRANTED
