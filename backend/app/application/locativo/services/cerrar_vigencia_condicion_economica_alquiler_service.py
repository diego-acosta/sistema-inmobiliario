from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.locativo.commands.cerrar_vigencia_condicion_economica_alquiler import (
    CerrarVigenciaCondicionEconomicaAlquilerCommand,
)


@dataclass(slots=True)
class CondicionEconomicaAlquilerCerrarVigenciaPayload:
    id_condicion_economica: int
    id_contrato_alquiler: int
    fecha_hasta: date
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class LocativoRepository(Protocol):
    def get_contrato_alquiler(self, id_contrato_alquiler: int) -> dict[str, Any] | None: ...

    def get_condicion_economica_alquiler(
        self,
        id_condicion_economica: int,
        id_contrato_alquiler: int,
    ) -> dict[str, Any] | None: ...

    def cerrar_vigencia_condicion_economica_alquiler(
        self, payload: CondicionEconomicaAlquilerCerrarVigenciaPayload
    ) -> dict[str, Any]: ...


class CerrarVigenciaCondicionEconomicaAlquilerService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(
        self, command: CerrarVigenciaCondicionEconomicaAlquilerCommand
    ) -> AppResult[dict[str, Any]]:
        contrato = self.repository.get_contrato_alquiler(command.id_contrato_alquiler)
        if contrato is None or contrato["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_CONTRATO_ALQUILER")

        condicion = self.repository.get_condicion_economica_alquiler(
            id_condicion_economica=command.id_condicion_economica,
            id_contrato_alquiler=command.id_contrato_alquiler,
        )
        if condicion is None or condicion["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_CONDICION_ECONOMICA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != condicion["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.fecha_hasta < condicion["fecha_desde"]:
            return AppResult.fail("INVALID_DATE_RANGE")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = CondicionEconomicaAlquilerCerrarVigenciaPayload(
            id_condicion_economica=command.id_condicion_economica,
            id_contrato_alquiler=command.id_contrato_alquiler,
            fecha_hasta=command.fecha_hasta,
            version_registro_actual=condicion["version_registro"],
            version_registro_nueva=condicion["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        result = self.repository.cerrar_vigencia_condicion_economica_alquiler(payload)
        if result.get("status") == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(result["data"])
