from dataclasses import dataclass
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateInmuebleCommand:
    context: CommandContext
    id_inmueble: int
    if_match_version: int | None
    id_desarrollo: int | None
    codigo_inmueble: str
    nombre_inmueble: str | None
    superficie: Decimal | None
    estado_administrativo: str
    estado_juridico: str
    observaciones: str | None
