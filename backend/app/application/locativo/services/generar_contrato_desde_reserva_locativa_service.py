from __future__ import annotations

from typing import Any, Protocol

from app.application.common.results import AppResult
from app.application.locativo.commands.create_contrato_alquiler import (
    CreateContratoAlquilerCommand,
    CreateContratoAlquilerObjetoCommand,
)
from app.application.locativo.commands.generar_contrato_desde_reserva_locativa import (
    GenerarContratoDesdeReservaLocativaCommand,
)
from app.application.locativo.services.create_contrato_alquiler_service import (
    ContratoAlquilerCreatePayload,
    ContratoAlquilerObjetoCreatePayload,
    CreateContratoAlquilerService,
)


ESTADO_CONFIRMADA = "confirmada"


class LocativoRepository(Protocol):
    def get_reserva_locativa(self, id_reserva_locativa: int) -> dict[str, Any] | None: ...

    def has_contrato_for_reserva_locativa(self, id_reserva_locativa: int) -> bool: ...

    def inmueble_exists(self, id_inmueble: int) -> bool: ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool: ...

    def create_contrato_alquiler(
        self,
        payload: ContratoAlquilerCreatePayload,
        objetos: list[ContratoAlquilerObjetoCreatePayload],
    ) -> dict[str, Any]: ...


class GenerarContratoDesdeReservaLocativaService:
    def __init__(self, repository: LocativoRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator

    def execute(
        self, command: GenerarContratoDesdeReservaLocativaCommand
    ) -> AppResult[dict[str, Any]]:
        reserva = self.repository.get_reserva_locativa(command.id_reserva_locativa)
        if reserva is None or reserva["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_RESERVA_LOCATIVA")

        estado = (reserva["estado_reserva"] or "").strip().lower()
        if estado != ESTADO_CONFIRMADA:
            return AppResult.fail("RESERVA_NOT_CONFIRMADA")

        if self.repository.has_contrato_for_reserva_locativa(command.id_reserva_locativa):
            return AppResult.fail("RESERVA_YA_TIENE_CONTRATO")

        objetos = reserva["objetos"]
        create_command = CreateContratoAlquilerCommand(
            context=command.context,
            codigo_contrato=command.codigo_contrato,
            fecha_inicio=command.fecha_inicio,
            fecha_fin=command.fecha_fin,
            observaciones=command.observaciones,
            objetos=[
                CreateContratoAlquilerObjetoCommand(
                    id_inmueble=o["id_inmueble"],
                    id_unidad_funcional=o["id_unidad_funcional"],
                    observaciones=o["observaciones"],
                )
                for o in objetos
            ],
            id_reserva_locativa=command.id_reserva_locativa,
        )

        kwargs = {}
        if self.uuid_generator is not None:
            kwargs["uuid_generator"] = self.uuid_generator
        service = CreateContratoAlquilerService(repository=self.repository, **kwargs)
        return service.execute(create_command)
