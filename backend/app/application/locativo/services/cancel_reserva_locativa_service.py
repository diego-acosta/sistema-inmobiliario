from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.locativo.commands.cancel_reserva_locativa import (
    CancelReservaLocativaCommand,
)


ESTADOS_CANCELABLES = {"pendiente", "confirmada"}
ESTADO_CANCELADA = "cancelada"


@dataclass(slots=True)
class ReservaLocativaCancelPayload:
    id_reserva_locativa: int
    estado_reserva: str
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class LocativoRepository(Protocol):
    def get_reserva_locativa(self, id_reserva_locativa: int) -> dict[str, Any] | None: ...

    def cancel_reserva_locativa(
        self, payload: ReservaLocativaCancelPayload
    ) -> dict[str, Any]: ...


class CancelReservaLocativaService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(
        self, command: CancelReservaLocativaCommand
    ) -> AppResult[dict[str, Any]]:
        reserva = self.repository.get_reserva_locativa(command.id_reserva_locativa)
        if reserva is None or reserva["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_RESERVA_LOCATIVA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != reserva["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_actual = (reserva["estado_reserva"] or "").strip().lower()
        if estado_actual not in ESTADOS_CANCELABLES:
            return AppResult.fail("INVALID_RESERVA_STATE")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = ReservaLocativaCancelPayload(
            id_reserva_locativa=command.id_reserva_locativa,
            estado_reserva=ESTADO_CANCELADA,
            version_registro_actual=reserva["version_registro"],
            version_registro_nueva=reserva["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        result = self.repository.cancel_reserva_locativa(payload)
        if result.get("status") == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(result["data"])
