from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateDisponibilidadCommand:
    context: CommandContext
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    motivo: str | None
    observaciones: str | None
