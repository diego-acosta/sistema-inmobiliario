from dataclasses import dataclass
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class DefineCondicionesComercialesVentaObjetoCommand:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    precio_asignado: Decimal


@dataclass(slots=True)
class DefineCondicionesComercialesVentaCommand:
    context: CommandContext
    id_venta: int
    if_match_version: int | None
    monto_total: Decimal
    objetos: list[DefineCondicionesComercialesVentaObjetoCommand]
