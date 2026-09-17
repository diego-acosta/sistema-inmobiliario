"""Dependencies HTTP para el evaluator central de autorización D1."""

from collections.abc import Callable
import re
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.api.authentication import get_authenticated_principal
from app.api.dependencies import get_db
from app.api.schemas.administrativo import ErrorResponse
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
    AdministrativeAuthorizationMode,
    AdministrativeAuthorizationService,
    AdministrativeAuthorizationTechnicalError,
    HOpPredicate,
    InsufficientAdministrativeAuthorization,
)

ADMINISTRATIVE_AUTHORIZATION_RESPONSES = {
    401: {"model": ErrorResponse},
    400: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}

CENTRAL_CONTEXT_HEADER = "X-Sucursal-Id"
_POSTGRES_BIGINT_MAX = 9_223_372_036_854_775_807


class CentralContextHeaderError(ValueError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.header = CENTRAL_CONTEXT_HEADER
        self.reason = reason


def parse_central_branch_selector(request: Request) -> int:
    """Parsea el selector humano central sin fallback ni instalación."""
    values = request.headers.getlist(CENTRAL_CONTEXT_HEADER)
    if len(values) != 1:
        raise CentralContextHeaderError("required_once")
    raw_value = values[0]
    if re.fullmatch(r"[0-9]+", raw_value) is None:
        raise CentralContextHeaderError("positive_bigint_required")
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise CentralContextHeaderError("positive_bigint_required") from exc
    if value <= 0 or value > _POSTGRES_BIGINT_MAX:
        raise CentralContextHeaderError("positive_bigint_required")
    return value


def require_administrative_permission(
    permission_code: str,
) -> Callable[..., AuthenticatedPrincipal]:
    """Construye un guard que preserva el principal canónico al conceder."""
    if not isinstance(permission_code, str) or not permission_code.strip():
        raise AdministrativeAuthorizationTechnicalError(
            "No fue posible resolver la autorización administrativa."
        )

    def dependency(
        principal: Annotated[
            AuthenticatedPrincipal, Depends(get_authenticated_principal)
        ],
        db: Annotated[Session, Depends(get_db)],
    ) -> AuthenticatedPrincipal:
        decision = AdministrativeAuthorizationService(db).authorize(
            principal.id_usuario,
            permission_code,
            mode=AdministrativeAuthorizationMode.GLOBAL,
        )
        if decision is not AdministrativeAuthorizationDecision.GRANTED:
            raise InsufficientAdministrativeAuthorization(
                "La autorización efectiva es insuficiente."
            )
        return principal

    return dependency


def require_contextual_administrative_permission(
    permission_code: str,
    *,
    h_op: HOpPredicate | None,
) -> Callable[..., AuthenticatedPrincipal]:
    """Construye un guard contextual con H declarado por la operación."""
    if not isinstance(permission_code, str) or not permission_code.strip():
        raise AdministrativeAuthorizationTechnicalError(
            "No fue posible resolver la autorización administrativa."
        )

    def dependency(
        principal: Annotated[
            AuthenticatedPrincipal, Depends(get_authenticated_principal)
        ],
        id_sucursal: Annotated[int, Depends(parse_central_branch_selector)],
        db: Annotated[Session, Depends(get_db)],
    ) -> AuthenticatedPrincipal:
        decision = AdministrativeAuthorizationService(db).authorize(
            principal.id_usuario,
            permission_code,
            mode=AdministrativeAuthorizationMode.EXPLICIT_CONTEXT,
            id_sucursal=id_sucursal,
            h_op=h_op,
        )
        if decision is not AdministrativeAuthorizationDecision.GRANTED:
            raise InsufficientAdministrativeAuthorization(
                "La autorización efectiva es insuficiente."
            )
        return principal

    return dependency
