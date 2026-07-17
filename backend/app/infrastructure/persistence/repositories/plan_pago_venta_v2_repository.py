from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class PlanPagoVentaV2Repository:
    def __init__(self, db: Session) -> None:
        self.db = db

    @staticmethod
    def _values(payload: Any) -> dict[str, Any]:
        if hasattr(payload, "__dataclass_fields__"):
            return {
                field: getattr(payload, field) for field in payload.__dataclass_fields__
            }
        if isinstance(payload, dict):
            return payload
        return vars(payload)

    def get_venta_minima(self, id_venta: int) -> dict[str, Any] | None:
        stmt = text("""
            SELECT
                id_venta,
                estado_venta,
                monto_total,
                moneda,
                deleted_at
            FROM venta
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """)
        row = self.db.execute(stmt, {"id_venta": id_venta}).mappings().one_or_none()
        return dict(row) if row else None

    def get_plan_pago_venta_vivo(self, id_venta: int) -> dict[str, Any] | None:
        stmt = text("""
            SELECT
                id_plan_pago_venta,
                id_venta,
                metodo_plan_pago,
                estado_plan_pago,
                moneda,
                monto_total_plan,
                cantidad_cuotas,
                periodicidad,
                fecha_primer_vencimiento,
                importe_anticipo,
                fecha_vencimiento_anticipo,
                regla_redondeo,
                observaciones
            FROM plan_pago_venta
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
              AND estado_plan_pago IN ('BORRADOR', 'ACTIVO', 'GENERADO')
            ORDER BY id_plan_pago_venta ASC
            LIMIT 1
            """)
        row = self.db.execute(stmt, {"id_venta": id_venta}).mappings().one_or_none()
        return dict(row) if row else None

    def get_plan_pago_venta_v2_integral(self, id_venta: int) -> dict[str, Any] | None:
        plan = self.get_plan_pago_venta_vivo(id_venta)
        if plan is None:
            return None

        id_plan_pago_venta = plan["id_plan_pago_venta"]
        relacion = self.get_relacion_generadora_venta(id_venta)
        bloques = self.get_plan_pago_venta_bloques_integrales(id_plan_pago_venta)
        obligaciones = self.get_obligaciones_plan_pago_venta_v2_integrales(
            id_plan_pago_venta
        )
        composiciones = self.get_composiciones_obligaciones_plan_pago_venta_v2(
            id_plan_pago_venta
        )
        obligados = self.get_obligados_obligaciones_plan_pago_venta_v2(
            id_plan_pago_venta
        )
        generaciones = self.get_generaciones_plan_pago_venta_v2(id_plan_pago_venta)
        resumen = self.get_resumen_plan_pago_venta_v2(id_plan_pago_venta)
        corridas = self.get_corridas_indexacion_v2(id_plan_pago_venta)

        corrida_por_obligacion: dict[int, dict[str, Any]] = {}
        corrida_aplicada_por_obligacion: dict[int, dict[str, Any]] = {}
        for corrida in corridas:
            for afectada in corrida["obligaciones_afectadas"]:
                # La corrida mas reciente es la referencia de presentacion de la cuota.
                corrida_por_obligacion[afectada["id_obligacion_financiera"]] = {
                    "id_corrida_indexacion_financiera": corrida[
                        "id_corrida_indexacion_financiera"
                    ],
                    "estado_corrida": corrida["estado_corrida"],
                    "origen_corrida": corrida["origen_corrida"],
                    "estado_elegibilidad": afectada["estado_elegibilidad"],
                    "codigo_error": afectada["codigo_error"],
                }
                if corrida["estado_corrida"] == "APLICADA":
                    corrida_aplicada_por_obligacion[
                        afectada["id_obligacion_financiera"]
                    ] = corrida_por_obligacion[afectada["id_obligacion_financiera"]]

        obligaciones_por_bloque: dict[int, list[dict[str, Any]]] = {}
        composiciones_por_obligacion: dict[int, list[dict[str, Any]]] = {}
        obligados_por_obligacion: dict[int, list[dict[str, Any]]] = {}
        for obligado in obligados:
            obligados_por_obligacion.setdefault(
                obligado["id_obligacion_financiera"], []
            ).append(obligado)

        for composicion in composiciones:
            composiciones_por_obligacion.setdefault(
                composicion["id_obligacion_financiera"], []
            ).append(composicion)

        for obligacion in obligaciones:
            composiciones_obligacion = composiciones_por_obligacion.get(
                obligacion["id_obligacion_financiera"], []
            )
            corrida_relacionada = corrida_por_obligacion.get(
                obligacion["id_obligacion_financiera"]
            )
            corrida_aplicada_vigente = corrida_aplicada_por_obligacion.get(
                obligacion["id_obligacion_financiera"]
            )
            obligacion["capital_original"] = sum(
                (
                    composicion["importe_componente"]
                    for composicion in composiciones_obligacion
                    if composicion["codigo_concepto_financiero"] == "CAPITAL_VENTA"
                ),
                Decimal("0"),
            )
            obligacion["ajuste_indexacion"] = sum(
                (
                    composicion["importe_componente"]
                    for composicion in composiciones_obligacion
                    if composicion["codigo_concepto_financiero"] == "AJUSTE_INDEXACION"
                ),
                Decimal("0"),
            )
            obligacion["importe_vigente"] = obligacion["importe_total"]
            obligacion["corrida_relacionada"] = corrida_relacionada
            obligacion["corrida_aplicada_vigente"] = corrida_aplicada_vigente
            if corrida_relacionada and corrida_relacionada["codigo_error"]:
                obligacion["estado_indexacion_presentacion"] = "CON_ERROR"
                obligacion["origen_indexacion"] = (
                    "CORRIDA_POSTERIOR"
                    if corrida_aplicada_vigente
                    else (
                        "AL_NACIMIENTO"
                        if obligacion["indexacion"] is not None
                        else None
                    )
                )
            elif corrida_relacionada and corrida_relacionada["estado_elegibilidad"] == "EXCLUIDA":
                obligacion["estado_indexacion_presentacion"] = "EXCLUIDA"
                obligacion["origen_indexacion"] = None
            elif obligacion["indexacion"] is not None:
                obligacion["estado_indexacion_presentacion"] = "CON_INDICE_APLICADO"
                obligacion["origen_indexacion"] = (
                    "CORRIDA_POSTERIOR"
                    if corrida_aplicada_vigente
                    else "AL_NACIMIENTO"
                )
            elif obligacion["id_plan_pago_venta_bloque"] in {
                bloque["id_plan_pago_venta_bloque"]
                for bloque in bloques
                if bloque["indexacion"] is not None
            }:
                obligacion["estado_indexacion_presentacion"] = "PROYECTADA_SIN_INDICE"
                obligacion["origen_indexacion"] = None
            else:
                obligacion["estado_indexacion_presentacion"] = "NO_REQUIERE_INDICE"
                obligacion["origen_indexacion"] = None
            obligacion["composiciones"] = composiciones_obligacion
            obligacion["obligados"] = obligados_por_obligacion.get(
                obligacion["id_obligacion_financiera"], []
            )
            obligaciones_por_bloque.setdefault(
                obligacion["id_plan_pago_venta_bloque"], []
            ).append(obligacion)

        for bloque in bloques:
            bloque["obligaciones"] = obligaciones_por_bloque.get(
                bloque["id_plan_pago_venta_bloque"], []
            )

        return {
            "id_venta": id_venta,
            "plan_pago_venta": plan,
            "relacion_generadora": relacion,
            "generaciones": generaciones,
            "bloques": bloques,
            "resumen": resumen,
            "corridas_indexacion": corridas,
        }

    def get_corridas_indexacion_v2(
        self, id_plan_pago_venta: int
    ) -> list[dict[str, Any]]:
        cabeceras = self.db.execute(text("""
            SELECT c.id_corrida_indexacion_financiera, c.estado_corrida,
                   c.origen_corrida, i.codigo_indice_financiero,
                   c.periodo_aplicado, c.fecha_corte, c.created_at AS fecha_preparacion,
                   c.fecha_aplicacion, c.cantidad_analizada, c.cantidad_elegible,
                   c.cantidad_excluida, c.cantidad_aplicada,
                   c.codigo_error, c.etapa_error, c.diagnostico_tecnico,
                   COALESCE(d.cantidad_error, 0)
                     + CASE WHEN c.codigo_error IS NULL THEN 0 ELSE 1 END AS cantidad_error,
                   COALESCE(d.capital_analizado_total, 0) AS capital_analizado_total,
                   c.ajuste_nuevo_total AS ajuste_total,
                   c.importe_total_nuevo AS importe_total
            FROM corrida_indexacion_financiera c
            JOIN indice_financiero i ON i.id_indice_financiero = c.id_indice_financiero
             AND i.deleted_at IS NULL
            LEFT JOIN LATERAL (
                SELECT COUNT(*) FILTER (WHERE codigo_error IS NOT NULL) AS cantidad_error,
                       COALESCE(SUM(capital_base), 0) AS capital_analizado_total
                FROM corrida_indexacion_financiera_detalle d
                WHERE d.id_corrida_indexacion_financiera = c.id_corrida_indexacion_financiera
                  AND d.deleted_at IS NULL
            ) d ON TRUE
            WHERE c.id_plan_pago_venta = :id_plan_pago_venta
              AND c.deleted_at IS NULL
            ORDER BY c.created_at ASC, c.id_corrida_indexacion_financiera ASC
        """), {"id_plan_pago_venta": id_plan_pago_venta}).mappings().all()
        corridas = [dict(row) for row in cabeceras]
        if not corridas:
            return []
        detalles = self.db.execute(text("""
            SELECT d.id_corrida_indexacion_financiera, d.id_obligacion_financiera,
                   d.estado_elegibilidad, d.motivo_exclusion, d.codigo_error,
                   d.detalle_controlado
            FROM corrida_indexacion_financiera_detalle d
            JOIN corrida_indexacion_financiera c
              ON c.id_corrida_indexacion_financiera = d.id_corrida_indexacion_financiera
             AND c.deleted_at IS NULL
            WHERE c.id_plan_pago_venta = :id_plan_pago_venta
              AND d.deleted_at IS NULL
            ORDER BY d.id_corrida_indexacion_financiera ASC, d.id_obligacion_financiera ASC
        """), {"id_plan_pago_venta": id_plan_pago_venta}).mappings().all()
        detalles_por_corrida: dict[int, list[dict[str, Any]]] = {}
        for row in detalles:
            detalle = dict(row)
            detalles_por_corrida.setdefault(
                detalle["id_corrida_indexacion_financiera"], []
            ).append(detalle)
        for corrida in corridas:
            detalles_corrida = detalles_por_corrida.get(
                corrida["id_corrida_indexacion_financiera"], []
            )
            corrida["exclusiones"] = [
                detalle for detalle in detalles_corrida
                if detalle["estado_elegibilidad"] == "EXCLUIDA"
            ]
            corrida["errores"] = [
                detalle for detalle in detalles_corrida if detalle["codigo_error"] is not None
            ]
            corrida["obligaciones_afectadas"] = detalles_corrida
        return corridas

    def get_relacion_generadora_venta(self, id_venta: int) -> dict[str, Any] | None:
        stmt = text("""
            SELECT
                id_relacion_generadora,
                tipo_origen,
                id_origen,
                estado_relacion_generadora
            FROM relacion_generadora
            WHERE tipo_origen = 'venta'
              AND id_origen = :id_venta
              AND deleted_at IS NULL
            ORDER BY id_relacion_generadora ASC
            LIMIT 1
            """)
        row = self.db.execute(stmt, {"id_venta": id_venta}).mappings().one_or_none()
        return dict(row) if row else None

    def get_generaciones_plan_pago_venta_v2(
        self, id_plan_pago_venta: int
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT
                id_generacion_cronograma_financiero,
                id_relacion_generadora,
                id_plan_pago_venta,
                tipo_generacion,
                clave_generacion,
                estado_generacion,
                fecha_generacion
            FROM generacion_cronograma_financiero
            WHERE id_plan_pago_venta = :id_plan_pago_venta
              AND deleted_at IS NULL
            ORDER BY fecha_generacion ASC, id_generacion_cronograma_financiero ASC
            """)
        rows = (
            self.db.execute(stmt, {"id_plan_pago_venta": id_plan_pago_venta})
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def get_plan_pago_venta_bloques_integrales(
        self, id_plan_pago_venta: int
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT
                b.id_plan_pago_venta_bloque,
                b.id_plan_pago_venta,
                b.numero_bloque,
                b.tipo_bloque,
                b.etiqueta_bloque,
                b.clave_bloque,
                b.cantidad_cuotas,
                b.importe_total_bloque,
                b.importe_cuota,
                b.fecha_vencimiento,
                b.fecha_primer_vencimiento,
                b.periodicidad,
                b.regla_redondeo,
                b.metodo_liquidacion,
                b.tasa_interes_directo_periodica,
                b.cantidad_periodos,
                b.base_calculo_interes,
                b.concepto_financiero_codigo,
                b.observaciones,
                bi.id_plan_pago_venta_bloque_indexacion,
                bi.id_indice_financiero,
                i.codigo_indice_financiero,
                i.nombre_indice_financiero,
                bi.fecha_base_indice,
                bi.valor_base_indice,
                bi.modo_indexacion,
                bi.base_calculo_indexacion,
                bi.tipo_generacion_indexada,
                bi.politica_valor_no_disponible,
                bi.conserva_capital_original,
                bi.genera_ajuste_por_diferencia
            FROM plan_pago_venta_bloque b
            LEFT JOIN plan_pago_venta_bloque_indexacion bi
              ON bi.id_plan_pago_venta_bloque = b.id_plan_pago_venta_bloque
             AND bi.deleted_at IS NULL
            LEFT JOIN indice_financiero i
              ON i.id_indice_financiero = bi.id_indice_financiero
             AND i.deleted_at IS NULL
            WHERE b.id_plan_pago_venta = :id_plan_pago_venta
              AND b.deleted_at IS NULL
            ORDER BY b.numero_bloque ASC
            """)
        rows = (
            self.db.execute(stmt, {"id_plan_pago_venta": id_plan_pago_venta})
            .mappings()
            .all()
        )
        bloques: list[dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            indexacion = None
            if data.pop("id_plan_pago_venta_bloque_indexacion") is not None:
                indexacion = {
                    "id_plan_pago_venta_bloque_indexacion": row[
                        "id_plan_pago_venta_bloque_indexacion"
                    ],
                    "id_indice_financiero": data.pop("id_indice_financiero"),
                    "codigo_indice_financiero": data.pop("codigo_indice_financiero"),
                    "nombre_indice_financiero": data.pop("nombre_indice_financiero"),
                    "fecha_base_indice": data.pop("fecha_base_indice"),
                    "valor_base_indice": data.pop("valor_base_indice"),
                    "modo_indexacion": data.pop("modo_indexacion"),
                    "base_calculo_indexacion": data.pop("base_calculo_indexacion"),
                    "tipo_generacion_indexada": data.pop("tipo_generacion_indexada"),
                    "politica_valor_no_disponible": data.pop(
                        "politica_valor_no_disponible"
                    ),
                    "conserva_capital_original": data.pop("conserva_capital_original"),
                    "genera_ajuste_por_diferencia": data.pop(
                        "genera_ajuste_por_diferencia"
                    ),
                }
            else:
                for key in (
                    "id_indice_financiero",
                    "codigo_indice_financiero",
                    "nombre_indice_financiero",
                    "fecha_base_indice",
                    "valor_base_indice",
                    "modo_indexacion",
                    "base_calculo_indexacion",
                    "tipo_generacion_indexada",
                    "politica_valor_no_disponible",
                    "conserva_capital_original",
                    "genera_ajuste_por_diferencia",
                ):
                    data.pop(key)
            data["indexacion"] = indexacion
            bloques.append(data)
        return bloques

    def get_obligaciones_plan_pago_venta_v2_integrales(
        self, id_plan_pago_venta: int
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT
                o.id_obligacion_financiera,
                o.id_relacion_generadora,
                o.id_generacion_cronograma_financiero,
                o.id_plan_pago_venta_bloque,
                o.numero_obligacion,
                o.tipo_item_cronograma,
                o.etiqueta_obligacion,
                o.clave_funcional_origen,
                o.fecha_vencimiento,
                o.importe_total,
                o.saldo_pendiente,
                o.moneda,
                o.estado_obligacion,
                b.tipo_bloque AS tipo_bloque_bloque,
                ofi.id_obligacion_financiera_indexacion,
                ofi.id_indice_financiero,
                ofi.id_indice_financiero_valor,
                ofi.fecha_base_indice,
                ofi.valor_base_indice,
                ofi.fecha_aplicacion_indice,
                ofi.valor_aplicado_indice,
                ofi.coeficiente_indexacion,
                ofi.modo_indexacion,
                ofi.base_calculo_indexacion,
                ofi.tipo_generacion_indexada
            FROM obligacion_financiera o
            JOIN plan_pago_venta_bloque b
              ON b.id_plan_pago_venta_bloque = o.id_plan_pago_venta_bloque
             AND b.deleted_at IS NULL
            LEFT JOIN obligacion_financiera_indexacion ofi
              ON ofi.id_obligacion_financiera = o.id_obligacion_financiera
             AND ofi.deleted_at IS NULL
            WHERE b.id_plan_pago_venta = :id_plan_pago_venta
              AND o.deleted_at IS NULL
            ORDER BY b.numero_bloque ASC, o.numero_obligacion ASC
            """)
        rows = (
            self.db.execute(stmt, {"id_plan_pago_venta": id_plan_pago_venta})
            .mappings()
            .all()
        )
        obligaciones: list[dict[str, Any]] = []
        for row in rows:
            data = dict(row)
            indexacion = None
            if data.pop("id_obligacion_financiera_indexacion") is not None:
                indexacion = {
                    "id_obligacion_financiera_indexacion": row[
                        "id_obligacion_financiera_indexacion"
                    ],
                    "id_indice_financiero": data.pop("id_indice_financiero"),
                    "id_indice_financiero_valor": data.pop(
                        "id_indice_financiero_valor"
                    ),
                    "fecha_base_indice": data.pop("fecha_base_indice"),
                    "valor_base_indice": data.pop("valor_base_indice"),
                    "fecha_aplicacion_indice": data.pop("fecha_aplicacion_indice"),
                    "valor_aplicado_indice": data.pop("valor_aplicado_indice"),
                    "coeficiente_indexacion": data.pop("coeficiente_indexacion"),
                    "modo_indexacion": data.pop("modo_indexacion"),
                    "base_calculo_indexacion": data.pop("base_calculo_indexacion"),
                    "tipo_generacion_indexada": data.pop("tipo_generacion_indexada"),
                }
            else:
                for key in (
                    "id_indice_financiero",
                    "id_indice_financiero_valor",
                    "fecha_base_indice",
                    "valor_base_indice",
                    "fecha_aplicacion_indice",
                    "valor_aplicado_indice",
                    "coeficiente_indexacion",
                    "modo_indexacion",
                    "base_calculo_indexacion",
                    "tipo_generacion_indexada",
                ):
                    data.pop(key)
            data["indexacion"] = indexacion
            tipo_bloque_bloque = data.pop("tipo_bloque_bloque")
            data["numero_cuota_asociada"] = (
                self._numero_cuota_asociada_desde_clave(
                    data.get("clave_funcional_origen")
                )
                if tipo_bloque_bloque == "TRAMO_CUOTAS"
                else None
            )
            obligaciones.append(data)
        return obligaciones

    @staticmethod
    def _numero_cuota_asociada_desde_clave(
        clave_funcional_origen: str | None,
    ) -> int | None:
        if not clave_funcional_origen:
            return None
        parts = clave_funcional_origen.split(":")
        if len(parts) < 2 or parts[-2] not in {"CUOTA", "REFUERZO"}:
            return None
        try:
            return int(parts[-1])
        except ValueError:
            return None

    def get_composiciones_obligaciones_plan_pago_venta_v2(
        self, id_plan_pago_venta: int
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT
                co.id_composicion_obligacion,
                co.id_obligacion_financiera,
                co.id_concepto_financiero,
                cf.codigo_concepto_financiero,
                co.orden_composicion,
                co.importe_componente,
                co.saldo_componente,
                co.moneda_componente
            FROM composicion_obligacion co
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = co.id_obligacion_financiera
             AND o.deleted_at IS NULL
            JOIN plan_pago_venta_bloque b
              ON b.id_plan_pago_venta_bloque = o.id_plan_pago_venta_bloque
             AND b.deleted_at IS NULL
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = co.id_concepto_financiero
             AND cf.deleted_at IS NULL
            WHERE b.id_plan_pago_venta = :id_plan_pago_venta
              AND co.deleted_at IS NULL
            ORDER BY b.numero_bloque ASC, o.numero_obligacion ASC, co.orden_composicion ASC
            """)
        rows = (
            self.db.execute(stmt, {"id_plan_pago_venta": id_plan_pago_venta})
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def get_obligados_obligaciones_plan_pago_venta_v2(
        self, id_plan_pago_venta: int
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT
                oo.id_obligacion_obligado,
                oo.id_obligacion_financiera,
                oo.id_persona,
                p.codigo_persona,
                p.nombre,
                p.apellido,
                p.razon_social,
                oo.rol_obligado,
                oo.porcentaje_responsabilidad,
                CASE
                    WHEN oo.porcentaje_responsabilidad IS NULL THEN NULL
                    ELSE ROUND(o.importe_total * oo.porcentaje_responsabilidad / 100, 2)
                END AS importe_responsabilidad_informativo
            FROM obligacion_obligado oo
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = oo.id_obligacion_financiera
             AND o.deleted_at IS NULL
            JOIN plan_pago_venta_bloque b
              ON b.id_plan_pago_venta_bloque = o.id_plan_pago_venta_bloque
             AND b.deleted_at IS NULL
            LEFT JOIN persona p
              ON p.id_persona = oo.id_persona
             AND p.deleted_at IS NULL
            WHERE b.id_plan_pago_venta = :id_plan_pago_venta
              AND oo.deleted_at IS NULL
            ORDER BY b.numero_bloque ASC, o.numero_obligacion ASC, oo.id_obligacion_obligado ASC
            """)
        rows = (
            self.db.execute(stmt, {"id_plan_pago_venta": id_plan_pago_venta})
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def get_resumen_plan_pago_venta_v2(self, id_plan_pago_venta: int) -> dict[str, Any]:
        stmt = text("""
            WITH obligaciones AS (
                SELECT o.id_obligacion_financiera, o.importe_total, b.metodo_liquidacion
                FROM obligacion_financiera o
                JOIN plan_pago_venta_bloque b
                  ON b.id_plan_pago_venta_bloque = o.id_plan_pago_venta_bloque
                 AND b.deleted_at IS NULL
                WHERE b.id_plan_pago_venta = :id_plan_pago_venta
                  AND o.deleted_at IS NULL
            ), composiciones AS (
                SELECT
                    cf.codigo_concepto_financiero,
                    co.importe_componente
                FROM composicion_obligacion co
                JOIN obligaciones o
                  ON o.id_obligacion_financiera = co.id_obligacion_financiera
                JOIN concepto_financiero cf
                  ON cf.id_concepto_financiero = co.id_concepto_financiero
                 AND cf.deleted_at IS NULL
                WHERE co.deleted_at IS NULL
            ), obligados AS (
                SELECT oo.id_obligacion_financiera, COUNT(*) AS cantidad_obligados
                FROM obligacion_obligado oo
                JOIN obligaciones o
                  ON o.id_obligacion_financiera = oo.id_obligacion_financiera
                WHERE oo.deleted_at IS NULL
                GROUP BY oo.id_obligacion_financiera
            ), indexaciones AS (
                SELECT ofi.id_obligacion_financiera
                FROM obligacion_financiera_indexacion ofi
                JOIN obligaciones o
                  ON o.id_obligacion_financiera = ofi.id_obligacion_financiera
                WHERE ofi.deleted_at IS NULL
            )
            SELECT
                (
                    SELECT COUNT(*)
                    FROM plan_pago_venta_bloque b
                    WHERE b.id_plan_pago_venta = :id_plan_pago_venta
                      AND b.deleted_at IS NULL
                ) AS cantidad_bloques,
                (SELECT COUNT(*) FROM obligaciones) AS cantidad_obligaciones,
                COALESCE((
                    SELECT SUM(importe_componente)
                    FROM composiciones
                    WHERE codigo_concepto_financiero = 'CAPITAL_VENTA'
                ), 0) AS total_capital,
                COALESCE((
                    SELECT SUM(importe_componente)
                    FROM composiciones
                    WHERE codigo_concepto_financiero = 'INTERES_FINANCIERO'
                ), 0) AS total_interes,
                COALESCE((
                    SELECT SUM(importe_componente)
                    FROM composiciones
                    WHERE codigo_concepto_financiero = 'AJUSTE_INDEXACION'
                ), 0) AS total_ajuste_indexacion,
                COALESCE((SELECT SUM(importe_total) FROM obligaciones), 0) AS total_obligaciones,
                (SELECT COUNT(*) FROM indexaciones) AS cantidad_obligaciones_con_indexacion,
                COALESCE((SELECT SUM(cantidad_obligados) FROM obligados), 0) AS cantidad_obligados_total,
                (
                    SELECT COUNT(*)
                    FROM obligados
                    WHERE cantidad_obligados > 1
                ) AS cantidad_obligaciones_con_multiples_obligados,
                (
                    SELECT COUNT(*)
                    FROM obligaciones o
                    LEFT JOIN indexaciones i
                      ON i.id_obligacion_financiera = o.id_obligacion_financiera
                    WHERE o.metodo_liquidacion = 'INDEXACION'
                      AND i.id_obligacion_financiera IS NULL
                ) AS cantidad_obligaciones_proyectadas_sin_indexacion
            """)
        row = (
            self.db.execute(stmt, {"id_plan_pago_venta": id_plan_pago_venta})
            .mappings()
            .one()
        )
        return dict(row)

    def upsert_plan_pago_venta_borrador(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        existing = self.get_plan_pago_venta_vivo(values["id_venta"])
        if existing is not None:
            stmt = text("""
                UPDATE plan_pago_venta
                SET
                    metodo_plan_pago = :metodo_plan_pago,
                    estado_plan_pago = 'BORRADOR',
                    moneda = :moneda,
                    monto_total_plan = :monto_total_plan,
                    cantidad_cuotas = :cantidad_cuotas,
                    periodicidad = :periodicidad,
                    fecha_primer_vencimiento = :fecha_primer_vencimiento,
                    importe_anticipo = :importe_anticipo,
                    fecha_vencimiento_anticipo = :fecha_vencimiento_anticipo,
                    regla_redondeo = :regla_redondeo,
                    observaciones = :observaciones,
                    updated_at = :updated_at,
                    id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                    op_id_ultima_modificacion = :op_id_ultima_modificacion
                WHERE id_plan_pago_venta = :id_plan_pago_venta
                  AND deleted_at IS NULL
                RETURNING
                    id_plan_pago_venta,
                    id_venta,
                    metodo_plan_pago,
                    estado_plan_pago,
                    moneda,
                    monto_total_plan,
                    cantidad_cuotas,
                    periodicidad,
                    fecha_primer_vencimiento,
                    importe_anticipo,
                    fecha_vencimiento_anticipo,
                    regla_redondeo,
                    observaciones
                """)
            row = (
                self.db.execute(
                    stmt,
                    {**values, "id_plan_pago_venta": existing["id_plan_pago_venta"]},
                )
                .mappings()
                .one()
            )
            return dict(row)

        stmt = text("""
            INSERT INTO plan_pago_venta (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_venta,
                metodo_plan_pago,
                estado_plan_pago,
                moneda,
                monto_total_plan,
                cantidad_cuotas,
                periodicidad,
                fecha_primer_vencimiento,
                importe_anticipo,
                fecha_vencimiento_anticipo,
                regla_redondeo,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_venta,
                :metodo_plan_pago,
                :estado_plan_pago,
                :moneda,
                :monto_total_plan,
                :cantidad_cuotas,
                :periodicidad,
                :fecha_primer_vencimiento,
                :importe_anticipo,
                :fecha_vencimiento_anticipo,
                :regla_redondeo,
                :observaciones
            )
            RETURNING
                id_plan_pago_venta,
                id_venta,
                metodo_plan_pago,
                estado_plan_pago,
                moneda,
                monto_total_plan,
                cantidad_cuotas,
                periodicidad,
                fecha_primer_vencimiento,
                importe_anticipo,
                fecha_vencimiento_anticipo,
                regla_redondeo,
                observaciones
            """)
        row = self.db.execute(stmt, values).mappings().one()
        return dict(row)

    def mark_plan_pago_venta_generado(
        self,
        *,
        id_plan_pago_venta: int,
        updated_at: Any,
        id_instalacion_ultima_modificacion: int | None,
        op_id_ultima_modificacion: Any,
    ) -> dict[str, Any]:
        stmt = text("""
            UPDATE plan_pago_venta
            SET
                estado_plan_pago = 'GENERADO',
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_plan_pago_venta = :id_plan_pago_venta
              AND deleted_at IS NULL
            RETURNING
                id_plan_pago_venta,
                id_venta,
                metodo_plan_pago,
                estado_plan_pago,
                moneda,
                monto_total_plan,
                cantidad_cuotas,
                periodicidad,
                fecha_primer_vencimiento,
                importe_anticipo,
                fecha_vencimiento_anticipo,
                regla_redondeo,
                observaciones
            """)
        row = (
            self.db.execute(
                stmt,
                {
                    "id_plan_pago_venta": id_plan_pago_venta,
                    "updated_at": updated_at,
                    "id_instalacion_ultima_modificacion": id_instalacion_ultima_modificacion,
                    "op_id_ultima_modificacion": op_id_ultima_modificacion,
                },
            )
            .mappings()
            .one()
        )
        return dict(row)

    def get_or_create_relacion_generadora(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text("""
            INSERT INTO relacion_generadora (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                tipo_origen,
                id_origen,
                descripcion
            )
            VALUES (
                gen_random_uuid(),
                1,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :tipo_origen,
                :id_origen,
                :descripcion
            )
            ON CONFLICT (tipo_origen, id_origen) WHERE (deleted_at IS NULL)
            DO UPDATE SET updated_at = relacion_generadora.updated_at
            RETURNING
                id_relacion_generadora,
                tipo_origen,
                id_origen,
                descripcion,
                estado_relacion_generadora
            """)
        row = self.db.execute(stmt, values).mappings().one()
        return dict(row)

    def get_or_create_generacion_cronograma(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text("""
            INSERT INTO generacion_cronograma_financiero (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_relacion_generadora,
                id_plan_pago_venta,
                tipo_generacion,
                clave_generacion,
                estado_generacion,
                fecha_generacion,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_relacion_generadora,
                :id_plan_pago_venta,
                :tipo_generacion,
                :clave_generacion,
                :estado_generacion,
                :fecha_generacion,
                :observaciones
            )
            ON CONFLICT (id_relacion_generadora, clave_generacion)
            WHERE deleted_at IS NULL
              AND estado_generacion <> 'ANULADA'
            DO UPDATE SET updated_at = generacion_cronograma_financiero.updated_at
            RETURNING
                id_generacion_cronograma_financiero,
                id_relacion_generadora,
                id_plan_pago_venta,
                tipo_generacion,
                clave_generacion,
                estado_generacion,
                fecha_generacion
            """)
        row = self.db.execute(stmt, values).mappings().one()
        return dict(row)

    def get_or_create_plan_pago_venta_bloque(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text("""
            INSERT INTO plan_pago_venta_bloque (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_plan_pago_venta,
                numero_bloque,
                tipo_bloque,
                etiqueta_bloque,
                clave_bloque,
                cantidad_cuotas,
                importe_total_bloque,
                importe_cuota,
                fecha_vencimiento,
                fecha_primer_vencimiento,
                periodicidad,
                regla_redondeo,
                metodo_liquidacion,
                tasa_interes_directo_periodica,
                cantidad_periodos,
                base_calculo_interes,
                concepto_financiero_codigo,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_plan_pago_venta,
                :numero_bloque,
                :tipo_bloque,
                :etiqueta_bloque,
                :clave_bloque,
                :cantidad_cuotas,
                :importe_total_bloque,
                :importe_cuota,
                :fecha_vencimiento,
                :fecha_primer_vencimiento,
                :periodicidad,
                :regla_redondeo,
                :metodo_liquidacion,
                :tasa_interes_directo_periodica,
                :cantidad_periodos,
                :base_calculo_interes,
                :concepto_financiero_codigo,
                :observaciones
            )
            ON CONFLICT (id_plan_pago_venta, clave_bloque)
            WHERE deleted_at IS NULL
            DO UPDATE SET updated_at = plan_pago_venta_bloque.updated_at
            RETURNING
                id_plan_pago_venta_bloque,
                id_plan_pago_venta,
                numero_bloque,
                tipo_bloque,
                etiqueta_bloque,
                clave_bloque,
                cantidad_cuotas,
                importe_total_bloque,
                importe_cuota,
                fecha_vencimiento,
                fecha_primer_vencimiento,
                periodicidad,
                regla_redondeo,
                metodo_liquidacion,
                tasa_interes_directo_periodica,
                cantidad_periodos,
                base_calculo_interes,
                concepto_financiero_codigo
            """)
        row = self.db.execute(stmt, values).mappings().one()
        bloque = dict(row)
        self._ensure_plan_pago_venta_bloque_compatible(bloque, values)
        return bloque

    def _ensure_plan_pago_venta_bloque_compatible(
        self, bloque: dict[str, Any], expected: dict[str, Any]
    ) -> None:
        fields_default = (
            "id_plan_pago_venta",
            "numero_bloque",
            "tipo_bloque",
            "etiqueta_bloque",
            "clave_bloque",
            "cantidad_cuotas",
            "importe_total_bloque",
            "importe_cuota",
            "fecha_vencimiento",
            "fecha_primer_vencimiento",
            "periodicidad",
            "regla_redondeo",
            "concepto_financiero_codigo",
        )
        incompatible = [
            field
            for field in fields_default
            if self._normalize_bloque_value(bloque.get(field))
            != self._normalize_bloque_value(expected.get(field))
        ]
        if self._normalize_upper_or_none(
            bloque.get("metodo_liquidacion")
        ) != self._normalize_upper_or_none(expected.get("metodo_liquidacion")):
            incompatible.append("metodo_liquidacion")
        if self._normalize_tasa_or_none(
            bloque.get("tasa_interes_directo_periodica")
        ) != self._normalize_tasa_or_none(
            expected.get("tasa_interes_directo_periodica")
        ):
            incompatible.append("tasa_interes_directo_periodica")
        if self._normalize_int_or_none(
            bloque.get("cantidad_periodos")
        ) != self._normalize_int_or_none(expected.get("cantidad_periodos")):
            incompatible.append("cantidad_periodos")
        if self._normalize_upper_or_none(
            bloque.get("base_calculo_interes")
        ) != self._normalize_upper_or_none(expected.get("base_calculo_interes")):
            incompatible.append("base_calculo_interes")
        if incompatible:
            clave = expected.get("clave_bloque") or bloque.get("clave_bloque")
            raise ValueError(
                "PLAN_PAGO_VENTA_BLOQUE_INCOMPATIBLE:"
                f"{clave}:{','.join(incompatible)}"
            )

    @staticmethod
    def _normalize_bloque_value(value: Any) -> Any:
        if isinstance(value, Decimal):
            return value.quantize(Decimal("0.01"))
        if isinstance(value, date):
            return value.isoformat()
        return value

    @staticmethod
    def _normalize_tasa_or_none(value: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value)).quantize(Decimal("0.00000001"))

    @staticmethod
    def _normalize_int_or_none(value: Any) -> int | None:
        if value is None:
            return None
        return int(value)

    @staticmethod
    def _normalize_upper_or_none(value: Any) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip().upper()
        return normalized or None

    def get_or_create_plan_pago_venta_bloque_indexacion(
        self, payload: Any
    ) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text("""
            INSERT INTO plan_pago_venta_bloque_indexacion (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_plan_pago_venta_bloque,
                id_indice_financiero,
                fecha_base_indice,
                valor_base_indice,
                modo_indexacion,
                base_calculo_indexacion,
                tipo_generacion_indexada,
                politica_valor_no_disponible,
                conserva_capital_original,
                genera_ajuste_por_diferencia,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_plan_pago_venta_bloque,
                :id_indice_financiero,
                :fecha_base_indice,
                :valor_base_indice,
                :modo_indexacion,
                :base_calculo_indexacion,
                :tipo_generacion_indexada,
                :politica_valor_no_disponible,
                :conserva_capital_original,
                :genera_ajuste_por_diferencia,
                :observaciones
            )
            ON CONFLICT (id_plan_pago_venta_bloque)
            WHERE deleted_at IS NULL
            DO UPDATE SET updated_at = plan_pago_venta_bloque_indexacion.updated_at
            RETURNING
                id_plan_pago_venta_bloque_indexacion,
                id_plan_pago_venta_bloque,
                id_indice_financiero,
                fecha_base_indice,
                valor_base_indice,
                modo_indexacion,
                base_calculo_indexacion,
                tipo_generacion_indexada,
                politica_valor_no_disponible,
                conserva_capital_original,
                genera_ajuste_por_diferencia,
                observaciones
            """)
        row = self.db.execute(stmt, values).mappings().one()
        indexacion = dict(row)
        self._ensure_plan_pago_venta_bloque_indexacion_compatible(indexacion, values)
        return indexacion

    def get_plan_pago_venta_bloque_indexacion(
        self, id_plan_pago_venta_bloque: int
    ) -> dict[str, Any] | None:
        stmt = text("""
            SELECT
                id_plan_pago_venta_bloque_indexacion,
                id_plan_pago_venta_bloque,
                id_indice_financiero,
                fecha_base_indice,
                valor_base_indice,
                modo_indexacion,
                base_calculo_indexacion,
                tipo_generacion_indexada,
                politica_valor_no_disponible,
                conserva_capital_original,
                genera_ajuste_por_diferencia,
                observaciones
            FROM plan_pago_venta_bloque_indexacion
            WHERE id_plan_pago_venta_bloque = :id_plan_pago_venta_bloque
              AND deleted_at IS NULL
            """)
        row = (
            self.db.execute(
                stmt, {"id_plan_pago_venta_bloque": id_plan_pago_venta_bloque}
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def _ensure_plan_pago_venta_bloque_indexacion_compatible(
        self, indexacion: dict[str, Any], expected: dict[str, Any]
    ) -> None:
        fields_default = (
            "id_plan_pago_venta_bloque",
            "id_indice_financiero",
            "fecha_base_indice",
            "conserva_capital_original",
            "genera_ajuste_por_diferencia",
        )
        incompatible = [
            field
            for field in fields_default
            if self._normalize_indexacion_value(indexacion.get(field))
            != self._normalize_indexacion_value(expected.get(field))
        ]
        if self._normalize_indice_value(
            indexacion.get("valor_base_indice")
        ) != self._normalize_indice_value(expected.get("valor_base_indice")):
            incompatible.append("valor_base_indice")
        for field in (
            "modo_indexacion",
            "base_calculo_indexacion",
            "tipo_generacion_indexada",
            "politica_valor_no_disponible",
        ):
            if self._normalize_upper_or_none(
                indexacion.get(field)
            ) != self._normalize_upper_or_none(expected.get(field)):
                incompatible.append(field)
        if incompatible:
            raise ValueError(
                "PLAN_PAGO_VENTA_BLOQUE_INDEXACION_INCOMPATIBLE:"
                f"{expected.get('id_plan_pago_venta_bloque')}:"
                f"{','.join(incompatible)}"
            )

    @staticmethod
    def _normalize_indexacion_value(value: Any) -> Any:
        if isinstance(value, date):
            return value.isoformat()
        return value

    @staticmethod
    def _normalize_indice_value(value: Any) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value)).quantize(Decimal("0.00000001"))

    def get_obligaciones_plan_pago_venta_v2_minimas(
        self, id_plan_pago_venta: int
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT
                o.numero_obligacion,
                o.tipo_item_cronograma,
                o.etiqueta_obligacion,
                o.clave_funcional_origen,
                o.fecha_vencimiento,
                o.importe_total
            FROM obligacion_financiera o
            JOIN plan_pago_venta_bloque b
              ON b.id_plan_pago_venta_bloque = o.id_plan_pago_venta_bloque
             AND b.deleted_at IS NULL
            WHERE b.id_plan_pago_venta = :id_plan_pago_venta
              AND o.deleted_at IS NULL
            ORDER BY o.numero_obligacion ASC
            """)
        rows = (
            self.db.execute(stmt, {"id_plan_pago_venta": id_plan_pago_venta})
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def get_plan_pago_venta_bloques(
        self, id_plan_pago_venta: int
    ) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT
                id_plan_pago_venta_bloque,
                id_plan_pago_venta,
                numero_bloque,
                tipo_bloque,
                etiqueta_bloque,
                clave_bloque,
                cantidad_cuotas,
                importe_total_bloque,
                importe_cuota,
                fecha_vencimiento,
                fecha_primer_vencimiento,
                periodicidad,
                regla_redondeo,
                metodo_liquidacion,
                tasa_interes_directo_periodica,
                cantidad_periodos,
                base_calculo_interes,
                concepto_financiero_codigo,
                observaciones
            FROM plan_pago_venta_bloque
            WHERE id_plan_pago_venta = :id_plan_pago_venta
              AND deleted_at IS NULL
            ORDER BY numero_bloque ASC
            """)
        rows = (
            self.db.execute(stmt, {"id_plan_pago_venta": id_plan_pago_venta})
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def get_concepto_financiero_by_codigo(self, codigo: str) -> dict[str, Any] | None:
        stmt = text("""
            SELECT id_concepto_financiero, codigo_concepto_financiero
            FROM concepto_financiero
            WHERE codigo_concepto_financiero = :codigo
              AND estado_concepto_financiero = 'ACTIVO'
              AND deleted_at IS NULL
            """)
        row = self.db.execute(stmt, {"codigo": codigo}).mappings().one_or_none()
        return dict(row) if row else None

    def get_compradores_financieros_venta(self, id_venta: int) -> list[dict[str, Any]]:
        stmt = text("""
            SELECT
                rpr.id_relacion_persona_rol,
                rpr.id_persona,
                rp.codigo_rol,
                rpr.porcentaje_responsabilidad
            FROM relacion_persona_rol rpr
            JOIN rol_participacion rp
              ON rp.id_rol_participacion = rpr.id_rol_participacion
             AND rp.deleted_at IS NULL
             AND rp.estado_rol = 'ACTIVO'
            JOIN persona p
              ON p.id_persona = rpr.id_persona
             AND p.deleted_at IS NULL
            WHERE rpr.tipo_relacion = 'venta'
              AND rpr.id_relacion = :id_venta
              AND rpr.deleted_at IS NULL
              AND rpr.fecha_desde <= CURRENT_TIMESTAMP
              AND (rpr.fecha_hasta IS NULL OR rpr.fecha_hasta >= CURRENT_TIMESTAMP)
              AND UPPER(rp.codigo_rol) = 'COMPRADOR'
            ORDER BY rpr.fecha_desde ASC, rpr.id_relacion_persona_rol ASC
            """)
        rows = self.db.execute(stmt, {"id_venta": id_venta}).mappings().all()
        return [dict(row) for row in rows]

    def get_indice_financiero_activo(
        self, id_indice_financiero: int
    ) -> dict[str, Any] | None:
        if id_indice_financiero <= 0:
            return None
        stmt = text("""
            SELECT id_indice_financiero, codigo_indice_financiero
            FROM indice_financiero
            WHERE id_indice_financiero = :id_indice_financiero
              AND estado_indice_financiero = 'ACTIVO'
              AND deleted_at IS NULL
            """)
        row = (
            self.db.execute(stmt, {"id_indice_financiero": id_indice_financiero})
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def get_valor_publicado_por_id_y_fecha(
        self,
        id_indice_financiero: int,
        fecha_objetivo: date,
    ) -> dict[str, Any] | None:
        if id_indice_financiero <= 0:
            return None
        stmt = text("""
            SELECT
                i.id_indice_financiero,
                i.codigo_indice_financiero,
                i.nombre_indice_financiero,
                iv.id_indice_financiero_valor,
                iv.fecha_valor,
                iv.valor_indice,
                iv.fecha_publicacion,
                iv.fuente_valor
            FROM indice_financiero AS i
            JOIN indice_financiero_valor AS iv
              ON iv.id_indice_financiero = i.id_indice_financiero
            WHERE i.id_indice_financiero = :id_indice_financiero
              AND i.estado_indice_financiero = 'ACTIVO'
              AND i.deleted_at IS NULL
              AND iv.estado_valor_indice = 'PUBLICADO'
              AND iv.fecha_publicacion IS NOT NULL
              AND iv.deleted_at IS NULL
              AND iv.fecha_valor <= :fecha_objetivo
            ORDER BY iv.fecha_valor DESC
            LIMIT 1
            """)
        row = (
            self.db.execute(
                stmt,
                {
                    "id_indice_financiero": id_indice_financiero,
                    "fecha_objetivo": fecha_objetivo,
                },
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def diagnosticar_valor_publicado_no_aplicable(
        self, id_indice_financiero: int, fecha_objetivo: date
    ) -> str:
        if self.get_indice_financiero_activo(id_indice_financiero) is None:
            return "INDICE_FINANCIERO_INACTIVO"
        stmt = text("""
            SELECT 1
            FROM indice_financiero_valor AS iv
            WHERE iv.id_indice_financiero = :id_indice_financiero
              AND iv.estado_valor_indice = 'PUBLICADO'
              AND iv.fecha_publicacion IS NULL
              AND iv.deleted_at IS NULL
              AND iv.fecha_valor <= :fecha_objetivo
            ORDER BY iv.fecha_valor DESC
            LIMIT 1
            """)
        row = self.db.execute(
            stmt,
            {
                "id_indice_financiero": id_indice_financiero,
                "fecha_objetivo": fecha_objetivo,
            },
        ).first()
        if row is not None:
            return "FECHA_PUBLICACION_INDICE_INCOMPLETA"
        return "VALOR_INDICE_PUBLICADO_INEXISTENTE"

    def create_obligacion_cronograma_v2_if_not_exists(
        self, payload: Any
    ) -> dict[str, Any]:
        values = self._values(payload)
        existing = self._get_obligacion_by_clave_or_none(
            id_relacion_generadora=values["id_relacion_generadora"],
            clave_funcional_origen=values["clave_funcional_origen"],
        )
        if existing is not None:
            existing_bloque = existing["id_plan_pago_venta_bloque"]
            expected_bloque = values["id_plan_pago_venta_bloque"]
            if existing_bloque is None and expected_bloque is not None:
                updated = self._set_obligacion_plan_pago_venta_bloque(
                    id_obligacion_financiera=existing["id_obligacion_financiera"],
                    id_plan_pago_venta_bloque=expected_bloque,
                    updated_at=values["updated_at"],
                    id_instalacion_ultima_modificacion=values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    op_id_ultima_modificacion=values["op_id_ultima_modificacion"],
                )
                self._create_obligados(values, updated["id_obligacion_financiera"])
                updated["__created"] = False
                return updated
            if (
                existing_bloque is not None
                and expected_bloque is not None
                and existing_bloque != expected_bloque
            ):
                raise ValueError(
                    "OBLIGACION_PLAN_PAGO_VENTA_BLOQUE_INCOMPATIBLE:"
                    f"{values['clave_funcional_origen']}"
                )
            self._create_obligados(values, existing["id_obligacion_financiera"])
            existing["__created"] = False
            return existing

        ob_stmt = text("""
            INSERT INTO obligacion_financiera (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_relacion_generadora,
                id_generacion_cronograma_financiero,
                id_plan_pago_venta_bloque,
                numero_obligacion,
                tipo_item_cronograma,
                etiqueta_obligacion,
                clave_funcional_origen,
                fecha_emision,
                fecha_vencimiento,
                importe_total,
                saldo_pendiente,
                moneda,
                estado_obligacion
            )
            VALUES (
                gen_random_uuid(),
                1,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_relacion_generadora,
                :id_generacion_cronograma_financiero,
                :id_plan_pago_venta_bloque,
                :numero_obligacion,
                :tipo_item_cronograma,
                :etiqueta_obligacion,
                :clave_funcional_origen,
                :fecha_emision,
                :fecha_vencimiento,
                :importe_total,
                :importe_total,
                :moneda,
                :estado_obligacion
            )
            ON CONFLICT (id_relacion_generadora, clave_funcional_origen)
            WHERE deleted_at IS NULL
              AND clave_funcional_origen IS NOT NULL
            DO NOTHING
            RETURNING
                id_obligacion_financiera,
                id_relacion_generadora,
                id_generacion_cronograma_financiero,
                id_plan_pago_venta_bloque,
                numero_obligacion,
                tipo_item_cronograma,
                etiqueta_obligacion,
                clave_funcional_origen,
                fecha_vencimiento,
                importe_total,
                saldo_pendiente,
                moneda,
                estado_obligacion
            """)
        ob_row = self.db.execute(ob_stmt, values).mappings().one_or_none()
        if ob_row is None:
            existing = self._get_obligacion_by_clave(
                id_relacion_generadora=values["id_relacion_generadora"],
                clave_funcional_origen=values["clave_funcional_origen"],
            )
            self._create_obligados(values, existing["id_obligacion_financiera"])
            existing["__created"] = False
            return existing

        obligacion = dict(ob_row)
        self._create_composicion(values, obligacion["id_obligacion_financiera"])
        self._create_obligados(values, obligacion["id_obligacion_financiera"])
        obligacion["__created"] = True
        return obligacion

    def get_obligaciones_cronograma_by_claves(
        self,
        *,
        id_relacion_generadora: int,
        claves_funcionales: list[str],
    ) -> list[dict[str, Any]]:
        if not claves_funcionales:
            return []
        stmt = text("""
            SELECT
                o.id_obligacion_financiera,
                o.id_relacion_generadora,
                o.id_generacion_cronograma_financiero,
                o.id_plan_pago_venta_bloque,
                o.numero_obligacion,
                o.tipo_item_cronograma,
                o.etiqueta_obligacion,
                o.clave_funcional_origen,
                o.fecha_vencimiento,
                o.importe_total,
                o.saldo_pendiente,
                o.moneda,
                o.estado_obligacion
            FROM obligacion_financiera o
            WHERE o.id_relacion_generadora = :id_relacion_generadora
              AND o.clave_funcional_origen = ANY(:claves_funcionales)
              AND o.deleted_at IS NULL
            ORDER BY o.numero_obligacion ASC
            """)
        rows = (
            self.db.execute(
                stmt,
                {
                    "id_relacion_generadora": id_relacion_generadora,
                    "claves_funcionales": claves_funcionales,
                },
            )
            .mappings()
            .all()
        )
        return [dict(row) for row in rows]

    def _get_obligacion_by_clave(
        self,
        *,
        id_relacion_generadora: int,
        clave_funcional_origen: str,
    ) -> dict[str, Any]:
        row = self._get_obligacion_by_clave_or_none(
            id_relacion_generadora=id_relacion_generadora,
            clave_funcional_origen=clave_funcional_origen,
        )
        if row is None:
            raise LookupError("OBLIGACION_CRONOGRAMA_NOT_FOUND")
        return row

    def _get_obligacion_by_clave_or_none(
        self,
        *,
        id_relacion_generadora: int,
        clave_funcional_origen: str,
    ) -> dict[str, Any] | None:
        rows = self.get_obligaciones_cronograma_by_claves(
            id_relacion_generadora=id_relacion_generadora,
            claves_funcionales=[clave_funcional_origen],
        )
        return rows[0] if rows else None

    def _set_obligacion_plan_pago_venta_bloque(
        self,
        *,
        id_obligacion_financiera: int,
        id_plan_pago_venta_bloque: int,
        updated_at: Any,
        id_instalacion_ultima_modificacion: int | None,
        op_id_ultima_modificacion: Any,
    ) -> dict[str, Any]:
        stmt = text("""
            UPDATE obligacion_financiera
            SET
                id_plan_pago_venta_bloque = :id_plan_pago_venta_bloque,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND deleted_at IS NULL
              AND id_plan_pago_venta_bloque IS NULL
            """)
        self.db.execute(
            stmt,
            {
                "id_obligacion_financiera": id_obligacion_financiera,
                "id_plan_pago_venta_bloque": id_plan_pago_venta_bloque,
                "updated_at": updated_at,
                "id_instalacion_ultima_modificacion": id_instalacion_ultima_modificacion,
                "op_id_ultima_modificacion": op_id_ultima_modificacion,
            },
        )
        stmt = text("""
            SELECT
                o.id_obligacion_financiera,
                o.id_relacion_generadora,
                o.id_generacion_cronograma_financiero,
                o.id_plan_pago_venta_bloque,
                o.numero_obligacion,
                o.tipo_item_cronograma,
                o.etiqueta_obligacion,
                o.clave_funcional_origen,
                o.fecha_vencimiento,
                o.importe_total,
                o.saldo_pendiente,
                o.moneda,
                o.estado_obligacion
            FROM obligacion_financiera o
            WHERE o.id_obligacion_financiera = :id_obligacion_financiera
              AND o.deleted_at IS NULL
            """)
        row = (
            self.db.execute(
                stmt, {"id_obligacion_financiera": id_obligacion_financiera}
            )
            .mappings()
            .one()
        )
        return dict(row)

    def get_obligacion_financiera_indexacion(
        self, id_obligacion_financiera: int
    ) -> dict[str, Any] | None:
        stmt = text("""
            SELECT
                id_obligacion_financiera_indexacion,
                id_obligacion_financiera,
                id_plan_pago_venta_bloque_indexacion,
                id_indice_financiero,
                id_indice_financiero_valor,
                fecha_base_indice,
                valor_base_indice,
                fecha_aplicacion_indice,
                valor_aplicado_indice,
                coeficiente_indexacion,
                modo_indexacion,
                base_calculo_indexacion,
                tipo_generacion_indexada,
                observaciones
            FROM obligacion_financiera_indexacion
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND deleted_at IS NULL
            """)
        row = (
            self.db.execute(
                stmt, {"id_obligacion_financiera": id_obligacion_financiera}
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def get_or_create_obligacion_financiera_indexacion(
        self, payload: Any
    ) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text("""
            INSERT INTO obligacion_financiera_indexacion (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_obligacion_financiera,
                id_plan_pago_venta_bloque_indexacion,
                id_indice_financiero,
                id_indice_financiero_valor,
                fecha_base_indice,
                valor_base_indice,
                fecha_aplicacion_indice,
                valor_aplicado_indice,
                coeficiente_indexacion,
                modo_indexacion,
                base_calculo_indexacion,
                tipo_generacion_indexada,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_obligacion_financiera,
                :id_plan_pago_venta_bloque_indexacion,
                :id_indice_financiero,
                :id_indice_financiero_valor,
                :fecha_base_indice,
                :valor_base_indice,
                :fecha_aplicacion_indice,
                :valor_aplicado_indice,
                :coeficiente_indexacion,
                :modo_indexacion,
                :base_calculo_indexacion,
                :tipo_generacion_indexada,
                :observaciones
            )
            ON CONFLICT (id_obligacion_financiera)
            WHERE deleted_at IS NULL
            DO UPDATE SET updated_at = obligacion_financiera_indexacion.updated_at
            RETURNING
                id_obligacion_financiera_indexacion,
                id_obligacion_financiera,
                id_plan_pago_venta_bloque_indexacion,
                id_indice_financiero,
                id_indice_financiero_valor,
                fecha_base_indice,
                valor_base_indice,
                fecha_aplicacion_indice,
                valor_aplicado_indice,
                coeficiente_indexacion,
                modo_indexacion,
                base_calculo_indexacion,
                tipo_generacion_indexada,
                observaciones
            """)
        row = self.db.execute(stmt, values).mappings().one()
        indexacion = dict(row)
        self.ensure_obligacion_financiera_indexacion_compatible(indexacion, values)
        return indexacion

    def ensure_obligacion_financiera_indexacion_compatible(
        self, indexacion: dict[str, Any], expected: dict[str, Any]
    ) -> None:
        fields_default = (
            "id_obligacion_financiera",
            "id_plan_pago_venta_bloque_indexacion",
            "id_indice_financiero",
            "id_indice_financiero_valor",
            "fecha_base_indice",
            "fecha_aplicacion_indice",
        )
        incompatible = [
            field
            for field in fields_default
            if self._normalize_indexacion_value(indexacion.get(field))
            != self._normalize_indexacion_value(expected.get(field))
        ]
        for field in (
            "valor_base_indice",
            "valor_aplicado_indice",
            "coeficiente_indexacion",
        ):
            if self._normalize_indice_value(
                indexacion.get(field)
            ) != self._normalize_indice_value(expected.get(field)):
                incompatible.append(field)
        for field in (
            "modo_indexacion",
            "base_calculo_indexacion",
            "tipo_generacion_indexada",
        ):
            if self._normalize_upper_or_none(
                indexacion.get(field)
            ) != self._normalize_upper_or_none(expected.get(field)):
                incompatible.append(field)
        if incompatible:
            raise ValueError(
                "PLAN_PAGO_VENTA_OBLIGACION_INDEXACION_INCOMPATIBLE:"
                f"{expected.get('id_obligacion_financiera')}:"
                f"{','.join(incompatible)}"
            )

    def _create_composicion(
        self, values: dict[str, Any], id_obligacion_financiera: int
    ) -> None:
        composiciones = values.get("composiciones") or [
            {
                "id_concepto_financiero": values["id_concepto_financiero"],
                "codigo_concepto_financiero": values["codigo_concepto_financiero"],
                "importe_componente": values["importe_total"],
            }
        ]
        stmt = text("""
            INSERT INTO composicion_obligacion (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_obligacion_financiera,
                id_concepto_financiero,
                orden_composicion,
                importe_componente,
                saldo_componente,
                moneda_componente
            )
            VALUES (
                gen_random_uuid(),
                1,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_obligacion_financiera,
                :id_concepto_financiero,
                :orden_composicion,
                :importe_componente,
                :importe_componente,
                :moneda
            )
            """)
        for orden, composicion in enumerate(composiciones, start=1):
            self.db.execute(
                stmt,
                {
                    **values,
                    **composicion,
                    "orden_composicion": orden,
                    "id_obligacion_financiera": id_obligacion_financiera,
                },
            )

    def _create_obligados(
        self, values: dict[str, Any], id_obligacion_financiera: int
    ) -> None:
        obligados = values.get("obligados")
        if not obligados:
            if (
                values.get("id_persona_obligado") is None
                or values.get("rol_obligado") is None
            ):
                raise ValueError("OBLIGACION_OBLIGADO_REQUERIDO")
            obligados = [
                {
                    "id_persona": values["id_persona_obligado"],
                    "rol_obligado": values["rol_obligado"],
                    "porcentaje_responsabilidad": Decimal("100.00"),
                }
            ]

        expected: set[tuple[int, str]] = set()
        roles: set[str] = set()
        for obligado_payload in obligados:
            obligado = self._values(obligado_payload)
            expected.add((obligado["id_persona"], obligado["rol_obligado"]))
            roles.add(obligado["rol_obligado"])
            self._get_or_create_obligado(
                values=values,
                id_obligacion_financiera=id_obligacion_financiera,
                id_persona=obligado["id_persona"],
                rol_obligado=obligado["rol_obligado"],
                porcentaje_responsabilidad=obligado["porcentaje_responsabilidad"],
            )
        self._validate_obligados_compatibles(
            id_obligacion_financiera=id_obligacion_financiera,
            roles=roles,
            expected=expected,
        )

    def _get_or_create_obligado(
        self,
        *,
        values: dict[str, Any],
        id_obligacion_financiera: int,
        id_persona: int,
        rol_obligado: str,
        porcentaje_responsabilidad: Decimal,
    ) -> dict[str, Any]:
        existing = self._get_obligado(
            id_obligacion_financiera=id_obligacion_financiera,
            id_persona=id_persona,
            rol_obligado=rol_obligado,
        )
        porcentaje = Decimal(str(porcentaje_responsabilidad)).quantize(Decimal("0.01"))
        if existing is not None:
            existing_porcentaje = Decimal(
                str(existing["porcentaje_responsabilidad"])
            ).quantize(Decimal("0.01"))
            if existing_porcentaje != porcentaje:
                raise ValueError("OBLIGACION_OBLIGADO_INCOMPATIBLE")
            return existing

        stmt = text("""
            INSERT INTO obligacion_obligado (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_obligacion_financiera,
                id_persona,
                rol_obligado,
                porcentaje_responsabilidad
            )
            VALUES (
                gen_random_uuid(),
                1,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_obligacion_financiera,
                :id_persona,
                :rol_obligado,
                :porcentaje_responsabilidad
            )
            RETURNING
                id_obligacion_obligado,
                id_obligacion_financiera,
                id_persona,
                rol_obligado,
                porcentaje_responsabilidad
            """)
        row = (
            self.db.execute(
                stmt,
                {
                    **values,
                    "id_obligacion_financiera": id_obligacion_financiera,
                    "id_persona": id_persona,
                    "rol_obligado": rol_obligado,
                    "porcentaje_responsabilidad": porcentaje,
                },
            )
            .mappings()
            .one()
        )
        return dict(row)

    def _validate_obligados_compatibles(
        self,
        *,
        id_obligacion_financiera: int,
        roles: set[str],
        expected: set[tuple[int, str]],
    ) -> None:
        if not roles:
            return
        stmt = text("""
            SELECT id_persona, rol_obligado
            FROM obligacion_obligado
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND rol_obligado = ANY(:roles)
              AND deleted_at IS NULL
            """)
        rows = (
            self.db.execute(
                stmt,
                {
                    "id_obligacion_financiera": id_obligacion_financiera,
                    "roles": list(roles),
                },
            )
            .mappings()
            .all()
        )
        found = [(row["id_persona"], row["rol_obligado"]) for row in rows]
        if len(found) != len(set(found)) or any(row not in expected for row in found):
            raise ValueError("OBLIGACION_OBLIGADO_INCOMPATIBLE")

    def _get_obligado(
        self, *, id_obligacion_financiera: int, id_persona: int, rol_obligado: str
    ) -> dict[str, Any] | None:
        stmt = text("""
            SELECT
                id_obligacion_obligado,
                id_obligacion_financiera,
                id_persona,
                rol_obligado,
                porcentaje_responsabilidad
            FROM obligacion_obligado
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND id_persona = :id_persona
              AND rol_obligado = :rol_obligado
              AND deleted_at IS NULL
            ORDER BY id_obligacion_obligado ASC
            LIMIT 1
            """)
        row = (
            self.db.execute(
                stmt,
                {
                    "id_obligacion_financiera": id_obligacion_financiera,
                    "id_persona": id_persona,
                    "rol_obligado": rol_obligado,
                },
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def _create_obligado(
        self, values: dict[str, Any], id_obligacion_financiera: int
    ) -> None:
        self._create_obligados(values, id_obligacion_financiera)
