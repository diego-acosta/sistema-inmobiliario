from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateCesionCommand:
    context: CommandContext
    id_venta: int
    fecha_cesion: datetime
    tipo_cesion: str | None
    observaciones: str | None
