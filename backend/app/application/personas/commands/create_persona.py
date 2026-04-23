from dataclasses import dataclass
from datetime import date
from typing import Optional

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreatePersonaCommand:
    context: CommandContext
    tipo_persona: str
    nombre: Optional[str]
    apellido: Optional[str]
    razon_social: Optional[str]
    fecha_nacimiento: Optional[date]
    estado_persona: str
    observaciones: Optional[str]
