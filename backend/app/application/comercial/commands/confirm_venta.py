from dataclasses import dataclass

from app.application.common.commands import CommandContext


@dataclass(slots=True)
class ConfirmVentaCommand:
    context: CommandContext
    id_venta: int
    if_match_version: int | None
    observaciones: str | None
