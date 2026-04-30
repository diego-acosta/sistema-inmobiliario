from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def relacion_generadora_exists(self, id_relacion_generadora: int) -> bool: ...

    def get_estado_cuenta_financiero(
        self,
        *,
        id_relacion_generadora: int,
        incluir_canceladas: bool,
        fecha_desde: date | None,
        fecha_hasta: date | None,
    ) -> dict[str, Any]: ...


class GetEstadoCuentaFinancieroService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        id_relacion_generadora: int,
        incluir_canceladas: bool,
        fecha_desde: date | None,
        fecha_hasta: date | None,
    ) -> AppResult[dict[str, Any]]:
        if (
            fecha_desde is not None
            and fecha_hasta is not None
            and fecha_hasta < fecha_desde
        ):
            return AppResult.fail("FECHA_RANGO_INVALIDO")

        if not self.repository.relacion_generadora_exists(id_relacion_generadora):
            return AppResult.fail("NOT_FOUND_RELACION")

        return AppResult.ok(
            self.repository.get_estado_cuenta_financiero(
                id_relacion_generadora=id_relacion_generadora,
                incluir_canceladas=incluir_canceladas,
                fecha_desde=fecha_desde,
                fecha_hasta=fecha_hasta,
            )
        )
