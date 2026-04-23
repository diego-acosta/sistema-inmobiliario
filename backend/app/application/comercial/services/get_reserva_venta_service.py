from typing import Any, Protocol

from app.application.common.results import AppResult


class ComercialRepository(Protocol):
    def get_reserva_venta(self, id_reserva_venta: int) -> dict[str, Any] | None:
        ...


class GetReservaVentaService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(self, id_reserva_venta: int) -> AppResult[dict[str, Any]]:
        reserva = self.repository.get_reserva_venta(id_reserva_venta)
        if reserva is None or reserva["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(
            {
                "id_reserva_venta": reserva["id_reserva_venta"],
                "uid_global": reserva["uid_global"],
                "version_registro": reserva["version_registro"],
                "codigo_reserva": reserva["codigo_reserva"],
                "fecha_reserva": reserva["fecha_reserva"],
                "estado_reserva": reserva["estado_reserva"],
                "fecha_vencimiento": reserva["fecha_vencimiento"],
                "observaciones": reserva["observaciones"],
                "objetos": reserva["objetos"],
            }
        )
