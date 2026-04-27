from typing import Any, Protocol

from app.application.common.results import AppResult


class LocativoRepository(Protocol):
    def get_reserva_locativa(self, id_reserva_locativa: int) -> dict[str, Any] | None: ...


class GetReservaLocativaService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(self, id_reserva_locativa: int) -> AppResult[dict[str, Any]]:
        reserva = self.repository.get_reserva_locativa(id_reserva_locativa)
        if reserva is None or reserva["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_RESERVA_LOCATIVA")

        return AppResult.ok(
            {
                "id_reserva_locativa": reserva["id_reserva_locativa"],
                "uid_global": reserva["uid_global"],
                "version_registro": reserva["version_registro"],
                "codigo_reserva": reserva["codigo_reserva"],
                "fecha_reserva": reserva["fecha_reserva"],
                "estado_reserva": reserva["estado_reserva"],
                "fecha_vencimiento": reserva["fecha_vencimiento"],
                "observaciones": reserva["observaciones"],
                "objetos": reserva["objetos"],
                "deleted_at": reserva["deleted_at"],
            }
        )
