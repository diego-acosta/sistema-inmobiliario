from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.comercial.commands.activate_reserva_venta import (
    ActivateReservaVentaCommand,
)
from app.application.comercial.services.create_reserva_venta_service import (
    ESTADOS_RESERVA_CONFLICTIVOS,
    ESTADOS_VENTA_CONFLICTIVOS,
)


ESTADO_BORRADOR_RESERVA_VENTA = "borrador"
ESTADO_ACTIVA_RESERVA_VENTA = "activa"


@dataclass(slots=True)
class ReservaVentaActivatePayload:
    id_reserva_venta: int
    estado_reserva: str
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class ComercialRepository(Protocol):
    def get_reserva_venta(self, id_reserva_venta: int) -> dict[str, Any] | None:
        ...

    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def has_current_disponibilidad_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
        ...

    def has_current_disponibilidad_no_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
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
    ) -> bool:
        ...

    def has_conflicting_active_reserva(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
        exclude_id_reserva_venta: int | None = None,
    ) -> bool:
        ...

    def activate_reserva_venta(
        self, payload: ReservaVentaActivatePayload
    ) -> dict[str, Any]:
        ...


class ActivateReservaVentaService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(
        self, command: ActivateReservaVentaCommand
    ) -> AppResult[dict[str, Any]]:
        reserva = self.repository.get_reserva_venta(command.id_reserva_venta)
        if reserva is None or reserva["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_RESERVA_VENTA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != reserva["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_reserva = (reserva["estado_reserva"] or "").strip().lower()
        if estado_reserva != ESTADO_BORRADOR_RESERVA_VENTA:
            return AppResult.fail("INVALID_RESERVA_STATE")

        objetos = reserva["objetos"]
        if not objetos:
            return AppResult.fail("RESERVA_WITHOUT_OBJECTS")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        for objeto in objetos:
            id_inmueble = objeto["id_inmueble"]
            id_unidad_funcional = objeto["id_unidad_funcional"]

            if id_inmueble is not None and not self.repository.inmueble_exists(id_inmueble):
                return AppResult.fail("NOT_FOUND_INMUEBLE")

            if (
                id_unidad_funcional is not None
                and not self.repository.unidad_funcional_exists(id_unidad_funcional)
            ):
                return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

            if self.repository.has_current_disponibilidad_no_disponible(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                at_datetime=now,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if not self.repository.has_current_disponibilidad_disponible(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                at_datetime=now,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if self.repository.has_current_ocupacion_conflict(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                at_datetime=now,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if self.repository.has_conflicting_active_venta(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                conflict_states=ESTADOS_VENTA_CONFLICTIVOS,
            ):
                return AppResult.fail("CONFLICTING_VENTA")

            if self.repository.has_conflicting_active_reserva(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                conflict_states=ESTADOS_RESERVA_CONFLICTIVOS,
                exclude_id_reserva_venta=command.id_reserva_venta,
            ):
                return AppResult.fail("CONFLICTING_RESERVA")

        payload = ReservaVentaActivatePayload(
            id_reserva_venta=command.id_reserva_venta,
            estado_reserva=ESTADO_ACTIVA_RESERVA_VENTA,
            version_registro_actual=reserva["version_registro"],
            version_registro_nueva=reserva["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        result = self.repository.activate_reserva_venta(payload)
        status = result.get("status")
        if status == "NOT_FOUND":
            return AppResult.fail("NOT_FOUND_RESERVA_VENTA")
        if status == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(result["data"])
