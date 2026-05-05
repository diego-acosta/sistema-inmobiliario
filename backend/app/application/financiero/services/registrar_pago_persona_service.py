from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.domain.financiero.resolver_mora import ResolucionMora, resolver_mora_params


_Q = Decimal("0.01")

# Prioridad de aplicación de pago contra composiciones (igual a imputacion existente)
_PRIORIDAD: dict[str, int] = {
    "PUNITORIO": 0,
    "CARGO_ADMINISTRATIVO": 2,
    "INTERES_FINANCIERO": 3,
    "AJUSTE_INDEXACION": 4,
    "CAPITAL_VENTA": 5,
    "ANTICIPO_VENTA": 6,
    "CANON_LOCATIVO": 7,
    "EXPENSA_TRASLADADA": 8,
    "SERVICIO_TRASLADADO": 9,
    "IMPUESTO_TRASLADADO": 10,
}


def _punitorio_dec(
    base_morable: Decimal,
    fv: date | None,
    corte: date,
    fecha_inicio: date | None = None,
    resolucion: ResolucionMora | None = None,
) -> Decimal:
    if fv is None or base_morable <= 0:
        return Decimal("0")
    r = resolucion if resolucion is not None else resolver_mora_params()
    if corte <= fv + timedelta(days=r.dias_gracia):
        return Decimal("0")
    inicio = fecha_inicio if fecha_inicio is not None else fv
    dias = max(0, (corte - inicio).days)
    if dias == 0:
        return Decimal("0")
    return (base_morable * r.tasa_diaria * dias).quantize(_Q, rounding=ROUND_HALF_UP)


def _clave_orden(comp: dict[str, Any]) -> tuple[int, int]:
    return (_PRIORIDAD.get(comp["codigo_concepto_financiero"], 999), comp["orden_composicion"])


def _payload_idempotencia_equivalente(
    payload: dict[str, Any] | None,
    *,
    id_persona: int,
    monto: Decimal,
    fecha_pago: date,
) -> bool:
    if payload is None or payload.get("tipo") != "pago_persona":
        return False

    try:
        payload_fecha = date.fromisoformat(str(payload["fecha_pago"]))
        payload_monto = Decimal(str(payload["monto_ingresado"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        payload_persona = int(payload["id_persona"])
    except (KeyError, TypeError, ValueError):
        return False

    return (
        payload_persona == id_persona
        and payload_fecha == fecha_pago
        and payload_monto == monto
    )


@dataclass(slots=True)
class LineaPagoPayload:
    uid_global: str
    id_composicion_obligacion: int
    importe_aplicado: float


@dataclass(slots=True)
class PagoObligacionPayload:
    id_obligacion_financiera: int
    monto_a_aplicar: float
    uid_global_movimiento: str
    fecha_movimiento: datetime
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    observaciones: str | None
    lineas: list[LineaPagoPayload]


class FinancieroRepository(Protocol):
    def persona_exists(self, id_persona: int) -> bool: ...

    def get_obligaciones_para_simular_pago(
        self, *, id_persona: int, fecha_corte: date
    ) -> list[dict[str, Any]]: ...

    def get_composiciones_para_imputar(
        self, id_obligacion_financiera: int
    ) -> list[dict[str, Any]]: ...

    def registrar_pago_multipago(
        self, pagos: list[PagoObligacionPayload]
    ) -> list[dict[str, Any]]: ...

    def get_pago_persona_by_op_id(
        self, *, op_id: UUID
    ) -> dict[str, Any] | None: ...

    def get_ultima_fecha_pago_posterior_vencimiento(
        self, *, id_obligacion_financiera: int, fecha_vencimiento: date
    ) -> date | None: ...

    def get_saldo_morable_pendiente(
        self, *, id_obligacion_financiera: int
    ) -> Decimal: ...

    def liquidar_punitorio_obligacion(
        self,
        *,
        id_obligacion_financiera: int,
        importe_punitorio: Decimal,
        detalle_calculo: str,
        now: datetime,
        id_instalacion: Any,
        op_id: UUID | None,
        uid_global: str,
    ) -> dict[str, Any]: ...


class RegistrarPagoPersonaService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self,
        *,
        id_persona: int,
        monto: float,
        fecha_pago: date | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        if monto <= 0:
            return AppResult.fail("MONTO_INVALIDO")

        if not self.repository.persona_exists(id_persona):
            return AppResult.fail("NOT_FOUND_PERSONA")

        corte = fecha_pago if fecha_pago is not None else date.today()
        now = datetime.now(UTC)
        fecha_movimiento = datetime.combine(corte, datetime.min.time())
        id_instalacion = getattr(context, "id_instalacion", None)
        op_id = getattr(context, "op_id", None)

        monto_dec = Decimal(str(monto)).quantize(_Q, rounding=ROUND_HALF_UP)
        if op_id is not None:
            pago_existente = self.repository.get_pago_persona_by_op_id(
                op_id=op_id
            )
            if pago_existente is not None:
                payload_existente = pago_existente.get("payload_idempotencia")
                if not _payload_idempotencia_equivalente(
                    payload_existente,
                    id_persona=id_persona,
                    monto=monto_dec,
                    fecha_pago=corte,
                ):
                    return AppResult.fail("IDEMPOTENCY_PAYLOAD_CONFLICT")

                monto_ingresado = Decimal(str(pago_existente["monto_ingresado"])).quantize(
                    _Q, rounding=ROUND_HALF_UP
                )
                monto_aplicado = Decimal(str(pago_existente["monto_aplicado"])).quantize(
                    _Q, rounding=ROUND_HALF_UP
                )
                monto_consumido = Decimal(str(pago_existente["monto_consumido"])).quantize(
                    _Q, rounding=ROUND_HALF_UP
                )
                remanente = max(monto_ingresado - monto_consumido, Decimal("0")).quantize(
                    _Q, rounding=ROUND_HALF_UP
                )
                return AppResult.ok(
                    {
                        "id_persona": pago_existente["id_persona"],
                        "fecha_pago": pago_existente["fecha_pago"],
                        "monto_ingresado": float(monto_ingresado),
                        "monto_aplicado": float(monto_aplicado),
                        "remanente": float(remanente),
                        "obligaciones_pagadas": pago_existente["obligaciones_pagadas"],
                    }
                )

        obligaciones = self.repository.get_obligaciones_para_simular_pago(
            id_persona=id_persona, fecha_corte=corte
        )

        restante = monto_dec
        pagos: list[PagoObligacionPayload] = []
        total_aplicado = Decimal("0")

        for ob in obligaciones:
            if restante <= 0:
                break

            saldo = Decimal(str(ob["saldo_pendiente"])).quantize(_Q, rounding=ROUND_HALF_UP)
            fv = ob["fecha_vencimiento"]
            punitorio = Decimal("0")
            if fv is not None:
                base_morable = self.repository.get_saldo_morable_pendiente(
                    id_obligacion_financiera=ob["id_obligacion_financiera"]
                ).quantize(_Q, rounding=ROUND_HALF_UP)
                ultima_fecha = self.repository.get_ultima_fecha_pago_posterior_vencimiento(
                    id_obligacion_financiera=ob["id_obligacion_financiera"],
                    fecha_vencimiento=fv,
                )
                punitorio = _punitorio_dec(base_morable, fv, corte, ultima_fecha)
                if punitorio > 0:
                    detalle = json.dumps(
                        {
                            "tipo": "PUNITORIO",
                            "fecha_pago": corte.isoformat(),
                            "fecha_vencimiento": fv.isoformat(),
                            "fecha_inicio_calculo": (ultima_fecha or fv).isoformat(),
                            "base_morable": float(base_morable),
                            "importe_liquidado": float(punitorio),
                        },
                        separators=(",", ":"),
                    )
                    self.repository.liquidar_punitorio_obligacion(
                        id_obligacion_financiera=ob["id_obligacion_financiera"],
                        importe_punitorio=punitorio,
                        detalle_calculo=detalle,
                        now=now,
                        id_instalacion=id_instalacion,
                        op_id=op_id,
                        uid_global=str(self.uuid_generator()),
                    )
                    saldo = (saldo + punitorio).quantize(_Q, rounding=ROUND_HALF_UP)

            monto_a_saldo = min(restante, saldo).quantize(_Q, rounding=ROUND_HALF_UP)

            if monto_a_saldo <= 0:
                continue

            composiciones = self.repository.get_composiciones_para_imputar(
                ob["id_obligacion_financiera"]
            )
            if not composiciones:
                # Sin composiciones activas: saltear sin consumir del monto
                continue

            composiciones_ord = sorted(composiciones, key=_clave_orden)
            monto_comp = float(monto_a_saldo)
            lineas: list[LineaPagoPayload] = []

            for comp in composiciones_ord:
                if monto_comp <= 0:
                    break
                aplicado = round(min(float(comp["saldo_componente"]), monto_comp), 2)
                if aplicado <= 0:
                    continue
                lineas.append(
                    LineaPagoPayload(
                        uid_global=str(self.uuid_generator()),
                        id_composicion_obligacion=comp["id_composicion_obligacion"],
                        importe_aplicado=aplicado,
                    )
                )
                monto_comp = round(monto_comp - aplicado, 2)

            if not lineas:
                continue

            pagos.append(
                PagoObligacionPayload(
                    id_obligacion_financiera=ob["id_obligacion_financiera"],
                    monto_a_aplicar=float(monto_a_saldo),
                    uid_global_movimiento=str(self.uuid_generator()),
                    fecha_movimiento=fecha_movimiento,
                    version_registro=1,
                    created_at=now,
                    updated_at=now,
                    id_instalacion_origen=id_instalacion,
                    id_instalacion_ultima_modificacion=id_instalacion,
                    op_id_alta=op_id,
                    op_id_ultima_modificacion=op_id,
                    observaciones=None,
                    lineas=lineas,
                )
            )

            restante -= monto_a_saldo
            total_aplicado += monto_a_saldo

        if not pagos:
            return AppResult.ok(
                {
                    "id_persona": id_persona,
                    "fecha_pago": corte,
                    "monto_ingresado": float(monto_dec),
                    "monto_aplicado": 0.0,
                    "remanente": float(monto_dec),
                    "obligaciones_pagadas": [],
                }
            )

        resumen_idempotencia = json.dumps(
            {
                "tipo": "pago_persona",
                "id_persona": id_persona,
                "fecha_pago": corte.isoformat(),
                "monto_ingresado": float(monto_dec),
                "monto_aplicado": float(total_aplicado),
                "remanente": float(restante),
            },
            separators=(",", ":"),
        )
        for pago in pagos:
            pago.observaciones = resumen_idempotencia

        resultados = self.repository.registrar_pago_multipago(pagos)

        return AppResult.ok(
            {
                "id_persona": id_persona,
                "fecha_pago": corte,
                "monto_ingresado": float(monto_dec),
                "monto_aplicado": float(total_aplicado),
                "remanente": float(restante),
                "obligaciones_pagadas": resultados,
            }
        )
