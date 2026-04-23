from dataclasses import dataclass
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateUnidadFuncionalCommand:
    context: CommandContext
    id_inmueble: int
    codigo_unidad: str | None
    nombre_unidad: str | None
    superficie: Decimal | None
    estado_administrativo: str | None
    estado_operativo: str | None
    observaciones: str | None
