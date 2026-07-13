from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID

from app.api.core_ef_headers import CoreEFHeaders
from app.application.common.results import AppResult

Q2 = Decimal("0.01")
Q8 = Decimal("0.00000001")
ESTADO_ELEGIBLE = "ELEGIBLE"
ESTADO_EXCLUIDA = "EXCLUIDA"
ESTADO_PREVIEW_PERSISTIDO = "PREVISUALIZADA"
ORIGEN_REINDEXACION_MANUAL = "REINDEXACION_MANUAL"
ESTADOS_ELEGIBLES = {"PROYECTADA", "EMITIDA", "EXIGIBLE", "VENCIDA"}


@dataclass(frozen=True, slots=True)
class PreviewIndexacionCuotasV2Command:
    id_plan_pago_venta: int
    id_plan_pago_venta_bloque: int
    id_plan_pago_venta_bloque_indexacion: int
    id_indice_financiero: int
    id_indice_financiero_valor_aplicado: int
    fecha_corte: date
    periodo_aplicado: date
    persistir: bool = False
    origen_corrida: str = ORIGEN_REINDEXACION_MANUAL
    motivo: str | None = None


class PreviewIndexacionCuotasV2Repository(Protocol):
    def get_scope(self, command: PreviewIndexacionCuotasV2Command) -> dict[str, Any] | None: ...
    def get_valor_indice(self, id_valor: int) -> dict[str, Any] | None: ...
    def list_obligaciones_bloque(self, id_bloque: int, fecha_corte: date) -> list[dict[str, Any]]: ...
    def get_corrida_by_op_id(self, op_id: UUID) -> dict[str, Any] | None: ...
    def create_corrida_preview(self, payload: dict[str, Any], detalles: list[dict[str, Any]]) -> dict[str, Any]: ...


class PreviewIndexacionCuotasV2Service:
    def __init__(self, repository: PreviewIndexacionCuotasV2Repository) -> None:
        self.repository = repository

    def execute(
        self,
        command: PreviewIndexacionCuotasV2Command,
        core_ef: CoreEFHeaders | None = None,
    ) -> AppResult[dict[str, Any]]:
        if command.persistir and core_ef is None:
            return AppResult.fail("CORE_EF_HEADERS_REQUERIDOS")

        scope = self.repository.get_scope(command)
        if scope is None:
            return AppResult.fail("ALCANCE_INDEXACION_INVALIDO")
        valor_aplicado_row = self.repository.get_valor_indice(
            command.id_indice_financiero_valor_aplicado
        )
        if valor_aplicado_row is None:
            return AppResult.fail("VALOR_INDICE_APLICADO_INEXISTENTE")
        if valor_aplicado_row["id_indice_financiero"] != command.id_indice_financiero:
            return AppResult.fail("VALOR_INDICE_APLICADO_INCOMPATIBLE")

        valor_base = _dec(scope["valor_base_indice"]).quantize(Q8)
        valor_aplicado = _dec(valor_aplicado_row["valor_indice"]).quantize(Q8)
        if valor_base <= 0 or valor_aplicado <= 0:
            return AppResult.fail("VALOR_INDICE_INVALIDO")
        coeficiente = (valor_aplicado / valor_base).quantize(Q8, rounding=ROUND_HALF_UP)

        obligaciones = self.repository.list_obligaciones_bloque(command.id_plan_pago_venta_bloque, command.fecha_corte)
        if not obligaciones:
            return AppResult.fail("SIN_OBLIGACIONES_ANALIZABLES")

        detalles = [
            self._build_detalle(row, valor_base, valor_aplicado, coeficiente)
            for row in sorted(obligaciones, key=lambda r: r["id_obligacion_financiera"])
        ]
        snapshot_alcance = {
            "id_plan_pago_venta": command.id_plan_pago_venta,
            "id_plan_pago_venta_bloque": command.id_plan_pago_venta_bloque,
            "id_plan_pago_venta_bloque_indexacion": command.id_plan_pago_venta_bloque_indexacion,
            "id_indice_financiero": command.id_indice_financiero,
            "id_indice_financiero_valor_aplicado": command.id_indice_financiero_valor_aplicado,
            "fecha_corte": command.fecha_corte.isoformat(),
            "periodo_aplicado": command.periodo_aplicado.isoformat(),
        }
        snapshot_versiones = {
            str(d["id_obligacion_financiera"]): d["version_esperada"] for d in detalles
        }
        canonical = {
            "alcance": snapshot_alcance,
            "valor_base_indice": _canon_decimal(valor_base, Q8),
            "valor_aplicado_indice": _canon_decimal(valor_aplicado, Q8),
            "coeficiente_indexacion": _canon_decimal(coeficiente, Q8),
            "detalles": [self._canonical_detalle(d) for d in detalles],
        }
        hash_corrida = hashlib.sha256(
            json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        data = self._response(
            command, scope, valor_aplicado_row, valor_base, valor_aplicado,
            coeficiente, detalles, hash_corrida, snapshot_alcance, snapshot_versiones,
        )

        if command.persistir:
            assert core_ef is not None
            payload_hash = hashlib.sha256(
                json.dumps(
                    {
                        **snapshot_alcance,
                        "origen_corrida": command.origen_corrida,
                        "motivo": command.motivo,
                        "persistir": command.persistir,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            existing = self.repository.get_corrida_by_op_id(core_ef.x_op_id)
            if existing is not None:
                if existing.get("payload_hash") != payload_hash or existing.get("hash_corrida") != hash_corrida:
                    return AppResult.fail("IDEMPOTENCIA_PAYLOAD_INCOMPATIBLE")
                data["id_corrida_indexacion_financiera"] = existing["id_corrida_indexacion_financiera"]
                data["modo"] = "PERSISTIDA"
                return AppResult.ok(data)
            created = self.repository.create_corrida_preview(
                {
                    **snapshot_alcance,
                    "periodo_base": scope["fecha_base_indice"].isoformat(),
                    "fecha_publicacion_indice": (
                        valor_aplicado_row.get("fecha_publicacion").isoformat()
                        if valor_aplicado_row.get("fecha_publicacion") is not None
                        else None
                    ),
                    "id_indice_financiero_valor_base": None,
                    "origen_corrida": command.origen_corrida,
                    "estado_corrida": ESTADO_PREVIEW_PERSISTIDO,
                    "op_id": str(core_ef.x_op_id),
                    "hash_corrida": hash_corrida,
                    "payload_hash": payload_hash,
                    "snapshot_alcance": snapshot_alcance,
                    "snapshot_versiones": snapshot_versiones,
                    "id_usuario": core_ef.x_usuario_id,
                    "id_sucursal": core_ef.x_sucursal_id,
                    "id_instalacion_origen": core_ef.x_instalacion_id,
                    "id_instalacion_ultima_modificacion": core_ef.x_instalacion_id,
                    "op_id_alta": str(core_ef.x_op_id),
                    "op_id_ultima_modificacion": str(core_ef.x_op_id),
                    "motivo": command.motivo,
                    **data["resumen"],
                },
                detalles,
            )
            data["id_corrida_indexacion_financiera"] = created["id_corrida_indexacion_financiera"]
            data["modo"] = "PERSISTIDA"
        return AppResult.ok(data)

    def _build_detalle(self, row: dict[str, Any], valor_base: Decimal, valor_aplicado: Decimal, coeficiente: Decimal) -> dict[str, Any]:
        capital = _dec(row.get("capital_base") or 0).quantize(Q2)
        ajuste_anterior = _dec(row.get("ajuste_anterior") or 0).quantize(Q2)
        ajuste_nuevo = (capital * (coeficiente - Decimal("1"))).quantize(Q2, rounding=ROUND_HALF_UP)
        ajuste_objetivo_calculado = ajuste_nuevo
        estado = ESTADO_ELEGIBLE
        motivo = None
        if row["estado_obligacion"] not in ESTADOS_ELEGIBLES:
            estado, motivo = ESTADO_EXCLUIDA, "ESTADO_OBLIGACION_NO_ELEGIBLE"
        elif capital <= 0:
            estado, motivo = ESTADO_EXCLUIDA, "SIN_CAPITAL_INDEXABLE"
        elif row.get("tiene_imputaciones"):
            estado, motivo = ESTADO_EXCLUIDA, "OBLIGACION_CON_IMPUTACIONES_ACTIVAS"
        elif row.get("tiene_pagos"):
            estado, motivo = ESTADO_EXCLUIDA, "OBLIGACION_CON_PAGOS_ACTIVOS"
        elif row.get("tiene_punitorios"):
            estado, motivo = ESTADO_EXCLUIDA, "OBLIGACION_CON_MORA_INCOMPATIBLE"
        elif ajuste_nuevo < 0:
            estado, motivo = ESTADO_EXCLUIDA, "AJUSTE_NEGATIVO_NO_SOPORTADO"
        advertencias = []
        if row.get("tiene_mora") and not row.get("tiene_punitorios"):
            advertencias.append("OBLIGACION_VENCIDA_SIN_EFECTOS_POSTERIORES")
        if row.get("tiene_recibos"):
            estado, motivo = ESTADO_EXCLUIDA, "OBLIGACION_CON_RECIBOS_CONGELANTES"
        importe_anterior = _dec(row["importe_total"]).quantize(Q2)
        saldo_anterior = _dec(row["saldo_pendiente"]).quantize(Q2)
        if estado != ESTADO_ELEGIBLE:
            ajuste_nuevo = ajuste_anterior
            diferencia = Decimal("0.00")
        else:
            diferencia = (ajuste_nuevo - ajuste_anterior).quantize(Q2)
        snapshot_antes = {
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "estado_obligacion": row["estado_obligacion"],
            "version_registro": row["version_registro"],
            "capital_base": _canon_decimal(capital, Q2),
            "ajuste_anterior": _canon_decimal(ajuste_anterior, Q2),
            "importe_total": _canon_decimal(importe_anterior, Q2),
            "saldo_pendiente": _canon_decimal(saldo_anterior, Q2),
            "id_composicion_capital_venta": row.get("id_composicion_capital_venta"),
            "id_composicion_ajuste_indexacion": row.get("id_composicion_ajuste_indexacion"),
            "id_obligacion_financiera_indexacion": row.get("id_obligacion_financiera_indexacion"),
            "flags": {
                "tiene_imputaciones": bool(row.get("tiene_imputaciones")),
                "tiene_pagos": bool(row.get("tiene_pagos")),
                "tiene_mora": bool(row.get("tiene_mora")),
                "tiene_punitorios": bool(row.get("tiene_punitorios")),
                "tiene_recibos": bool(row.get("tiene_recibos")),
            },
        }
        snapshot_despues = {
            "estado_elegibilidad": estado,
            "motivo_exclusion": motivo,
            "ajuste_objetivo_calculado": _canon_decimal(ajuste_objetivo_calculado, Q2),
            "ajuste_nuevo_persistible": _canon_decimal(ajuste_nuevo, Q2),
            "diferencia_neta": _canon_decimal(diferencia, Q2),
            "importe_nuevo": _canon_decimal((importe_anterior + diferencia).quantize(Q2), Q2),
            "saldo_nuevo": _canon_decimal((saldo_anterior + diferencia).quantize(Q2), Q2),
            "advertencias": advertencias,
            "version_esperada": row["version_registro"],
        }
        return {
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "id_composicion_capital_venta": row.get("id_composicion_capital_venta"),
            "id_composicion_ajuste_indexacion": row.get("id_composicion_ajuste_indexacion"),
            "id_obligacion_financiera_indexacion": row.get("id_obligacion_financiera_indexacion"),
            "version_esperada": row["version_registro"],
            "capital_base": capital,
            "valor_indice_base": valor_base,
            "valor_indice_aplicado": valor_aplicado,
            "coeficiente_indexacion": coeficiente,
            "ajuste_anterior": ajuste_anterior,
            "ajuste_nuevo": ajuste_nuevo,
            "diferencia_neta": diferencia,
            "importe_anterior": importe_anterior,
            "importe_nuevo": (importe_anterior + diferencia).quantize(Q2),
            "saldo_anterior": saldo_anterior,
            "saldo_nuevo": (saldo_anterior + diferencia).quantize(Q2),
            "estado_elegibilidad": estado,
            "motivo_exclusion": motivo,
            "advertencias": advertencias,
            "snapshot_antes": snapshot_antes,
            "snapshot_despues": snapshot_despues,
        }

    @staticmethod
    def _canonical_detalle(d: dict[str, Any]) -> dict[str, Any]:
        keys = ["id_obligacion_financiera", "id_composicion_capital_venta", "id_composicion_ajuste_indexacion", "id_obligacion_financiera_indexacion", "version_esperada", "capital_base", "ajuste_anterior", "ajuste_nuevo", "diferencia_neta", "importe_anterior", "importe_nuevo", "saldo_anterior", "saldo_nuevo", "estado_elegibilidad", "motivo_exclusion", "advertencias", "snapshot_antes", "snapshot_despues"]
        return {k: _canon(d[k]) for k in keys}

    def _response(self, command, scope, valor_aplicado_row, valor_base, valor_aplicado, coeficiente, detalles, hash_corrida, snapshot_alcance, snapshot_versiones):
        resumen = {
            "cantidad_analizada": len(detalles),
            "cantidad_elegible": sum(1 for d in detalles if d["estado_elegibilidad"] == ESTADO_ELEGIBLE),
            "cantidad_excluida": sum(1 for d in detalles if d["estado_elegibilidad"] != ESTADO_ELEGIBLE),
            "cantidad_aplicada": 0,
            "importe_total_anterior": sum((d["importe_anterior"] for d in detalles), Decimal("0")).quantize(Q2),
            "importe_total_nuevo": sum((d["importe_nuevo"] for d in detalles), Decimal("0")).quantize(Q2),
            "ajuste_anterior_total": sum((d["ajuste_anterior"] for d in detalles), Decimal("0")).quantize(Q2),
            "ajuste_nuevo_total": sum((d["ajuste_nuevo"] for d in detalles), Decimal("0")).quantize(Q2),
            "saldo_anterior_total": sum((d["saldo_anterior"] for d in detalles), Decimal("0")).quantize(Q2),
            "saldo_nuevo_total": sum((d["saldo_nuevo"] for d in detalles), Decimal("0")).quantize(Q2),
        }
        return {
            "modo": "EFIMERA",
            "id_corrida_indexacion_financiera": None,
            "id_plan_pago_venta": command.id_plan_pago_venta,
            "id_plan_pago_venta_bloque": command.id_plan_pago_venta_bloque,
            "id_plan_pago_venta_bloque_indexacion": command.id_plan_pago_venta_bloque_indexacion,
            "id_indice_financiero": command.id_indice_financiero,
            "id_indice_financiero_valor_aplicado": command.id_indice_financiero_valor_aplicado,
            "periodo_base": scope["fecha_base_indice"],
            "periodo_aplicado": command.periodo_aplicado,
            "fecha_corte": command.fecha_corte,
            "fecha_publicacion_indice": valor_aplicado_row.get("fecha_publicacion"),
            "valor_indice_base": valor_base,
            "valor_indice_aplicado": valor_aplicado,
            "coeficiente_indexacion": coeficiente,
            "hash_corrida": hash_corrida,
            "resumen": resumen,
            "snapshot_alcance": snapshot_alcance,
            "snapshot_versiones": snapshot_versiones,
            "detalles": detalles,
        }


def _dec(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))

def _canon_decimal(value: Decimal, quantum: Decimal) -> str:
    return str(value.quantize(quantum))

def _canon(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value
