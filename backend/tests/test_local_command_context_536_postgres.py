from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from app.api.core_ef_headers import parse_local_command_core_ef_headers
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.common.local_command_context import (
    InstallationAssertionMismatch,
    InstallationBranchMismatch,
    LocalCommandActor,
    LocalCommandContextPolicy,
    OperationalBranchNotEligible,
    OperationalBranchScopeDenied,
    resolve_local_command_context,
)
from sqlalchemy import text


def _principal(id_usuario=1):
    return AuthenticatedPrincipal(
        id_usuario=id_usuario,
        codigo_usuario=f"USR-{id_usuario}",
        login=f"usuario-{id_usuario}",
        id_sesion=uuid4(),
        mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=datetime(2026, 9, 4, tzinfo=UTC).replace(tzinfo=None),
        id_instalacion_origen_sesion=1,
        id_sucursal_operativa=None,
    )


def _policy(actor=LocalCommandActor.HUMAN, *, assertion=True, cas=False):
    return LocalCommandContextPolicy(actor, cas, assertion)


def _headers(branch=1, installation="1", version=None, *, assertion=True, cas=False):
    return parse_local_command_core_ef_headers(
        str(uuid4()),
        str(branch),
        installation,
        version,
        require_installation_assertion=assertion,
        require_if_match_version=cas,
    )


def _resolve(db_session, *, policy=None, headers=None, principal=None):
    return resolve_local_command_context(
        db_session,
        SimpleNamespace(local_installation_code="INST-TEST-001"),
        policy=policy or _policy(),
        headers=headers or _headers(),
        principal=principal if principal is not None else _principal(),
    )


def _insert_branch(db_session, *, state="ACTIVA", allows=True, deleted=False):
    return db_session.execute(
        text(
            """
            INSERT INTO sucursal(
                codigo_sucursal, nombre_sucursal, estado_sucursal,
                permite_operacion, fecha_baja, deleted_at
            ) VALUES (
                :code, 'Sucursal contexto 536', :state, :allows,
                CASE WHEN :state = 'ACTIVA' THEN NULL ELSE now() END,
                CASE WHEN :deleted THEN now() ELSE NULL END
            ) RETURNING id_sucursal
            """
        ),
        {
            "code": f"SUC-536-{uuid4()}",
            "state": state,
            "allows": allows,
            "deleted": deleted,
        },
    ).scalar_one()


def _insert_installation(db_session, branch_id):
    return db_session.execute(
        text(
            """
            INSERT INTO instalacion(
                id_sucursal, codigo_instalacion, nombre_instalacion,
                estado_instalacion, es_principal, permite_sincronizacion
            ) VALUES (
                :branch, :code, 'Instalación alternativa 536',
                'ACTIVA', false, false
            ) RETURNING id_instalacion
            """
        ),
        {"branch": branch_id, "code": f"INST-536-{uuid4()}"},
    ).scalar_one()


def test_postgres_humano_resuelve_nodo_canonico_scope_y_cas(db_session):
    before = db_session.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM outbox_event) AS outbox,
              (SELECT count(*) FROM operacion_idempotente) AS receipts
            """
        )
    ).mappings().one()

    context = _resolve(
        db_session,
        policy=_policy(cas=True),
        headers=_headers(version="7", cas=True),
    )

    installation = db_session.execute(
        text("SELECT uid_global FROM instalacion WHERE id_instalacion = 1")
    ).scalar_one()
    after = db_session.execute(
        text(
            """
            SELECT
              (SELECT count(*) FROM outbox_event) AS outbox,
              (SELECT count(*) FROM operacion_idempotente) AS receipts
            """
        )
    ).mappings().one()
    assert context.id_usuario == 1
    assert context.id_sucursal == 1
    assert context.id_instalacion == 1
    assert context.uid_instalacion == installation
    assert context.if_match_version == 7
    assert dict(after) == dict(before)


def test_postgres_tecnico_sin_principal_y_header_instalacion_opcional(db_session):
    context = _resolve(
        db_session,
        policy=_policy(LocalCommandActor.TECHNICAL, assertion=False),
        headers=_headers(installation=None, assertion=False),
        principal=None,
    )
    assert context.principal is None
    assert context.id_usuario is None
    assert context.id_instalacion == 1


def test_postgres_rechaza_assertion_de_otra_instalacion_valida(db_session):
    alternative = _insert_installation(db_session, 1)
    with pytest.raises(InstallationAssertionMismatch):
        _resolve(db_session, headers=_headers(installation=str(alternative)))


def test_postgres_sucursal_es_independiente_pero_debe_ser_compatible(db_session):
    other_branch = _insert_branch(db_session)
    with pytest.raises(InstallationBranchMismatch):
        _resolve(db_session, headers=_headers(branch=other_branch))


@pytest.mark.parametrize(
    ("state", "allows", "deleted"),
    [("INACTIVA", True, False), ("ACTIVA", False, False), ("ACTIVA", True, True)],
)
def test_postgres_rechaza_sucursal_no_elegible(
    db_session, state, allows, deleted
):
    branch = _insert_branch(
        db_session, state=state, allows=allows, deleted=deleted
    )
    with pytest.raises(OperationalBranchNotEligible):
        _resolve(db_session, headers=_headers(branch=branch))


def test_postgres_rechaza_principal_sin_alcance_operativo(db_session):
    with pytest.raises(OperationalBranchScopeDenied):
        _resolve(db_session, principal=_principal(987654321))

