"""Dependencias HTTP canónicas de autenticación administrativa."""

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.application.administrativo.authentication import (
    AuthenticatedPrincipal,
    AuthenticationService,
    parse_bearer_header,
)


def get_authenticated_principal(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
    db: Session = Depends(get_db),
) -> AuthenticatedPrincipal:
    """Obtiene identidad humana sólo desde un bearer y su sesión persistida."""
    access_token = parse_bearer_header(authorization)
    return AuthenticationService(db, settings=None).resolve_principal(access_token)
