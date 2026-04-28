from __future__ import annotations

from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def get_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> dict[str, Any] | None: ...


class GetRelacionGeneradoraService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(self, id_relacion_generadora: int) -> AppResult[dict[str, Any]]:
        rg = self.repository.get_relacion_generadora(id_relacion_generadora)
        if rg is None or rg["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_RELACION_GENERADORA")
        return AppResult.ok(rg)
