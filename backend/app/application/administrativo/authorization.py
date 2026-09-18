"""Evaluator central de autorización humana D1, sin dependencias HTTP."""

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Generic, TypeVar

from app.infrastructure.persistence.repositories.administrative_authorization_repository import (
    AdministrativeAuthorizationProjection,
    AdministrativeAuthorizationRepository,
    ResourceAuthorizationProjection,
)


class AdministrativeAuthorizationError(RuntimeError):
    """Base de errores públicos sanitizables de autorización."""


class InsufficientAdministrativeAuthorization(AdministrativeAuthorizationError):
    pass


class AdministrativeAuthorizationTechnicalError(AdministrativeAuthorizationError):
    pass


class AdministrativeAuthorizationDecision(Enum):
    GRANTED = "GRANTED"
    DENIED = "DENIED"


class AdministrativeAuthorizationMode(Enum):
    GLOBAL = "GLOBAL"
    EXPLICIT_CONTEXT = "EXPLICIT_CONTEXT"


class ScopeCapability(Enum):
    QUERY = "puede_consultar"
    OPERATE = "puede_operar"
    ADMINISTER = "puede_administrar"


@dataclass(frozen=True, slots=True)
class FunctionalScope:
    id_sucursal: int
    branch_active: bool
    branch_allows_operation: bool
    has_current_assignment: bool


def _scope_enabled(_scope: FunctionalScope) -> bool:
    return True


@dataclass(frozen=True, slots=True)
class HOpPredicate:
    required_capabilities: frozenset[ScopeCapability] = frozenset()
    scope_predicate: Callable[[FunctionalScope], bool] = _scope_enabled

    def evaluate(
        self,
        scope: FunctionalScope,
        *,
        assignment_capabilities_satisfied: bool,
    ) -> bool:
        capabilities_satisfied = (
            not self.required_capabilities or assignment_capabilities_satisfied
        )
        predicate_result = self.scope_predicate(scope)
        if type(predicate_result) is not bool:
            raise AdministrativeAuthorizationTechnicalError(
                AdministrativeAuthorizationService._TECHNICAL_MESSAGE
            )
        return capabilities_satisfied and predicate_result


ResourceT = TypeVar("ResourceT")
_POSTGRES_BIGINT_MAX = 9_223_372_036_854_775_807


@dataclass(frozen=True, slots=True)
class ResourceAuthorizationCandidate(Generic[ResourceT]):
    resource: ResourceT
    persisted_scope: int | None


@dataclass(frozen=True, slots=True)
class ResourceAuthorizationEvidence:
    global_granted: bool
    contextual_scope_ids: frozenset[int]
    invalid_branch_scope_ids: frozenset[int]

    def contextual_granted(self, id_sucursal: int | None) -> bool:
        if id_sucursal is not None and id_sucursal in self.invalid_branch_scope_ids:
            raise AdministrativeAuthorizationTechnicalError(
                AdministrativeAuthorizationService._TECHNICAL_MESSAGE
            )
        return id_sucursal is not None and id_sucursal in self.contextual_scope_ids


@dataclass(frozen=True, slots=True)
class ResourceAuthorizationPath(Generic[ResourceT]):
    functional: Callable[[ResourceAuthorizationCandidate[ResourceT]], bool]
    authorization: Callable[
        [ResourceAuthorizationCandidate[ResourceT], ResourceAuthorizationEvidence], bool
    ]


@dataclass(frozen=True, slots=True)
class AuthorizedResourcePage(Generic[ResourceT]):
    items: tuple[ResourceAuthorizationCandidate[ResourceT], ...]
    total: int


class AdministrativeAuthorizationService:
    _TECHNICAL_MESSAGE = "No fue posible resolver la autorización administrativa."
    _KNOWN_STATES = frozenset({"ACTIVO", "INACTIVO"})
    _KNOWN_BRANCH_STATES = frozenset({"ACTIVA", "INACTIVA", "DADA_DE_BAJA"})

    def __init__(self, session) -> None:
        self.db = session

    def authorize(
        self,
        id_usuario: int,
        permission_code: str,
        *,
        mode: AdministrativeAuthorizationMode = AdministrativeAuthorizationMode.GLOBAL,
        id_sucursal: int | None = None,
        h_op: HOpPredicate | None = None,
    ) -> AdministrativeAuthorizationDecision:
        self._validate_permission_code(permission_code)
        self._validate_mode(mode)
        if mode is AdministrativeAuthorizationMode.EXPLICIT_CONTEXT:
            if (
                not isinstance(id_sucursal, int)
                or isinstance(id_sucursal, bool)
                or id_sucursal <= 0
            ):
                raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
            self._validate_h_op(h_op)

        try:
            projection = AdministrativeAuthorizationRepository(self.db).resolve_permission(
                id_usuario,
                permission_code,
                id_sucursal=(
                    id_sucursal
                    if mode is AdministrativeAuthorizationMode.EXPLICIT_CONTEXT
                    else None
                ),
                require_can_query=(
                    ScopeCapability.QUERY in h_op.required_capabilities
                    if h_op is not None
                    else False
                ),
                require_can_operate=(
                    ScopeCapability.OPERATE in h_op.required_capabilities
                    if h_op is not None
                    else False
                ),
                require_can_administer=(
                    ScopeCapability.ADMINISTER in h_op.required_capabilities
                    if h_op is not None
                    else False
                ),
            )
        except Exception as exc:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE) from exc

        self._validate_projection(projection)
        if (
            mode is AdministrativeAuthorizationMode.EXPLICIT_CONTEXT
            and projection.scope_identifiable
            and projection.branch_state not in self._KNOWN_BRANCH_STATES
        ):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        if not projection.principal_active:
            return AdministrativeAuthorizationDecision.DENIED
        if projection.permission_state == "INACTIVO" or projection.denied:
            return AdministrativeAuthorizationDecision.DENIED

        if mode is AdministrativeAuthorizationMode.GLOBAL:
            granted = projection.global_granted
        elif mode is AdministrativeAuthorizationMode.EXPLICIT_CONTEXT:
            if not projection.scope_identifiable:
                return AdministrativeAuthorizationDecision.DENIED
            scope = FunctionalScope(
                id_sucursal=id_sucursal,
                branch_active=projection.branch_active,
                branch_allows_operation=projection.branch_allows_operation,
                has_current_assignment=projection.has_current_assignment,
            )
            try:
                functional_enabled = h_op.evaluate(
                    scope,
                    assignment_capabilities_satisfied=(
                        projection.assignment_capabilities_satisfied
                    ),
                )
            except Exception as exc:
                raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE) from exc
            self._validate_boolean_result(functional_enabled)
            granted = functional_enabled and (
                projection.global_granted or projection.contextual_granted
            )
        return (
            AdministrativeAuthorizationDecision.GRANTED
            if granted
            else AdministrativeAuthorizationDecision.DENIED
        )

    def authorize_resources(
        self,
        id_usuario: int,
        permission_code: str,
        candidates: Sequence[ResourceAuthorizationCandidate[ResourceT]],
        paths: Sequence[ResourceAuthorizationPath[ResourceT]],
        *,
        offset: int = 0,
        limit: int | None = None,
    ) -> AuthorizedResourcePage[ResourceT]:
        """Filtra todas las filas autorizadas antes de totalizar y paginar."""
        self._validate_permission_code(permission_code)
        validated_candidates = self._validate_resource_candidates(candidates)
        validated_paths = self._validate_resource_paths(paths)
        if offset < 0 or limit is not None and limit < 0:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        scope_ids = {
            candidate.persisted_scope
            for candidate in validated_candidates
            if candidate.persisted_scope is not None
        }
        try:
            projection = AdministrativeAuthorizationRepository(
                self.db
            ).resolve_resource_permission(id_usuario, permission_code, scope_ids)
        except Exception as exc:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE) from exc
        self._validate_resource_projection(projection)
        self._validate_persisted_scopes(scope_ids, projection)
        evidence = ResourceAuthorizationEvidence(
            global_granted=projection.global_granted,
            contextual_scope_ids=projection.contextual_scope_ids,
            invalid_branch_scope_ids=projection.invalid_branch_scope_ids,
        )
        if (
            not projection.principal_active
            or projection.permission_state == "INACTIVO"
            or projection.denied
        ):
            raise InsufficientAdministrativeAuthorization(
                "La autorización efectiva es insuficiente."
            )
        authorized: list[ResourceAuthorizationCandidate[ResourceT]] = []
        for candidate in validated_candidates:
            candidate_granted = False
            for path in validated_paths:
                functional_result = self._evaluate_resource_callback(
                    path.functional, candidate
                )
                if not functional_result:
                    continue
                authorization_result = self._evaluate_resource_callback(
                    path.authorization, candidate, evidence
                )
                candidate_granted = candidate_granted or authorization_result
            if candidate_granted:
                authorized.append(candidate)
        total = len(authorized)
        stop = None if limit is None else offset + limit
        return AuthorizedResourcePage(items=tuple(authorized[offset:stop]), total=total)

    def _validate_permission_code(self, permission_code: str) -> None:
        if not isinstance(permission_code, str) or not permission_code.strip():
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)

    def _validate_mode(self, mode: object) -> None:
        if not isinstance(mode, AdministrativeAuthorizationMode):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)

    def _validate_h_op(self, h_op: HOpPredicate | None) -> None:
        if not isinstance(h_op, HOpPredicate):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        capabilities = h_op.required_capabilities
        if (
            not isinstance(capabilities, (set, frozenset))
            or any(
                not isinstance(capability, ScopeCapability)
                for capability in capabilities
            )
            or not callable(h_op.scope_predicate)
        ):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)

    def _validate_projection(self, projection: object) -> None:
        if not isinstance(projection, AdministrativeAuthorizationProjection):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        if not projection.permission_defined:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        self._validate_authorization_states(
            projection.permission_state,
            projection.principal_state,
            projection.invalid_role_state,
            projection.invalid_assignment_state,
        )

    def _validate_resource_projection(self, projection: object) -> None:
        if not isinstance(projection, ResourceAuthorizationProjection):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        if not projection.permission_defined:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        self._validate_authorization_states(
            projection.permission_state,
            projection.principal_state,
            projection.invalid_role_state,
        )

    def _validate_resource_candidates(
        self, candidates: object
    ) -> tuple[ResourceAuthorizationCandidate[ResourceT], ...]:
        if not isinstance(candidates, Sequence) or isinstance(
            candidates, (str, bytes, bytearray)
        ):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        validated = tuple(candidates)
        for candidate in validated:
            if not isinstance(candidate, ResourceAuthorizationCandidate):
                raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
            scope = candidate.persisted_scope
            if scope is not None and (
                not isinstance(scope, int)
                or isinstance(scope, bool)
                or scope <= 0
                or scope > _POSTGRES_BIGINT_MAX
            ):
                raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        return validated

    def _validate_resource_paths(
        self, paths: object
    ) -> tuple[ResourceAuthorizationPath[ResourceT], ...]:
        if (
            not isinstance(paths, Sequence)
            or isinstance(paths, (str, bytes, bytearray))
            or not paths
        ):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        validated = tuple(paths)
        if any(
            not isinstance(path, ResourceAuthorizationPath)
            or not callable(path.functional)
            or not callable(path.authorization)
            for path in validated
        ):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        return validated

    def _validate_persisted_scopes(
        self,
        requested_scope_ids: set[int],
        projection: ResourceAuthorizationProjection,
    ) -> None:
        known_scope_ids = projection.known_branch_scope_ids
        invalid_scope_ids = projection.invalid_branch_scope_ids
        if (
            invalid_scope_ids
            or requested_scope_ids - known_scope_ids - invalid_scope_ids
            or known_scope_ids - requested_scope_ids
            or invalid_scope_ids - requested_scope_ids
        ):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)

    def _evaluate_resource_callback(self, callback: Callable, *args) -> bool:
        try:
            result = callback(*args)
        except Exception as exc:
            if isinstance(exc, AdministrativeAuthorizationTechnicalError):
                raise
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE) from exc
        self._validate_boolean_result(result)
        return result

    def _validate_boolean_result(self, result: object) -> None:
        if type(result) is not bool:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)

    def _validate_authorization_states(
        self,
        permission_state: str | None,
        principal_state: str | None,
        invalid_role_state: bool,
        invalid_assignment_state: bool = False,
    ) -> None:
        if (
            permission_state not in self._KNOWN_STATES
            or principal_state not in self._KNOWN_STATES
            or invalid_role_state
            or invalid_assignment_state
        ):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
