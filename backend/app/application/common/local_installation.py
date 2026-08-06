"""Resolución read-only de la identidad canónica de la instalación local."""

from dataclasses import dataclass
from typing import TYPE_CHECKING
from uuid import UUID

from app.infrastructure.persistence.repositories.instalacion_repository import (
    InstalacionRepository,
)

if TYPE_CHECKING:
    from app.config.settings import Settings


class LocalInstallationError(RuntimeError):
    """Error externo sanitizado al resolver la instalación local."""


class LocalInstallationNotConfigured(LocalInstallationError):
    pass


class InvalidLocalInstallationCode(LocalInstallationError):
    pass


class LocalInstallationNotFound(LocalInstallationError):
    pass


class LocalInstallationNotEligible(LocalInstallationError):
    pass


class LocalInstallationStateConflict(LocalInstallationError):
    pass


class LocalInstallationTechnicalError(LocalInstallationError):
    pass


@dataclass(frozen=True, slots=True)
class LocalInstallationIdentity:
    id_instalacion: int
    uid_global: UUID
    codigo_instalacion: str
    nombre_instalacion: str


def resolve_local_installation(session, settings: "Settings") -> LocalInstallationIdentity:
    """Resuelve exactamente una instalación elegible dentro de la sesión recibida."""
    try:
        row = InstalacionRepository(session).get_by_codigo_exact(
            settings.local_installation_code
        )
    except Exception as exc:
        raise LocalInstallationTechnicalError(
            "No fue posible resolver la instalación local."
        ) from exc

    if row is None:
        raise LocalInstallationNotFound("La instalación local configurada no existe.")
    if row["deleted_at"] is not None:
        raise LocalInstallationNotEligible(
            "La instalación local configurada no es elegible."
        )

    state = row["estado_instalacion"]
    if state == "ACTIVA":
        if row["fecha_baja"] is not None:
            raise LocalInstallationStateConflict(
                "La instalación local tiene un estado inconsistente."
            )
    elif state in {"INACTIVA", "DADA_DE_BAJA"}:
        raise LocalInstallationNotEligible(
            "La instalación local configurada no es elegible."
        )
    else:
        raise LocalInstallationStateConflict(
            "La instalación local tiene un estado desconocido."
        )

    try:
        return LocalInstallationIdentity(
            id_instalacion=row["id_instalacion"],
            uid_global=UUID(str(row["uid_global"])),
            codigo_instalacion=row["codigo_instalacion"],
            nombre_instalacion=row["nombre_instalacion"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise LocalInstallationTechnicalError(
            "La identidad de la instalación local es inválida."
        ) from exc
