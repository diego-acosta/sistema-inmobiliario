from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol

from app.application.common.results import AppResult
from app.domain.financiero.parametros_mora import TASA_DIARIA_MORA_DEFAULT


DIAS_GRACIA_MORA = 5
_Q = Decimal("0.01")


def _mora(saldo: Decimal, fecha_vencimiento: date | None, fecha_corte: date) -> Decimal:
    if fecha_vencimiento is None or saldo <= 0:
        return Decimal("0")
    fecha_inicio_mora = fecha_vencimiento + timedelta(days=DIAS_GRACIA_MORA)
    dias = max(0, (fecha_corte - fecha_inicio_mora).days)
    if dias == 0:
        return Decimal("0")
    return (saldo * TASA_DIARIA_MORA_DEFAULT * dias).quantize(
        _Q, rounding=ROUND_HALF_UP
    )


class FinancieroRepository(Protocol):
    def persona_exists(self, id_persona: int) -> bool: ...

    def get_obligaciones_para_simular_pago(
        self,
        *,
        id_persona: int,
        fecha_corte: date,
    ) -> list[dict[str, Any]]: ...


class SimularPagoPersonaService:
    def __init__(self, repository: FinancieroRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        id_persona: int,
        monto: float,
        fecha_corte: date | None,
    ) -> AppResult[dict[str, Any]]:
        if monto <= 0:
            return AppResult.fail("MONTO_INVALIDO")

        if not self.repository.persona_exists(id_persona):
            return AppResult.fail("NOT_FOUND_PERSONA")

        corte = fecha_corte if fecha_corte is not None else date.today()
        obligaciones = self.repository.get_obligaciones_para_simular_pago(
            id_persona=id_persona, fecha_corte=corte
        )

        monto_dec = Decimal(str(monto)).quantize(_Q, rounding=ROUND_HALF_UP)
        restante = monto_dec
        total_aplicado = Decimal("0")
        total_deuda = Decimal("0")
        detalle: list[dict[str, Any]] = []

        for ob in obligaciones:
            saldo = Decimal(str(ob["saldo_pendiente"]))
            pct = Decimal(str(ob["porcentaje_responsabilidad"]))
            mora = _mora(saldo, ob["fecha_vencimiento"], corte)
            total_a_cubrir = ((saldo + mora) * pct / 100).quantize(_Q, rounding=ROUND_HALF_UP)
            total_deuda += total_a_cubrir

            aplicado = min(restante, total_a_cubrir)
            restante -= aplicado
            total_aplicado += aplicado

            detalle.append(
                {
                    "id_obligacion_financiera": ob["id_obligacion_financiera"],
                    "saldo_pendiente": float(saldo),
                    "mora_calculada": float(mora),
                    "total_a_cubrir": float(total_a_cubrir),
                    "monto_aplicado": float(aplicado),
                    "saldo_restante_simulado": float(
                        (total_a_cubrir - aplicado).quantize(_Q, rounding=ROUND_HALF_UP)
                    ),
                }
            )

        return AppResult.ok(
            {
                "id_persona": id_persona,
                "fecha_corte": corte,
                "monto_ingresado": float(monto_dec),
                "monto_aplicado": float(total_aplicado),
                "remanente": float(restante),
                "total_deuda_considerada": float(total_deuda),
                "detalle": detalle,
            }
        )
