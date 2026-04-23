from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdatePersonaDocumentoCommand:
    context: CommandContext
    id_persona: int
    id_persona_documento: int
    if_match_version: int | None
    tipo_documento: str
    numero_documento: str
    pais_emision: str | None
    es_principal: bool
    fecha_desde: date | None
    fecha_hasta: date | None
    observaciones: str | None
