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


TIPO_ORIGEN_LIQUIDACION_IMPUESTO = "liquidacion_impuesto_trasladado"
CONCEPTO_IMPUESTO_TRASLADADO = "IMPUESTO_TRASLADADO"
ROL_OBLIGADO_IMPUESTO = "RESPONSABLE_IMPUESTO_TRASLADADO"
MODALIDAD_EMPRESA_ASUME = "EMPRESA_ASUME"
MODALIDAD_DIRECTO_RESPONSABLE = "DIRECTO_RESPONSABLE"
MODALIDAD_EMPRESA_PAGA_Y_RECUPERA = "EMPRESA_PAGA_Y_RECUPERA"
_Q = Decimal("0.01")
_PCT_Q = Decimal("0.01")


@dataclass(slots=True)
class ResponsableImpuestoInput:
    id_persona: int
    porcentaje_responsabilidad: Decimal
    importe_responsable: Decimal
    origen_responsable: str


@dataclass(slots=True)
class LiquidacionImpuestoPayload:
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
    codigo_liquidacion_impuesto_trasladado: str
    id_comprobante_impuesto: int
    modalidad_gestion_impuesto: str
    fecha_liquidacion: date
    fecha_vencimiento: date
    importe_total_base: Decimal
    importe_total_trasladar: Decimal
    importe_absorbido_empresa: Decimal
    id_concepto_financiero: int
    codigo_concepto_financiero: str
    comprobante: dict[str, Any]
    egresos: list[dict[str, Any]]
    responsables: list[ResponsableImpuestoInput]
    observaciones: str


class FinancieroRepository(Protocol):
    db: Any

    def get_comprobante_impuesto(
        self, id_comprobante_impuesto: int
    ) -> dict[str, Any] | None: ...

    def get_concepto_financiero_by_codigo(
        self, codigo: str
    ) -> dict[str, Any] | None: ...

    def persona_exists(self, id_persona: int) -> bool: ...

    def list_egresos_impuesto_disponibles_para_liquidacion(
        self, id_comprobante_impuesto: int
    ) -> list[dict[str, Any]]: ...

    def get_total_egresos_impuesto_empresa(
        self, id_comprobante_impuesto: int
    ) -> Decimal: ...

    def get_liquidacion_impuesto_trasladado_by_op_id(
        self, *, op_id: UUID
    ) -> dict[str, Any] | None: ...

    def create_relacion_generadora(
        self, payload: RelacionGeneradoraCreatePayload
    ) -> dict[str, Any]: ...

    def crear_liquidacion_impuesto_trasladado(
        self, payload: LiquidacionImpuestoPayload
    ) -> dict[str, Any]: ...

    def completar_liquidacion_impuesto_trasladado_financiera(
        self,
        *,
        id_liquidacion_impuesto_trasladado: int,
        id_relacion_generadora: int,
        payload: LiquidacionImpuestoPayload,
    ) -> None: ...

    def get_liquidacion_impuesto_trasladado_by_id(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> dict[str, Any] | None: ...


class LiquidarImpuestoTrasladadoService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self,
        *,
        id_comprobante_impuesto: int,
        fecha_liquidacion: date,
        fecha_vencimiento: date,
        importe_total_trasladar: float,
        responsables: list[dict[str, Any]],
        observaciones: str | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        try:
            with self._transaction():
                return self._execute_in_transaction(
                    id_comprobante_impuesto=id_comprobante_impuesto,
                    fecha_liquidacion=fecha_liquidacion,
                    fecha_vencimiento=fecha_vencimiento,
                    importe_total_trasladar=importe_total_trasladar,
                    responsables=responsables,
                    observaciones=observaciones,
                    context=context,
                )
        except _RollbackAppResult as exc:
            return exc.result

    def _execute_in_transaction(
        self,
        *,
        id_comprobante_impuesto: int,
        fecha_liquidacion: date,
        fecha_vencimiento: date,
        importe_total_trasladar: float,
        responsables: list[dict[str, Any]],
        observaciones: str | None,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        monto_trasladar = Decimal(str(importe_total_trasladar)).quantize(
            _Q, rounding=ROUND_HALF_UP
        )
        if monto_trasladar <= 0:
            return AppResult.fail("IMPORTE_TRASLADO_INVALIDO")
        if fecha_vencimiento < fecha_liquidacion:
            return AppResult.fail("FECHA_VENCIMIENTO_INVALIDA")
        if not responsables:
            return AppResult.fail("RESPONSABLES_REQUERIDOS")

        normalizados = self._normalizar_responsables(
            responsables=responsables,
            importe_total_trasladar=monto_trasladar,
        )
        if not normalizados.success:
            return normalizados

        op_id = getattr(context, "op_id", None)
        payload_idempotencia = _build_payload_idempotencia(
            id_comprobante_impuesto=id_comprobante_impuesto,
            fecha_liquidacion=fecha_liquidacion,
            fecha_vencimiento=fecha_vencimiento,
            importe_total_trasladar=monto_trasladar,
            responsables=normalizados.data or [],
            observaciones=observaciones,
        )
        if op_id is not None:
            existente = self.repository.get_liquidacion_impuesto_trasladado_by_op_id(
                op_id=op_id
            )
            if existente is not None:
                if not _payload_equivalente(
                    existente.get("payload_idempotencia"), payload_idempotencia
                ):
                    return AppResult.fail("IDEMPOTENCY_PAYLOAD_CONFLICT")
                existente["resultado"] = "YA_EMITIDA"
                return AppResult.ok(existente)

        comprobante = self.repository.get_comprobante_impuesto(id_comprobante_impuesto)
        if comprobante is None:
            return AppResult.fail("COMPROBANTE_IMPUESTO_NOT_FOUND")
        if (
            comprobante.get("estado_comprobante_impuesto") or ""
        ).strip().upper() != "REGISTRADO":
            return AppResult.fail("COMPROBANTE_IMPUESTO_ANULADO")

        modalidad = (comprobante.get("modalidad_gestion_impuesto") or "").strip().upper()
        if modalidad == MODALIDAD_EMPRESA_ASUME:
            return AppResult.fail("IMPUESTO_EMPRESA_ASUME_NO_TRASLADABLE")
        if modalidad not in {MODALIDAD_DIRECTO_RESPONSABLE, MODALIDAD_EMPRESA_PAGA_Y_RECUPERA}:
            return AppResult.fail("MODALIDAD_IMPUESTO_INVALIDA")

        for responsable in normalizados.data or []:
            if not self.repository.persona_exists(responsable.id_persona):
                return AppResult.fail("RESPONSABLE_PERSONA_NOT_FOUND")

        concepto = self.repository.get_concepto_financiero_by_codigo(
            CONCEPTO_IMPUESTO_TRASLADADO
        )
        if concepto is None:
            return AppResult.fail("CONCEPTO_IMPUESTO_TRASLADADO_NO_EXISTE")

        egresos: list[dict[str, Any]] = []
        if modalidad == MODALIDAD_DIRECTO_RESPONSABLE:
            importe_base = Decimal(str(comprobante["importe_total"])).quantize(
                _Q, rounding=ROUND_HALF_UP
            )
            if monto_trasladar > importe_base:
                return AppResult.fail("IMPORTE_TRASLADO_INVALIDO")
        else:
            egresos = self.repository.list_egresos_impuesto_disponibles_para_liquidacion(
                id_comprobante_impuesto
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
                total_registrado = self.repository.get_total_egresos_impuesto_empresa(
                    id_comprobante_impuesto
                ).quantize(_Q, rounding=ROUND_HALF_UP)
                if total_registrado > 0:
                    return AppResult.fail("EGRESO_IMPUESTO_NO_DISPONIBLE")
                return AppResult.fail("EGRESO_IMPUESTO_REQUERIDO")
            importe_base = total_disponible
            if monto_trasladar > importe_base:
                return AppResult.fail("IMPORTE_TRASLADO_SUPERA_EGRESADO")

        now = datetime.now(UTC)
        id_instalacion = getattr(context, "id_instalacion", None)
        codigo = _codigo_liquidacion(fecha_liquidacion, self.uuid_generator)
        payload = LiquidacionImpuestoPayload(
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
            codigo_liquidacion_impuesto_trasladado=codigo,
            id_comprobante_impuesto=id_comprobante_impuesto,
            modalidad_gestion_impuesto=modalidad,
            fecha_liquidacion=fecha_liquidacion,
            fecha_vencimiento=fecha_vencimiento,
            importe_total_base=importe_base,
            importe_total_trasladar=monto_trasladar,
            importe_absorbido_empresa=(importe_base - monto_trasladar).quantize(
                _Q, rounding=ROUND_HALF_UP
            ),
            id_concepto_financiero=concepto["id_concepto_financiero"],
            codigo_concepto_financiero=CONCEPTO_IMPUESTO_TRASLADADO,
            comprobante=comprobante,
            egresos=egresos,
            responsables=normalizados.data or [],
            observaciones=payload_idempotencia,
        )
        liquidacion = self.repository.crear_liquidacion_impuesto_trasladado(payload)
        relacion = self.repository.create_relacion_generadora(
            RelacionGeneradoraCreatePayload(
                tipo_origen=TIPO_ORIGEN_LIQUIDACION_IMPUESTO,
                id_origen=liquidacion["id_liquidacion_impuesto_trasladado"],
                descripcion=(
                    "Relacion generadora creada desde "
                    "liquidacion_impuesto_trasladado"
                ),
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
        self.repository.completar_liquidacion_impuesto_trasladado_financiera(
            id_liquidacion_impuesto_trasladado=liquidacion[
                "id_liquidacion_impuesto_trasladado"
            ],
            id_relacion_generadora=relacion["id_relacion_generadora"],
            payload=payload,
        )
        creada = self.repository.get_liquidacion_impuesto_trasladado_by_id(
            liquidacion["id_liquidacion_impuesto_trasladado"]
        )
        if creada is None:
            raise _RollbackAppResult(
                AppResult.fail("LIQUIDACION_IMPUESTO_TRASLADADO_NOT_FOUND")
            )
        creada["resultado"] = "EMITIDA"
        return AppResult.ok(creada)

    def _normalizar_responsables(
        self, *, responsables: list[dict[str, Any]], importe_total_trasladar: Decimal
    ) -> AppResult[list[ResponsableImpuestoInput]]:
        total_pct = Decimal("0.00")
        normalizados: list[ResponsableImpuestoInput] = []
        ids: set[int] = set()
        for item in responsables:
            try:
                id_persona = int(item["id_persona"])
                pct = Decimal(str(item["porcentaje_responsabilidad"])).quantize(
                    _PCT_Q, rounding=ROUND_HALF_UP
                )
            except (KeyError, TypeError, ValueError):
                return AppResult.fail("PORCENTAJES_RESPONSABLES_INVALIDOS")
            if id_persona <= 0 or pct <= 0 or pct > 100:
                return AppResult.fail("PORCENTAJES_RESPONSABLES_INVALIDOS")
            if id_persona in ids:
                return AppResult.fail("PORCENTAJES_RESPONSABLES_INVALIDOS")
            ids.add(id_persona)
            total_pct += pct
            normalizados.append(
                ResponsableImpuestoInput(
                    id_persona=id_persona,
                    porcentaje_responsabilidad=pct,
                    importe_responsable=Decimal("0.00"),
                    origen_responsable=str(item.get("origen_responsable") or "MANUAL"),
                )
            )
        if total_pct != Decimal("100.00"):
            return AppResult.fail("PORCENTAJES_RESPONSABLES_INVALIDOS")

        acumulado = Decimal("0.00")
        calculados: list[ResponsableImpuestoInput] = []
        for idx, item in enumerate(normalizados):
            if idx == len(normalizados) - 1:
                importe = (importe_total_trasladar - acumulado).quantize(
                    _Q, rounding=ROUND_HALF_UP
                )
            else:
                importe = (
                    importe_total_trasladar * item.porcentaje_responsabilidad / 100
                ).quantize(_Q, rounding=ROUND_HALF_UP)
                acumulado += importe
            calculados.append(
                ResponsableImpuestoInput(
                    id_persona=item.id_persona,
                    porcentaje_responsabilidad=item.porcentaje_responsabilidad,
                    importe_responsable=importe,
                    origen_responsable=item.origen_responsable,
                )
            )
        return AppResult.ok(calculados)

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()


def _build_payload_idempotencia(
    *,
    id_comprobante_impuesto: int,
    fecha_liquidacion: date,
    fecha_vencimiento: date,
    importe_total_trasladar: Decimal,
    responsables: list[ResponsableImpuestoInput],
    observaciones: str | None,
) -> str:
    return json.dumps(
        {
            "tipo": "liquidacion_impuesto_trasladado",
            "id_comprobante_impuesto": id_comprobante_impuesto,
            "fecha_liquidacion": fecha_liquidacion.isoformat(),
            "fecha_vencimiento": fecha_vencimiento.isoformat(),
            "importe_total_trasladar": float(importe_total_trasladar),
            "responsables": [
                {
                    "id_persona": r.id_persona,
                    "porcentaje_responsabilidad": float(r.porcentaje_responsabilidad),
                    "importe_responsable": float(r.importe_responsable),
                    "origen_responsable": r.origen_responsable,
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
    if (
        payload_existente is None
        or payload_existente.get("tipo") != "liquidacion_impuesto_trasladado"
    ):
        return False
    try:
        actual = json.loads(payload_actual)
    except (TypeError, ValueError):
        return False
    return payload_existente == actual


def _codigo_liquidacion(fecha_liquidacion: date, uuid_generator: Any) -> str:
    return f"IMP-{fecha_liquidacion:%Y%m%d}-{str(uuid_generator())[:8].upper()}"


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[Any]) -> None:
        self.result = result
