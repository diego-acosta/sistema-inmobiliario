from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any

from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import GeneratePlanPagoVentaV2PorBloquesCommand

CLASIFICACION_HISTORICA_EXIGIBLE = "HISTORICA_EXIGIBLE"
CLASIFICACION_PERIODO_CORTE = "PERIODO_CORTE"
CLASIFICACION_FUTURA = "FUTURA"
ERROR_VENTA_HISTORICA_INDEXACION_NO_RESUELTA = "VENTA_HISTORICA_INDEXACION_NO_RESUELTA"
ERROR_FECHA_CORTE_REQUERIDA_VENTA_HISTORICA = "FECHA_CORTE_REQUERIDA_VENTA_HISTORICA"


@dataclass(frozen=True, slots=True)
class PrevalidateVentaHistoricaIndexacionInput:
    fecha_venta: date
    fecha_corte: date
    command: GeneratePlanPagoVentaV2PorBloquesCommand
    preview: dict[str, Any]


class PrevalidateVentaHistoricaIndexacionService:
    """Prevalidación read-like reusable para ventas históricas con Plan Pago V2."""

    def __init__(self, indice_financiero_query: Any | None = None) -> None:
        self.indice_financiero_query = indice_financiero_query

    def execute(self, data: PrevalidateVentaHistoricaIndexacionInput) -> dict[str, Any]:
        cuotas: list[dict[str, Any]] = []
        motivos: set[str] = set()
        for obligacion in data.preview["obligaciones"]:
            clasificacion = clasificar_cuota_historica(
                obligacion.fecha_vencimiento, data.fecha_corte
            )
            bloque = obligacion.bloque.input
            requiere_indice = (bloque.metodo_liquidacion or "").strip().upper() == "INDEXACION"
            estado = obligacion.estado_preview_indexacion or "NO_REQUIERE_INDICE"
            motivo = self._motivo_bloqueo(obligacion, clasificacion)
            bloquea = motivo is not None
            if bloquea:
                estado = "BLOQUEADA"
                motivos.add(motivo)
            cuotas.append(
                {
                    "numero_cuota": obligacion.item_numero,
                    "numero_bloque": obligacion.bloque.numero_bloque,
                    "clave_bloque": obligacion.bloque.clave_bloque,
                    "fecha_vencimiento": obligacion.fecha_vencimiento,
                    "clasificacion_temporal": clasificacion,
                    "capital": obligacion.capital_cuota or obligacion.importe_total,
                    "ajuste": obligacion.ajuste_indexacion_cuota,
                    "total": obligacion.importe_total,
                    "moneda": data.command.moneda.strip().upper(),
                    "estado_indexacion": estado,
                    "bloquea_confirmacion": bloquea,
                    "motivo_bloqueo": motivo,
                    "id_indice_financiero": obligacion.id_indice_financiero or (bloque.id_indice_financiero if requiere_indice else None),
                    "codigo_indice_financiero": obligacion.codigo_indice_financiero,
                    "nombre_indice_financiero": obligacion.nombre_indice_financiero,
                    "fecha_base_indice": bloque.fecha_base_indice if requiere_indice else None,
                    "valor_base_indice": obligacion.valor_base_indice,
                    "id_indice_financiero_valor_aplicado": obligacion.id_indice_financiero_valor,
                    "fecha_valor": obligacion.fecha_valor_indice,
                    "fecha_publicacion": obligacion.fecha_publicacion_indice,
                    "valor_indice": obligacion.valor_aplicado_indice,
                    "coeficiente": obligacion.coeficiente_indexacion,
                }
            )
        return {
            "es_venta_historica": data.fecha_venta < data.fecha_corte,
            "fecha_venta": data.fecha_venta,
            "fecha_corte": data.fecha_corte,
            "puede_confirmar": not motivos,
            "cantidad_cuotas": len(cuotas),
            "cantidad_historicas_exigibles": sum(1 for c in cuotas if c["clasificacion_temporal"] == CLASIFICACION_HISTORICA_EXIGIBLE),
            "cantidad_periodo_corte": sum(1 for c in cuotas if c["clasificacion_temporal"] == CLASIFICACION_PERIODO_CORTE),
            "cantidad_futuras": sum(1 for c in cuotas if c["clasificacion_temporal"] == CLASIFICACION_FUTURA),
            "cantidad_con_indice": sum(1 for c in cuotas if c["estado_indexacion"] == "CON_INDICE_APLICADO"),
            "cantidad_sin_indice": sum(1 for c in cuotas if c["estado_indexacion"] == "PROYECTADA_SIN_INDICE"),
            "cantidad_bloqueadas": sum(1 for c in cuotas if c["bloquea_confirmacion"]),
            "motivos_bloqueo": sorted(motivos),
            "cuotas": cuotas,
        }

    def _motivo_bloqueo(self, obligacion: Any, clasificacion: str) -> str | None:
        if clasificacion != CLASIFICACION_HISTORICA_EXIGIBLE:
            return None
        bloque = obligacion.bloque.input
        if (bloque.metodo_liquidacion or "").strip().upper() != "INDEXACION":
            return None
        if (bloque.valor_base_indice or 0) <= 0:
            return "VALOR_BASE_INDICE_INVALIDO"
        if obligacion.estado_preview_indexacion == "CON_INDICE_APLICADO":
            if obligacion.fecha_publicacion_indice is None:
                return "FECHA_PUBLICACION_INDICE_INCOMPLETA"
            return None
        if self.indice_financiero_query is not None and hasattr(self.indice_financiero_query, "diagnosticar_valor_publicado_no_aplicable"):
            return self.indice_financiero_query.diagnosticar_valor_publicado_no_aplicable(
                bloque.id_indice_financiero or 0, obligacion.fecha_vencimiento
            )
        if obligacion.id_indice_financiero is None and bloque.id_indice_financiero:
            return "INDICE_FINANCIERO_INACTIVO"
        return "VALOR_INDICE_PUBLICADO_INEXISTENTE"


def clasificar_cuota_historica(fecha_vencimiento: date, fecha_corte: date) -> str:
    if fecha_vencimiento < fecha_corte:
        return CLASIFICACION_HISTORICA_EXIGIBLE
    if fecha_vencimiento == fecha_corte:
        return CLASIFICACION_PERIODO_CORTE
    return CLASIFICACION_FUTURA


def resumen_confirmacion_prevalidacion(prevalidacion: dict[str, Any]) -> dict[str, Any]:
    return {
        "puede_confirmar": prevalidacion["puede_confirmar"],
        "cantidad_historicas_exigibles": prevalidacion["cantidad_historicas_exigibles"],
        "cantidad_con_indice": prevalidacion["cantidad_con_indice"],
        "cantidad_futuras": prevalidacion["cantidad_futuras"],
        "cantidad_bloqueadas": prevalidacion["cantidad_bloqueadas"],
    }


def detalle_bloqueo_prevalidacion(prevalidacion: dict[str, Any]) -> dict[str, Any]:
    return {
        "puede_confirmar": False,
        "cantidad_bloqueadas": prevalidacion["cantidad_bloqueadas"],
        "motivos_bloqueo": prevalidacion["motivos_bloqueo"],
        "cuotas_bloqueadas": [
            {
                "numero_cuota": cuota["numero_cuota"],
                "clave_bloque": cuota["clave_bloque"],
                "fecha_vencimiento": cuota["fecha_vencimiento"].isoformat() if hasattr(cuota["fecha_vencimiento"], "isoformat") else cuota["fecha_vencimiento"],
                "motivo_bloqueo": cuota["motivo_bloqueo"],
                "id_indice_financiero": cuota["id_indice_financiero"],
            }
            for cuota in prevalidacion["cuotas"]
            if cuota["bloquea_confirmacion"]
        ],
    }
