from datetime import datetime
from typing import Any, Protocol

from app.application.common.results import AppResult


class ComercialRepository(Protocol):
    def list_ventas(
        self,
        *,
        q: str | None,
        estado_venta: str | None,
        id_persona: int | None,
        rol_codigo: str | None,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        tipo_plan_financiero: str | None,
        fecha_venta_desde: datetime | None,
        fecha_venta_hasta: datetime | None,
        con_saldo: bool | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]: ...


class ListVentasService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        q: str | None,
        estado_venta: str | None,
        id_persona: int | None,
        rol_codigo: str | None,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        tipo_plan_financiero: str | None,
        fecha_venta_desde: datetime | None,
        fecha_venta_hasta: datetime | None,
        con_saldo: bool | None,
        limit: int,
        offset: int,
    ) -> AppResult[dict[str, Any]]:
        if limit < 0 or offset < 0:
            return AppResult.fail("INVALID_PAGINATION")

        return AppResult.ok(
            self.repository.list_ventas(
                q=q,
                estado_venta=estado_venta,
                id_persona=id_persona,
                rol_codigo=rol_codigo,
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                tipo_plan_financiero=tipo_plan_financiero,
                fecha_venta_desde=fecha_venta_desde,
                fecha_venta_hasta=fecha_venta_hasta,
                con_saldo=con_saldo,
                limit=limit,
                offset=offset,
            )
        )
