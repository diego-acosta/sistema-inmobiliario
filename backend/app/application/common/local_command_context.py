"""Contexto read-only para commands originados en el deployment local."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from app.application.common.local_command_headers import LocalCommandCoreEFHeaders
from app.application.common.local_installation import (
    LocalInstallationError,
    LocalInstallationIdentity,
    resolve_local_installation,
)
from app.infrastructure.persistence.repositories.technical_context_repository import (
    TechnicalContextRepository,
)

if TYPE_CHECKING:
    from app.application.administrativo.authentication import AuthenticatedPrincipal
    from app.config.settings import Settings
    from sqlalchemy.orm import Session


class LocalCommandActor(StrEnum):
    HUMAN = "HUMAN"
    TECHNICAL = "TECHNICAL"


@dataclass(frozen=True, slots=True)
class LocalCommandContextPolicy:
    actor: LocalCommandActor
    require_if_match_version: bool
    require_installation_assertion: bool


@dataclass(frozen=True, slots=True)
class ResolvedLocalCommandContext:
    principal: AuthenticatedPrincipal | None
    id_usuario: int | None
    id_sucursal: int
    local_installation: LocalInstallationIdentity
    id_instalacion: int
    uid_instalacion: UUID
    op_id: UUID
    if_match_version: int | None


class LocalCommandContextError(RuntimeError):
    """Base sanitizada para rechazos del contexto local."""

    code = "LOCAL_COMMAND_CONTEXT_ERROR"


class HumanPrincipalRequired(LocalCommandContextError):
    code = "HUMAN_PRINCIPAL_REQUIRED"


class LocalInstallationUnavailable(LocalCommandContextError):
    code = "LOCAL_INSTALLATION_UNAVAILABLE"


class InstallationAssertionMismatch(LocalCommandContextError):
    code = "INSTALLATION_CONTEXT_MISMATCH"


class OperationalBranchNotFound(LocalCommandContextError):
    code = "OPERATIONAL_BRANCH_NOT_FOUND"


class OperationalBranchNotEligible(LocalCommandContextError):
    code = "OPERATIONAL_BRANCH_NOT_ELIGIBLE"


class InstallationBranchMismatch(LocalCommandContextError):
    code = "INSTALLATION_BRANCH_MISMATCH"


class OperationalBranchScopeDenied(LocalCommandContextError):
    code = "OPERATIONAL_BRANCH_SCOPE_DENIED"


class LocalCommandContextTechnicalError(LocalCommandContextError):
    code = "LOCAL_COMMAND_CONTEXT_TECHNICAL_ERROR"


def resolve_local_command_context(
    session: Session,
    settings: Settings,
    *,
    policy: LocalCommandContextPolicy,
    headers: LocalCommandCoreEFHeaders,
    principal: AuthenticatedPrincipal | None,
) -> ResolvedLocalCommandContext:
    """Resuelve identidad y scope sin apropiarse de la transacción del caller."""
    if policy.actor is LocalCommandActor.HUMAN and principal is None:
        raise HumanPrincipalRequired("El command humano requiere autenticación.")

    try:
        installation = resolve_local_installation(session, settings)
    except LocalInstallationError as exc:
        raise LocalInstallationUnavailable(
            "La instalación local no está disponible."
        ) from exc

    assertion = headers.x_instalacion_id
    if assertion is not None and assertion != installation.id_instalacion:
        raise InstallationAssertionMismatch(
            "La aserción de instalación no coincide con el contexto local."
        )

    effective_principal = (
        principal if policy.actor is LocalCommandActor.HUMAN else None
    )
    id_usuario = (
        effective_principal.id_usuario if effective_principal is not None else None
    )
    try:
        projection = TechnicalContextRepository(session).resolve_operational_context(
            id_sucursal=headers.x_sucursal_id,
            id_instalacion=installation.id_instalacion,
            id_usuario=(
                id_usuario if policy.actor is LocalCommandActor.HUMAN else None
            ),
        )
    except Exception as exc:
        raise LocalCommandContextTechnicalError(
            "No fue posible validar el contexto local."
        ) from exc

    if not projection.branch_exists:
        raise OperationalBranchNotFound("La Sucursal operativa no existe.")
    if not projection.branch_eligible:
        raise OperationalBranchNotEligible("La Sucursal operativa no es elegible.")
    if not projection.installation_belongs_to_branch:
        raise InstallationBranchMismatch(
            "La Sucursal no es compatible con la instalación local."
        )
    if (
        policy.actor is LocalCommandActor.HUMAN
        and projection.principal_has_operational_scope is not True
    ):
        raise OperationalBranchScopeDenied(
            "El principal no posee alcance sobre la Sucursal operativa."
        )

    return ResolvedLocalCommandContext(
        principal=effective_principal,
        id_usuario=id_usuario,
        id_sucursal=headers.x_sucursal_id,
        local_installation=installation,
        id_instalacion=installation.id_instalacion,
        uid_instalacion=installation.uid_global,
        op_id=headers.x_op_id,
        if_match_version=headers.if_match_version,
    )
