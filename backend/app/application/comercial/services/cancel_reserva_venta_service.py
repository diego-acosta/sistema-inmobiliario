from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.comercial.commands.cancel_reserva_venta import (
    CancelReservaVentaCommand,
)
from app.application.comercial.services.create_reserva_venta_service import (
    ESTADOS_VENTA_CONFLICTIVOS,
)
from app.application.common.results import AppResult


ESTADOS_CANCELABLES_RESERVA_VENTA = {
    "borrador",
    "activa",
    "confirmada",
}
ESTADO_CANCELADO_RESERVA_VENTA = "cancelada"
ESTADO_BLOQUEO_RESERVA_CONFIRMADA = "RESERVADA"
ESTADO_DISPONIBILIDAD_LIBERADA = "DISPONIBLE"


@dataclass(slots=True)
class ReservaVentaCancelPayload:
    id_reserva_venta: int
    estado_reserva: str
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class ReservaVentaDisponibilidadReplacePayload:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    motivo: str | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class ComercialRepository(Protocol):
    def get_reserva_venta(self, id_reserva_venta: int) -> dict[str, Any] | None:
        ...

    def has_active_venta_for_reserva(
        self,
        id_reserva_venta: int,
        *,
        conflict_states: set[str],
    ) -> bool:
        ...

    def cancel_reserva_venta(
        self,
        payload: ReservaVentaCancelPayload,
        disponibilidades: list[ReservaVentaDisponibilidadReplacePayload],
    ) -> dict[str, Any]:
        ...


class CancelReservaVentaService:
    def __init__(self, repository: ComercialRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CancelReservaVentaCommand
    ) -> AppResult[dict[str, Any]]:
        reserva = self.repository.get_reserva_venta(command.id_reserva_venta)
        if reserva is None or reserva["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_RESERVA_VENTA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != reserva["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_reserva = (reserva["estado_reserva"] or "").strip().lower()
        if estado_reserva not in ESTADOS_CANCELABLES_RESERVA_VENTA:
            return AppResult.fail("INVALID_RESERVA_STATE")

        if self.repository.has_active_venta_for_reserva(
            command.id_reserva_venta,
            conflict_states=ESTADOS_VENTA_CONFLICTIVOS,
        ):
            return AppResult.fail("CONFLICTING_VENTA")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = ReservaVentaCancelPayload(
            id_reserva_venta=command.id_reserva_venta,
            estado_reserva=ESTADO_CANCELADO_RESERVA_VENTA,
            version_registro_actual=reserva["version_registro"],
            version_registro_nueva=reserva["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        disponibilidades: list[ReservaVentaDisponibilidadReplacePayload] = []
        if estado_reserva == "confirmada":
            objetos = reserva["objetos"]
            if not objetos:
                return AppResult.fail("RESERVA_WITHOUT_OBJECTS")

            for objeto in objetos:
                disponibilidades.append(
                    ReservaVentaDisponibilidadReplacePayload(
                        id_inmueble=objeto["id_inmueble"],
                        id_unidad_funcional=objeto["id_unidad_funcional"],
                        estado_disponibilidad=ESTADO_DISPONIBILIDAD_LIBERADA,
                        fecha_desde=now,
                        motivo="Cancelacion de reserva confirmada",
                        observaciones=None,
                        uid_global=str(self.uuid_generator()),
                        version_registro=1,
                        created_at=now,
                        updated_at=now,
                        id_instalacion_origen=id_instalacion,
                        id_instalacion_ultima_modificacion=id_instalacion,
                        op_id_alta=op_id,
                        op_id_ultima_modificacion=op_id,
                    )
                )

        result = self.repository.cancel_reserva_venta(payload, disponibilidades)
        status = result.get("status")
        if status == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")
        if status in {
            "NO_OPEN_DISPONIBILIDAD",
            "MULTIPLE_OPEN_DISPONIBILIDAD",
            "CURRENT_NOT_EXPECTED_STATE",
        }:
            return AppResult.fail("INVALID_RESERVA_BLOCK")

        return AppResult.ok(result["data"])
