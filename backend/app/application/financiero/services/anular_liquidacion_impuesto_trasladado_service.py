from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    db: Any

    def get_liquidacion_impuesto_trasladado_para_anular(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> dict[str, Any] | None: ...

    def get_operaciones_activas_liquidacion_impuesto_trasladado(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> dict[str, Any]: ...

    def anular_liquidacion_impuesto_trasladado(
        self,
        *,
        id_liquidacion_impuesto_trasladado: int,
        motivo: str,
        context: Any,
    ) -> dict[str, Any]: ...


class AnularLiquidacionImpuestoTrasladadoService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository
        self.db = repository.db

    def execute(
        self,
        *,
        id_liquidacion_impuesto_trasladado: int,
        motivo: str,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        motivo_limpio = motivo.strip()
        if not motivo_limpio:
            return AppResult.fail("MOTIVO_REQUERIDO")

        try:
            with self._transaction():
                return self._execute_in_transaction(
                    id_liquidacion_impuesto_trasladado=(
                        id_liquidacion_impuesto_trasladado
                    ),
                    motivo=motivo_limpio,
                    context=context,
                )
        except _RollbackAppResult as exc:
            return exc.result

    def _execute_in_transaction(
        self,
        *,
        id_liquidacion_impuesto_trasladado: int,
        motivo: str,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        liquidacion = (
            self.repository.get_liquidacion_impuesto_trasladado_para_anular(
                id_liquidacion_impuesto_trasladado
            )
        )
        if liquidacion is None:
            return AppResult.fail("LIQUIDACION_IMPUESTO_TRASLADADO_NOT_FOUND")

        if liquidacion["estado_liquidacion"] == "ANULADA":
            liquidacion["resultado"] = "YA_ANULADA"
            liquidacion["motivo"] = liquidacion.get("motivo_anulacion") or motivo
            liquidacion["egresos_liberados"] = 0
            liquidacion["ya_anulada"] = True
            return AppResult.ok(_response(liquidacion))

        operaciones = (
            self.repository.get_operaciones_activas_liquidacion_impuesto_trasladado(
                id_liquidacion_impuesto_trasladado
            )
        )
        if operaciones["tiene_operaciones"]:
            return AppResult.fail("LIQUIDACION_IMPUESTO_TRASLADADO_TIENE_OPERACIONES")

        anulado = self.repository.anular_liquidacion_impuesto_trasladado(
            id_liquidacion_impuesto_trasladado=id_liquidacion_impuesto_trasladado,
            motivo=motivo,
            context=context,
        )
        anulado["resultado"] = "ANULADA"
        anulado["motivo"] = motivo
        anulado["ya_anulada"] = False
        return AppResult.ok(_response(anulado))

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()


def _response(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "resultado": values.get("resultado"),
        "id_liquidacion_impuesto_trasladado": values[
            "id_liquidacion_impuesto_trasladado"
        ],
        "estado_liquidacion": values["estado_liquidacion"],
        "id_relacion_generadora": values.get("id_relacion_generadora"),
        "estado_relacion_generadora": values.get("estado_relacion_generadora"),
        "id_obligacion_financiera": values.get("id_obligacion_financiera"),
        "estado_obligacion": values.get("estado_obligacion"),
        "egresos_liberados": values["egresos_liberados"],
        "ya_anulada": values["ya_anulada"],
        "motivo": values["motivo"],
    }


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[Any]) -> None:
        self.result = result
