from dataclasses import dataclass
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateEdificacionCommand:
    context: CommandContext
    id_inmueble: int | None
    id_unidad_funcional: int | None
    descripcion: str | None
    tipo_edificacion: str | None
    superficie: Decimal | None
    observaciones: str | None
