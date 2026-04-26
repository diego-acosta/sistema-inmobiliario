from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.locativo.commands.update_contrato_alquiler import (
    UpdateContratoAlquilerCommand,
)


ESTADO_PERMITIDO_UPDATE = "borrador"


@dataclass(slots=True)
class ContratoAlquilerUpdatePayload:
    id_contrato_alquiler: int
    codigo_contrato: str
    fecha_inicio: datetime
    fecha_fin: datetime | None
    observaciones: str | None
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class ContratoAlquilerObjetoUpdatePayload:
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


class LocativoRepository(Protocol):
    def get_contrato_alquiler(self, id_contrato_alquiler: int) -> dict[str, Any] | None: ...

    def inmueble_exists(self, id_inmueble: int) -> bool: ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool: ...

    def update_contrato_alquiler(
        self,
        payload: ContratoAlquilerUpdatePayload,
        objetos: list[ContratoAlquilerObjetoUpdatePayload],
    ) -> dict[str, Any]: ...


class UpdateContratoAlquilerService:
    def __init__(self, repository: LocativoRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: UpdateContratoAlquilerCommand
    ) -> AppResult[dict[str, Any]]:
        contrato = self.repository.get_contrato_alquiler(command.id_contrato_alquiler)
        if contrato is None or contrato["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_CONTRATO_ALQUILER")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != contrato["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_actual = (contrato["estado_contrato"] or "").strip().lower()
        if estado_actual != ESTADO_PERMITIDO_UPDATE:
            return AppResult.fail("INVALID_CONTRATO_STATE")

        if not command.objetos:
            return AppResult.fail("OBJETOS_REQUIRED")

        if command.fecha_fin is not None and command.fecha_fin < command.fecha_inicio:
            return AppResult.fail("INVALID_DATE_RANGE")

        for objeto in command.objetos:
            if (objeto.id_inmueble is None) == (objeto.id_unidad_funcional is None):
                return AppResult.fail("EXACTLY_ONE_OBJECT_PARENT_REQUIRED")

            if objeto.id_inmueble is not None:
                if not self.repository.inmueble_exists(objeto.id_inmueble):
                    return AppResult.fail("NOT_FOUND_INMUEBLE")
            else:
                if not self.repository.unidad_funcional_exists(objeto.id_unidad_funcional):
                    return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = ContratoAlquilerUpdatePayload(
            id_contrato_alquiler=command.id_contrato_alquiler,
            codigo_contrato=command.codigo_contrato,
            fecha_inicio=command.fecha_inicio,
            fecha_fin=command.fecha_fin,
            observaciones=command.observaciones,
            version_registro_actual=contrato["version_registro"],
            version_registro_nueva=contrato["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        objetos_payload: list[ContratoAlquilerObjetoUpdatePayload] = []
        for objeto in command.objetos:
            objetos_payload.append(
                ContratoAlquilerObjetoUpdatePayload(
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

        result = self.repository.update_contrato_alquiler(payload, objetos_payload)
        if result.get("status") == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(result["data"])
