from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Any, Protocol

from app.application.common.results import AppResult


class FinancieroRepository(Protocol):
    db: Any

    def get_egreso_proveedor_factura_servicio_by_id(
        self, id_egreso: int
    ) -> dict[str, Any] | None: ...

    def egreso_proveedor_usado_en_liquidacion_recupero(self, id_egreso: int) -> bool: ...

    def anular_egreso_proveedor_factura_servicio(
        self, *, id_egreso: int, motivo: str, context: Any
    ) -> dict[str, Any]: ...


class AnularEgresoProveedorFacturaServicioService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository
        self.db = repository.db

    def execute(
        self, *, id_egreso: int, motivo: str, context: Any
    ) -> AppResult[dict[str, Any]]:
        motivo_limpio = motivo.strip()
        if not motivo_limpio:
            return AppResult.fail("MOTIVO_REQUERIDO")

        try:
            with self._transaction():
                return self._execute_in_transaction(
                    id_egreso=id_egreso,
                    motivo=motivo_limpio,
                    context=context,
                )
        except _RollbackAppResult as exc:
            return exc.result

    def _execute_in_transaction(
        self, *, id_egreso: int, motivo: str, context: Any
    ) -> AppResult[dict[str, Any]]:
        egreso = self.repository.get_egreso_proveedor_factura_servicio_by_id(id_egreso)
        if egreso is None:
            return AppResult.fail("EGRESO_PROVEEDOR_NOT_FOUND")

        if egreso["estado_egreso"] == "ANULADO":
            egreso["resultado"] = "YA_ANULADO"
            egreso["motivo"] = egreso.get("motivo_anulacion") or motivo
            egreso["ya_anulado"] = True
            return AppResult.ok(_response(egreso))

        if self.repository.egreso_proveedor_usado_en_liquidacion_recupero(id_egreso):
            return AppResult.fail("EGRESO_PROVEEDOR_CON_LIQUIDACION_RECUPERO")

        anulado = self.repository.anular_egreso_proveedor_factura_servicio(
            id_egreso=id_egreso,
            motivo=motivo,
            context=context,
        )
        anulado["resultado"] = "ANULADO"
        anulado["motivo"] = motivo
        anulado["ya_anulado"] = False
        return AppResult.ok(_response(anulado))

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()


def _response(values: dict[str, Any]) -> dict[str, Any]:
    return {
        "resultado": values.get("resultado"),
        "id_egreso_proveedor_factura_servicio": values[
            "id_egreso_proveedor_factura_servicio"
        ],
        "id_factura_servicio": values["id_factura_servicio"],
        "id_movimiento_tesoreria": values["id_movimiento_tesoreria"],
        "estado_egreso": values["estado_egreso"],
        "estado_movimiento_tesoreria": values["estado_movimiento_tesoreria"],
        "motivo": values["motivo"],
        "ya_anulado": values["ya_anulado"],
    }


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[Any]) -> None:
        self.result = result
