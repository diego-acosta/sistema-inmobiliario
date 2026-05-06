from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CreateAsignacionServicioResponsableCommand:
    context: CommandContext
    id_servicio: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    id_persona: int
    porcentaje_responsabilidad: Decimal
    fecha_desde: date
    fecha_hasta: date | None
    estado_asignacion: str
    observaciones: str | None


@dataclass(slots=True)
class UpdateAsignacionServicioResponsableCommand:
    context: CommandContext
    id_asignacion_servicio_responsable: int
    if_match_version: int | None
    id_servicio: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    id_persona: int
    porcentaje_responsabilidad: Decimal
    fecha_desde: date
    fecha_hasta: date | None
    estado_asignacion: str
    observaciones: str | None


@dataclass(slots=True)
class DeleteAsignacionServicioResponsableCommand:
    context: CommandContext
    id_asignacion_servicio_responsable: int
    if_match_version: int | None
