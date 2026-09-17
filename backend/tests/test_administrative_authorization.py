from datetime import UTC, datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI, Request
from fastapi.testclient import TestClient

from app.api.administrative_authorization import (
    CentralContextHeaderError,
    parse_central_branch_selector,
    require_administrative_permission,
)
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
    AdministrativeAuthorizationMode,
    AdministrativeAuthorizationService,
    AdministrativeAuthorizationTechnicalError,
    HOpPredicate,
    InsufficientAdministrativeAuthorization,
    ResourceAuthorizationCandidate,
    ResourceAuthorizationPath,
    ScopeCapability,
)
from app.infrastructure.persistence.repositories.administrative_authorization_repository import (
    AdministrativeAuthorizationProjection,
    AdministrativeAuthorizationRepository,
    ResourceAuthorizationProjection,
)
from app.main import central_context_header_error_handler

TEST_NOW = datetime(2026, 8, 10, tzinfo=UTC).replace(tzinfo=None)


def _principal(id_usuario: int = 42) -> AuthenticatedPrincipal:
    return AuthenticatedPrincipal(
        id_usuario=id_usuario,
        codigo_usuario="USR-42",
        login="admin",
        id_sesion=uuid4(),
        mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=TEST_NOW,
    )


def _projection(**overrides) -> AdministrativeAuthorizationProjection:
    values = {
        "permission_defined": True,
        "permission_state": "ACTIVO",
        "principal_state": "ACTIVO",
        "principal_active": True,
        "invalid_role_state": False,
        "invalid_assignment_state": False,
        "global_granted": False,
        "contextual_granted": False,
        "denied": False,
        "scope_identifiable": False,
        "branch_active": False,
        "branch_allows_operation": False,
        "has_current_assignment": False,
        "assignment_capabilities_satisfied": False,
    }
    values.update(overrides)
    return AdministrativeAuthorizationProjection(**values)


def _resource_projection(**overrides) -> ResourceAuthorizationProjection:
    values = {
        "permission_defined": True,
        "permission_state": "ACTIVO",
        "principal_state": "ACTIVO",
        "principal_active": True,
        "invalid_role_state": False,
        "global_granted": False,
        "denied": False,
        "contextual_scope_ids": frozenset(),
    }
    values.update(overrides)
    return ResourceAuthorizationProjection(**values)


def _request(*values: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(b"x-sucursal-id", value.encode()) for value in values],
        }
    )


@pytest.mark.parametrize("value", ["1", "9223372036854775807"])
def test_central_selector_accepts_one_positive_bigint(value):
    assert parse_central_branch_selector(_request(value)) == int(value)


@pytest.mark.parametrize(
    "values",
    [(), ("1", "2"), ("0",), ("-1",), (" 1",), ("1.0",), ("9223372036854775808",)],
)
def test_central_selector_rejects_absent_repeated_or_invalid_values(values):
    with pytest.raises(CentralContextHeaderError):
        parse_central_branch_selector(_request(*values))


def test_central_selector_http_error_is_contractual_and_sanitized():
    app = FastAPI()
    app.add_exception_handler(
        CentralContextHeaderError, central_context_header_error_handler
    )

    @app.get("/context")
    def context(id_sucursal: int = Depends(parse_central_branch_selector)):
        return {"id_sucursal": id_sucursal}

    response = TestClient(app).get("/context")
    assert response.status_code == 400
    assert response.json()["error_code"] == "CENTRAL_CONTEXT_HEADER_INVALID"
    assert response.json()["details"] == {
        "header": "X-Sucursal-Id",
        "reason": "required_once",
    }


def test_compatible_global_dependency_delegates_to_d1_and_preserves_principal():
    principal = _principal()
    dependency = require_administrative_permission("permiso.opaco")
    with patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService"
    ) as service:
        service.return_value.authorize.return_value = AdministrativeAuthorizationDecision.GRANTED
        assert dependency(principal, Mock()) is principal
    service.return_value.authorize.assert_called_once_with(
        42, "permiso.opaco", mode=AdministrativeAuthorizationMode.GLOBAL
    )


def test_compatible_global_dependency_maps_denial_to_existing_exception():
    dependency = require_administrative_permission("permiso.opaco")
    with patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService"
    ) as service:
        service.return_value.authorize.return_value = AdministrativeAuthorizationDecision.DENIED
        with pytest.raises(InsufficientAdministrativeAuthorization):
            dependency(_principal(), Mock())


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (_projection(global_granted=True), AdministrativeAuthorizationDecision.GRANTED),
        (_projection(), AdministrativeAuthorizationDecision.DENIED),
        (_projection(permission_state="INACTIVO", global_granted=True), AdministrativeAuthorizationDecision.DENIED),
        (_projection(principal_active=False, global_granted=True), AdministrativeAuthorizationDecision.DENIED),
        (_projection(global_granted=True, denied=True), AdministrativeAuthorizationDecision.DENIED),
    ],
)
def test_global_evaluates_p_e_g_and_d(projection, expected):
    db = Mock()
    with patch(
        "app.application.administrativo.authorization.AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_permission.return_value = projection
        assert AdministrativeAuthorizationService(db).authorize(42, "p") is expected
    db.commit.assert_not_called()
    db.rollback.assert_not_called()
    db.flush.assert_not_called()


def test_undefined_permission_is_technical_error():
    with patch(
        "app.application.administrativo.authorization.AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_permission.return_value = _projection(
            permission_defined=False, permission_state=None
        )
        with pytest.raises(AdministrativeAuthorizationTechnicalError):
            AdministrativeAuthorizationService(Mock()).authorize(42, "missing")


@pytest.mark.parametrize(
    "projection",
    [
        _projection(permission_state="DESCONOCIDO"),
        _projection(principal_state="DESCONOCIDO"),
        _projection(invalid_role_state=True),
        _projection(invalid_assignment_state=True),
    ],
)
def test_unknown_authorization_states_are_technical_errors(projection):
    with patch(
        "app.application.administrativo.authorization.AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_permission.return_value = projection
        with pytest.raises(AdministrativeAuthorizationTechnicalError):
            AdministrativeAuthorizationService(Mock()).authorize(42, "p")


@pytest.mark.parametrize(
    ("projection", "expected"),
    [
        (
            _projection(
                scope_identifiable=True,
                global_granted=True,
                assignment_capabilities_satisfied=True,
            ),
            AdministrativeAuthorizationDecision.GRANTED,
        ),
        (
            _projection(
                scope_identifiable=True,
                contextual_granted=True,
                assignment_capabilities_satisfied=True,
            ),
            AdministrativeAuthorizationDecision.GRANTED,
        ),
        (
            _projection(
                scope_identifiable=True,
                contextual_granted=True,
                assignment_capabilities_satisfied=False,
            ),
            AdministrativeAuthorizationDecision.DENIED,
        ),
        (
            _projection(
                scope_identifiable=False,
                global_granted=True,
                assignment_capabilities_satisfied=True,
            ),
            AdministrativeAuthorizationDecision.DENIED,
        ),
        (
            _projection(
                scope_identifiable=True,
                contextual_granted=True,
                assignment_capabilities_satisfied=True,
                denied=True,
            ),
            AdministrativeAuthorizationDecision.DENIED,
        ),
    ],
)
def test_explicit_context_evaluates_h_and_global_or_contextual_then_d(projection, expected):
    with patch(
        "app.application.administrativo.authorization.AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_permission.return_value = projection
        decision = AdministrativeAuthorizationService(Mock()).authorize(
            42,
            "p",
            mode=AdministrativeAuthorizationMode.EXPLICIT_CONTEXT,
            id_sucursal=7,
            h_op=HOpPredicate(
                required_capabilities=frozenset({ScopeCapability.QUERY})
            ),
        )
    assert decision is expected


def test_contextual_permission_is_bound_to_selected_scope():
    with patch(
        "app.application.administrativo.authorization.AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_permission.side_effect = [
            _projection(
                scope_identifiable=True,
                contextual_granted=True,
                assignment_capabilities_satisfied=True,
            ),
            _projection(
                scope_identifiable=True,
                contextual_granted=False,
                assignment_capabilities_satisfied=True,
            ),
        ]
        service = AdministrativeAuthorizationService(Mock())
        assert service.authorize(
            42, "p", mode=AdministrativeAuthorizationMode.EXPLICIT_CONTEXT,
            id_sucursal=1,
            h_op=HOpPredicate(
                required_capabilities=frozenset({ScopeCapability.QUERY})
            ),
        ) is AdministrativeAuthorizationDecision.GRANTED
        assert service.authorize(
            42, "p", mode=AdministrativeAuthorizationMode.EXPLICIT_CONTEXT,
            id_sucursal=2,
            h_op=HOpPredicate(
                required_capabilities=frozenset({ScopeCapability.QUERY})
            ),
        ) is AdministrativeAuthorizationDecision.DENIED


@pytest.mark.parametrize(
    ("capabilities", "expected_requirements"),
    [
        (
            frozenset({ScopeCapability.QUERY, ScopeCapability.ADMINISTER}),
            {
                "require_can_query": True,
                "require_can_operate": False,
                "require_can_administer": True,
            },
        ),
        (
            frozenset({ScopeCapability.OPERATE, ScopeCapability.ADMINISTER}),
            {
                "require_can_query": False,
                "require_can_operate": True,
                "require_can_administer": True,
            },
        ),
    ],
)
def test_explicit_context_requires_combined_capabilities_on_one_assignment(
    capabilities, expected_requirements
):
    with patch(
        "app.application.administrativo.authorization.AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_permission.side_effect = [
            _projection(
                scope_identifiable=True,
                contextual_granted=True,
                assignment_capabilities_satisfied=False,
            ),
            _projection(
                scope_identifiable=True,
                contextual_granted=True,
                assignment_capabilities_satisfied=True,
            ),
        ]
        service = AdministrativeAuthorizationService(Mock())
        h_op = HOpPredicate(required_capabilities=capabilities)

        assert service.authorize(
            42,
            "p",
            mode=AdministrativeAuthorizationMode.EXPLICIT_CONTEXT,
            id_sucursal=7,
            h_op=h_op,
        ) is AdministrativeAuthorizationDecision.DENIED
        assert service.authorize(
            42,
            "p",
            mode=AdministrativeAuthorizationMode.EXPLICIT_CONTEXT,
            id_sucursal=7,
            h_op=h_op,
        ) is AdministrativeAuthorizationDecision.GRANTED

    for call in repository.return_value.resolve_permission.call_args_list:
        assert {
            key: call.kwargs[key] for key in expected_requirements
        } == expected_requirements


def test_explicit_context_requires_declared_h_predicate():
    with pytest.raises(AdministrativeAuthorizationTechnicalError):
        AdministrativeAuthorizationService(Mock()).authorize(
            42,
            "p",
            mode=AdministrativeAuthorizationMode.EXPLICIT_CONTEXT,
            id_sucursal=1,
        )


def test_resource_derived_ors_paths_preserves_scope_and_filters_before_paging():
    candidates = [
        ResourceAuthorizationCandidate("global", None),
        ResourceAuthorizationCandidate("context-a", 1),
        ResourceAuthorizationCandidate("hidden", 2),
    ]
    paths = [
        ResourceAuthorizationPath(
            functional=lambda _candidate: True,
            authorization=lambda _candidate, _evidence: False,
        ),
        ResourceAuthorizationPath(
            functional=lambda candidate: candidate.resource == "global",
            authorization=lambda _candidate, evidence: evidence.global_granted,
        ),
        ResourceAuthorizationPath(
            functional=lambda candidate: candidate.resource.startswith("context"),
            authorization=lambda candidate, evidence: evidence.contextual_granted(
                candidate.persisted_scope
            ),
        ),
    ]
    with patch(
        "app.application.administrativo.authorization.AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_resource_permission.return_value = _resource_projection(
            global_granted=True, contextual_scope_ids=frozenset({1})
        )
        page = AdministrativeAuthorizationService(Mock()).authorize_resources(
            42, "p", candidates, paths, offset=1, limit=1
        )
    assert page.total == 2
    assert page.items == (candidates[1],)
    assert candidates[1].persisted_scope == 1


@pytest.mark.parametrize(
    "projection",
    [
        _resource_projection(denied=True, global_granted=True),
        _resource_projection(permission_state="INACTIVO"),
        _resource_projection(principal_active=False),
    ],
)
def test_resource_derived_applies_common_security_before_paths(projection):
    path = ResourceAuthorizationPath(lambda _candidate: True, lambda _candidate, _evidence: True)
    with patch(
        "app.application.administrativo.authorization.AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_resource_permission.return_value = projection
        with pytest.raises(InsufficientAdministrativeAuthorization):
            AdministrativeAuthorizationService(Mock()).authorize_resources(
                42, "p", [ResourceAuthorizationCandidate("r", None)], [path]
            )


def test_resource_derived_rejects_unknown_permission_state_as_technical():
    path = ResourceAuthorizationPath(
        lambda _candidate: True, lambda _candidate, _evidence: True
    )
    with patch(
        "app.application.administrativo.authorization.AdministrativeAuthorizationRepository"
    ) as repository:
        repository.return_value.resolve_resource_permission.return_value = (
            _resource_projection(permission_state="DESCONOCIDO")
        )
        with pytest.raises(AdministrativeAuthorizationTechnicalError):
            AdministrativeAuthorizationService(Mock()).authorize_resources(
                42, "p", [ResourceAuthorizationCandidate("r", None)], [path]
            )


def test_repository_is_read_only_uses_one_utc_clock_and_contains_g_c_d():
    db = Mock()
    db.execute.return_value.mappings.return_value.one.return_value = dict(
        _projection().__dict__ if hasattr(_projection(), "__dict__") else {
            field: getattr(_projection(), field)
            for field in _projection().__dataclass_fields__
        }
    )
    AdministrativeAuthorizationRepository(db).resolve_permission(
        42, "Case.Sensitive", id_sucursal=7
    )
    sql = str(db.execute.call_args.args[0]).lower()
    assert sql.count("clock_timestamp() at time zone 'utc'") == 1
    assert "usuario_rol_seguridad" in sql
    assert "usuario_rol_sucursal" in sql
    assert "denegacion_explicita" in sql
    assert "usuario_sucursal" in sql
    assert "for update" not in sql
    assert not any(word in sql for word in ("insert ", "update ", "delete "))
    assert db.execute.call_args.args[1]["id_sucursal"] == 7
