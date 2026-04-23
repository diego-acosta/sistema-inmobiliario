from datetime import datetime
from typing import Any, Protocol

from app.application.common.results import AppResult


class ComercialRepository(Protocol):
    def get_venta(self, id_venta: int) -> dict[str, Any] | None:
        ...

    def list_escrituraciones_for_venta(
        self,
        id_venta: int,
        *,
        fecha_desde: datetime | None,
        fecha_hasta: datetime | None,
        numero_escritura: str | None,
    ) -> dict[str, Any]:
        ...


class ListEscrituracionesService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(
        self,
        id_venta: int,
        *,
        fecha_desde: datetime | None,
        fecha_hasta: datetime | None,
        numero_escritura: str | None,
    ) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta(id_venta)
        if venta is None or venta["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(
            self.repository.list_escrituraciones_for_venta(
                id_venta,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
                numero_escritura=numero_escritura,
            )
        )
