from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class ReplaceOcupacionVigenteCommand:
    context: CommandContext
    id_inmueble: int | None
    id_unidad_funcional: int | None
    tipo_ocupacion: str
    fecha_desde: datetime
    descripcion: str | None
    observaciones: str | None
