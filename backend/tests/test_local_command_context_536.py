from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import UUID, uuid4

import pytest
from app.api.core_ef_headers import (
    CoreEFHeaderValidationError,
    parse_local_command_core_ef_headers,
)
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.common.local_command_context import (
    HumanPrincipalRequired,
    InstallationAssertionMismatch,
    InstallationBranchMismatch,
    LocalCommandActor,
    LocalCommandContextPolicy,
    LocalCommandContextTechnicalError,
    LocalInstallationUnavailable,
    OperationalBranchNotEligible,
    OperationalBranchNotFound,
    OperationalBranchScopeDenied,
    resolve_local_command_context,
)
from app.application.common.local_command_headers import LocalCommandCoreEFHeaders
from app.application.common.local_installation import (
    LocalInstallationIdentity,
    LocalInstallationNotFound,
)
from app.infrastructure.persistence.repositories.technical_context_repository import (
    OperationalContextProjection,
)

OP_ID = UUID("550e8400-e29b-41d4-a716-446655440000")
INSTALLATION_UID = UUID("9e602174-8c8b-4f67-a723-2142c6756b6a")


def _policy(
    actor=LocalCommandActor.HUMAN,
    *,
    require_if_match_version=False,
    require_installation_assertion=True,
):
    return LocalCommandContextPolicy(
        actor=actor,
        require_if_match_version=require_if_match_version,
        require_installation_assertion=require_installation_assertion,
    )


def _headers(*, branch=20, installation=30, version=None):
    return LocalCommandCoreEFHeaders(OP_ID, branch, installation, version)


def _principal(id_usuario=10):
    return AuthenticatedPrincipal(
        id_usuario=id_usuario,
        codigo_usuario="USR-010",
        login="operador",
        id_sesion=uuid4(),
        mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=datetime(2026, 9, 4, tzinfo=UTC).replace(tzinfo=None),
        id_instalacion_origen_sesion=30,
        id_sucursal_operativa=None,
    )


def _projection(**changes):
    return OperationalContextProjection(
        branch_exists=changes.get("branch_exists", True),
        branch_eligible=changes.get("branch_eligible", True),
        installation_belongs_to_branch=changes.get(
            "installation_belongs_to_branch", True
        ),
        principal_has_operational_scope=changes.get(
            "principal_has_operational_scope", True
        ),
    )


def _resolve(*, policy=None, headers=None, principal=None, projection=None):
    session = Mock()
    installation = LocalInstallationIdentity(
        30, INSTALLATION_UID, "INST-LOCAL", "Instalación local"
    )
    with patch(
        "app.application.common.local_command_context.resolve_local_installation",
        return_value=installation,
    ) as local, patch(
        "app.application.common.local_command_context.TechnicalContextRepository"
    ) as repository:
        repository.return_value.resolve_operational_context.return_value = (
            projection or _projection()
        )
        result = resolve_local_command_context(
            session,
            SimpleNamespace(local_installation_code="INST-LOCAL"),
            policy=policy or _policy(),
            headers=headers or _headers(),
            principal=principal if principal is not None else _principal(),
        )
    return session, local, repository, result


def test_parser_local_no_conoce_x_usuario_y_soporta_policies_explicitas():
    parsed = parse_local_command_core_ef_headers(
        str(OP_ID),
        "20",
        None,
        None,
        require_installation_assertion=False,
        require_if_match_version=False,
    )
    assert parsed == LocalCommandCoreEFHeaders(OP_ID, 20, None, None)
    assert not hasattr(parsed, "x_usuario_id")


@pytest.mark.parametrize(
    ("values", "expected_header"),
    [
        ((None, "20", "30", None, False, False), "X-Op-Id"),
        (("invalid", "20", "30", None, False, False), "X-Op-Id"),
        ((str(OP_ID), None, "30", None, False, False), "X-Sucursal-Id"),
        ((str(OP_ID), "0", "30", None, False, False), "X-Sucursal-Id"),
        ((str(OP_ID), "20", None, None, True, False), "X-Instalacion-Id"),
        ((str(OP_ID), "20", "x", None, False, False), "X-Instalacion-Id"),
        ((str(OP_ID), "20", "30", None, False, True), "If-Match-Version"),
        ((str(OP_ID), "20", "30", "0", False, False), "If-Match-Version"),
    ],
)
def test_parser_rechaza_headers_faltantes_o_invalidos(values, expected_header):
    op_id, branch, installation, version, require_installation, require_version = values
    with pytest.raises(CoreEFHeaderValidationError) as error:
        parse_local_command_core_ef_headers(
            op_id,
            branch,
            installation,
            version,
            require_installation_assertion=require_installation,
            require_if_match_version=require_version,
        )
    assert error.value.header_name == expected_header


def test_contexto_humano_devuelve_identidades_canonicas_y_es_read_only():
    principal = _principal()
    session, local, repository, result = _resolve(
        headers=_headers(installation=30, version=7), principal=principal
    )

    assert result.principal is principal
    assert result.id_usuario == principal.id_usuario
    assert result.id_sucursal == 20
    assert result.id_instalacion == 30
    assert result.uid_instalacion == INSTALLATION_UID
    assert result.local_installation.id_instalacion == 30
    assert result.op_id == OP_ID
    assert result.if_match_version == 7
    local.assert_called_once()
    repository.return_value.resolve_operational_context.assert_called_once_with(
        id_sucursal=20, id_instalacion=30, id_usuario=10
    )
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.flush.assert_not_called()


def test_contexto_tecnico_no_inventa_usuario_humano():
    _, _, repository, result = _resolve(
        policy=_policy(LocalCommandActor.TECHNICAL),
        principal=None,
    )
    assert result.principal is None
    assert result.id_usuario is None
    repository.return_value.resolve_operational_context.assert_called_once_with(
        id_sucursal=20, id_instalacion=30, id_usuario=None
    )


def test_contexto_humano_requiere_principal_antes_de_consultar():
    session = Mock()
    with pytest.raises(HumanPrincipalRequired):
        resolve_local_command_context(
            session,
            Mock(),
            policy=_policy(),
            headers=_headers(),
            principal=None,
        )
    session.execute.assert_not_called()
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.flush.assert_not_called()


def test_assertion_de_instalacion_no_puede_elegir_otro_nodo():
    with pytest.raises(InstallationAssertionMismatch):
        _resolve(headers=_headers(installation=31))


def test_header_instalacion_puede_omitirse_si_la_policy_ya_lo_permite():
    _, _, _, result = _resolve(
        policy=_policy(require_installation_assertion=False),
        headers=_headers(installation=None),
    )
    assert result.id_instalacion == 30
    assert result.uid_instalacion == INSTALLATION_UID


@pytest.mark.parametrize(
    ("projection", "error_type"),
    [
        (_projection(branch_exists=False), OperationalBranchNotFound),
        (_projection(branch_eligible=False), OperationalBranchNotEligible),
        (
            _projection(installation_belongs_to_branch=False),
            InstallationBranchMismatch,
        ),
        (
            _projection(principal_has_operational_scope=False),
            OperationalBranchScopeDenied,
        ),
    ],
)
def test_contexto_rechaza_sucursal_o_alcance_incompatibles(projection, error_type):
    with pytest.raises(error_type):
        _resolve(projection=projection)


def test_falla_de_instalacion_se_sanitiza_y_no_consulta_contexto():
    session = Mock()
    with patch(
        "app.application.common.local_command_context.resolve_local_installation",
        side_effect=LocalInstallationNotFound("código interno secreto"),
    ), patch(
        "app.application.common.local_command_context.TechnicalContextRepository"
    ) as repository, pytest.raises(LocalInstallationUnavailable) as error:
        resolve_local_command_context(
            session,
            Mock(),
            policy=_policy(),
            headers=_headers(),
            principal=_principal(),
        )
    assert str(error.value) == "La instalación local no está disponible."
    repository.assert_not_called()


def test_falla_db_se_sanitiza_sin_commit_rollback_o_flush():
    session = Mock()
    installation = LocalInstallationIdentity(
        30, INSTALLATION_UID, "INST-LOCAL", "Instalación local"
    )
    with patch(
        "app.application.common.local_command_context.resolve_local_installation",
        return_value=installation,
    ), patch(
        "app.application.common.local_command_context.TechnicalContextRepository"
    ) as repository:
        repository.return_value.resolve_operational_context.side_effect = RuntimeError(
            "SQL DSN secreto"
        )
        with pytest.raises(LocalCommandContextTechnicalError) as error:
            resolve_local_command_context(
                session,
                Mock(),
                policy=_policy(),
                headers=_headers(),
                principal=_principal(),
            )
    assert str(error.value) == "No fue posible validar el contexto local."
    session.commit.assert_not_called()
    session.rollback.assert_not_called()
    session.flush.assert_not_called()
