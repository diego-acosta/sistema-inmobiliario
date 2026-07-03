from typing import Any, Protocol

from app.application.common.results import AppResult
from app.application.personas.commands.update_datos_principales import (
    UpdateDatosPrincipalesCommand,
)


class PersonaDatosPrincipalesRepository(Protocol):
    def update_datos_principales_tx(self, command: UpdateDatosPrincipalesCommand) -> dict[str, Any] | None:
        ...


class UpdateDatosPrincipalesService:
    def __init__(self, repository: PersonaDatosPrincipalesRepository) -> None:
        self.repository = repository

    def execute(self, command: UpdateDatosPrincipalesCommand) -> AppResult[dict[str, Any]]:
        if getattr(command.context, "id_instalacion", None) is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")
        if getattr(command.context, "op_id", None) is None:
            return AppResult.fail("X-Op-Id es requerido.")
        try:
            data = self.repository.update_datos_principales_tx(command)
        except ValueError as exc:
            return AppResult.fail(str(exc))
        if data is None:
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(data)
