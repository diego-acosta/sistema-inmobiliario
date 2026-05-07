from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateComprobanteImpuestoCommand:
    context: CommandContext
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
