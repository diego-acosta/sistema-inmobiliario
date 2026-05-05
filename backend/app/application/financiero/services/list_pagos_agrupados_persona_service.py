from dataclasses import dataclass

from app.application.common.results import AppResult


@dataclass(slots=True)
class ListPagosAgrupadosPersonaService:
    repository: object

    def execute(self, *, id_persona: int) -> AppResult[list[dict]]:
        rows = self.repository.list_pagos_agrupados_persona(id_persona=id_persona)
        return AppResult.ok(rows)
