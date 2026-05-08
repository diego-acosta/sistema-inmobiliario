from typing import Any, Protocol

from app.application.common.results import AppResult


class LocativoRepository(Protocol):
    def get_contrato_alquiler_detalle_integral(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None: ...


class GetContratoAlquilerDetalleIntegralService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(self, id_contrato_alquiler: int) -> AppResult[dict[str, Any]]:
        contrato = self.repository.get_contrato_alquiler_detalle_integral(
            id_contrato_alquiler
        )
        if contrato is None or contrato["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND")
        return AppResult.ok(contrato)
