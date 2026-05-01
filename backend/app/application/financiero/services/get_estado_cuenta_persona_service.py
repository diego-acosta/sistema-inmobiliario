from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def persona_exists(self, id_persona: int) -> bool: ...

    def get_estado_cuenta_por_persona(
        self,
        *,
        id_persona: int,
        estado: str | None,
        tipo_origen: str | None,
        id_origen: int | None,
        vencidas: bool | None,
        fecha_vencimiento_desde: date | None,
        fecha_vencimiento_hasta: date | None,
        fecha_corte: date,
    ) -> dict[str, Any]: ...


class GetEstadoCuentaPersonaService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        id_persona: int,
        estado: str | None,
        tipo_origen: str | None,
        id_origen: int | None,
        vencidas: bool | None,
        fecha_vencimiento_desde: date | None,
        fecha_vencimiento_hasta: date | None,
        fecha_corte: date | None,
    ) -> AppResult[dict[str, Any]]:
        if (
            fecha_vencimiento_desde is not None
            and fecha_vencimiento_hasta is not None
            and fecha_vencimiento_hasta < fecha_vencimiento_desde
        ):
            return AppResult.fail("FECHA_RANGO_INVALIDO")

        if not self.repository.persona_exists(id_persona):
            return AppResult.fail("NOT_FOUND_PERSONA")

        corte = fecha_corte if fecha_corte is not None else date.today()

        return AppResult.ok(
            self.repository.get_estado_cuenta_por_persona(
                id_persona=id_persona,
                estado=estado,
                tipo_origen=tipo_origen,
                id_origen=id_origen,
                vencidas=vencidas,
                fecha_vencimiento_desde=fecha_vencimiento_desde,
                fecha_vencimiento_hasta=fecha_vencimiento_hasta,
                fecha_corte=corte,
            )
        )
