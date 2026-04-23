from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateRepresentacionPoderCommand:
    context: CommandContext
    id_persona_representado: int
    id_representacion_poder: int
    if_match_version: int | None
    id_persona_representante: int
    tipo_poder: str
    estado_representacion: str
    fecha_desde: datetime | None
    fecha_hasta: datetime | None
    descripcion: str | None
