from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreatePersonaDocumentoCommand:
    context: CommandContext
    id_persona: int
    tipo_documento: str
    numero_documento: str
    pais_emision: str | None
    es_principal: bool
    fecha_desde: date | None
    fecha_hasta: date | None
    observaciones: str | None
