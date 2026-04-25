from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.locativo.commands.create_contrato_alquiler import (
    CreateContratoAlquilerCommand,
)


ESTADO_INICIAL_CONTRATO_ALQUILER = "borrador"


@dataclass(slots=True)
class ContratoAlquilerParticipacionCreatePayload:
    id_persona: int
    id_rol_participacion: int
    tipo_relacion: str
    id_relacion: int
    fecha_desde: date
    fecha_hasta: date | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class ContratoAlquilerObjetoCreatePayload:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class ContratoAlquilerCreatePayload:
    codigo_contrato: str
    fecha_inicio: date
    fecha_fin: date | None
    estado_contrato: str
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    id_reserva_locativa: int | None
    id_cartera_locativa: int | None
    id_contrato_anterior: int | None


class LocativoRepository(Protocol):
    def inmueble_exists(self, id_inmueble: int) -> bool: ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool: ...

    def persona_exists(self, id_persona: int) -> bool: ...

    def rol_participacion_exists(self, id_rol_participacion: int) -> bool: ...

    def create_contrato_alquiler(
        self,
        payload: ContratoAlquilerCreatePayload,
        objetos: list[ContratoAlquilerObjetoCreatePayload],
        participaciones: list[ContratoAlquilerParticipacionCreatePayload],
    ) -> dict[str, Any]: ...


class CreateContratoAlquilerService:
    def __init__(self, repository: LocativoRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateContratoAlquilerCommand
    ) -> AppResult[dict[str, Any]]:
        if not command.objetos:
            return AppResult.fail("OBJETOS_REQUIRED")
        if not command.participaciones:
            return AppResult.fail("PARTICIPACIONES_REQUIRED")
        if command.fecha_fin is not None and command.fecha_fin < command.fecha_inicio:
            return AppResult.fail("INVALID_DATE_RANGE")

        for objeto in command.objetos:
            if (objeto.id_inmueble is None) == (objeto.id_unidad_funcional is None):
                return AppResult.fail("EXACTLY_ONE_OBJECT_PARENT_REQUIRED")

            if objeto.id_inmueble is not None:
                if not self.repository.inmueble_exists(objeto.id_inmueble):
                    return AppResult.fail("NOT_FOUND_INMUEBLE")
            else:
                if not self.repository.unidad_funcional_exists(
                    objeto.id_unidad_funcional
                ):
                    return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

        for participacion in command.participaciones:
            if not self.repository.persona_exists(participacion.id_persona):
                return AppResult.fail("NOT_FOUND_PERSONA")
            if not self.repository.rol_participacion_exists(
                participacion.id_rol_participacion
            ):
                return AppResult.fail("NOT_FOUND_ROL_PARTICIPACION")
            fecha_desde = participacion.fecha_desde or command.fecha_inicio
            if participacion.fecha_hasta and participacion.fecha_hasta < fecha_desde:
                return AppResult.fail("INVALID_PARTICIPACION_DATE_RANGE")

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = ContratoAlquilerCreatePayload(
            codigo_contrato=command.codigo_contrato,
            fecha_inicio=command.fecha_inicio,
            fecha_fin=command.fecha_fin,
            estado_contrato=ESTADO_INICIAL_CONTRATO_ALQUILER,
            observaciones=command.observaciones,
            uid_global=uid_global,
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
            id_reserva_locativa=None,
            id_cartera_locativa=None,
            id_contrato_anterior=None,
        )

        objetos_payload: list[ContratoAlquilerObjetoCreatePayload] = []
        for objeto in command.objetos:
            objetos_payload.append(
                ContratoAlquilerObjetoCreatePayload(
                    id_inmueble=objeto.id_inmueble,
                    id_unidad_funcional=objeto.id_unidad_funcional,
                    observaciones=objeto.observaciones,
                    uid_global=str(self.uuid_generator()),
                    version_registro=1,
                    created_at=now,
                    updated_at=now,
                    id_instalacion_origen=id_instalacion,
                    id_instalacion_ultima_modificacion=id_instalacion,
                    op_id_alta=op_id,
                    op_id_ultima_modificacion=op_id,
                )
            )

        participaciones_payload: list[ContratoAlquilerParticipacionCreatePayload] = []
        for participacion in command.participaciones:
            participaciones_payload.append(
                ContratoAlquilerParticipacionCreatePayload(
                    id_persona=participacion.id_persona,
                    id_rol_participacion=participacion.id_rol_participacion,
                    tipo_relacion="contrato_alquiler",
                    id_relacion=0,
                    fecha_desde=participacion.fecha_desde or command.fecha_inicio,
                    fecha_hasta=participacion.fecha_hasta,
                    observaciones=participacion.observaciones,
                    uid_global=str(self.uuid_generator()),
                    version_registro=1,
                    created_at=now,
                    updated_at=now,
                    id_instalacion_origen=id_instalacion,
                    id_instalacion_ultima_modificacion=id_instalacion,
                    op_id_alta=op_id,
                    op_id_ultima_modificacion=op_id,
                )
            )

        created = self.repository.create_contrato_alquiler(
            payload, objetos_payload, participaciones_payload
        )
        id_contrato = created["id_contrato_alquiler"]
        created_objetos = created["objetos"]

        return AppResult.ok(
            {
                "id_contrato_alquiler": id_contrato,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "codigo_contrato": payload.codigo_contrato,
                "fecha_inicio": payload.fecha_inicio,
                "fecha_fin": payload.fecha_fin,
                "estado_contrato": payload.estado_contrato,
                "canon_inicial": command.canon_inicial
                if command.canon_inicial is not None
                else None,
                "moneda": command.moneda,
                "observaciones": payload.observaciones,
                "objetos": created_objetos,
            }
        )
