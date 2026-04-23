from typing import Any, Protocol

from app.application.common.results import AppResult


class ComercialRepository(Protocol):
    def list_reservas_venta(
        self,
        *,
        codigo_reserva: str | None,
        estado_reserva: str | None,
        fecha_desde: Any | None,
        fecha_hasta: Any | None,
        vigente: bool | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        ...


class ListReservasVentaService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        codigo_reserva: str | None,
        estado_reserva: str | None,
        fecha_desde: Any | None,
        fecha_hasta: Any | None,
        vigente: bool | None,
        limit: int,
        offset: int,
    ) -> AppResult[dict[str, Any]]:
        if limit < 0 or offset < 0:
            return AppResult.fail("INVALID_PAGINATION")

        reservas = self.repository.list_reservas_venta(
            codigo_reserva=codigo_reserva,
            estado_reserva=estado_reserva,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            vigente=vigente,
            limit=limit,
            offset=offset,
        )
        return AppResult.ok(reservas)
