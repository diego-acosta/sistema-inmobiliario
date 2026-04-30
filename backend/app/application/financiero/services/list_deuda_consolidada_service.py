from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def list_deuda_consolidada(
        self,
        *,
        id_relacion_generadora: int | None,
        estado_obligacion: str | None,
        fecha_vencimiento_desde: date | None,
        fecha_vencimiento_hasta: date | None,
        con_saldo: bool | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]: ...


class ListDeudaConsolidadaService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        id_relacion_generadora: int | None,
        estado_obligacion: str | None,
        fecha_vencimiento_desde: date | None,
        fecha_vencimiento_hasta: date | None,
        con_saldo: bool | None,
        limit: int,
        offset: int,
    ) -> AppResult[dict[str, Any]]:
        if (
            fecha_vencimiento_desde is not None
            and fecha_vencimiento_hasta is not None
            and fecha_vencimiento_hasta < fecha_vencimiento_desde
        ):
            return AppResult.fail("FECHA_RANGO_INVALIDO")

        result = self.repository.list_deuda_consolidada(
            id_relacion_generadora=id_relacion_generadora,
            estado_obligacion=estado_obligacion,
            fecha_vencimiento_desde=fecha_vencimiento_desde,
            fecha_vencimiento_hasta=fecha_vencimiento_hasta,
            con_saldo=con_saldo,
            limit=limit,
            offset=offset,
        )
        return AppResult.ok(result)
