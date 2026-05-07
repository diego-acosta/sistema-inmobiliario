from typing import Any, Protocol

from app.application.common.results import AppResult


class ComprobanteImpuestoRepository(Protocol):
    def get_comprobante_impuesto(
        self, id_comprobante_impuesto: int
    ) -> dict[str, Any] | None: ...


class GetComprobanteImpuestoService:
    def __init__(self, repository: ComprobanteImpuestoRepository) -> None:
        self.repository = repository

    def execute(self, id_comprobante_impuesto: int) -> AppResult[dict[str, Any]]:
        comprobante = self.repository.get_comprobante_impuesto(id_comprobante_impuesto)
        if comprobante is None:
            return AppResult.fail("NOT_FOUND_COMPROBANTE_IMPUESTO")
        return AppResult.ok(comprobante)
