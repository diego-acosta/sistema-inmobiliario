from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.comercial.commands.delete_reserva_venta import (
    DeleteReservaVentaCommand,
)


ESTADOS_ELIMINABLES_RESERVA_VENTA = {
    "borrador",
    "activa",
}


@dataclass(slots=True)
class ReservaVentaDeletePayload:
    id_reserva_venta: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class ComercialRepository(Protocol):
    def get_reserva_venta(self, id_reserva_venta: int) -> dict[str, Any] | None:
        ...

    def venta_exists_for_reserva(self, id_reserva_venta: int) -> bool:
        ...

    def delete_reserva_venta(
        self, payload: ReservaVentaDeletePayload
    ) -> dict[str, Any] | None:
        ...


class DeleteReservaVentaService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(
        self, command: DeleteReservaVentaCommand
    ) -> AppResult[dict[str, Any]]:
        reserva = self.repository.get_reserva_venta(command.id_reserva_venta)
        if reserva is None or reserva["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_RESERVA_VENTA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != reserva["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_reserva = (reserva["estado_reserva"] or "").strip().lower()
        if estado_reserva not in ESTADOS_ELIMINABLES_RESERVA_VENTA:
            return AppResult.fail("INVALID_RESERVA_STATE")

        if self.repository.venta_exists_for_reserva(command.id_reserva_venta):
            return AppResult.fail("RESERVA_WITH_LINKED_VENTA")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        payload = ReservaVentaDeletePayload(
            id_reserva_venta=command.id_reserva_venta,
            version_registro_actual=reserva["version_registro"],
            version_registro_nueva=reserva["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=getattr(command.context, "op_id", None),
        )

        deleted = self.repository.delete_reserva_venta(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        return AppResult.ok(
            {
                "id_reserva_venta": deleted["id_reserva_venta"],
                "version_registro": deleted["version_registro"],
                "deleted": True,
            }
        )
