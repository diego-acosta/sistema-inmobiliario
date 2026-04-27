from typing import Any, Protocol

from app.application.common.results import AppResult


class LocativoRepository(Protocol):
    def get_solicitud_alquiler(
        self, id_solicitud_alquiler: int
    ) -> dict[str, Any] | None: ...


class GetSolicitudAlquilerService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(self, id_solicitud_alquiler: int) -> AppResult[dict[str, Any]]:
        solicitud = self.repository.get_solicitud_alquiler(id_solicitud_alquiler)
        if solicitud is None or solicitud["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_SOLICITUD_ALQUILER")
        return AppResult.ok(solicitud)
