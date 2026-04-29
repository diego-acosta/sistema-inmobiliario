from __future__ import annotations

from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def list_conceptos_financieros(
        self,
        *,
        estado: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]: ...


class ListConceptosFinancierosService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        estado: str | None,
        limit: int,
        offset: int,
    ) -> AppResult[dict[str, Any]]:
        result = self.repository.list_conceptos_financieros(
            estado=estado,
            limit=limit,
            offset=offset,
        )
        return AppResult.ok(result)
