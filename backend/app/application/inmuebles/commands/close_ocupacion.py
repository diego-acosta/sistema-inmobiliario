from dataclasses import dataclass
from datetime import datetime

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class CloseOcupacionCommand:
    context: CommandContext
    id_ocupacion: int
    fecha_hasta: datetime
    if_match_version: int | None
