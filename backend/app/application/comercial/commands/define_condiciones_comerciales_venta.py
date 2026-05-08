from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DefineCondicionesComercialesVentaObjetoCommand:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    precio_asignado: Decimal


@dataclass(slots=True)
class DefineCondicionesComercialesVentaCuotaCommand:
    numero_cuota: int
    importe_cuota: Decimal
    fecha_vencimiento: date
    moneda: str | None = None
    observaciones: str | None = None


@dataclass(slots=True)
class DefineCondicionesComercialesVentaCommand:
    context: CommandContext
    id_venta: int
    if_match_version: int | None
    monto_total: Decimal
    tipo_plan_financiero: str | None
    moneda: str | None
    importe_anticipo: Decimal | None
    fecha_vencimiento_anticipo: date | None
    importe_saldo: Decimal | None
    fecha_vencimiento_saldo: date | None
    cuotas: list[DefineCondicionesComercialesVentaCuotaCommand]
    objetos: list[DefineCondicionesComercialesVentaObjetoCommand]
