from dataclasses import dataclass

from app.application.common.result import Result


@dataclass(slots=True)
class ListPagosAgrupadosPersonaService:
    repository: object

    def execute(self, *, id_persona: int) -> Result:
        rows = self.repository.list_pagos_agrupados_persona(id_persona=id_persona)
        return Result(success=True, data=rows, errors=[])
