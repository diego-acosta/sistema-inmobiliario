from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CloseDisponibilidadCommand:
    context: CommandContext
    id_disponibilidad: int
    fecha_hasta: datetime
    if_match_version: int | None
