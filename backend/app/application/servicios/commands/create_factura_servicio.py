from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateFacturaServicioCommand:
    context: CommandContext
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
