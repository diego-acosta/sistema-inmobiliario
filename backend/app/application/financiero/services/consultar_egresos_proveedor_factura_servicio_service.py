from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol

from app.application.common.results import AppResult


_Q = Decimal("0.01")


class FinancieroRepository(Protocol):
    def get_factura_servicio_para_materializar(
        self, id_factura_servicio: int
    ) -> dict[str, Any] | None: ...

    def list_egresos_proveedor_factura_servicio(
        self, id_factura_servicio: int
    ) -> list[dict[str, Any]]: ...


class ConsultarEgresosProveedorFacturaServicioService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(self, *, id_factura_servicio: int) -> AppResult[dict[str, Any]]:
        factura = self.repository.get_factura_servicio_para_materializar(
            id_factura_servicio
        )
        if factura is None:
            return AppResult.fail("FACTURA_SERVICIO_NOT_FOUND")

        importe_total = Decimal(str(factura["importe_total"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        egresos = self.repository.list_egresos_proveedor_factura_servicio(
            id_factura_servicio
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
                "id_factura_servicio": id_factura_servicio,
                "importe_total_factura": float(importe_total),
                "total_egresado": float(total_egresado),
                "saldo_pendiente_pago_proveedor": float(saldo),
                "estado_pago_proveedor": _estado_pago_proveedor(
                    total_egresado=total_egresado,
                    importe_total=importe_total,
                ),
                "egresos": egresos,
            }
        )


def _estado_pago_proveedor(*, total_egresado: Decimal, importe_total: Decimal) -> str:
    if total_egresado == 0:
        return "SIN_PAGO"
    if total_egresado < importe_total:
        return "PAGO_PARCIAL"
    if total_egresado == importe_total:
        return "PAGADA"
    return "SOBREPAGADA"
