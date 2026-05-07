from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol

from app.application.common.results import AppResult


_Q = Decimal("0.01")


class FinancieroRepository(Protocol):
    def get_comprobante_impuesto(
        self, id_comprobante_impuesto: int
    ) -> dict[str, Any] | None: ...

    def list_egresos_impuesto_empresa(
        self, id_comprobante_impuesto: int
    ) -> list[dict[str, Any]]: ...


class ConsultarEgresosImpuestoEmpresaService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(self, *, id_comprobante_impuesto: int) -> AppResult[dict[str, Any]]:
        comprobante = self.repository.get_comprobante_impuesto(id_comprobante_impuesto)
        if comprobante is None:
            return AppResult.fail("COMPROBANTE_IMPUESTO_NOT_FOUND")

        importe_total = Decimal(str(comprobante["importe_total"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        egresos = self.repository.list_egresos_impuesto_empresa(
            id_comprobante_impuesto
        )
        total_egresado = sum(
            (
                Decimal(str(egreso["importe_pagado"])).quantize(
                    _Q, rounding=ROUND_HALF_UP
                )
                for egreso in egresos
                if egreso["estado_egreso"] == "REGISTRADO"
            ),
            Decimal("0.00"),
        ).quantize(_Q, rounding=ROUND_HALF_UP)
        saldo = (importe_total - total_egresado).quantize(_Q, rounding=ROUND_HALF_UP)

        return AppResult.ok(
            {
                "id_comprobante_impuesto": id_comprobante_impuesto,
                "importe_total_comprobante": float(importe_total),
                "total_egresado": float(total_egresado),
                "saldo_pendiente_pago_impuesto": float(saldo),
                "estado_pago_impuesto": _estado_pago_impuesto(
                    total_egresado=total_egresado,
                    importe_total=importe_total,
                ),
                "egresos": egresos,
            }
        )


def _estado_pago_impuesto(*, total_egresado: Decimal, importe_total: Decimal) -> str:
    if total_egresado == 0:
        return "SIN_PAGO"
    if total_egresado < importe_total:
        return "PAGO_PARCIAL"
    if total_egresado == importe_total:
        return "PAGADO"
    return "SOBREPAGADO"
