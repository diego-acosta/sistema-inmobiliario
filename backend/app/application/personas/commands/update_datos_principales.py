from dataclasses import dataclass
from datetime import date

from app.application.common.commands import CommandContext


@dataclass(frozen=True, slots=True)
class DatosPrincipalesPersonaInput:
    tipo_persona: str
    nombre: str | None
    apellido: str | None
    razon_social: str | None
    fecha_nacimiento: date | None
    estado_persona: str
    observaciones: str | None
    version_registro: int


@dataclass(frozen=True, slots=True)
class DatosPrincipalesDocumentoInput:
    id_persona_documento: int | None
    tipo_documento: str
    numero_documento: str | None
    pais_emision: str | None
    es_principal: bool
    version_registro: int | None


@dataclass(frozen=True, slots=True)
class UpdateDatosPrincipalesCommand:
    context: CommandContext
    id_persona: int
    persona: DatosPrincipalesPersonaInput
    documento_identidad: DatosPrincipalesDocumentoInput | None
    identificacion_fiscal: DatosPrincipalesDocumentoInput | None
