from datetime import date
from typing import Any, Protocol

from app.application.common.results import AppResult


class LocativoRepository(Protocol):
    def get_contrato_alquiler(self, id_contrato_alquiler: int) -> dict[str, Any] | None: ...

    def list_condiciones_economicas_alquiler(
        self,
        *,
        id_contrato_alquiler: int,
        vigente: bool | None,
        fecha_desde: date | None,
        fecha_hasta: date | None,
        moneda: str | None,
        periodicidad: str | None,
    ) -> dict[str, Any]: ...


class ListCondicionesEconomicasAlquilerService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        id_contrato_alquiler: int,
        vigente: bool | None,
        fecha_desde: date | None,
        fecha_hasta: date | None,
        moneda: str | None,
        periodicidad: str | None,
    ) -> AppResult[dict[str, Any]]:
        contrato = self.repository.get_contrato_alquiler(id_contrato_alquiler)
        if contrato is None or contrato["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_CONTRATO_ALQUILER")

        result = self.repository.list_condiciones_economicas_alquiler(
            id_contrato_alquiler=id_contrato_alquiler,
            vigente=vigente,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            moneda=moneda,
            periodicidad=periodicidad,
        )
        return AppResult.ok(result)
