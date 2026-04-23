from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.inmuebles.commands.associate_inmueble_desarrollo import (
    AssociateInmuebleDesarrolloCommand,
)


@dataclass(slots=True)
class InmuebleAssociateDesarrolloPayload:
    id_inmueble: int
    id_desarrollo: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class InmuebleRepository(Protocol):
    def get_inmueble_for_update(self, id_inmueble: int) -> dict[str, Any] | None:
        ...

    def desarrollo_exists(self, id_desarrollo: int) -> bool:
        ...

    def associate_inmueble_desarrollo(
        self, payload: InmuebleAssociateDesarrolloPayload
    ) -> Any | None:
        ...


class AssociateInmuebleDesarrolloService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(
        self, command: AssociateInmuebleDesarrolloCommand
    ) -> AppResult[dict[str, Any]]:
        inmueble = self.repository.get_inmueble_for_update(command.id_inmueble)
        if inmueble is None:
            return AppResult.fail("NOT_FOUND_INMUEBLE")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != inmueble["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        if not self.repository.desarrollo_exists(command.id_desarrollo):
            return AppResult.fail("NOT_FOUND_DESARROLLO")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = InmuebleAssociateDesarrolloPayload(
            id_inmueble=command.id_inmueble,
            id_desarrollo=command.id_desarrollo,
            version_registro_actual=inmueble["version_registro"],
            version_registro_nueva=inmueble["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        associated = self.repository.associate_inmueble_desarrollo(payload)
        if associated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_inmueble = (
            associated["id_inmueble"]
            if isinstance(associated, dict)
            else getattr(associated, "id_inmueble")
        )

        return AppResult.ok(
            {
                "id_inmueble": id_inmueble,
                "id_desarrollo": payload.id_desarrollo,
                "version_registro": payload.version_registro_nueva,
            }
        )
