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


@dataclass(frozen=True, slots=True)
class FunctionalScope:
    id_sucursal: int
    branch_active: bool
    branch_allows_operation: bool
    has_current_assignment: bool
    can_query: bool
    can_operate: bool
    can_administer: bool


HOpPredicate = Callable[[FunctionalScope], bool]

ResourceT = TypeVar("ResourceT")


@dataclass(frozen=True, slots=True)
class ResourceAuthorizationCandidate(Generic[ResourceT]):
    resource: ResourceT
    persisted_scope: int | None


@dataclass(frozen=True, slots=True)
class ResourceAuthorizationEvidence:
    global_granted: bool
    contextual_scope_ids: frozenset[int]

    def contextual_granted(self, id_sucursal: int | None) -> bool:
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
        if mode is AdministrativeAuthorizationMode.EXPLICIT_CONTEXT:
            if (
                not isinstance(id_sucursal, int)
                or isinstance(id_sucursal, bool)
                or id_sucursal <= 0
            ):
                raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
            if h_op is None:
                raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)

        try:
            projection = AdministrativeAuthorizationRepository(self.db).resolve_permission(
                id_usuario,
                permission_code,
                id_sucursal=(
                    id_sucursal
                    if mode is AdministrativeAuthorizationMode.EXPLICIT_CONTEXT
                    else None
                ),
            )
        except Exception as exc:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE) from exc

        self._validate_projection(projection)
        if not projection.principal_active:
            return AdministrativeAuthorizationDecision.DENIED
        if not projection.permission_active or projection.denied:
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
                can_query=projection.can_query,
                can_operate=projection.can_operate,
                can_administer=projection.can_administer,
            )
            try:
                functional_enabled = h_op(scope)
            except Exception as exc:
                raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE) from exc
            granted = bool(functional_enabled) and (
                projection.global_granted or projection.contextual_granted
            )
        else:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
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
        if not paths or offset < 0 or limit is not None and limit < 0:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        scope_ids = {
            candidate.persisted_scope
            for candidate in candidates
            if candidate.persisted_scope is not None
        }
        try:
            projection = AdministrativeAuthorizationRepository(
                self.db
            ).resolve_resource_permission(id_usuario, permission_code, scope_ids)
        except Exception as exc:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE) from exc
        self._validate_resource_projection(projection)
        if (
            not projection.principal_active
            or not projection.permission_active
            or projection.denied
        ):
            raise InsufficientAdministrativeAuthorization(
                "La autorización efectiva es insuficiente."
            )
        evidence = ResourceAuthorizationEvidence(
            global_granted=projection.global_granted,
            contextual_scope_ids=projection.contextual_scope_ids,
        )
        authorized: list[ResourceAuthorizationCandidate[ResourceT]] = []
        try:
            for candidate in candidates:
                if any(
                    path.functional(candidate) and path.authorization(candidate, evidence)
                    for path in paths
                ):
                    authorized.append(candidate)
        except Exception as exc:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE) from exc
        total = len(authorized)
        stop = None if limit is None else offset + limit
        return AuthorizedResourcePage(items=tuple(authorized[offset:stop]), total=total)

    def _validate_permission_code(self, permission_code: str) -> None:
        if not isinstance(permission_code, str) or not permission_code.strip():
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)

    def _validate_projection(self, projection: object) -> None:
        if not isinstance(projection, AdministrativeAuthorizationProjection):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        if not projection.permission_defined:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)

    def _validate_resource_projection(self, projection: object) -> None:
        if not isinstance(projection, ResourceAuthorizationProjection):
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
        if not projection.permission_defined:
            raise AdministrativeAuthorizationTechnicalError(self._TECHNICAL_MESSAGE)
