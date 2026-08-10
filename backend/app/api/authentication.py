"""Dependencias HTTP canónicas de autenticación administrativa."""

from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.application.administrativo.authentication import (
    AuthenticatedPrincipal,
    AuthenticationService,
    parse_bearer_header,
)

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="BearerAuth")


def get_authenticated_principal(
    request: Request,
    _bearer: Annotated[
        HTTPAuthorizationCredentials | None, Security(bearer_scheme)
    ],
    db: Session = Depends(get_db),
) -> AuthenticatedPrincipal:
    """Obtiene identidad humana sólo desde un bearer y su sesión persistida."""
    # HTTPBearer declara el contrato OpenAPI, pero el parser estricto de #446
    # conserva autoridad sobre el valor raw y sobre todos sus rechazos.
    access_token = parse_bearer_header(request.headers.get("Authorization"))
    return AuthenticationService(db, settings=None).resolve_principal(access_token)
