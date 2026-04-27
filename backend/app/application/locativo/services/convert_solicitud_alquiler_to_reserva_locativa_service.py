from __future__ import annotations

from typing import Any, Protocol
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.locativo.commands.confirmar_reserva_locativa import (
    ConfirmarReservaLocativaCommand,
)
from app.application.locativo.commands.convert_solicitud_alquiler_to_reserva_locativa import (
    ConvertSolicitudAlquilerToReservaLocativaCommand,
)
from app.application.locativo.commands.create_reserva_locativa import (
    CreateReservaLocativaCommand,
)
from app.application.locativo.services.confirmar_reserva_locativa_service import (
    ConfirmarReservaLocativaService,
)
from app.application.locativo.services.create_reserva_locativa_service import (
    CreateReservaLocativaService,
)


ESTADO_APROBADA = "aprobada"


class LocativoRepository(Protocol):
    def get_solicitud_alquiler(self, id_solicitud_alquiler: int) -> dict[str, Any] | None: ...

    def has_reserva_locativa_for_solicitud(self, id_solicitud_alquiler: int) -> bool: ...

    def vincular_solicitud_a_reserva_locativa(
        self, id_reserva_locativa: int, id_solicitud_alquiler: int
    ) -> None: ...


class ConvertSolicitudAlquilerToReservaLocativaService:
    def __init__(self, repository: LocativoRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: ConvertSolicitudAlquilerToReservaLocativaCommand
    ) -> AppResult[dict[str, Any]]:
        solicitud = self.repository.get_solicitud_alquiler(command.id_solicitud_alquiler)
        if solicitud is None or solicitud["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_SOLICITUD_ALQUILER")

        estado = (solicitud["estado_solicitud"] or "").strip().lower()
        if estado != ESTADO_APROBADA:
            return AppResult.fail("SOLICITUD_NOT_APROBADA")

        if self.repository.has_reserva_locativa_for_solicitud(command.id_solicitud_alquiler):
            return AppResult.fail("SOLICITUD_YA_CONVERTIDA")

        create_command = CreateReservaLocativaCommand(
            context=command.context,
            codigo_reserva=command.codigo_reserva,
            fecha_reserva=command.fecha_reserva,
            fecha_vencimiento=command.fecha_vencimiento,
            observaciones=command.observaciones,
            objetos=command.objetos,
        )
        create_service = CreateReservaLocativaService(
            repository=self.repository,
            uuid_generator=self.uuid_generator,
        )
        create_result = create_service.execute(create_command)
        if not create_result.success:
            return create_result

        id_reserva_locativa: int = create_result.data["id_reserva_locativa"]
        self.repository.vincular_solicitud_a_reserva_locativa(
            id_reserva_locativa, command.id_solicitud_alquiler
        )

        if not command.confirmar:
            return AppResult.ok(create_result.data)

        confirmar_command = ConfirmarReservaLocativaCommand(
            context=command.context,
            id_reserva_locativa=id_reserva_locativa,
            if_match_version=1,
        )
        confirmar_service = ConfirmarReservaLocativaService(repository=self.repository)
        confirmar_result = confirmar_service.execute(confirmar_command)
        if not confirmar_result.success:
            return confirmar_result
        return AppResult.ok(confirmar_result.data)
