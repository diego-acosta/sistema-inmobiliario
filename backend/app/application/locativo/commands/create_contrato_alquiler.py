from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateContratoAlquilerParticipacionCommand:
    id_persona: int
    id_rol_participacion: int
    fecha_desde: date | None
    fecha_hasta: date | None
    observaciones: str | None


@dataclass(slots=True)
class CreateContratoAlquilerObjetoCommand:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    observaciones: str | None


@dataclass(slots=True)
class CreateContratoAlquilerCommand:
    context: CommandContext
    codigo_contrato: str
    fecha_contrato: date | None
    fecha_inicio: date
    fecha_fin: date | None
    canon_inicial: Decimal | None
    moneda: str | None
    observaciones: str | None
    objetos: list[CreateContratoAlquilerObjetoCommand]
    participaciones: list[CreateContratoAlquilerParticipacionCommand]
