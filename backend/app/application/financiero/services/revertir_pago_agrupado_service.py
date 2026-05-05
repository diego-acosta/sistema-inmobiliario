from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    def get_pago_agrupado_by_codigo(
        self, *, codigo_pago_grupo: str
    ) -> dict[str, Any] | None: ...

    def revertir_pago_agrupado(
        self,
        *,
        codigo_pago_grupo: str,
        motivo: str,
        id_instalacion: Any,
        op_id: UUID | None,
    ) -> dict[str, Any]: ...


class RevertirPagoAgrupadoService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        codigo_pago_grupo: str,
        motivo: str,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        motivo_normalizado = motivo.strip()
        if not motivo_normalizado:
            return AppResult.fail("MOTIVO_REQUERIDO")

        pago = self.repository.get_pago_agrupado_by_codigo(
            codigo_pago_grupo=codigo_pago_grupo
        )
        if pago is None:
            return AppResult.fail("NOT_FOUND_PAGO")

        id_instalacion = getattr(context, "id_instalacion", None)
        op_id = getattr(context, "op_id", None)
        data = self.repository.revertir_pago_agrupado(
            codigo_pago_grupo=codigo_pago_grupo,
            motivo=motivo_normalizado,
            id_instalacion=id_instalacion,
            op_id=op_id,
        )
        return AppResult.ok(data)
