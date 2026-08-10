"""Dependency reusable de autorización administrativa GLOBAL."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.authentication import get_authenticated_principal
from app.api.dependencies import get_db
from app.api.schemas.administrativo import ErrorResponse
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
    AdministrativeAuthorizationService,
    AdministrativeAuthorizationTechnicalError,
    InsufficientAdministrativeAuthorization,
)

ADMINISTRATIVE_AUTHORIZATION_RESPONSES = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
}


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
            principal.id_usuario, permission_code
        )
        if decision is not AdministrativeAuthorizationDecision.GRANTED:
            raise InsufficientAdministrativeAuthorization(
                "La autorización efectiva es insuficiente."
            )
        return principal

    return dependency
