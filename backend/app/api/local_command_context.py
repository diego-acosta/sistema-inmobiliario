"""Adaptadores HTTP del contexto canónico para commands locales."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from app.api.authentication import get_authenticated_principal
from app.api.core_ef_headers import (
    CoreEFHeaderValidationError,
    parse_local_command_core_ef_headers,
)
from app.api.dependencies import get_db
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.common.local_command_context import (
    LocalCommandActor,
    LocalCommandContextPolicy,
    LocalInstallationUnavailable,
    ResolvedLocalCommandContext,
    resolve_local_command_context,
)
from app.application.common.local_command_headers import LocalCommandCoreEFHeaders
from app.application.common.local_installation import LocalInstallationError
from app.config.settings import get_settings
from fastapi import Depends, Request
from sqlalchemy.orm import Session


class LocalCommandHeaderError(RuntimeError):
    code = "LOCAL_COMMAND_HEADER_INVALID"

    def __init__(self, *, header_name: str, reason: str) -> None:
        self.header_name = header_name
        self.reason = reason
        super().__init__("El contexto técnico contiene un header inválido.")


def _get_local_context_settings():
    try:
        return get_settings()
    except LocalInstallationError as exc:
        raise LocalInstallationUnavailable(
            "La instalación local no está disponible."
        ) from exc


def _parse_request(
    request: Request, policy: LocalCommandContextPolicy
) -> LocalCommandCoreEFHeaders:
    try:
        return parse_local_command_core_ef_headers(
            request.headers.get("X-Op-Id"),
            request.headers.get("X-Sucursal-Id"),
            request.headers.get("X-Instalacion-Id"),
            request.headers.get("If-Match-Version"),
            require_installation_assertion=policy.require_installation_assertion,
            require_if_match_version=policy.require_if_match_version,
        )
    except CoreEFHeaderValidationError as exc:
        raise LocalCommandHeaderError(
            header_name=exc.header_name, reason=exc.reason
        ) from exc


def require_local_human_command_context(
    *,
    require_if_match_version: bool,
    require_installation_assertion: bool,
) -> Callable[..., ResolvedLocalCommandContext]:
    policy = LocalCommandContextPolicy(
        actor=LocalCommandActor.HUMAN,
        require_if_match_version=require_if_match_version,
        require_installation_assertion=require_installation_assertion,
    )

    def dependency(
        request: Request,
        principal: Annotated[
            AuthenticatedPrincipal, Depends(get_authenticated_principal)
        ],
        db: Annotated[Session, Depends(get_db)],
    ) -> ResolvedLocalCommandContext:
        return resolve_local_command_context(
            db,
            _get_local_context_settings(),
            policy=policy,
            headers=_parse_request(request, policy),
            principal=principal,
        )

    return dependency


def require_local_technical_command_context(
    *,
    require_if_match_version: bool,
    require_installation_assertion: bool,
) -> Callable[..., ResolvedLocalCommandContext]:
    policy = LocalCommandContextPolicy(
        actor=LocalCommandActor.TECHNICAL,
        require_if_match_version=require_if_match_version,
        require_installation_assertion=require_installation_assertion,
    )

    def dependency(
        request: Request,
        db: Annotated[Session, Depends(get_db)],
    ) -> ResolvedLocalCommandContext:
        return resolve_local_command_context(
            db,
            _get_local_context_settings(),
            policy=policy,
            headers=_parse_request(request, policy),
            principal=None,
        )

    return dependency
