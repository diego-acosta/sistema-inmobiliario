from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreatePersonaRelacionCommand:
    context: CommandContext
    id_persona_origen: int
    id_persona_destino: int
    tipo_relacion: str
    fecha_desde: datetime | None
    fecha_hasta: datetime | None
    observaciones: str | None
