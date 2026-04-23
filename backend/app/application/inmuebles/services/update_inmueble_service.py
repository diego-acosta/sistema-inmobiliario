from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.inmuebles.commands.update_inmueble import UpdateInmuebleCommand


@dataclass(slots=True)
class InmuebleUpdatePayload:
    id_inmueble: int
    id_desarrollo: int | None
    codigo_inmueble: str
    nombre_inmueble: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_juridico: str
    observaciones: str | None
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

    def update_inmueble(self, payload: InmuebleUpdatePayload) -> Any | None:
        ...


class UpdateInmuebleService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, command: UpdateInmuebleCommand) -> AppResult[dict[str, Any]]:
        inmueble = self.repository.get_inmueble_for_update(command.id_inmueble)
        if inmueble is None:
            return AppResult.fail("NOT_FOUND_INMUEBLE")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != inmueble["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        if (
            command.id_desarrollo is not None
            and not self.repository.desarrollo_exists(command.id_desarrollo)
        ):
            return AppResult.fail("NOT_FOUND_DESARROLLO")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = InmuebleUpdatePayload(
            id_inmueble=command.id_inmueble,
            id_desarrollo=command.id_desarrollo,
            codigo_inmueble=command.codigo_inmueble,
            nombre_inmueble=command.nombre_inmueble,
            superficie=command.superficie,
            estado_administrativo=command.estado_administrativo,
            estado_juridico=command.estado_juridico,
            observaciones=command.observaciones,
            version_registro_actual=inmueble["version_registro"],
            version_registro_nueva=inmueble["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        updated = self.repository.update_inmueble(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        id_inmueble = (
            updated["id_inmueble"]
            if isinstance(updated, dict)
            else getattr(updated, "id_inmueble")
        )

        return AppResult.ok(
            {
                "id_inmueble": id_inmueble,
                "version_registro": payload.version_registro_nueva,
                "id_desarrollo": payload.id_desarrollo,
                "codigo_inmueble": payload.codigo_inmueble,
                "nombre_inmueble": payload.nombre_inmueble,
                "superficie": payload.superficie,
                "estado_administrativo": payload.estado_administrativo,
                "estado_juridico": payload.estado_juridico,
                "observaciones": payload.observaciones,
            }
        )
