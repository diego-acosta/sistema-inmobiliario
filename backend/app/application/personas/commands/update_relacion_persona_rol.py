from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateRelacionPersonaRolCommand:
    context: CommandContext
    id_relacion_persona_rol: int
    if_match_version: int | None
    id_persona: int
    id_rol_participacion: int
    tipo_relacion: str
    id_relacion: int
    fecha_desde: date
    fecha_hasta: date | None
    observaciones: str | None
