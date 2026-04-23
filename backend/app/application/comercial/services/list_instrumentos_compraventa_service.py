from datetime import datetime
from typing import Any, Protocol

from app.application.common.results import AppResult


class ComercialRepository(Protocol):
    def get_venta(self, id_venta: int) -> dict[str, Any] | None:
        ...

    def list_instrumentos_compraventa_for_venta(
        self,
        id_venta: int,
        *,
        tipo_instrumento: str | None,
        estado_instrumento: str | None,
        fecha_desde: datetime | None,
        fecha_hasta: datetime | None,
    ) -> dict[str, Any]:
        ...


class ListInstrumentosCompraventaService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(
        self,
        id_venta: int,
        *,
        tipo_instrumento: str | None,
        estado_instrumento: str | None,
        fecha_desde: datetime | None,
        fecha_hasta: datetime | None,
    ) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta(id_venta)
        if venta is None or venta["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(
            self.repository.list_instrumentos_compraventa_for_venta(
                id_venta,
                tipo_instrumento=tipo_instrumento,
                estado_instrumento=estado_instrumento,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )
        )
