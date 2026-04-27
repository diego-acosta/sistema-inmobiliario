from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol

from app.application.common.results import AppResult
from app.application.locativo.commands.rechazar_solicitud_alquiler import (
    RechazarSolicitudAlquilerCommand,
)
from app.application.locativo.services.create_solicitud_alquiler_service import (
    SolicitudAlquilerTransicionPayload,
)


ESTADO_ORIGEN = "pendiente"
ESTADO_DESTINO = "rechazada"


class LocativoRepository(Protocol):
    def get_solicitud_alquiler(
        self, id_solicitud_alquiler: int
    ) -> dict[str, Any] | None: ...

    def transicionar_solicitud_alquiler(
        self, payload: SolicitudAlquilerTransicionPayload
    ) -> dict[str, Any]: ...


class RechazarSolicitudAlquilerService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(
        self, command: RechazarSolicitudAlquilerCommand
    ) -> AppResult[dict[str, Any]]:
        solicitud = self.repository.get_solicitud_alquiler(command.id_solicitud_alquiler)
        if solicitud is None or solicitud["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_SOLICITUD_ALQUILER")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")
        if command.if_match_version != solicitud["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_actual = (solicitud["estado_solicitud"] or "").strip().lower()
        if estado_actual != ESTADO_ORIGEN:
            return AppResult.fail("INVALID_SOLICITUD_STATE")

        now = datetime.now(UTC)
        payload = SolicitudAlquilerTransicionPayload(
            id_solicitud_alquiler=command.id_solicitud_alquiler,
            estado_solicitud=ESTADO_DESTINO,
            version_registro_actual=solicitud["version_registro"],
            version_registro_nueva=solicitud["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=getattr(command.context, "id_instalacion", None),
            op_id_ultima_modificacion=getattr(command.context, "op_id", None),
        )

        result = self.repository.transicionar_solicitud_alquiler(payload)
        if result.get("status") == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(result["data"])
