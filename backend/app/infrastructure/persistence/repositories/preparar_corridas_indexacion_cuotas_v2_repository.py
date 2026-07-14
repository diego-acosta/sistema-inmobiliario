from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class PrepararCorridasIndexacionCuotasV2SqlAlchemyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_valor_publicado(self, id_valor: int) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT iv.id_indice_financiero_valor, iv.id_indice_financiero, iv.fecha_valor,
                   iv.valor_indice, iv.fecha_publicacion, iv.estado_valor_indice
            FROM indice_financiero_valor iv
            JOIN indice_financiero i ON i.id_indice_financiero = iv.id_indice_financiero
            WHERE iv.id_indice_financiero_valor = :id
              AND iv.deleted_at IS NULL
              AND iv.estado_valor_indice = 'PUBLICADO'
              AND i.deleted_at IS NULL
              AND i.estado_indice_financiero = 'ACTIVO'
        """), {"id": id_valor}).mappings().first()
        return dict(row) if row else None

    def list_configuraciones_alcanzadas(self, id_indice_financiero: int, periodo_aplicado: date, fecha_corte: date) -> list[dict[str, Any]]:
        rows = self.db.execute(text("""
            SELECT ppv.id_plan_pago_venta,
                   ppvb.id_plan_pago_venta_bloque,
                   ppvbi.id_plan_pago_venta_bloque_indexacion,
                   ppvbi.fecha_base_indice,
                   ppvbi.valor_base_indice,
                   COUNT(o.id_obligacion_financiera) AS cantidad_obligaciones_analizables
            FROM plan_pago_venta_bloque_indexacion ppvbi
            JOIN plan_pago_venta_bloque ppvb
              ON ppvb.id_plan_pago_venta_bloque = ppvbi.id_plan_pago_venta_bloque
             AND ppvb.deleted_at IS NULL
            JOIN plan_pago_venta ppv
              ON ppv.id_plan_pago_venta = ppvb.id_plan_pago_venta
             AND ppv.deleted_at IS NULL
            LEFT JOIN obligacion_financiera o
              ON o.id_plan_pago_venta_bloque = ppvb.id_plan_pago_venta_bloque
             AND o.deleted_at IS NULL
             AND (o.fecha_vencimiento IS NULL OR o.fecha_vencimiento <= :fecha_corte)
            WHERE ppvbi.deleted_at IS NULL
              AND ppvbi.id_indice_financiero = :id_indice_financiero
              AND ppvbi.fecha_base_indice <= :periodo_aplicado
            GROUP BY ppv.id_plan_pago_venta, ppvb.id_plan_pago_venta_bloque,
                     ppvbi.id_plan_pago_venta_bloque_indexacion, ppvbi.fecha_base_indice,
                     ppvbi.valor_base_indice
            ORDER BY ppv.id_plan_pago_venta, ppvb.id_plan_pago_venta_bloque,
                     ppvbi.id_plan_pago_venta_bloque_indexacion
        """), {"id_indice_financiero": id_indice_financiero, "periodo_aplicado": periodo_aplicado, "fecha_corte": fecha_corte}).mappings().all()
        return [dict(r) for r in rows]

    def get_corrida_existente(self, *, id_plan_pago_venta: int, id_plan_pago_venta_bloque: int, id_plan_pago_venta_bloque_indexacion: int, id_indice_financiero: int, id_indice_financiero_valor_aplicado: int, periodo_aplicado: date) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT id_corrida_indexacion_financiera, estado_corrida, hash_corrida,
                   cantidad_analizada, cantidad_elegible
            FROM corrida_indexacion_financiera
            WHERE id_plan_pago_venta = :id_plan_pago_venta
              AND id_plan_pago_venta_bloque = :id_plan_pago_venta_bloque
              AND id_plan_pago_venta_bloque_indexacion = :id_plan_pago_venta_bloque_indexacion
              AND id_indice_financiero = :id_indice_financiero
              AND id_indice_financiero_valor_aplicado = :id_indice_financiero_valor_aplicado
              AND periodo_aplicado = :periodo_aplicado
              AND origen_corrida = 'PUBLICACION_INDICE'
              AND deleted_at IS NULL
              AND estado_corrida NOT IN ('ANULADA','REEMPLAZADA')
            ORDER BY id_corrida_indexacion_financiera DESC
            LIMIT 1
        """), {
            "id_plan_pago_venta": id_plan_pago_venta,
            "id_plan_pago_venta_bloque": id_plan_pago_venta_bloque,
            "id_plan_pago_venta_bloque_indexacion": id_plan_pago_venta_bloque_indexacion,
            "id_indice_financiero": id_indice_financiero,
            "id_indice_financiero_valor_aplicado": id_indice_financiero_valor_aplicado,
            "periodo_aplicado": periodo_aplicado,
        }).mappings().first()
        return dict(row) if row else None
