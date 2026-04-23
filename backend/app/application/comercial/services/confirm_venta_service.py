from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from app.application.comercial.commands.confirm_venta import ConfirmVentaCommand
from app.application.comercial.services.create_reserva_venta_service import (
    ESTADOS_VENTA_CONFLICTIVOS,
)
from app.application.common.outbox import OutboxEventPayload
from app.application.common.results import AppResult


ESTADOS_CONFIRMABLES_VENTA = {"borrador", "activa"}
ESTADO_CONFIRMADO_VENTA = "confirmada"
ESTADOS_RESERVA_VINCULADA_COMPATIBLES = {"confirmada", "finalizada"}


@dataclass(slots=True)
class VentaConfirmPayload:
    id_venta: int
    estado_venta: str
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class ComercialRepository(Protocol):
    def get_venta(self, id_venta: int) -> dict[str, Any] | None:
        ...

    def get_reserva_venta(self, id_reserva_venta: int) -> dict[str, Any] | None:
        ...

    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def has_current_ocupacion_conflict(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
        ...

    def has_conflicting_active_venta(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
        exclude_id_venta: int | None = None,
    ) -> bool:
        ...

    def confirm_venta(
        self,
        payload: VentaConfirmPayload,
        *,
        outbox_event: OutboxEventPayload | None = None,
    ) -> dict[str, Any]:
        ...


class ConfirmVentaService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(self, command: ConfirmVentaCommand) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta(command.id_venta)
        if venta is None or venta["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_VENTA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != venta["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_venta = (venta["estado_venta"] or "").strip().lower()
        if estado_venta not in ESTADOS_CONFIRMABLES_VENTA:
            return AppResult.fail("INVALID_VENTA_STATE")

        objetos = venta["objetos"]
        if not objetos:
            return AppResult.fail("VENTA_WITHOUT_OBJECTS")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        existing_objects_by_key: dict[tuple[str, int], dict[str, Any]] = {}
        for objeto in objetos:
            id_inmueble = objeto["id_inmueble"]
            id_unidad_funcional = objeto["id_unidad_funcional"]

            if (id_inmueble is None) == (id_unidad_funcional is None):
                return AppResult.fail("INVALID_VENTA_OBJECTS")

            object_key = (
                ("inmueble", id_inmueble)
                if id_inmueble is not None
                else ("unidad_funcional", id_unidad_funcional)
            )
            if object_key in existing_objects_by_key:
                return AppResult.fail("INVALID_VENTA_OBJECTS")
            existing_objects_by_key[object_key] = objeto

            precio_asignado = objeto["precio_asignado"]
            if precio_asignado is None or precio_asignado <= 0:
                return AppResult.fail("INCOMPLETE_VENTA_CONDITIONS")

            if id_inmueble is not None and not self.repository.inmueble_exists(id_inmueble):
                return AppResult.fail("NOT_FOUND_INMUEBLE")

            if (
                id_unidad_funcional is not None
                and not self.repository.unidad_funcional_exists(id_unidad_funcional)
            ):
                return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

        monto_total = venta["monto_total"]
        if monto_total is None or monto_total <= 0:
            return AppResult.fail("INCOMPLETE_VENTA_CONDITIONS")

        suma_precios = sum(
            (objeto["precio_asignado"] for objeto in objetos),
            start=Decimal("0"),
        )
        if suma_precios != monto_total:
            return AppResult.fail("INCOMPLETE_VENTA_CONDITIONS")

        if venta["id_reserva_venta"] is not None:
            reserva = self.repository.get_reserva_venta(venta["id_reserva_venta"])
            if reserva is None or reserva["deleted_at"] is not None:
                return AppResult.fail("NOT_FOUND_RESERVA_VENTA")

            estado_reserva = (reserva["estado_reserva"] or "").strip().lower()
            if estado_reserva not in ESTADOS_RESERVA_VINCULADA_COMPATIBLES:
                return AppResult.fail("INVALID_LINKED_RESERVA_STATE")

        now = datetime.now(UTC)
        for objeto in objetos:
            if self.repository.has_current_ocupacion_conflict(
                id_inmueble=objeto["id_inmueble"],
                id_unidad_funcional=objeto["id_unidad_funcional"],
                at_datetime=now,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if self.repository.has_conflicting_active_venta(
                id_inmueble=objeto["id_inmueble"],
                id_unidad_funcional=objeto["id_unidad_funcional"],
                conflict_states=ESTADOS_VENTA_CONFLICTIVOS,
                exclude_id_venta=command.id_venta,
            ):
                return AppResult.fail("CONFLICTING_VENTA")

        payload = VentaConfirmPayload(
            id_venta=command.id_venta,
            estado_venta=ESTADO_CONFIRMADO_VENTA,
            observaciones=(
                command.observaciones
                if command.observaciones is not None
                else venta["observaciones"]
            ),
            version_registro_actual=venta["version_registro"],
            version_registro_nueva=venta["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=getattr(command.context, "op_id", None),
        )

        outbox_event = OutboxEventPayload(
            event_type="venta_confirmada",
            aggregate_type="venta",
            aggregate_id=command.id_venta,
            payload={
                "id_venta": command.id_venta,
                "id_reserva_venta": venta["id_reserva_venta"],
                "estado_venta": ESTADO_CONFIRMADO_VENTA,
                "objetos": [
                    {
                        "id_inmueble": objeto["id_inmueble"],
                        "id_unidad_funcional": objeto["id_unidad_funcional"],
                    }
                    for objeto in objetos
                ],
            },
            occurred_at=now,
        )

        result = self.repository.confirm_venta(payload, outbox_event=outbox_event)
        if result.get("status") == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")

        return AppResult.ok(result["data"])
