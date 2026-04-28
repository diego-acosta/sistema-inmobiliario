from __future__ import annotations

from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def list_relaciones_generadoras(
        self,
        *,
        tipo_origen: str | None,
        id_origen: int | None,
        vigente: bool | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]: ...


class ListRelacionesGeneradorasService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        tipo_origen: str | None,
        id_origen: int | None,
        vigente: bool | None,
        limit: int,
        offset: int,
    ) -> AppResult[dict[str, Any]]:
        result = self.repository.list_relaciones_generadoras(
            tipo_origen=tipo_origen,
            id_origen=id_origen,
            vigente=vigente,
            limit=limit,
            offset=offset,
        )
        return AppResult.ok(result)
