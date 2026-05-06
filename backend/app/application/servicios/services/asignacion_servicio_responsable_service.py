from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.servicios.commands.asignacion_servicio_responsable import (
    CreateAsignacionServicioResponsableCommand,
    DeleteAsignacionServicioResponsableCommand,
    UpdateAsignacionServicioResponsableCommand,
)


@dataclass(slots=True)
class AsignacionServicioResponsablePayload:
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    id_servicio: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    id_persona: int
    porcentaje_responsabilidad: Decimal
    fecha_desde: date
    fecha_hasta: date | None
    estado_asignacion: str
    observaciones: str | None


@dataclass(slots=True)
class AsignacionServicioResponsableUpdatePayload:
    id_asignacion_servicio_responsable: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None
    id_servicio: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    id_persona: int
    porcentaje_responsabilidad: Decimal
    fecha_desde: date
    fecha_hasta: date | None
    estado_asignacion: str
    observaciones: str | None


@dataclass(slots=True)
class AsignacionServicioResponsableDeletePayload:
    id_asignacion_servicio_responsable: int
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    deleted_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class AsignacionServicioResponsableRepository(Protocol):
    def servicio_activo_exists(self, id_servicio: int) -> bool: ...

    def persona_activa_exists(self, id_persona: int) -> bool: ...

    def servicio_asociado_a_inmueble(self, id_servicio: int, id_inmueble: int) -> bool: ...

    def servicio_asociado_a_unidad_funcional(
        self, id_servicio: int, id_unidad_funcional: int
    ) -> bool: ...

    def get_asignacion_servicio_responsable_for_update(
        self, id_asignacion_servicio_responsable: int
    ) -> dict[str, Any] | None: ...

    def get_porcentaje_asignaciones_solapadas(
        self,
        *,
        id_servicio: int,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        fecha_desde: date,
        fecha_hasta: date | None,
        exclude_id: int | None,
    ) -> dict[str, Any]: ...

    def create_asignacion_servicio_responsable(
        self, payload: AsignacionServicioResponsablePayload
    ) -> dict[str, Any]: ...

    def update_asignacion_servicio_responsable(
        self, payload: AsignacionServicioResponsableUpdatePayload
    ) -> dict[str, Any] | None: ...

    def delete_asignacion_servicio_responsable(
        self, payload: AsignacionServicioResponsableDeletePayload
    ) -> dict[str, Any] | None: ...

    def get_asignacion_servicio_responsable(
        self, id_asignacion_servicio_responsable: int
    ) -> dict[str, Any] | None: ...

    def get_asignaciones_servicio_responsable(self) -> list[dict[str, Any]]: ...


def _normalizar_estado(estado: str) -> str:
    return estado.strip().upper()


def _validar_basico(command: Any) -> list[str]:
    errors: list[str] = []
    if (command.id_inmueble is not None) == (command.id_unidad_funcional is not None):
        errors.append("ASIGNACION_SERVICIO_RESPONSABLE_XOR_INVALIDO")
    if command.porcentaje_responsabilidad <= Decimal("0") or command.porcentaje_responsabilidad > Decimal("100"):
        errors.append("PORCENTAJE_RESPONSABILIDAD_INVALIDO")
    if command.fecha_hasta is not None and command.fecha_hasta < command.fecha_desde:
        errors.append("VIGENCIA_INVALIDA")
    if _normalizar_estado(command.estado_asignacion) not in {"ACTIVA", "INACTIVA"}:
        errors.append("ESTADO_ASIGNACION_INVALIDO")
    return errors


class _AsignacionServicioResponsableValidator:
    def __init__(self, repository: AsignacionServicioResponsableRepository) -> None:
        self.repository = repository

    def validate(self, command: Any, *, exclude_id: int | None = None) -> list[str]:
        errors = _validar_basico(command)
        if errors:
            return errors

        if not self.repository.servicio_activo_exists(command.id_servicio):
            return ["NOT_FOUND_SERVICIO"]

        if not self.repository.persona_activa_exists(command.id_persona):
            return ["NOT_FOUND_PERSONA"]

        if command.id_inmueble is not None:
            asociado = self.repository.servicio_asociado_a_inmueble(
                command.id_servicio, command.id_inmueble
            )
        else:
            asociado = self.repository.servicio_asociado_a_unidad_funcional(
                command.id_servicio, command.id_unidad_funcional or 0
            )
        if not asociado:
            return ["SERVICIO_NO_ASOCIADO"]

        if _normalizar_estado(command.estado_asignacion) != "ACTIVA":
            return []

        solapadas = self.repository.get_porcentaje_asignaciones_solapadas(
            id_servicio=command.id_servicio,
            id_inmueble=command.id_inmueble,
            id_unidad_funcional=command.id_unidad_funcional,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            exclude_id=exclude_id,
        )
        cantidad = int(solapadas["cantidad"])
        total = Decimal(str(solapadas["total"] or "0")) + command.porcentaje_responsabilidad

        if cantidad > 0 and total != Decimal("100"):
            return ["RESPONSABLE_SERVICIO_AMBIGUO"]

        return []


class CreateAsignacionServicioResponsableService:
    def __init__(self, repository: AsignacionServicioResponsableRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, command: CreateAsignacionServicioResponsableCommand) -> AppResult[dict[str, Any]]:
        errors = _AsignacionServicioResponsableValidator(self.repository).validate(command)
        if errors:
            return AppResult.fail(*errors)

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)
        payload = AsignacionServicioResponsablePayload(
            uid_global=str(self.uuid_generator()),
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
            id_servicio=command.id_servicio,
            id_inmueble=command.id_inmueble,
            id_unidad_funcional=command.id_unidad_funcional,
            id_persona=command.id_persona,
            porcentaje_responsabilidad=command.porcentaje_responsabilidad,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            estado_asignacion=_normalizar_estado(command.estado_asignacion),
            observaciones=command.observaciones,
        )
        return AppResult.ok(self.repository.create_asignacion_servicio_responsable(payload))


class UpdateAsignacionServicioResponsableService:
    def __init__(self, repository: AsignacionServicioResponsableRepository) -> None:
        self.repository = repository

    def execute(self, command: UpdateAsignacionServicioResponsableCommand) -> AppResult[dict[str, Any]]:
        actual = self.repository.get_asignacion_servicio_responsable_for_update(
            command.id_asignacion_servicio_responsable
        )
        if actual is None:
            return AppResult.fail("NOT_FOUND_ASIGNACION_SERVICIO_RESPONSABLE")
        if command.if_match_version is None or command.if_match_version != actual["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        errors = _AsignacionServicioResponsableValidator(self.repository).validate(
            command, exclude_id=command.id_asignacion_servicio_responsable
        )
        if errors:
            return AppResult.fail(*errors)

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)
        payload = AsignacionServicioResponsableUpdatePayload(
            id_asignacion_servicio_responsable=command.id_asignacion_servicio_responsable,
            version_registro_actual=actual["version_registro"],
            version_registro_nueva=actual["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
            id_servicio=command.id_servicio,
            id_inmueble=command.id_inmueble,
            id_unidad_funcional=command.id_unidad_funcional,
            id_persona=command.id_persona,
            porcentaje_responsabilidad=command.porcentaje_responsabilidad,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
            estado_asignacion=_normalizar_estado(command.estado_asignacion),
            observaciones=command.observaciones,
        )
        updated = self.repository.update_asignacion_servicio_responsable(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(updated)


class DeleteAsignacionServicioResponsableService:
    def __init__(self, repository: AsignacionServicioResponsableRepository) -> None:
        self.repository = repository

    def execute(self, command: DeleteAsignacionServicioResponsableCommand) -> AppResult[dict[str, Any]]:
        actual = self.repository.get_asignacion_servicio_responsable_for_update(
            command.id_asignacion_servicio_responsable
        )
        if actual is None:
            return AppResult.fail("NOT_FOUND_ASIGNACION_SERVICIO_RESPONSABLE")
        if command.if_match_version is None or command.if_match_version != actual["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)
        payload = AsignacionServicioResponsableDeletePayload(
            id_asignacion_servicio_responsable=command.id_asignacion_servicio_responsable,
            version_registro_actual=actual["version_registro"],
            version_registro_nueva=actual["version_registro"] + 1,
            updated_at=now,
            deleted_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )
        deleted = self.repository.delete_asignacion_servicio_responsable(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(deleted)


class GetAsignacionServicioResponsableService:
    def __init__(self, repository: AsignacionServicioResponsableRepository) -> None:
        self.repository = repository

    def execute(self, id_asignacion_servicio_responsable: int) -> AppResult[dict[str, Any]]:
        data = self.repository.get_asignacion_servicio_responsable(id_asignacion_servicio_responsable)
        if data is None:
            return AppResult.fail("NOT_FOUND_ASIGNACION_SERVICIO_RESPONSABLE")
        return AppResult.ok(data)


class GetAsignacionesServicioResponsableService:
    def __init__(self, repository: AsignacionServicioResponsableRepository) -> None:
        self.repository = repository

    def execute(self) -> AppResult[list[dict[str, Any]]]:
        return AppResult.ok(self.repository.get_asignaciones_servicio_responsable())
