from sqlalchemy import text

from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
    AdministrativeAuthorizationService,
    AdministrativeAuthorizationTechnicalError,
)


def _insert_chain(db_session, suffix: str, *, role_state="ACTIVO", permission_state="ACTIVO"):
    user_id = db_session.execute(
        text("""
            INSERT INTO usuario (codigo_usuario, login, estado_usuario)
            VALUES (:code, :login, 'ACTIVO') RETURNING id_usuario
        """),
        {"code": f"USR-{suffix}", "login": f"usr-{suffix}"},
    ).scalar_one()
    role_id = db_session.execute(
        text("""
            INSERT INTO rol_seguridad (codigo_rol, nombre_rol, estado_rol)
            VALUES (:code, :name, :state) RETURNING id_rol_seguridad
        """),
        {"code": f"ROL-{suffix}", "name": suffix, "state": role_state},
    ).scalar_one()
    permission_code = f"test.authorization.{suffix}"
    permission_id = db_session.execute(
        text("""
            INSERT INTO permiso (codigo_permiso, nombre_permiso, estado_permiso)
            VALUES (:code, :name, :state) RETURNING id_permiso
        """),
        {"code": permission_code, "name": suffix, "state": permission_state},
    ).scalar_one()
    db_session.execute(
        text("""
            INSERT INTO rol_seguridad_permiso (id_rol_seguridad, id_permiso)
            VALUES (:role_id, :permission_id)
        """),
        {"role_id": role_id, "permission_id": permission_id},
    )
    return user_id, role_id, permission_id, permission_code


def _assign(db_session, user_id, role_id, start_sql, end_sql="NULL", deleted_sql="NULL"):
    db_session.execute(
        text(f"""
            INSERT INTO usuario_rol_seguridad
                (id_usuario, id_rol_seguridad, fecha_desde, fecha_hasta, deleted_at)
            VALUES (:user_id, :role_id, {start_sql}, {end_sql}, {deleted_sql})
        """),
        {"user_id": user_id, "role_id": role_id},
    )


def _decision(db_session, user_id, permission_code):
    return AdministrativeAuthorizationService(db_session).authorize(
        user_id, permission_code
    )


def test_postgres_vigency_boundaries_states_cardinality_and_case(db_session):
    cases = [
        ("valid", "clock_timestamp()", "NULL", "NULL", "ACTIVO", "ACTIVO", True),
        ("future", "clock_timestamp()+interval '1 hour'", "NULL", "NULL", "ACTIVO", "ACTIVO", False),
        ("end-now", "clock_timestamp()-interval '1 hour'", "clock_timestamp()", "NULL", "ACTIVO", "ACTIVO", False),
        ("end-future", "clock_timestamp()-interval '1 hour'", "clock_timestamp()+interval '1 hour'", "NULL", "ACTIVO", "ACTIVO", True),
        ("deleted", "clock_timestamp()-interval '1 hour'", "NULL", "clock_timestamp()", "ACTIVO", "ACTIVO", False),
        ("role-off", "clock_timestamp()-interval '1 hour'", "NULL", "NULL", "INACTIVO", "ACTIVO", False),
        ("permission-off", "clock_timestamp()-interval '1 hour'", "NULL", "NULL", "ACTIVO", "INACTIVO", False),
    ]
    for suffix, start, end, deleted, role_state, permission_state, granted in cases:
        user_id, role_id, _, code = _insert_chain(
            db_session,
            suffix,
            role_state=role_state,
            permission_state=permission_state,
        )
        _assign(db_session, user_id, role_id, start, end, deleted)
        expected = (
            AdministrativeAuthorizationDecision.GRANTED
            if granted
            else AdministrativeAuthorizationDecision.DENIED
        )
        assert _decision(db_session, user_id, code) is expected

    # El código con case distinto no existe físicamente: no es un deny ordinario.
    try:
        _decision(db_session, user_id, code.swapcase())
    except AdministrativeAuthorizationTechnicalError:
        pass
    else:
        raise AssertionError("El permiso debe compararse de forma case-sensitive")


def test_postgres_multiple_roles_and_duplicate_grants_do_not_break_cardinality(db_session):
    user_id, role_id, permission_id, code = _insert_chain(db_session, "multi")
    _assign(db_session, user_id, role_id, "clock_timestamp()")
    second_role = db_session.execute(
        text("""
            INSERT INTO rol_seguridad (codigo_rol, nombre_rol, estado_rol)
            VALUES ('ROL-multi-2', 'multi-2', 'ACTIVO') RETURNING id_rol_seguridad
        """)
    ).scalar_one()
    db_session.execute(
        text("""
            INSERT INTO rol_seguridad_permiso (id_rol_seguridad, id_permiso)
            VALUES (:role, :permission)
        """),
        {"role": second_role, "permission": permission_id},
    )
    _assign(db_session, user_id, second_role, "clock_timestamp()")
    assert _decision(db_session, user_id, code) is AdministrativeAuthorizationDecision.GRANTED


def test_postgres_read_only_resolution_does_not_mutate_session_or_outbox(db_session):
    user_id, role_id, _, code = _insert_chain(db_session, "readonly")
    _assign(db_session, user_id, role_id, "clock_timestamp()")
    before = db_session.execute(
        text("""
            SELECT version_registro, updated_at FROM usuario WHERE id_usuario=:id
        """),
        {"id": user_id},
    ).one()
    outbox_before = db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one()
    assert _decision(db_session, user_id, code) is AdministrativeAuthorizationDecision.GRANTED
    assert db_session.execute(
        text("SELECT version_registro, updated_at FROM usuario WHERE id_usuario=:id"),
        {"id": user_id},
    ).one() == before
    assert db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one() == outbox_before
