from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.comercial.commands.update_reserva_venta import (
    UpdateReservaVentaCommand,
)


ESTADOS_MODIFICABLES_RESERVA_VENTA = {
    "borrador",
    "activa",
    "confirmada",
}


@dataclass(slots=True)
class ReservaVentaUpdatePayload:
    id_reserva_venta: int
    codigo_reserva: str
    fecha_reserva: datetime
    fecha_vencimiento: datetime | None
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class ComercialRepository(Protocol):
    def get_reserva_venta(self, id_reserva_venta: int) -> dict[str, Any] | None:
        ...

    def venta_exists_for_reserva(self, id_reserva_venta: int) -> bool:
        ...

    def reserva_codigo_exists(
        self,
        codigo_reserva: str,
        *,
        exclude_id_reserva_venta: int | None = None,
    ) -> bool:
        ...

    def update_reserva_venta(
        self, payload: ReservaVentaUpdatePayload
    ) -> dict[str, Any] | None:
        ...


class UpdateReservaVentaService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(
        self, command: UpdateReservaVentaCommand
    ) -> AppResult[dict[str, Any]]:
        reserva = self.repository.get_reserva_venta(command.id_reserva_venta)
        if reserva is None or reserva["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_RESERVA_VENTA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != reserva["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        if not command.codigo_reserva.strip():
            return AppResult.fail("INVALID_REQUIRED_FIELDS")

        if (
            command.fecha_vencimiento is not None
            and command.fecha_vencimiento < command.fecha_reserva
        ):
            return AppResult.fail("INVALID_DATE_RANGE")

        estado_reserva = (reserva["estado_reserva"] or "").strip().lower()
        if estado_reserva not in ESTADOS_MODIFICABLES_RESERVA_VENTA:
            return AppResult.fail("INVALID_RESERVA_STATE")

        if self.repository.venta_exists_for_reserva(command.id_reserva_venta):
            return AppResult.fail("RESERVA_WITH_LINKED_VENTA")

        if self.repository.reserva_codigo_exists(
            command.codigo_reserva,
            exclude_id_reserva_venta=command.id_reserva_venta,
        ):
            return AppResult.fail("DUPLICATE_CODIGO_RESERVA")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        payload = ReservaVentaUpdatePayload(
            id_reserva_venta=command.id_reserva_venta,
            codigo_reserva=command.codigo_reserva,
            fecha_reserva=command.fecha_reserva,
            fecha_vencimiento=command.fecha_vencimiento,
            observaciones=command.observaciones,
            version_registro_actual=reserva["version_registro"],
            version_registro_nueva=reserva["version_registro"] + 1,
            updated_at=datetime.now(UTC),
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=getattr(command.context, "op_id", None),
        )

        updated = self.repository.update_reserva_venta(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        return AppResult.ok(updated)
