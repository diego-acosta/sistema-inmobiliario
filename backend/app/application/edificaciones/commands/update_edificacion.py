from dataclasses import dataclass
from decimal import Decimal

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class UpdateEdificacionCommand:
    context: CommandContext
    id_edificacion: int
    if_match_version: int | None
    descripcion: str | None
    tipo_edificacion: str | None
    superficie: Decimal | None
    observaciones: str | None
