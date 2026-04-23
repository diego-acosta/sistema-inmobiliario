from dataclasses import dataclass
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateUnidadFuncionalCommand:
    context: CommandContext
    id_unidad_funcional: int
    if_match_version: int | None
    codigo_unidad: str | None
    nombre_unidad: str | None
    superficie: Decimal | None
    estado_administrativo: str | None
    estado_operativo: str | None
    observaciones: str | None
