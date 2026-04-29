from __future__ import annotations

from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def get_obligacion_financiera(
        self, id_obligacion_financiera: int
    ) -> dict[str, Any] | None: ...


class GetObligacionFinancieraService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(self, id_obligacion_financiera: int) -> AppResult[dict[str, Any]]:
        ob = self.repository.get_obligacion_financiera(id_obligacion_financiera)
        if ob is None or ob.get("deleted_at") is not None:
            return AppResult.fail("NOT_FOUND_OBLIGACION")
        return AppResult.ok(ob)
