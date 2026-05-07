from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.financiero.commands.create_relacion_generadora import (
    CreateRelacionGeneradoraCommand,
)


TIPOS_ORIGEN_VALIDOS = {
    "VENTA",
    "CONTRATO_ALQUILER",
    "FACTURA_SERVICIO",
    "LIQUIDACION_RECUPERO",
}


@dataclass(slots=True)
class RelacionGeneradoraCreatePayload:
    tipo_origen: str
    id_origen: int
    descripcion: str | None
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

    def venta_exists(self, id_venta: int) -> bool: ...

    def contrato_alquiler_exists(self, id_contrato_alquiler: int) -> bool: ...

    def factura_servicio_exists(self, id_factura_servicio: int) -> bool: ...

    def liquidacion_recupero_exists(self, id_liquidacion_recupero: int) -> bool: ...

    def create_relacion_generadora(
        self, payload: RelacionGeneradoraCreatePayload
    ) -> dict[str, Any]: ...


class CreateRelacionGeneradoraService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateRelacionGeneradoraCommand
    ) -> AppResult[dict[str, Any]]:
        tipo = command.tipo_origen.strip().upper()
        if tipo not in TIPOS_ORIGEN_VALIDOS:
            return AppResult.fail("TIPO_ORIGEN_INVALIDO")

        with self._transaction():
            return self._execute_in_transaction(command, tipo)

    def _execute_in_transaction(
        self, command: CreateRelacionGeneradoraCommand, tipo: str
    ) -> AppResult[dict[str, Any]]:
        if tipo == "VENTA":
            if not self.repository.venta_exists(command.id_origen):
                return AppResult.fail("NOT_FOUND_ORIGEN")
        elif tipo == "CONTRATO_ALQUILER":
            if not self.repository.contrato_alquiler_exists(command.id_origen):
                return AppResult.fail("NOT_FOUND_ORIGEN")
        elif tipo == "FACTURA_SERVICIO":
            if not self.repository.factura_servicio_exists(command.id_origen):
                return AppResult.fail("NOT_FOUND_ORIGEN")
        elif tipo == "LIQUIDACION_RECUPERO":
            if not self.repository.liquidacion_recupero_exists(command.id_origen):
                return AppResult.fail("NOT_FOUND_ORIGEN")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = RelacionGeneradoraCreatePayload(
            # La API acepta tipo_origen en uppercase, pero el trigger SQL vigente valida lowercase.
            # Persistimos lowercase y el repositorio expone uppercase en responses.
            tipo_origen=tipo.lower(),
            id_origen=command.id_origen,
            descripcion=command.descripcion,
            uid_global=str(self.uuid_generator()),
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        created = self.repository.create_relacion_generadora(payload)
        return AppResult.ok(created)

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()
