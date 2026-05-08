from __future__ import annotations

import json
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult


TIPO_PAGO_EXTERNO_INFORMADO = "PAGO_EXTERNO_INFORMADO"
CONCEPTO_IMPUESTO_TRASLADADO = "IMPUESTO_TRASLADADO"
_Q = Decimal("0.01")


@dataclass(slots=True)
class PagoExternoImpuestoTrasladadoPayload:
    uid_global_movimiento: str
    uid_global_aplicacion: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    id_liquidacion_impuesto_trasladado: int
    id_relacion_generadora: int
    id_obligacion_financiera: int
    id_composicion_obligacion: int
    id_persona: int
    fecha_pago: date
    importe_informado: Decimal
    importe_aplicado: Decimal
    remanente_no_aplicado: Decimal
    referencia_comprobante: str | None
    medio_pago: str
    observaciones_usuario: str | None
    observaciones: str


class FinancieroRepository(Protocol):
    db: Any

    def get_pago_externo_impuesto_trasladado_by_op_id(
        self, *, op_id: UUID
    ) -> dict[str, Any] | None: ...

    def get_liquidacion_impuesto_trasladado_para_pago_externo(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> dict[str, Any] | None: ...

    def get_composicion_impuesto_trasladado_con_saldo(
        self, id_obligacion_financiera: int
    ) -> dict[str, Any] | None: ...

    def get_pagos_externos_impuesto_persona_aplicados(
        self,
        *,
        id_liquidacion_impuesto_trasladado: int,
        id_persona: int,
    ) -> Decimal: ...

    def registrar_pago_externo_impuesto_trasladado(
        self, payload: PagoExternoImpuestoTrasladadoPayload
    ) -> dict[str, Any]: ...


class RegistrarPagoExternoImpuestoTrasladadoService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self,
        *,
        id_liquidacion_impuesto_trasladado: int,
        id_persona: int | None,
        fecha_pago: date,
        importe_pagado: float,
        medio_pago: str,
        referencia_comprobante: str | None,
        observaciones: str | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        try:
            with self._transaction():
                return self._execute_in_transaction(
                    id_liquidacion_impuesto_trasladado=(
                        id_liquidacion_impuesto_trasladado
                    ),
                    id_persona=id_persona,
                    fecha_pago=fecha_pago,
                    importe_pagado=importe_pagado,
                    medio_pago=medio_pago,
                    referencia_comprobante=referencia_comprobante,
                    observaciones=observaciones,
                    context=context,
                )
        except _RollbackAppResult as exc:
            return exc.result

    def _execute_in_transaction(
        self,
        *,
        id_liquidacion_impuesto_trasladado: int,
        id_persona: int | None,
        fecha_pago: date,
        importe_pagado: float,
        medio_pago: str,
        referencia_comprobante: str | None,
        observaciones: str | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        monto = Decimal(str(importe_pagado)).quantize(_Q, rounding=ROUND_HALF_UP)
        if monto <= 0:
            return AppResult.fail("IMPORTE_INVALIDO")

        op_id = getattr(context, "op_id", None)
        if op_id is not None:
            existente = self.repository.get_pago_externo_impuesto_trasladado_by_op_id(
                op_id=op_id
            )
            if existente is not None:
                payload_existente = existente.get("payload_idempotencia")
                if not _payload_equivalente(
                    payload_existente,
                    id_liquidacion_impuesto_trasladado=(
                        id_liquidacion_impuesto_trasladado
                    ),
                    id_persona=id_persona,
                    fecha_pago=fecha_pago,
                    importe_pagado=monto,
                    medio_pago=medio_pago,
                    referencia_comprobante=referencia_comprobante,
                    observaciones=observaciones,
                ):
                    return AppResult.fail("IDEMPOTENCY_PAYLOAD_CONFLICT")
                existente["resultado"] = "YA_REGISTRADO"
                return AppResult.ok(existente)

        liquidacion = (
            self.repository.get_liquidacion_impuesto_trasladado_para_pago_externo(
                id_liquidacion_impuesto_trasladado
            )
        )
        if liquidacion is None:
            return AppResult.fail("LIQUIDACION_IMPUESTO_TRASLADADO_NOT_FOUND")

        estado = (liquidacion.get("estado_liquidacion") or "").strip().upper()
        if estado == "ANULADA":
            return AppResult.fail("LIQUIDACION_IMPUESTO_TRASLADADO_ANULADA")
        if estado != "EMITIDA":
            return AppResult.fail("LIQUIDACION_IMPUESTO_TRASLADADO_ANULADA")

        modalidad = (liquidacion.get("modalidad_gestion_impuesto") or "").strip().upper()
        if modalidad != "DIRECTO_RESPONSABLE":
            return AppResult.fail("PAGO_EXTERNO_IMPUESTO_NO_APLICA_MODALIDAD")

        id_relacion_generadora = liquidacion.get("id_relacion_generadora")
        id_obligacion = liquidacion.get("id_obligacion_financiera")
        if id_relacion_generadora is None or id_obligacion is None:
            return AppResult.fail("OBLIGACION_IMPUESTO_TRASLADADO_NO_EXISTE")

        estado_obligacion = (
            liquidacion.get("estado_obligacion") or ""
        ).strip().upper()
        if estado_obligacion in {"ANULADA", "REEMPLAZADA"}:
            return AppResult.fail("OBLIGACION_IMPUESTO_TRASLADADO_NO_EXISTE")

        responsables = liquidacion.get("responsables") or []
        responsable = _resolver_responsable(responsables, id_persona)
        if responsable is None:
            return AppResult.fail("RESPONSABLE_IMPUESTO_NO_VALIDO")
        id_persona_responsable = int(responsable["id_persona"])

        composicion = self.repository.get_composicion_impuesto_trasladado_con_saldo(
            id_obligacion
        )
        if composicion is None:
            return AppResult.fail("SIN_SALDO_APLICABLE")

        saldo_componente = Decimal(str(composicion["saldo_componente"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        if saldo_componente <= 0:
            return AppResult.fail("SIN_SALDO_APLICABLE")

        importe_responsable = Decimal(str(responsable["importe_responsable"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        ya_aplicado = self.repository.get_pagos_externos_impuesto_persona_aplicados(
            id_liquidacion_impuesto_trasladado=id_liquidacion_impuesto_trasladado,
            id_persona=id_persona_responsable,
        ).quantize(_Q, rounding=ROUND_HALF_UP)
        saldo_responsable = (importe_responsable - ya_aplicado).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        saldo_imputable = min(saldo_componente, saldo_responsable).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        if saldo_imputable <= 0:
            return AppResult.fail("SIN_SALDO_APLICABLE")

        if monto > saldo_imputable:
            return AppResult.fail("PAGO_EXTERNO_IMPUESTO_SUPERA_RESPONSABILIDAD")

        remanente = Decimal("0.00")
        now = datetime.now(UTC)
        id_instalacion = getattr(context, "id_instalacion", None)
        payload_json = _build_payload_idempotencia(
            id_liquidacion_impuesto_trasladado=id_liquidacion_impuesto_trasladado,
            id_persona=id_persona_responsable,
            fecha_pago=fecha_pago,
            importe_pagado=monto,
            medio_pago=medio_pago,
            referencia_comprobante=referencia_comprobante,
            observaciones=observaciones,
            id_relacion_generadora=id_relacion_generadora,
            id_obligacion_financiera=id_obligacion,
            id_composicion_obligacion=composicion["id_composicion_obligacion"],
            importe_aplicado=monto,
            remanente_no_aplicado=remanente,
        )

        registrado = self.repository.registrar_pago_externo_impuesto_trasladado(
            PagoExternoImpuestoTrasladadoPayload(
                uid_global_movimiento=str(self.uuid_generator()),
                uid_global_aplicacion=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
                id_liquidacion_impuesto_trasladado=(
                    id_liquidacion_impuesto_trasladado
                ),
                id_relacion_generadora=id_relacion_generadora,
                id_obligacion_financiera=id_obligacion,
                id_composicion_obligacion=composicion["id_composicion_obligacion"],
                id_persona=id_persona_responsable,
                fecha_pago=fecha_pago,
                importe_informado=monto,
                importe_aplicado=monto,
                remanente_no_aplicado=remanente,
                referencia_comprobante=referencia_comprobante,
                medio_pago=medio_pago,
                observaciones_usuario=observaciones,
                observaciones=payload_json,
            )
        )
        registrado["resultado"] = "REGISTRADO"
        return AppResult.ok(registrado)

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()


def _resolver_responsable(
    responsables: list[dict[str, Any]], id_persona: int | None
) -> dict[str, Any] | None:
    if id_persona is None:
        if len(responsables) != 1:
            return None
        return responsables[0]
    for responsable in responsables:
        if int(responsable["id_persona"]) == id_persona:
            return responsable
    return None


def _build_payload_idempotencia(
    *,
    id_liquidacion_impuesto_trasladado: int,
    id_persona: int,
    fecha_pago: date,
    importe_pagado: Decimal,
    medio_pago: str,
    referencia_comprobante: str | None,
    observaciones: str | None,
    id_relacion_generadora: int,
    id_obligacion_financiera: int,
    id_composicion_obligacion: int,
    importe_aplicado: Decimal,
    remanente_no_aplicado: Decimal,
) -> str:
    return json.dumps(
        {
            "tipo": "pago_externo_impuesto_trasladado",
            "id_liquidacion_impuesto_trasladado": (
                id_liquidacion_impuesto_trasladado
            ),
            "id_persona": id_persona,
            "fecha_pago": fecha_pago.isoformat(),
            "importe_pagado": float(importe_pagado),
            "medio_pago": medio_pago,
            "referencia_comprobante": referencia_comprobante,
            "observaciones": observaciones,
            "id_relacion_generadora": id_relacion_generadora,
            "id_obligacion_financiera": id_obligacion_financiera,
            "id_composicion_obligacion": id_composicion_obligacion,
            "importe_aplicado": float(importe_aplicado),
            "remanente_no_aplicado": float(remanente_no_aplicado),
        },
        separators=(",", ":"),
    )


def _payload_equivalente(
    payload: dict[str, Any] | None,
    *,
    id_liquidacion_impuesto_trasladado: int,
    id_persona: int | None,
    fecha_pago: date,
    importe_pagado: Decimal,
    medio_pago: str,
    referencia_comprobante: str | None,
    observaciones: str | None,
) -> bool:
    if payload is None or payload.get("tipo") != "pago_externo_impuesto_trasladado":
        return False
    try:
        payload_fecha = date.fromisoformat(str(payload["fecha_pago"]))
        payload_importe = Decimal(str(payload["importe_pagado"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        payload_liquidacion = int(payload["id_liquidacion_impuesto_trasladado"])
        payload_persona = int(payload["id_persona"])
    except (KeyError, TypeError, ValueError):
        return False
    persona_equivalente = id_persona is None or payload_persona == id_persona
    return (
        payload_liquidacion == id_liquidacion_impuesto_trasladado
        and persona_equivalente
        and payload_fecha == fecha_pago
        and payload_importe == importe_pagado
        and payload.get("medio_pago") == medio_pago
        and payload.get("referencia_comprobante") == referencia_comprobante
        and payload.get("observaciones") == observaciones
    )


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[Any]) -> None:
        self.result = result
