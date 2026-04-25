from datetime import date
from typing import Any, Protocol

from app.application.common.results import AppResult


class LocativoRepository(Protocol):
    def list_contratos_alquiler(
        self,
        *,
        codigo_contrato: str | None,
        estado_contrato: str | None,
        fecha_desde: date | None,
        fecha_hasta: date | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]: ...


class ListContratosAlquilerService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        codigo_contrato: str | None,
        estado_contrato: str | None,
        fecha_desde: date | None,
        fecha_hasta: date | None,
        limit: int,
        offset: int,
    ) -> AppResult[dict[str, Any]]:
        if limit < 0 or offset < 0:
            return AppResult.fail("INVALID_PAGINATION")

        result = self.repository.list_contratos_alquiler(
            codigo_contrato=codigo_contrato,
            estado_contrato=estado_contrato,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            limit=limit,
            offset=offset,
        )
        return AppResult.ok(result)
