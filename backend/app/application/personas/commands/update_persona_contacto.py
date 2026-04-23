from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdatePersonaContactoCommand:
    context: CommandContext
    id_persona: int
    id_persona_contacto: int
    if_match_version: int | None
    tipo_contacto: str | None
    valor_contacto: str
    es_principal: bool
    fecha_desde: date | None
    fecha_hasta: date | None
    observaciones: str | None
