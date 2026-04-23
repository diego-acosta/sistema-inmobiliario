from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdatePersonaCommand:
    context: CommandContext
    id_persona: int
    if_match_version: int | None
    tipo_persona: str
    nombre: str | None
    apellido: str | None
    razon_social: str | None
    fecha_nacimiento: date | None
    estado_persona: str
    observaciones: str | None
