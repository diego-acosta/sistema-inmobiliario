from __future__ import annotations

import json
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.financiero.services.materializar_factura_servicio_service import (
    CONCEPTO_SERVICIO_TRASLADADO,
    TIPO_ORIGEN_FACTURA_SERVICIO,
)


TIPO_PAGO_EXTERNO_INFORMADO = "PAGO_EXTERNO_INFORMADO"
_Q = Decimal("0.01")


@dataclass(slots=True)
class PagoExternoFacturaServicioPayload:
    uid_global_movimiento: str
    uid_global_aplicacion: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    id_factura_servicio: int
    id_relacion_generadora: int
    id_obligacion_financiera: int
    id_composicion_obligacion: int
    fecha_pago: date
    monto_ingresado: Decimal
    monto_aplicado: Decimal
    remanente_no_aplicado: Decimal
    referencia_pago: str | None
    medio_pago_externo: str
    observaciones_usuario: str | None
    observaciones: str


class FinancieroRepository(Protocol):
    db: Any

    def get_factura_servicio_para_materializar(
        self, id_factura_servicio: int
    ) -> dict[str, Any] | None: ...

    def get_relacion_generadora_by_origen(
        self, tipo_origen: str, id_origen: int
    ) -> dict[str, Any] | None: ...

    def get_obligacion_activa_by_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> dict[str, Any] | None: ...

    def get_composicion_servicio_trasladado_con_saldo(
        self, id_obligacion_financiera: int
    ) -> dict[str, Any] | None: ...

    def get_obligados_activos_by_obligacion(
        self, id_obligacion_financiera: int
    ) -> list[dict[str, Any]]: ...

    def get_pago_externo_factura_servicio_by_op_id(
        self, *, op_id: UUID
    ) -> dict[str, Any] | None: ...

    def registrar_pago_externo_factura_servicio(
        self, payload: PagoExternoFacturaServicioPayload
    ) -> dict[str, Any]: ...


class RegistrarPagoExternoFacturaServicioService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self,
        *,
        id_factura_servicio: int,
        fecha_pago: date,
        importe_pagado: float,
        referencia_pago: str | None,
        medio_pago_externo: str,
        observaciones: str | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        try:
            with self._transaction():
                return self._execute_in_transaction(
                    id_factura_servicio=id_factura_servicio,
                    fecha_pago=fecha_pago,
                    importe_pagado=importe_pagado,
                    referencia_pago=referencia_pago,
                    medio_pago_externo=medio_pago_externo,
                    observaciones=observaciones,
                    context=context,
                )
        except _RollbackAppResult as exc:
            return exc.result

    def _execute_in_transaction(
        self,
        *,
        id_factura_servicio: int,
        fecha_pago: date,
        importe_pagado: float,
        referencia_pago: str | None,
        medio_pago_externo: str,
        observaciones: str | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        monto = Decimal(str(importe_pagado)).quantize(_Q, rounding=ROUND_HALF_UP)
        if monto <= 0:
            return AppResult.fail("MONTO_INVALIDO")

        op_id = getattr(context, "op_id", None)
        if op_id is not None:
            existente = self.repository.get_pago_externo_factura_servicio_by_op_id(
                op_id=op_id
            )
            if existente is not None:
                payload_existente = existente.get("payload_idempotencia")
                if not _payload_equivalente(
                    payload_existente,
                    id_factura_servicio=id_factura_servicio,
                    fecha_pago=fecha_pago,
                    importe_pagado=monto,
                    referencia_pago=referencia_pago,
                    medio_pago_externo=medio_pago_externo,
                    observaciones=observaciones,
                ):
                    return AppResult.fail("IDEMPOTENCY_PAYLOAD_CONFLICT")
                existente["resultado"] = "YA_REGISTRADO"
                return AppResult.ok(existente)

        factura = self.repository.get_factura_servicio_para_materializar(
            id_factura_servicio
        )
        if factura is None:
            return AppResult.fail("NOT_FOUND_FACTURA_SERVICIO")
        if (factura.get("estado_factura_servicio") or "").strip().upper() != "REGISTRADA":
            return AppResult.fail("FACTURA_SERVICIO_NO_ACTIVA")

        relacion = self.repository.get_relacion_generadora_by_origen(
            TIPO_ORIGEN_FACTURA_SERVICIO,
            id_factura_servicio,
        )
        if relacion is None:
            return AppResult.fail("FACTURA_SERVICIO_NO_MATERIALIZADA")

        id_relacion_generadora = relacion["id_relacion_generadora"]
        obligacion = self.repository.get_obligacion_activa_by_relacion_generadora(
            id_relacion_generadora
        )
        if obligacion is None:
            return AppResult.fail("FACTURA_SERVICIO_NO_MATERIALIZADA")

        id_obligacion = obligacion["id_obligacion_financiera"]
        obligados = self.repository.get_obligados_activos_by_obligacion(id_obligacion)
        if len(obligados) != 1:
            return AppResult.fail("PAGO_EXTERNO_REQUIERE_RESPONSABLE_UNICO")
        porcentaje = Decimal(str(obligados[0]["porcentaje_responsabilidad"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        if porcentaje != Decimal("100.00"):
            return AppResult.fail("PAGO_EXTERNO_REQUIERE_RESPONSABLE_UNICO")

        composicion = self.repository.get_composicion_servicio_trasladado_con_saldo(
            id_obligacion
        )
        if composicion is None:
            return AppResult.fail("SIN_SALDO_APLICABLE")

        saldo = Decimal(str(composicion["saldo_componente"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        if saldo <= 0:
            return AppResult.fail("SIN_SALDO_APLICABLE")

        monto_aplicado = min(monto, saldo).quantize(_Q, rounding=ROUND_HALF_UP)
        remanente = (monto - monto_aplicado).quantize(_Q, rounding=ROUND_HALF_UP)
        now = datetime.now(UTC)
        id_instalacion = getattr(context, "id_instalacion", None)
        payload_json = _build_payload_idempotencia(
            id_factura_servicio=id_factura_servicio,
            fecha_pago=fecha_pago,
            importe_pagado=monto,
            referencia_pago=referencia_pago,
            medio_pago_externo=medio_pago_externo,
            observaciones=observaciones,
            id_relacion_generadora=id_relacion_generadora,
            id_obligacion_financiera=id_obligacion,
            id_composicion_obligacion=composicion["id_composicion_obligacion"],
            monto_aplicado=monto_aplicado,
            remanente_no_aplicado=remanente,
        )

        registrado = self.repository.registrar_pago_externo_factura_servicio(
            PagoExternoFacturaServicioPayload(
                uid_global_movimiento=str(self.uuid_generator()),
                uid_global_aplicacion=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
                id_factura_servicio=id_factura_servicio,
                id_relacion_generadora=id_relacion_generadora,
                id_obligacion_financiera=id_obligacion,
                id_composicion_obligacion=composicion["id_composicion_obligacion"],
                fecha_pago=fecha_pago,
                monto_ingresado=monto,
                monto_aplicado=monto_aplicado,
                remanente_no_aplicado=remanente,
                referencia_pago=referencia_pago,
                medio_pago_externo=medio_pago_externo,
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
    fecha_pago: date,
    importe_pagado: Decimal,
    referencia_pago: str | None,
    medio_pago_externo: str,
    observaciones: str | None,
    id_relacion_generadora: int,
    id_obligacion_financiera: int,
    id_composicion_obligacion: int,
    monto_aplicado: Decimal,
    remanente_no_aplicado: Decimal,
) -> str:
    return json.dumps(
        {
            "tipo": "pago_externo_factura_servicio",
            "id_factura_servicio": id_factura_servicio,
            "fecha_pago": fecha_pago.isoformat(),
            "importe_pagado": float(importe_pagado),
            "referencia_pago": referencia_pago,
            "medio_pago_externo": medio_pago_externo,
            "observaciones": observaciones,
            "id_relacion_generadora": id_relacion_generadora,
            "id_obligacion_financiera": id_obligacion_financiera,
            "id_composicion_obligacion": id_composicion_obligacion,
            "monto_aplicado": float(monto_aplicado),
            "remanente_no_aplicado": float(remanente_no_aplicado),
        },
        separators=(",", ":"),
    )


def _payload_equivalente(
    payload: dict[str, Any] | None,
    *,
    id_factura_servicio: int,
    fecha_pago: date,
    importe_pagado: Decimal,
    referencia_pago: str | None,
    medio_pago_externo: str,
    observaciones: str | None,
) -> bool:
    if payload is None or payload.get("tipo") != "pago_externo_factura_servicio":
        return False
    try:
        payload_fecha = date.fromisoformat(str(payload["fecha_pago"]))
        payload_importe = Decimal(str(payload["importe_pagado"])).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        payload_factura = int(payload["id_factura_servicio"])
    except (KeyError, TypeError, ValueError):
        return False
    return (
        payload_factura == id_factura_servicio
        and payload_fecha == fecha_pago
        and payload_importe == importe_pagado
        and payload.get("referencia_pago") == referencia_pago
        and payload.get("medio_pago_externo") == medio_pago_externo
        and payload.get("observaciones") == observaciones
    )


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[Any]) -> None:
        self.result = result
