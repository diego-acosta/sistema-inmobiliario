from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.comercial.commands.create_reserva_venta import (
    CreateReservaVentaCommand,
)
from app.application.common.results import AppResult


ESTADO_INICIAL_RESERVA_VENTA = "borrador"
ESTADOS_RESERVA_CONFLICTIVOS = {
    "borrador",
    "activa",
    "confirmada",
}
ESTADOS_VENTA_CONFLICTIVOS = {
    "activa",
    "confirmada",
    "en_proceso",
    "finalizada",
}


@dataclass(slots=True)
class ReservaVentaParticipacionCreatePayload:
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
class ReservaVentaObjetoCreatePayload:
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
class ReservaVentaCreatePayload:
    codigo_reserva: str
    fecha_reserva: datetime
    estado_reserva: str
    fecha_vencimiento: datetime | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class ComercialRepository(Protocol):
    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def persona_exists(self, id_persona: int) -> bool:
        ...

    def rol_participacion_exists(self, id_rol_participacion: int) -> bool:
        ...

    def has_current_disponibilidad_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
        ...

    def has_current_disponibilidad_no_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
        ...

    def has_current_ocupacion_conflict(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
        ...

    def has_conflicting_active_venta(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
    ) -> bool:
        ...

    def has_conflicting_active_reserva(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
    ) -> bool:
        ...

    def create_reserva_venta(
        self,
        payload: ReservaVentaCreatePayload,
        objetos: list[ReservaVentaObjetoCreatePayload],
        participaciones: list[ReservaVentaParticipacionCreatePayload],
    ) -> Any:
        ...


class CreateReservaVentaService:
    def __init__(self, repository: ComercialRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, command: CreateReservaVentaCommand) -> AppResult[dict[str, Any]]:
        if not command.codigo_reserva.strip():
            return AppResult.fail("INVALID_REQUIRED_FIELDS")

        if command.fecha_vencimiento and command.fecha_vencimiento < command.fecha_reserva:
            return AppResult.fail("INVALID_DATE_RANGE")

        if not command.objetos:
            return AppResult.fail("OBJETOS_REQUIRED")

        if not command.participaciones:
            return AppResult.fail("PARTICIPACIONES_REQUIRED")

        seen_objects: set[tuple[str, int]] = set()
        for objeto in command.objetos:
            if (objeto.id_inmueble is None) == (objeto.id_unidad_funcional is None):
                return AppResult.fail("EXACTLY_ONE_OBJECT_PARENT_REQUIRED")

            if objeto.id_inmueble is not None:
                object_key = ("inmueble", objeto.id_inmueble)
                if not self.repository.inmueble_exists(objeto.id_inmueble):
                    return AppResult.fail("NOT_FOUND_INMUEBLE")
            else:
                object_key = ("unidad_funcional", objeto.id_unidad_funcional)
                if not self.repository.unidad_funcional_exists(objeto.id_unidad_funcional):
                    return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

            if object_key in seen_objects:
                return AppResult.fail("DUPLICATE_OBJECT")
            seen_objects.add(object_key)

        for participacion in command.participaciones:
            if not self.repository.persona_exists(participacion.id_persona):
                return AppResult.fail("NOT_FOUND_PERSONA")
            if not self.repository.rol_participacion_exists(
                participacion.id_rol_participacion
            ):
                return AppResult.fail("NOT_FOUND_ROL_PARTICIPACION")
            fecha_desde = participacion.fecha_desde or command.fecha_reserva.date()
            if participacion.fecha_hasta and participacion.fecha_hasta < fecha_desde:
                return AppResult.fail("INVALID_PARTICIPACION_DATE_RANGE")

        for objeto in command.objetos:
            if self.repository.has_current_disponibilidad_no_disponible(
                id_inmueble=objeto.id_inmueble,
                id_unidad_funcional=objeto.id_unidad_funcional,
                at_datetime=command.fecha_reserva,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if not self.repository.has_current_disponibilidad_disponible(
                id_inmueble=objeto.id_inmueble,
                id_unidad_funcional=objeto.id_unidad_funcional,
                at_datetime=command.fecha_reserva,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if self.repository.has_current_ocupacion_conflict(
                id_inmueble=objeto.id_inmueble,
                id_unidad_funcional=objeto.id_unidad_funcional,
                at_datetime=command.fecha_reserva,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if self.repository.has_conflicting_active_venta(
                id_inmueble=objeto.id_inmueble,
                id_unidad_funcional=objeto.id_unidad_funcional,
                conflict_states=ESTADOS_VENTA_CONFLICTIVOS,
            ):
                return AppResult.fail("CONFLICTING_VENTA")

            if self.repository.has_conflicting_active_reserva(
                id_inmueble=objeto.id_inmueble,
                id_unidad_funcional=objeto.id_unidad_funcional,
                conflict_states=ESTADOS_RESERVA_CONFLICTIVOS,
            ):
                return AppResult.fail("CONFLICTING_RESERVA")

        uid_global = str(self.uuid_generator())
        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = ReservaVentaCreatePayload(
            codigo_reserva=command.codigo_reserva,
            fecha_reserva=command.fecha_reserva,
            estado_reserva=ESTADO_INICIAL_RESERVA_VENTA,
            fecha_vencimiento=command.fecha_vencimiento,
            observaciones=command.observaciones,
            uid_global=uid_global,
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        objetos_payload: list[ReservaVentaObjetoCreatePayload] = []
        for objeto in command.objetos:
            objetos_payload.append(
                ReservaVentaObjetoCreatePayload(
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

        participaciones_payload: list[ReservaVentaParticipacionCreatePayload] = []
        for participacion in command.participaciones:
            participaciones_payload.append(
                ReservaVentaParticipacionCreatePayload(
                    id_persona=participacion.id_persona,
                    id_rol_participacion=participacion.id_rol_participacion,
                    tipo_relacion="reserva_venta",
                    id_relacion=0,
                    fecha_desde=participacion.fecha_desde
                    or command.fecha_reserva.date(),
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

        created = self.repository.create_reserva_venta(
            payload,
            objetos_payload,
            participaciones_payload,
        )

        id_reserva_venta = (
            created["id_reserva_venta"]
            if isinstance(created, dict)
            else getattr(created, "id_reserva_venta")
        )
        created_objetos = (
            created["objetos"]
            if isinstance(created, dict)
            else getattr(created, "objetos")
        )

        return AppResult.ok(
            {
                "id_reserva_venta": id_reserva_venta,
                "uid_global": payload.uid_global,
                "version_registro": payload.version_registro,
                "codigo_reserva": payload.codigo_reserva,
                "fecha_reserva": payload.fecha_reserva,
                "estado_reserva": payload.estado_reserva,
                "fecha_vencimiento": payload.fecha_vencimiento,
                "observaciones": payload.observaciones,
                "objetos": created_objetos,
            }
        )
