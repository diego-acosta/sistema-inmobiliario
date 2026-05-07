from typing import Any, Protocol

from app.application.common.results import AppResult


class ComprobanteImpuestoRepository(Protocol):
    def list_comprobantes_impuesto(self) -> list[dict[str, Any]]: ...


class ListComprobantesImpuestoService:
    def __init__(self, repository: ComprobanteImpuestoRepository) -> None:
        self.repository = repository

    def execute(self) -> AppResult[list[dict[str, Any]]]:
        return AppResult.ok(self.repository.list_comprobantes_impuesto())
