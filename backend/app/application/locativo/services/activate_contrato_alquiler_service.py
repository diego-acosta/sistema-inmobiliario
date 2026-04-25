from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.locativo.commands.activate_contrato_alquiler import (
    ActivateContratoAlquilerCommand,
)


ESTADO_BORRADOR = "borrador"
ESTADO_ACTIVO = "activo"


@dataclass(slots=True)
class ContratoAlquilerActivatePayload:
    id_contrato_alquiler: int
    estado_contrato: str
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class LocativoRepository(Protocol):
    def get_contrato_alquiler(self, id_contrato_alquiler: int) -> dict[str, Any] | None: ...

    def activate_contrato_alquiler(self, payload: ContratoAlquilerActivatePayload) -> dict[str, Any]: ...


class ActivateContratoAlquilerService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(
        self, command: ActivateContratoAlquilerCommand
    ) -> AppResult[dict[str, Any]]:
        contrato = self.repository.get_contrato_alquiler(command.id_contrato_alquiler)
        if contrato is None or contrato["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_CONTRATO_ALQUILER")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != contrato["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_actual = (contrato["estado_contrato"] or "").strip().lower()
        if estado_actual != ESTADO_BORRADOR:
            return AppResult.fail("INVALID_CONTRATO_STATE")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = ContratoAlquilerActivatePayload(
            id_contrato_alquiler=command.id_contrato_alquiler,
            estado_contrato=ESTADO_ACTIVO,
            version_registro_actual=contrato["version_registro"],
            version_registro_nueva=contrato["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        result = self.repository.activate_contrato_alquiler(payload)
        if result.get("status") == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(result["data"])
