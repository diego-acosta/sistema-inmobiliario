from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.locativo.commands.create_reserva_locativa import (
    CreateReservaLocativaCommand,
)


ESTADO_INICIAL_RESERVA_LOCATIVA = "pendiente"
ESTADOS_ACTIVOS_RESERVA_LOCATIVA = {"pendiente", "confirmada"}


@dataclass(slots=True)
class ReservaLocativaObjetoCreatePayload:
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
class ReservaLocativaCreatePayload:
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


class LocativoRepository(Protocol):
    def inmueble_exists(self, id_inmueble: int) -> bool: ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool: ...

    def has_current_disponibilidad_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool: ...

    def has_current_disponibilidad_no_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool: ...

    def has_conflicting_active_reserva_locativa(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
        exclude_id_reserva_locativa: int | None = None,
    ) -> bool: ...

    def create_reserva_locativa(
        self,
        payload: ReservaLocativaCreatePayload,
        objetos: list[ReservaLocativaObjetoCreatePayload],
    ) -> dict[str, Any]: ...


class CreateReservaLocativaService:
    def __init__(self, repository: LocativoRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, command: CreateReservaLocativaCommand) -> AppResult[dict[str, Any]]:
        if not command.codigo_reserva.strip():
            return AppResult.fail("INVALID_REQUIRED_FIELDS")

        if (
            command.fecha_vencimiento is not None
            and command.fecha_vencimiento < command.fecha_reserva
        ):
            return AppResult.fail("INVALID_DATE_RANGE")

        if not command.objetos:
            return AppResult.fail("OBJETOS_REQUIRED")

        seen: set[tuple[str, int]] = set()
        for objeto in command.objetos:
            if (objeto.id_inmueble is None) == (objeto.id_unidad_funcional is None):
                return AppResult.fail("EXACTLY_ONE_OBJECT_PARENT_REQUIRED")

            if objeto.id_inmueble is not None:
                key: tuple[str, int] = ("inmueble", objeto.id_inmueble)
                if not self.repository.inmueble_exists(objeto.id_inmueble):
                    return AppResult.fail("NOT_FOUND_INMUEBLE")
            else:
                key = ("unidad_funcional", objeto.id_unidad_funcional)
                if not self.repository.unidad_funcional_exists(objeto.id_unidad_funcional):
                    return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

            if key in seen:
                return AppResult.fail("DUPLICATE_OBJECT")
            seen.add(key)

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

            if self.repository.has_conflicting_active_reserva_locativa(
                id_inmueble=objeto.id_inmueble,
                id_unidad_funcional=objeto.id_unidad_funcional,
                conflict_states=ESTADOS_ACTIVOS_RESERVA_LOCATIVA,
            ):
                return AppResult.fail("CONFLICTING_RESERVA_LOCATIVA")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = ReservaLocativaCreatePayload(
            codigo_reserva=command.codigo_reserva,
            fecha_reserva=command.fecha_reserva,
            estado_reserva=ESTADO_INICIAL_RESERVA_LOCATIVA,
            fecha_vencimiento=command.fecha_vencimiento,
            observaciones=command.observaciones,
            uid_global=str(self.uuid_generator()),
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        objetos_payload: list[ReservaLocativaObjetoCreatePayload] = []
        for objeto in command.objetos:
            objetos_payload.append(
                ReservaLocativaObjetoCreatePayload(
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

        created = self.repository.create_reserva_locativa(payload, objetos_payload)
        return AppResult.ok(created)
