from typing import Any, Protocol

from app.application.common.results import AppResult


class LocativoRepository(Protocol):
    def get_contrato_alquiler(self, id_contrato_alquiler: int) -> dict[str, Any] | None: ...


class GetContratoAlquilerService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(self, id_contrato_alquiler: int) -> AppResult[dict[str, Any]]:
        contrato = self.repository.get_contrato_alquiler(id_contrato_alquiler)
        if contrato is None or contrato["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND")

        return AppResult.ok(
            {
                "id_contrato_alquiler": contrato["id_contrato_alquiler"],
                "uid_global": contrato["uid_global"],
                "version_registro": contrato["version_registro"],
                "codigo_contrato": contrato["codigo_contrato"],
                "fecha_inicio": contrato["fecha_inicio"],
                "fecha_fin": contrato["fecha_fin"],
                "estado_contrato": contrato["estado_contrato"],
                "observaciones": contrato["observaciones"],
                "objetos": contrato["objetos"],
                "condiciones_economicas_alquiler": [],
                "deleted_at": contrato["deleted_at"],
            }
        )
