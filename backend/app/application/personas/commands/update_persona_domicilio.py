from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdatePersonaDomicilioCommand:
    context: CommandContext
    id_persona: int
    id_persona_domicilio: int
    if_match_version: int | None
    tipo_domicilio: str | None
    direccion: str | None
    localidad: str | None
    provincia: str | None
    pais: str | None
    codigo_postal: str | None
    es_principal: bool
    fecha_desde: date | None
    fecha_hasta: date | None
    observaciones: str | None
