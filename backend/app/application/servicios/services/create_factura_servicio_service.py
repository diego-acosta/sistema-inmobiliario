from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.servicios.commands.create_factura_servicio import (
    CreateFacturaServicioCommand,
)


@dataclass(slots=True)
class FacturaServicioCreatePayload:
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
    proveedor: str
    numero_factura: str
    fecha_emision: date
    fecha_vencimiento: date | None
    periodo_desde: date | None
    periodo_hasta: date | None
    importe_total: Decimal
    observaciones: str | None


class FacturaServicioRepository(Protocol):
    def servicio_activo_exists(self, id_servicio: int) -> bool:
        ...

    def servicio_asociado_a_inmueble(self, id_servicio: int, id_inmueble: int) -> bool:
        ...

    def servicio_asociado_a_unidad_funcional(
        self, id_servicio: int, id_unidad_funcional: int
    ) -> bool:
        ...

    def factura_servicio_activa_exists(
        self, proveedor: str, numero_factura: str
    ) -> bool:
        ...

    def create_factura_servicio(self, payload: FacturaServicioCreatePayload) -> Any:
        ...


class CreateFacturaServicioService:
    def __init__(self, repository: FacturaServicioRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateFacturaServicioCommand
    ) -> AppResult[dict[str, Any]]:
        proveedor = command.proveedor.strip()
        numero_factura = command.numero_factura.strip()

        if (command.id_inmueble is not None) == (
            command.id_unidad_funcional is not None
        ):
            return AppResult.fail("FACTURA_SERVICIO_XOR_INVALIDO")
        if not proveedor or not numero_factura:
            return AppResult.fail("FACTURA_SERVICIO_DATOS_REQUERIDOS")
        if command.importe_total < Decimal("0"):
            return AppResult.fail("IMPORTE_TOTAL_INVALIDO")
        if (
            command.fecha_vencimiento is not None
            and command.fecha_vencimiento < command.fecha_emision
        ):
            return AppResult.fail("FECHA_VENCIMIENTO_INVALIDA")
        if (
            command.periodo_desde is not None
            and command.periodo_hasta is not None
            and command.periodo_hasta < command.periodo_desde
        ):
            return AppResult.fail("PERIODO_INVALIDO")

        if not self.repository.servicio_activo_exists(command.id_servicio):
            return AppResult.fail("NOT_FOUND_SERVICIO")

        if command.id_inmueble is not None:
            asociado = self.repository.servicio_asociado_a_inmueble(
                command.id_servicio,
                command.id_inmueble,
            )
        else:
            asociado = self.repository.servicio_asociado_a_unidad_funcional(
                command.id_servicio,
                command.id_unidad_funcional or 0,
            )
        if not asociado:
            return AppResult.fail("SERVICIO_NO_ASOCIADO")

        if self.repository.factura_servicio_activa_exists(proveedor, numero_factura):
            return AppResult.fail("FACTURA_SERVICIO_DUPLICADA")

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        payload = FacturaServicioCreatePayload(
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
            proveedor=proveedor,
            numero_factura=numero_factura,
            fecha_emision=command.fecha_emision,
            fecha_vencimiento=command.fecha_vencimiento,
            periodo_desde=command.periodo_desde,
            periodo_hasta=command.periodo_hasta,
            importe_total=command.importe_total,
            observaciones=command.observaciones,
        )

        return AppResult.ok(self.repository.create_factura_servicio(payload))
