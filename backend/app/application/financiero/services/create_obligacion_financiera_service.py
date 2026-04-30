from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.financiero.commands.create_obligacion_financiera import (
    CreateObligacionFinancieraCommand,
)


@dataclass(slots=True)
class ObligacionCreatePayload:
    id_relacion_generadora: int
    fecha_emision: date
    fecha_vencimiento: date | None
    importe_total: float
    estado_obligacion: str
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class ComposicionCreatePayload:
    id_concepto_financiero: int
    codigo_concepto_financiero: str
    orden_composicion: int
    importe_componente: float
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class FinancieroRepository(Protocol):
    db: Any

    def relacion_generadora_exists(self, id_relacion_generadora: int) -> bool: ...

    def get_concepto_financiero_by_codigo(
        self, codigo: str
    ) -> dict[str, Any] | None: ...

    def create_obligacion_financiera(
        self,
        obligacion: ObligacionCreatePayload,
        composiciones: list[ComposicionCreatePayload],
    ) -> dict[str, Any]: ...


class CreateObligacionFinancieraService:
    def __init__(
        self, repository: FinancieroRepository, uuid_generator=None
    ) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateObligacionFinancieraCommand
    ) -> AppResult[dict[str, Any]]:
        if not command.composiciones:
            return AppResult.fail("COMPOSICIONES_REQUERIDAS")

        with self._transaction():
            return self._execute_in_transaction(command)

    def _execute_in_transaction(
        self, command: CreateObligacionFinancieraCommand
    ) -> AppResult[dict[str, Any]]:
        if not self.repository.relacion_generadora_exists(command.id_relacion_generadora):
            return AppResult.fail("NOT_FOUND_RELACION")

        conceptos: list[dict[str, Any]] = []
        for comp in command.composiciones:
            concepto = self.repository.get_concepto_financiero_by_codigo(
                comp.codigo_concepto_financiero
            )
            if concepto is None:
                return AppResult.fail(
                    f"NOT_FOUND_CONCEPTO:{comp.codigo_concepto_financiero}"
                )
            conceptos.append(concepto)

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        importe_total = sum(c.importe_componente for c in command.composiciones)

        obligacion_payload = ObligacionCreatePayload(
            id_relacion_generadora=command.id_relacion_generadora,
            fecha_emision=now.date(),
            fecha_vencimiento=command.fecha_vencimiento,
            importe_total=importe_total,
            estado_obligacion="PROYECTADA",
            uid_global=str(self.uuid_generator()),
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        composicion_payloads = [
            ComposicionCreatePayload(
                id_concepto_financiero=conceptos[i]["id_concepto_financiero"],
                codigo_concepto_financiero=comp.codigo_concepto_financiero,
                orden_composicion=i + 1,
                importe_componente=comp.importe_componente,
                uid_global=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
            for i, comp in enumerate(command.composiciones)
        ]

        created = self.repository.create_obligacion_financiera(
            obligacion_payload, composicion_payloads
        )
        return AppResult.ok(created)

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()
