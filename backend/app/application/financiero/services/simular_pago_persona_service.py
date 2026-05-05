from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol

from app.application.common.results import AppResult
from app.domain.financiero.resolver_mora import ResolucionMora, resolver_mora_params


_Q = Decimal("0.01")


def _mora(
    base_morable: Decimal,
    fecha_vencimiento: date | None,
    fecha_corte: date,
    fecha_inicio: date | None = None,
    resolucion: ResolucionMora | None = None,
) -> Decimal:
    if fecha_vencimiento is None or base_morable <= 0:
        return Decimal("0")
    r = resolucion if resolucion is not None else resolver_mora_params()
    if fecha_corte <= fecha_vencimiento + timedelta(days=r.dias_gracia):
        return Decimal("0")
    inicio = fecha_inicio if fecha_inicio is not None else fecha_vencimiento
    dias = max(0, (fecha_corte - inicio).days)
    if dias == 0:
        return Decimal("0")
    return (base_morable * r.tasa_diaria * dias).quantize(_Q, rounding=ROUND_HALF_UP)


class FinancieroRepository(Protocol):
    def persona_exists(self, id_persona: int) -> bool: ...

    def get_obligaciones_para_simular_pago(
        self,
        *,
        id_persona: int,
        fecha_corte: date,
    ) -> list[dict[str, Any]]: ...

    def get_ultima_fecha_pago_posterior_vencimiento(
        self, *, id_obligacion_financiera: int, fecha_vencimiento: date
    ) -> date | None: ...

    def get_saldo_morable_pendiente(
        self, *, id_obligacion_financiera: int
    ) -> Decimal: ...


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
            id_obligacion = ob["id_obligacion_financiera"]
            saldo = Decimal(str(ob["saldo_pendiente"]))
            pct = Decimal(str(ob["porcentaje_responsabilidad"]))
            fv = ob["fecha_vencimiento"]
            base_morable = Decimal("0")
            ultima_fecha = None
            if fv is not None:
                base_morable = self.repository.get_saldo_morable_pendiente(
                    id_obligacion_financiera=id_obligacion
                ).quantize(_Q, rounding=ROUND_HALF_UP)
                ultima_fecha = self.repository.get_ultima_fecha_pago_posterior_vencimiento(
                    id_obligacion_financiera=id_obligacion,
                    fecha_vencimiento=fv,
                )
            mora = _mora(base_morable, fv, corte, ultima_fecha)
            total_a_cubrir = ((saldo + mora) * pct / 100).quantize(_Q, rounding=ROUND_HALF_UP)
            total_deuda += total_a_cubrir

            aplicado = min(restante, total_a_cubrir)
            restante -= aplicado
            total_aplicado += aplicado

            detalle.append(
                {
                    "id_obligacion_financiera": id_obligacion,
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
