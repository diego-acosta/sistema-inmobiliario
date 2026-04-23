from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateDisponibilidadCommand:
    context: CommandContext
    id_disponibilidad: int
    if_match_version: int | None
    id_inmueble: int | None
    id_unidad_funcional: int | None
    estado_disponibilidad: str
    fecha_desde: datetime
    fecha_hasta: datetime | None
    motivo: str | None
    observaciones: str | None
