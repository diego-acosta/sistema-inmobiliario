from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class RechazarSolicitudAlquilerCommand:
    context: CommandContext
    id_solicitud_alquiler: int
    if_match_version: int | None
