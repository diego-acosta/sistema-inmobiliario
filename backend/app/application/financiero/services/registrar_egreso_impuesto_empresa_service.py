from __future__ import annotations

import json
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult


TIPO_MOVIMIENTO_TESORERIA_EGRESO_IMPUESTO = "EGRESO_IMPUESTO_EMPRESA"
MODALIDADES_CON_EGRESO_EMPRESA = {"EMPRESA_ASUME", "EMPRESA_PAGA_Y_RECUPERA"}
_Q = Decimal("0.01")


@dataclass(slots=True)
class EgresoImpuestoEmpresaPayload:
    uid_global_movimiento_tesoreria: str
    uid_global_egreso: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    id_comprobante_impuesto: int
    id_cuenta_financiera_origen: int
    fecha_pago: date
    importe_pagado: Decimal
    medio_pago: str | None
    referencia_comprobante: str | None
    observaciones_usuario: str | None
    observaciones: str


class FinancieroRepository(Protocol):
    db: Any

    def get_comprobante_impuesto(
        self, id_comprobante_impuesto: int
    ) -> dict[str, Any] | None: ...

    def get_cuenta_financiera_by_id(
        self, id_cuenta_financiera: int
    ) -> dict[str, Any] | None: ...

    def get_total_egresos_impuesto_empresa(
        self, id_comprobante_impuesto: int
    ) -> Decimal: ...

    def get_egreso_impuesto_empresa_by_op_id(
        self, *, op_id: UUID
    ) -> dict[str, Any] | None: ...

    def registrar_egreso_impuesto_empresa(
        self, payload: EgresoImpuestoEmpresaPayload
    ) -> dict[str, Any]: ...


class RegistrarEgresoImpuestoEmpresaService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self,
        *,
        id_comprobante_impuesto: int,
        id_cuenta_financiera_origen: int,
        fecha_pago: date,
        importe_pagado: float,
        medio_pago: str | None,
        referencia_comprobante: str | None,
        observaciones: str | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        try:
            with self._transaction():
                return self._execute_in_transaction(
                    id_comprobante_impuesto=id_comprobante_impuesto,
                    id_cuenta_financiera_origen=id_cuenta_financiera_origen,
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
        id_comprobante_impuesto: int,
        id_cuenta_financiera_origen: int,
        fecha_pago: date,
        importe_pagado: float,
        medio_pago: str | None,
        referencia_comprobante: str | None,
        observaciones: str | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        monto = Decimal(str(importe_pagado)).quantize(_Q, rounding=ROUND_HALF_UP)
        if monto <= 0:
            return AppResult.fail("IMPORTE_INVALIDO")

        op_id = getattr(context, "op_id", None)
        if op_id is not None:
            existente = self.repository.get_egreso_impuesto_empresa_by_op_id(
                op_id=op_id
            )
            if existente is not None:
                if not _payload_equivalente(
                    existente.get("payload_idempotencia"),
                    id_comprobante_impuesto=id_comprobante_impuesto,
                    id_cuenta_financiera_origen=id_cuenta_financiera_origen,
                    fecha_pago=fecha_pago,
                    importe_pagado=monto,
                    medio_pago=medio_pago,
                    referencia_comprobante=referencia_comprobante,
                    observaciones=observaciones,
                ):
                    return AppResult.fail("IDEMPOTENCY_PAYLOAD_CONFLICT")
                existente["resultado"] = "YA_REGISTRADO"
                return AppResult.ok(existente)

        comprobante = self.repository.get_comprobante_impuesto(id_comprobante_impuesto)
        if comprobante is None:
            return AppResult.fail("COMPROBANTE_IMPUESTO_NOT_FOUND")
        if (
            comprobante.get("estado_comprobante_impuesto") or ""
        ).strip().upper() != "REGISTRADO":
            return AppResult.fail("COMPROBANTE_IMPUESTO_ANULADO")

        modalidad = (comprobante.get("modalidad_gestion_impuesto") or "").strip().upper()
        if modalidad not in MODALIDADES_CON_EGRESO_EMPRESA:
            return AppResult.fail("EGRESO_IMPUESTO_NO_APLICA_MODALIDAD")

        cuenta = self.repository.get_cuenta_financiera_by_id(id_cuenta_financiera_origen)
        if cuenta is None:
            return AppResult.fail("CUENTA_FINANCIERA_NOT_FOUND")
        if (cuenta.get("estado") or "").strip().upper() not in {"ACTIVA", "ACTIVO"}:
            return AppResult.fail("CUENTA_FINANCIERA_INACTIVA")

        total_comprobante = Decimal(str(comprobante["importe_total"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        total_egresado = self.repository.get_total_egresos_impuesto_empresa(
            id_comprobante_impuesto
        ).quantize(_Q, rounding=ROUND_HALF_UP)
        if total_egresado + monto > total_comprobante:
            return AppResult.fail("EGRESO_SUPERA_IMPORTE_COMPROBANTE")

        now = datetime.now(UTC)
        id_instalacion = getattr(context, "id_instalacion", None)
        payload_json = _build_payload_idempotencia(
            id_comprobante_impuesto=id_comprobante_impuesto,
            id_cuenta_financiera_origen=id_cuenta_financiera_origen,
            fecha_pago=fecha_pago,
            importe_pagado=monto,
            medio_pago=medio_pago,
            referencia_comprobante=referencia_comprobante,
            observaciones=observaciones,
            organismo=comprobante.get("organismo"),
            numero_comprobante=comprobante.get("numero_comprobante"),
        )

        registrado = self.repository.registrar_egreso_impuesto_empresa(
            EgresoImpuestoEmpresaPayload(
                uid_global_movimiento_tesoreria=str(self.uuid_generator()),
                uid_global_egreso=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
                id_comprobante_impuesto=id_comprobante_impuesto,
                id_cuenta_financiera_origen=id_cuenta_financiera_origen,
                fecha_pago=fecha_pago,
                importe_pagado=monto,
                medio_pago=medio_pago,
                referencia_comprobante=referencia_comprobante,
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


def _build_payload_idempotencia(
    *,
    id_comprobante_impuesto: int,
    id_cuenta_financiera_origen: int,
    fecha_pago: date,
    importe_pagado: Decimal,
    medio_pago: str | None,
    referencia_comprobante: str | None,
    observaciones: str | None,
    organismo: str | None,
    numero_comprobante: str | None,
) -> str:
    return json.dumps(
        {
            "tipo": "egreso_impuesto_empresa",
            "id_comprobante_impuesto": id_comprobante_impuesto,
            "id_cuenta_financiera_origen": id_cuenta_financiera_origen,
            "fecha_pago": fecha_pago.isoformat(),
            "importe_pagado": float(importe_pagado),
            "medio_pago": medio_pago,
            "referencia_comprobante": referencia_comprobante,
            "observaciones": observaciones,
            "organismo": organismo,
            "numero_comprobante": numero_comprobante,
        },
        separators=(",", ":"),
    )


def _payload_equivalente(
    payload: dict[str, Any] | None,
    *,
    id_comprobante_impuesto: int,
    id_cuenta_financiera_origen: int,
    fecha_pago: date,
    importe_pagado: Decimal,
    medio_pago: str | None,
    referencia_comprobante: str | None,
    observaciones: str | None,
) -> bool:
    if payload is None or payload.get("tipo") != "egreso_impuesto_empresa":
        return False
    try:
        payload_fecha = date.fromisoformat(str(payload["fecha_pago"]))
        payload_importe = Decimal(str(payload["importe_pagado"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        payload_comprobante = int(payload["id_comprobante_impuesto"])
        payload_cuenta = int(payload["id_cuenta_financiera_origen"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        payload_comprobante == id_comprobante_impuesto
        and payload_cuenta == id_cuenta_financiera_origen
        and payload_fecha == fecha_pago
        and payload_importe == importe_pagado
        and payload.get("medio_pago") == medio_pago
        and payload.get("referencia_comprobante") == referencia_comprobante
        and payload.get("observaciones") == observaciones
    )


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[dict[str, Any]]) -> None:
        self.result = result
