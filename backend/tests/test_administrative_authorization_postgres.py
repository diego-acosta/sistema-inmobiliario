from uuid import uuid4

import pytest
from sqlalchemy import text

from app.api.core_ef_headers import CoreEFHeaders
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
    AdministrativeAuthorizationMode,
    AdministrativeAuthorizationService,
    AdministrativeAuthorizationTechnicalError,
    HOpPredicate,
    ScopeCapability,
)
from app.infrastructure.persistence.repositories.usuario_rol_seguridad_repository import (
    UsuarioRolSeguridadRepository,
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


def _assign_global(db_session, user_id, role_id, start_sql, end_sql="NULL", deleted_sql="NULL"):
    db_session.execute(
        text(f"""
            INSERT INTO usuario_rol_seguridad
                (id_usuario, id_rol_seguridad, fecha_desde, fecha_hasta, deleted_at)
            VALUES (:user_id, :role_id, {start_sql}, {end_sql}, {deleted_sql})
        """),
        {"user_id": user_id, "role_id": role_id},
    )


def _insert_branch(db_session, suffix: str) -> int:
    return db_session.execute(
        text("""
            INSERT INTO sucursal (codigo_sucursal, nombre_sucursal, estado_sucursal)
            VALUES (:code, :name, 'ACTIVA') RETURNING id_sucursal
        """),
        {"code": f"SUC-{suffix}", "name": suffix},
    ).scalar_one()


def _assign_context(db_session, user_id, role_id, branch_id, start_sql, end_sql="NULL"):
    db_session.execute(
        text(f"""
            INSERT INTO usuario_rol_sucursal
                (id_usuario, id_rol_seguridad, id_sucursal, fecha_desde, fecha_hasta)
            VALUES (:user_id, :role_id, :branch_id, {start_sql}, {end_sql})
        """),
        {"user_id": user_id, "role_id": role_id, "branch_id": branch_id},
    )


def _global(db_session, user_id, code):
    return AdministrativeAuthorizationService(db_session).authorize(user_id, code)


def _contextual(db_session, user_id, code, branch_id, h_op=None):
    return AdministrativeAuthorizationService(db_session).authorize(
        user_id,
        code,
        mode=AdministrativeAuthorizationMode.EXPLICIT_CONTEXT,
        id_sucursal=branch_id,
        h_op=h_op or HOpPredicate(),
    )


def _assign_user_branch(
    db_session,
    user_id,
    branch_id,
    *,
    can_query=False,
    can_operate=False,
    can_administer=False,
    state="ACTIVO",
):
    db_session.execute(
        text("""
            INSERT INTO usuario_sucursal
                (id_usuario, id_sucursal, estado_vinculo,
                 puede_consultar, puede_operar, puede_administrar,
                 fecha_desde, fecha_hasta)
            VALUES
                (:user_id, :branch_id, :state,
                 :can_query, :can_operate, :can_administer,
                 clock_timestamp() AT TIME ZONE 'UTC' - interval '1 hour',
                 clock_timestamp() AT TIME ZONE 'UTC' + interval '1 hour')
        """),
        {
            "user_id": user_id,
            "branch_id": branch_id,
            "can_query": can_query,
            "can_operate": can_operate,
            "can_administer": can_administer,
            "state": state,
        },
    )


def test_postgres_global_vigency_states_and_half_open_interval(db_session):
    utc_now = "clock_timestamp() AT TIME ZONE 'UTC'"
    cases = [
        ("valid", f"{utc_now}-interval '1 hour'", "NULL", "NULL", "ACTIVO", "ACTIVO", True),
        ("future", f"{utc_now}+interval '1 hour'", "NULL", "NULL", "ACTIVO", "ACTIVO", False),
        ("end-now", f"{utc_now}-interval '1 hour'", utc_now, "NULL", "ACTIVO", "ACTIVO", False),
        ("empty", utc_now, utc_now, "NULL", "ACTIVO", "ACTIVO", False),
        ("deleted", f"{utc_now}-interval '1 hour'", "NULL", utc_now, "ACTIVO", "ACTIVO", False),
        ("role-off", f"{utc_now}-interval '1 hour'", "NULL", "NULL", "INACTIVO", "ACTIVO", False),
        ("permission-off", f"{utc_now}-interval '1 hour'", "NULL", "NULL", "ACTIVO", "INACTIVO", False),
    ]
    for suffix, start, end, deleted, role_state, permission_state, granted in cases:
        user_id, role_id, _, code = _insert_chain(
            db_session, suffix, role_state=role_state, permission_state=permission_state
        )
        _assign_global(db_session, user_id, role_id, start, end, deleted)
        expected = (
            AdministrativeAuthorizationDecision.GRANTED
            if granted
            else AdministrativeAuthorizationDecision.DENIED
        )
        assert _global(db_session, user_id, code) is expected

    with pytest.raises(AdministrativeAuthorizationTechnicalError):
        _global(db_session, user_id, code.swapcase())


def test_postgres_unknown_permission_state_is_technical_error(db_session):
    user_id, role_id, _, code = _insert_chain(
        db_session, "permission-unknown", permission_state="DESCONOCIDO"
    )
    _assign_global(db_session, user_id, role_id, "clock_timestamp() AT TIME ZONE 'UTC'")

    with pytest.raises(AdministrativeAuthorizationTechnicalError):
        _global(db_session, user_id, code)


def test_postgres_unknown_role_state_is_technical_error(db_session):
    user_id, role_id, _, code = _insert_chain(
        db_session, "role-unknown", role_state="DESCONOCIDO"
    )
    _assign_global(db_session, user_id, role_id, "clock_timestamp() AT TIME ZONE 'UTC'")

    with pytest.raises(AdministrativeAuthorizationTechnicalError):
        _global(db_session, user_id, code)


def test_postgres_unknown_user_state_is_technical_error(db_session):
    user_id, role_id, _, code = _insert_chain(db_session, "user-unknown")
    _assign_global(db_session, user_id, role_id, "clock_timestamp() AT TIME ZONE 'UTC'")
    db_session.execute(
        text("UPDATE usuario SET estado_usuario = 'DESCONOCIDO' WHERE id_usuario = :id"),
        {"id": user_id},
    )

    with pytest.raises(AdministrativeAuthorizationTechnicalError):
        _global(db_session, user_id, code)


def test_postgres_unknown_assignment_state_is_technical_error(db_session):
    user_id, role_id, _, code = _insert_chain(db_session, "assignment-unknown")
    branch_id = _insert_branch(db_session, "assignment-unknown")
    _assign_context(
        db_session,
        user_id,
        role_id,
        branch_id,
        "clock_timestamp() AT TIME ZONE 'UTC' - interval '1 hour'",
    )
    _assign_user_branch(
        db_session,
        user_id,
        branch_id,
        can_query=True,
        state="DESCONOCIDO",
    )

    with pytest.raises(AdministrativeAuthorizationTechnicalError):
        _contextual(
            db_session,
            user_id,
            code,
            branch_id,
            HOpPredicate(
                required_capabilities=frozenset({ScopeCapability.QUERY})
            ),
        )


def test_postgres_multiple_global_roles_and_explicit_deny_precedence(db_session):
    user_id, role_id, permission_id, code = _insert_chain(db_session, "multi-deny")
    _assign_global(db_session, user_id, role_id, "clock_timestamp() AT TIME ZONE 'UTC'")
    second_role = db_session.execute(
        text("""
            INSERT INTO rol_seguridad (codigo_rol, nombre_rol, estado_rol)
            VALUES ('ROL-multi-deny-2', 'multi-deny-2', 'ACTIVO')
            RETURNING id_rol_seguridad
        """)
    ).scalar_one()
    db_session.execute(
        text("""
            INSERT INTO rol_seguridad_permiso (id_rol_seguridad, id_permiso)
            VALUES (:role, :permission)
        """),
        {"role": second_role, "permission": permission_id},
    )
    _assign_global(db_session, user_id, second_role, "clock_timestamp() AT TIME ZONE 'UTC'")
    assert _global(db_session, user_id, code) is AdministrativeAuthorizationDecision.GRANTED
    db_session.execute(
        text("""
            INSERT INTO denegacion_explicita (id_usuario, id_permiso, motivo)
            VALUES (:user, :permission, 'uno'), (:user, :permission, 'dos')
        """),
        {"user": user_id, "permission": permission_id},
    )
    assert _global(db_session, user_id, code) is AdministrativeAuthorizationDecision.DENIED


def test_postgres_contextual_grant_is_scoped_and_needs_no_global_grant(db_session):
    user_id, role_id, permission_id, code = _insert_chain(db_session, "context")
    branch_a = _insert_branch(db_session, "context-a")
    branch_b = _insert_branch(db_session, "context-b")
    _assign_context(
        db_session,
        user_id,
        role_id,
        branch_a,
        "clock_timestamp() AT TIME ZONE 'UTC' - interval '1 hour'",
    )
    assert _global(db_session, user_id, code) is AdministrativeAuthorizationDecision.DENIED
    assert _contextual(db_session, user_id, code, branch_a) is AdministrativeAuthorizationDecision.GRANTED
    assert _contextual(db_session, user_id, code, branch_b) is AdministrativeAuthorizationDecision.DENIED
    db_session.execute(
        text("INSERT INTO denegacion_explicita (id_usuario, id_permiso) VALUES (:u, :p)"),
        {"u": user_id, "p": permission_id},
    )
    assert _contextual(db_session, user_id, code, branch_a) is AdministrativeAuthorizationDecision.DENIED


@pytest.mark.parametrize(
    ("suffix", "capabilities", "first", "second", "combined"),
    [
        (
            "same-row-query-admin",
            frozenset({ScopeCapability.QUERY, ScopeCapability.ADMINISTER}),
            {"can_query": True},
            {"can_administer": True},
            {"can_query": True, "can_administer": True},
        ),
        (
            "same-row-operate-admin",
            frozenset({ScopeCapability.OPERATE, ScopeCapability.ADMINISTER}),
            {"can_operate": True},
            {"can_administer": True},
            {"can_operate": True, "can_administer": True},
        ),
    ],
)
def test_postgres_contextual_capabilities_must_share_one_current_assignment(
    db_session, suffix, capabilities, first, second, combined
):
    user_id, role_id, _, code = _insert_chain(db_session, suffix)
    branch_id = _insert_branch(db_session, suffix)
    _assign_context(
        db_session,
        user_id,
        role_id,
        branch_id,
        "clock_timestamp() AT TIME ZONE 'UTC' - interval '1 hour'",
    )
    _assign_user_branch(db_session, user_id, branch_id, **first)
    _assign_user_branch(db_session, user_id, branch_id, **second)
    h_op = HOpPredicate(required_capabilities=capabilities)

    assert _contextual(
        db_session, user_id, code, branch_id, h_op
    ) is AdministrativeAuthorizationDecision.DENIED

    _assign_user_branch(db_session, user_id, branch_id, **combined)

    assert _contextual(
        db_session, user_id, code, branch_id, h_op
    ) is AdministrativeAuthorizationDecision.GRANTED


def test_postgres_decision_is_independent_of_session_timezone(db_session):
    user_id, role_id, _, code = _insert_chain(db_session, "timezone")
    _assign_global(
        db_session,
        user_id,
        role_id,
        "clock_timestamp() AT TIME ZONE 'UTC' - interval '1 minute'",
        "clock_timestamp() AT TIME ZONE 'UTC' + interval '1 minute'",
    )
    decisions = []
    for timezone in ("UTC", "America/Argentina/Buenos_Aires", "Pacific/Auckland"):
        db_session.execute(
            text("SELECT set_config('TimeZone', :timezone, true)"),
            {"timezone": timezone},
        )
        decisions.append(_global(db_session, user_id, code))
    assert decisions == [AdministrativeAuthorizationDecision.GRANTED] * 3


def test_postgres_read_only_resolution_does_not_mutate_session_or_outbox(db_session):
    user_id, role_id, _, code = _insert_chain(db_session, "readonly")
    _assign_global(db_session, user_id, role_id, "clock_timestamp() AT TIME ZONE 'UTC'")
    before = db_session.execute(
        text("SELECT version_registro, updated_at FROM usuario WHERE id_usuario=:id"),
        {"id": user_id},
    ).one()
    outbox_before = db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one()
    assert _global(db_session, user_id, code) is AdministrativeAuthorizationDecision.GRANTED
    assert db_session.execute(
        text("SELECT version_registro, updated_at FROM usuario WHERE id_usuario=:id"),
        {"id": user_id},
    ).one() == before
    assert db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one() == outbox_before


def test_postgres_usuario_rol_seguridad_writer_and_evaluator_share_utc(db_session):
    user_id, role_id, _, code = _insert_chain(db_session, "writer-utc")
    db_session.execute(
        text("SELECT set_config('TimeZone', 'America/Argentina/Buenos_Aires', true)")
    )
    utc_before_create = db_session.execute(
        text("SELECT clock_timestamp() AT TIME ZONE 'UTC'")
    ).scalar_one()
    repository = UsuarioRolSeguridadRepository(db_session)
    created = repository.create(
        user_id,
        {"id_rol_seguridad": role_id},
        CoreEFHeaders(uuid4(), user_id, 1, 1),
    )
    utc_after_create = db_session.execute(
        text("SELECT clock_timestamp() AT TIME ZONE 'UTC'")
    ).scalar_one()

    assert created is not None
    assert utc_before_create <= created["fecha_desde"] <= utc_after_create
    assert _global(db_session, user_id, code) is AdministrativeAuthorizationDecision.GRANTED

    utc_before_delete = db_session.execute(
        text("SELECT clock_timestamp() AT TIME ZONE 'UTC'")
    ).scalar_one()
    deleted = repository.baja_logica(
        user_id,
        created["id_usuario_rol_seguridad"],
        core=CoreEFHeaders(uuid4(), user_id, 1, 1),
        if_match_version=created["version_registro"],
    )
    utc_after_delete = db_session.execute(
        text("SELECT clock_timestamp() AT TIME ZONE 'UTC'")
    ).scalar_one()

    assert deleted is not None
    assert utc_before_delete <= deleted["fecha_hasta"] <= utc_after_delete
    assert _global(db_session, user_id, code) is AdministrativeAuthorizationDecision.DENIED
