from __future__ import annotations

import json
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult


TIPO_MOVIMIENTO_TESORERIA_EGRESO_PROVEEDOR = "EGRESO_PROVEEDOR_FACTURA_SERVICIO"
_Q = Decimal("0.01")


@dataclass(slots=True)
class EgresoProveedorFacturaServicioPayload:
    uid_global_movimiento_tesoreria: str
    uid_global_egreso: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    id_factura_servicio: int
    id_cuenta_financiera_origen: int
    fecha_pago: date
    importe_pagado: Decimal
    medio_pago: str | None
    referencia_comprobante: str | None
    observaciones_usuario: str | None
    observaciones: str


class FinancieroRepository(Protocol):
    db: Any

    def get_factura_servicio_para_materializar(
        self, id_factura_servicio: int
    ) -> dict[str, Any] | None: ...

    def get_cuenta_financiera_by_id(
        self, id_cuenta_financiera: int
    ) -> dict[str, Any] | None: ...

    def get_total_egresos_proveedor_factura_servicio(
        self, id_factura_servicio: int
    ) -> Decimal: ...

    def get_egreso_proveedor_factura_servicio_by_op_id(
        self, *, op_id: UUID
    ) -> dict[str, Any] | None: ...

    def registrar_egreso_proveedor_factura_servicio(
        self, payload: EgresoProveedorFacturaServicioPayload
    ) -> dict[str, Any]: ...


class RegistrarEgresoProveedorFacturaServicioService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self,
        *,
        id_factura_servicio: int,
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
                    id_factura_servicio=id_factura_servicio,
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
        id_factura_servicio: int,
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
            existente = self.repository.get_egreso_proveedor_factura_servicio_by_op_id(
                op_id=op_id
            )
            if existente is not None:
                payload_existente = existente.get("payload_idempotencia")
                if not _payload_equivalente(
                    payload_existente,
                    id_factura_servicio=id_factura_servicio,
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

        factura = self.repository.get_factura_servicio_para_materializar(
            id_factura_servicio
        )
        if factura is None:
            return AppResult.fail("FACTURA_SERVICIO_NOT_FOUND")
        if (factura.get("estado_factura_servicio") or "").strip().upper() != "REGISTRADA":
            return AppResult.fail("FACTURA_SERVICIO_ANULADA")

        cuenta = self.repository.get_cuenta_financiera_by_id(id_cuenta_financiera_origen)
        if cuenta is None:
            return AppResult.fail("CUENTA_FINANCIERA_NOT_FOUND")
        if (cuenta.get("estado") or "").strip().upper() not in {"ACTIVA", "ACTIVO"}:
            return AppResult.fail("CUENTA_FINANCIERA_INACTIVA")

        total_factura = Decimal(str(factura["importe_total"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        total_egresos = self.repository.get_total_egresos_proveedor_factura_servicio(
            id_factura_servicio
        ).quantize(_Q, rounding=ROUND_HALF_UP)
        if total_egresos + monto > total_factura:
            return AppResult.fail("EGRESO_SUPERA_IMPORTE_FACTURA")

        now = datetime.now(UTC)
        id_instalacion = getattr(context, "id_instalacion", None)
        payload_json = _build_payload_idempotencia(
            id_factura_servicio=id_factura_servicio,
            id_cuenta_financiera_origen=id_cuenta_financiera_origen,
            fecha_pago=fecha_pago,
            importe_pagado=monto,
            medio_pago=medio_pago,
            referencia_comprobante=referencia_comprobante,
            observaciones=observaciones,
            proveedor=factura.get("proveedor"),
            numero_factura=factura.get("numero_factura"),
        )

        registrado = self.repository.registrar_egreso_proveedor_factura_servicio(
            EgresoProveedorFacturaServicioPayload(
                uid_global_movimiento_tesoreria=str(self.uuid_generator()),
                uid_global_egreso=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
                id_factura_servicio=id_factura_servicio,
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
    id_factura_servicio: int,
    id_cuenta_financiera_origen: int,
    fecha_pago: date,
    importe_pagado: Decimal,
    medio_pago: str | None,
    referencia_comprobante: str | None,
    observaciones: str | None,
    proveedor: str | None,
    numero_factura: str | None,
) -> str:
    return json.dumps(
        {
            "tipo": "egreso_proveedor_factura_servicio",
            "id_factura_servicio": id_factura_servicio,
            "id_cuenta_financiera_origen": id_cuenta_financiera_origen,
            "fecha_pago": fecha_pago.isoformat(),
            "importe_pagado": float(importe_pagado),
            "medio_pago": medio_pago,
            "referencia_comprobante": referencia_comprobante,
            "observaciones": observaciones,
            "proveedor": proveedor,
            "numero_factura": numero_factura,
        },
        separators=(",", ":"),
    )


def _payload_equivalente(
    payload: dict[str, Any] | None,
    *,
    id_factura_servicio: int,
    id_cuenta_financiera_origen: int,
    fecha_pago: date,
    importe_pagado: Decimal,
    medio_pago: str | None,
    referencia_comprobante: str | None,
    observaciones: str | None,
) -> bool:
    if payload is None or payload.get("tipo") != "egreso_proveedor_factura_servicio":
        return False
    try:
        payload_fecha = date.fromisoformat(str(payload["fecha_pago"]))
        payload_importe = Decimal(str(payload["importe_pagado"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        payload_factura = int(payload["id_factura_servicio"])
        payload_cuenta = int(payload["id_cuenta_financiera_origen"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        payload_factura == id_factura_servicio
        and payload_cuenta == id_cuenta_financiera_origen
        and payload_fecha == fecha_pago
        and payload_importe == importe_pagado
        and payload.get("medio_pago") == medio_pago
        and payload.get("referencia_comprobante") == referencia_comprobante
        and payload.get("observaciones") == observaciones
    )


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[Any]) -> None:
        self.result = result
