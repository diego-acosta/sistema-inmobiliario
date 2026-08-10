"""Resolución default-deny de permisos administrativos GLOBAL."""

from enum import Enum

from app.infrastructure.persistence.repositories.administrative_authorization_repository import (
    AdministrativeAuthorizationProjection,
    AdministrativeAuthorizationRepository,
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


class AdministrativeAuthorizationService:
    def __init__(self, session) -> None:
        self.db = session

    def authorize(
        self, id_usuario: int, permission_code: str
    ) -> AdministrativeAuthorizationDecision:
        if not isinstance(permission_code, str) or not permission_code.strip():
            raise AdministrativeAuthorizationTechnicalError(
                "No fue posible resolver la autorización administrativa."
            )
        try:
            projection = AdministrativeAuthorizationRepository(
                self.db
            ).resolve_global_permission(id_usuario, permission_code)
        except Exception as exc:
            raise AdministrativeAuthorizationTechnicalError(
                "No fue posible resolver la autorización administrativa."
            ) from exc

        if not isinstance(projection, AdministrativeAuthorizationProjection):
            raise AdministrativeAuthorizationTechnicalError(
                "No fue posible resolver la autorización administrativa."
            )
        if not projection.permission_defined:
            raise AdministrativeAuthorizationTechnicalError(
                "No fue posible resolver la autorización administrativa."
            )
        if projection.granted:
            return AdministrativeAuthorizationDecision.GRANTED
        return AdministrativeAuthorizationDecision.DENIED
