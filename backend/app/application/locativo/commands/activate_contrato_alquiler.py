from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class ActivateContratoAlquilerCommand:
    context: CommandContext
    id_contrato_alquiler: int
    if_match_version: int | None
