from dataclasses import dataclass
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateInmuebleCommand:
    context: CommandContext
    id_desarrollo: int | None
    codigo_inmueble: str
    nombre_inmueble: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_juridico: str
    observaciones: str | None
