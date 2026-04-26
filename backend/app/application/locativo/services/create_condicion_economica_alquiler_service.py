from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.locativo.commands.create_condicion_economica_alquiler import (
    CreateCondicionEconomicaAlquilerCommand,
)


ESTADOS_VALIDOS = {"borrador", "activo"}


@dataclass(slots=True)
class CondicionEconomicaAlquilerCreatePayload:
    id_contrato_alquiler: int
    monto_base: Decimal
    periodicidad: str | None
    moneda: str | None
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


class LocativoRepository(Protocol):
    def get_contrato_alquiler(self, id_contrato_alquiler: int) -> dict[str, Any] | None: ...

    def has_vigencia_overlap_condicion(
        self,
        id_contrato_alquiler: int,
        moneda: str | None,
        fecha_desde: date,
        fecha_hasta: date | None,
    ) -> bool: ...

    def create_condicion_economica_alquiler(
        self, payload: CondicionEconomicaAlquilerCreatePayload
    ) -> dict[str, Any]: ...


class CreateCondicionEconomicaAlquilerService:
    def __init__(self, repository: LocativoRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateCondicionEconomicaAlquilerCommand
    ) -> AppResult[dict[str, Any]]:
        contrato = self.repository.get_contrato_alquiler(command.id_contrato_alquiler)
        if contrato is None or contrato["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_CONTRATO_ALQUILER")

        estado = (contrato["estado_contrato"] or "").strip().lower()
        if estado not in ESTADOS_VALIDOS:
            return AppResult.fail("INVALID_CONTRATO_STATE")

        if command.monto_base <= 0:
            return AppResult.fail("INVALID_MONTO_BASE")

        if command.fecha_hasta is not None and command.fecha_hasta < command.fecha_desde:
            return AppResult.fail("INVALID_DATE_RANGE")

        if self.repository.has_vigencia_overlap_condicion(
            id_contrato_alquiler=command.id_contrato_alquiler,
            moneda=command.moneda,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
        ):
            return AppResult.fail("CONDICION_ECONOMICA_SOLAPADA")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = CondicionEconomicaAlquilerCreatePayload(
            id_contrato_alquiler=command.id_contrato_alquiler,
            monto_base=command.monto_base,
            periodicidad=command.periodicidad,
            moneda=command.moneda,
            fecha_desde=command.fecha_desde,
            fecha_hasta=command.fecha_hasta,
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

        created = self.repository.create_condicion_economica_alquiler(payload)
        return AppResult.ok(created)
