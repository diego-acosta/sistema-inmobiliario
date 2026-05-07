from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.financiero.commands.create_comprobante_impuesto import (
    CreateComprobanteImpuestoCommand,
)


MODALIDADES_GESTION_IMPUESTO = {
    "EMPRESA_ASUME",
    "DIRECTO_RESPONSABLE",
    "EMPRESA_PAGA_Y_RECUPERA",
}


@dataclass(slots=True)
class ComprobanteImpuestoCreatePayload:
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    id_inmueble: int | None
    id_unidad_funcional: int | None
    organismo: str
    tipo_impuesto: str
    partida_nomenclatura: str | None
    numero_comprobante: str
    periodo_desde: date | None
    periodo_hasta: date | None
    fecha_emision: date | None
    fecha_vencimiento: date
    importe_total: Decimal
    modalidad_gestion_impuesto: str
    observaciones: str | None


class ComprobanteImpuestoRepository(Protocol):
    def inmueble_exists(self, id_inmueble: int) -> bool: ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool: ...

    def comprobante_impuesto_activo_exists(
        self, organismo: str, numero_comprobante: str
    ) -> bool: ...

    def create_comprobante_impuesto(
        self, payload: ComprobanteImpuestoCreatePayload
    ) -> dict[str, Any]: ...


class CreateComprobanteImpuestoService:
    def __init__(
        self, repository: ComprobanteImpuestoRepository, uuid_generator=None
    ) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateComprobanteImpuestoCommand
    ) -> AppResult[dict[str, Any]]:
        organismo = command.organismo.strip()
        tipo_impuesto = command.tipo_impuesto.strip()
        numero_comprobante = command.numero_comprobante.strip()
        modalidad = command.modalidad_gestion_impuesto.strip().upper()
        partida = (
            command.partida_nomenclatura.strip()
            if command.partida_nomenclatura is not None
            else None
        )

        if (command.id_inmueble is not None) == (
            command.id_unidad_funcional is not None
        ):
            return AppResult.fail("COMPROBANTE_IMPUESTO_XOR_INVALIDO")
        if not organismo or not tipo_impuesto or not numero_comprobante:
            return AppResult.fail("COMPROBANTE_IMPUESTO_DATOS_REQUERIDOS")
        if modalidad not in MODALIDADES_GESTION_IMPUESTO:
            return AppResult.fail("MODALIDAD_GESTION_IMPUESTO_INVALIDA")
        if command.importe_total < Decimal("0"):
            return AppResult.fail("IMPORTE_TOTAL_INVALIDO")
        if (
            command.periodo_desde is not None
            and command.periodo_hasta is not None
            and command.periodo_hasta < command.periodo_desde
        ):
            return AppResult.fail("PERIODO_INVALIDO")
        if (
            command.fecha_emision is not None
            and command.fecha_vencimiento < command.fecha_emision
        ):
            return AppResult.fail("FECHA_VENCIMIENTO_INVALIDA")

        if command.id_inmueble is not None:
            if not self.repository.inmueble_exists(command.id_inmueble):
                return AppResult.fail("NOT_FOUND_INMUEBLE")
        elif command.id_unidad_funcional is not None and not self.repository.unidad_funcional_exists(
            command.id_unidad_funcional
        ):
            return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

        if self.repository.comprobante_impuesto_activo_exists(
            organismo, numero_comprobante
        ):
            return AppResult.fail("COMPROBANTE_IMPUESTO_DUPLICADO")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = ComprobanteImpuestoCreatePayload(
            uid_global=str(self.uuid_generator()),
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
            id_inmueble=command.id_inmueble,
            id_unidad_funcional=command.id_unidad_funcional,
            organismo=organismo,
            tipo_impuesto=tipo_impuesto,
            partida_nomenclatura=partida,
            numero_comprobante=numero_comprobante,
            periodo_desde=command.periodo_desde,
            periodo_hasta=command.periodo_hasta,
            fecha_emision=command.fecha_emision,
            fecha_vencimiento=command.fecha_vencimiento,
            importe_total=command.importe_total,
            modalidad_gestion_impuesto=modalidad,
            observaciones=command.observaciones,
        )

        return AppResult.ok(self.repository.create_comprobante_impuesto(payload))
