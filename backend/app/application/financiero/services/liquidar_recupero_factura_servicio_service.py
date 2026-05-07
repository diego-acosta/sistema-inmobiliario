from __future__ import annotations

import json
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.financiero.services.create_relacion_generadora_service import (
    RelacionGeneradoraCreatePayload,
)


TIPO_ORIGEN_LIQUIDACION_RECUPERO = "liquidacion_recupero"
CONCEPTO_SERVICIO_RECUPERADO = "SERVICIO_RECUPERADO"
ROL_OBLIGADO_RECUPERO = "RESPONSABLE_RECUPERO"
_Q = Decimal("0.01")
_PCT_Q = Decimal("0.01")


@dataclass(slots=True)
class ResponsableRecuperoInput:
    id_persona: int
    porcentaje_responsabilidad: Decimal
    importe_responsable: Decimal
    origen_responsable: str
    id_asignacion_servicio_responsable: int | None


@dataclass(slots=True)
class LiquidacionRecuperoPayload:
    uid_global_liquidacion: str
    uid_global_obligacion: str
    uid_global_composicion: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    codigo_liquidacion_recupero: str
    fecha_liquidacion: date
    fecha_vencimiento: date
    id_factura_servicio: int
    importe_total_egresado_base: Decimal
    importe_total_recuperar: Decimal
    importe_absorbido_empresa: Decimal
    id_concepto_financiero: int
    codigo_concepto_financiero: str
    egresos: list[dict[str, Any]]
    responsables: list[ResponsableRecuperoInput]
    observaciones: str


class FinancieroRepository(Protocol):
    db: Any

    def get_factura_servicio_para_materializar(
        self, id_factura_servicio: int
    ) -> dict[str, Any] | None: ...

    def get_concepto_financiero_by_codigo(
        self, codigo: str
    ) -> dict[str, Any] | None: ...

    def persona_exists(self, id_persona: int) -> bool: ...

    def get_total_egresos_proveedor_factura_servicio(
        self, id_factura_servicio: int
    ) -> Decimal: ...

    def list_egresos_proveedor_disponibles_para_recupero(
        self, id_factura_servicio: int
    ) -> list[dict[str, Any]]: ...

    def get_liquidacion_recupero_by_op_id(
        self, *, op_id: UUID
    ) -> dict[str, Any] | None: ...

    def create_relacion_generadora(
        self, payload: RelacionGeneradoraCreatePayload
    ) -> dict[str, Any]: ...

    def crear_liquidacion_recupero(
        self, payload: LiquidacionRecuperoPayload
    ) -> dict[str, Any]: ...

    def completar_liquidacion_recupero_financiera(
        self,
        *,
        id_liquidacion_recupero: int,
        id_relacion_generadora: int,
        payload: LiquidacionRecuperoPayload,
    ) -> None: ...

    def get_liquidacion_recupero_by_id(
        self, id_liquidacion_recupero: int
    ) -> dict[str, Any] | None: ...


class LiquidarRecuperoFacturaServicioService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self,
        *,
        id_factura_servicio: int,
        fecha_liquidacion: date,
        fecha_vencimiento: date,
        importe_total_recuperar: float,
        responsables: list[dict[str, Any]],
        observaciones: str | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        try:
            with self._transaction():
                return self._execute_in_transaction(
                    id_factura_servicio=id_factura_servicio,
                    fecha_liquidacion=fecha_liquidacion,
                    fecha_vencimiento=fecha_vencimiento,
                    importe_total_recuperar=importe_total_recuperar,
                    responsables=responsables,
                    observaciones=observaciones,
                    context=context,
                )
        except _RollbackAppResult as exc:
            return exc.result

    def _execute_in_transaction(
        self,
        *,
        id_factura_servicio: int,
        fecha_liquidacion: date,
        fecha_vencimiento: date,
        importe_total_recuperar: float,
        responsables: list[dict[str, Any]],
        observaciones: str | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        monto_recuperar = Decimal(str(importe_total_recuperar)).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        if monto_recuperar <= 0:
            return AppResult.fail("IMPORTE_RECUPERO_INVALIDO")
        if fecha_vencimiento < fecha_liquidacion:
            return AppResult.fail("FECHA_VENCIMIENTO_INVALIDA")
        if not responsables:
            return AppResult.fail("RESPONSABLES_REQUERIDOS")

        normalizados = self._normalizar_responsables(
            responsables=responsables,
            importe_total_recuperar=monto_recuperar,
        )
        if not normalizados.success:
            return normalizados

        op_id = getattr(context, "op_id", None)
        payload_idempotencia = _build_payload_idempotencia(
            id_factura_servicio=id_factura_servicio,
            fecha_liquidacion=fecha_liquidacion,
            fecha_vencimiento=fecha_vencimiento,
            importe_total_recuperar=monto_recuperar,
            responsables=normalizados.data or [],
            observaciones=observaciones,
        )
        if op_id is not None:
            existente = self.repository.get_liquidacion_recupero_by_op_id(op_id=op_id)
            if existente is not None:
                if not _payload_equivalente(
                    existente.get("payload_idempotencia"), payload_idempotencia
                ):
                    return AppResult.fail("IDEMPOTENCY_PAYLOAD_CONFLICT")
                existente["resultado"] = "YA_EMITIDA"
                return AppResult.ok(existente)

        factura = self.repository.get_factura_servicio_para_materializar(
            id_factura_servicio
        )
        if factura is None:
            return AppResult.fail("FACTURA_SERVICIO_NOT_FOUND")
        if (factura.get("estado_factura_servicio") or "").strip().upper() != "REGISTRADA":
            return AppResult.fail("FACTURA_SERVICIO_ANULADA")

        for responsable in normalizados.data or []:
            if not self.repository.persona_exists(responsable.id_persona):
                return AppResult.fail("RESPONSABLE_PERSONA_NOT_FOUND")

        concepto = self.repository.get_concepto_financiero_by_codigo(
            CONCEPTO_SERVICIO_RECUPERADO
        )
        if concepto is None:
            return AppResult.fail("CONCEPTO_SERVICIO_RECUPERADO_NO_EXISTE")

        total_egresado_registrado = self.repository.get_total_egresos_proveedor_factura_servicio(
            id_factura_servicio
        ).quantize(_Q, rounding=ROUND_HALF_UP)
        if total_egresado_registrado <= 0:
            return AppResult.fail("EGRESO_PROVEEDOR_REQUERIDO")

        egresos = self.repository.list_egresos_proveedor_disponibles_para_recupero(
            id_factura_servicio
        )
        total_disponible = sum(
            (
                Decimal(str(egreso["importe_pagado"])).quantize(
                    _Q, rounding=ROUND_HALF_UP
                )
                for egreso in egresos
            ),
            Decimal("0.00"),
        ).quantize(_Q, rounding=ROUND_HALF_UP)
        if total_disponible <= 0:
            return AppResult.fail("SIN_MONTO_EGRESADO_DISPONIBLE")
        if monto_recuperar > total_disponible:
            return AppResult.fail("IMPORTE_RECUPERO_SUPERA_EGRESADO")

        now = datetime.now(UTC)
        id_instalacion = getattr(context, "id_instalacion", None)
        codigo = _codigo_liquidacion(fecha_liquidacion, self.uuid_generator)
        payload = LiquidacionRecuperoPayload(
            uid_global_liquidacion=str(self.uuid_generator()),
            uid_global_obligacion=str(self.uuid_generator()),
            uid_global_composicion=str(self.uuid_generator()),
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
            codigo_liquidacion_recupero=codigo,
            fecha_liquidacion=fecha_liquidacion,
            fecha_vencimiento=fecha_vencimiento,
            id_factura_servicio=id_factura_servicio,
            importe_total_egresado_base=total_disponible,
            importe_total_recuperar=monto_recuperar,
            importe_absorbido_empresa=(total_disponible - monto_recuperar).quantize(
                _Q, rounding=ROUND_HALF_UP
            ),
            id_concepto_financiero=concepto["id_concepto_financiero"],
            codigo_concepto_financiero=CONCEPTO_SERVICIO_RECUPERADO,
            egresos=egresos,
            responsables=normalizados.data or [],
            observaciones=payload_idempotencia,
        )
        liquidacion = self.repository.crear_liquidacion_recupero(payload)

        relacion = self.repository.create_relacion_generadora(
            RelacionGeneradoraCreatePayload(
                tipo_origen=TIPO_ORIGEN_LIQUIDACION_RECUPERO,
                id_origen=liquidacion["id_liquidacion_recupero"],
                descripcion="Relacion generadora creada desde liquidacion_recupero",
                uid_global=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
        )
        self.repository.completar_liquidacion_recupero_financiera(
            id_liquidacion_recupero=liquidacion["id_liquidacion_recupero"],
            id_relacion_generadora=relacion["id_relacion_generadora"],
            payload=payload,
        )
        creada = self.repository.get_liquidacion_recupero_by_id(
            liquidacion["id_liquidacion_recupero"]
        )
        if creada is None:
            raise _RollbackAppResult(AppResult.fail("LIQUIDACION_RECUPERO_NOT_FOUND"))
        creada["resultado"] = "EMITIDA"
        return AppResult.ok(creada)

    def _normalizar_responsables(
        self, *, responsables: list[dict[str, Any]], importe_total_recuperar: Decimal
    ) -> AppResult[list[ResponsableRecuperoInput]]:
        total_pct = Decimal("0.00")
        normalizados: list[ResponsableRecuperoInput] = []
        ids: set[int] = set()
        for item in responsables:
            try:
                id_persona = int(item["id_persona"])
                pct = Decimal(str(item["porcentaje_responsabilidad"])).quantize(
                    _PCT_Q, rounding=ROUND_HALF_UP
                )
            except (KeyError, TypeError, ValueError):
                return AppResult.fail("RESPONSABLES_PORCENTAJE_INVALIDO")
            if id_persona <= 0 or pct <= 0 or pct > 100:
                return AppResult.fail("RESPONSABLES_PORCENTAJE_INVALIDO")
            if id_persona in ids:
                return AppResult.fail("RESPONSABLES_DUPLICADOS")
            ids.add(id_persona)
            total_pct += pct
            normalizados.append(
                ResponsableRecuperoInput(
                    id_persona=id_persona,
                    porcentaje_responsabilidad=pct,
                    importe_responsable=Decimal("0.00"),
                    origen_responsable=str(item.get("origen_responsable") or "MANUAL"),
                    id_asignacion_servicio_responsable=item.get(
                        "id_asignacion_servicio_responsable"
                    ),
                )
            )
        if total_pct != Decimal("100.00"):
            return AppResult.fail("RESPONSABLES_SUMA_DISTINTA_100")

        acumulado = Decimal("0.00")
        calculados: list[ResponsableRecuperoInput] = []
        for idx, item in enumerate(normalizados):
            if idx == len(normalizados) - 1:
                importe = (importe_total_recuperar - acumulado).quantize(
                    _Q, rounding=ROUND_HALF_UP
                )
            else:
                importe = (importe_total_recuperar * item.porcentaje_responsabilidad / 100).quantize(
                    _Q, rounding=ROUND_HALF_UP
                )
                acumulado += importe
            calculados.append(
                ResponsableRecuperoInput(
                    id_persona=item.id_persona,
                    porcentaje_responsabilidad=item.porcentaje_responsabilidad,
                    importe_responsable=importe,
                    origen_responsable=item.origen_responsable,
                    id_asignacion_servicio_responsable=item.id_asignacion_servicio_responsable,
                )
            )
        return AppResult.ok(calculados)

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()


def _build_payload_idempotencia(
    *,
    id_factura_servicio: int,
    fecha_liquidacion: date,
    fecha_vencimiento: date,
    importe_total_recuperar: Decimal,
    responsables: list[ResponsableRecuperoInput],
    observaciones: str | None,
) -> str:
    return json.dumps(
        {
            "tipo": "liquidacion_recupero",
            "id_factura_servicio": id_factura_servicio,
            "fecha_liquidacion": fecha_liquidacion.isoformat(),
            "fecha_vencimiento": fecha_vencimiento.isoformat(),
            "importe_total_recuperar": float(importe_total_recuperar),
            "responsables": [
                {
                    "id_persona": r.id_persona,
                    "porcentaje_responsabilidad": float(r.porcentaje_responsabilidad),
                    "importe_responsable": float(r.importe_responsable),
                    "origen_responsable": r.origen_responsable,
                    "id_asignacion_servicio_responsable": r.id_asignacion_servicio_responsable,
                }
                for r in responsables
            ],
            "observaciones": observaciones,
        },
        separators=(",", ":"),
        sort_keys=True,
    )


def _payload_equivalente(
    payload_existente: dict[str, Any] | None, payload_actual: str
) -> bool:
    if payload_existente is None or payload_existente.get("tipo") != "liquidacion_recupero":
        return False
    try:
        actual = json.loads(payload_actual)
    except (TypeError, ValueError):
        return False
    return payload_existente == actual


def _codigo_liquidacion(fecha_liquidacion: date, uuid_generator: Any) -> str:
    return f"REC-{fecha_liquidacion:%Y%m%d}-{str(uuid_generator())[:8].upper()}"


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[Any]) -> None:
        self.result = result
