from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class PreviewIndexacionCuotasV2SqlAlchemyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_scope(self, command: Any) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT ppv.id_plan_pago_venta, ppvb.id_plan_pago_venta_bloque,
                   ppvbi.id_plan_pago_venta_bloque_indexacion, ppvbi.id_indice_financiero,
                   ppvbi.fecha_base_indice, ppvbi.valor_base_indice,
                   ppvbi.modo_indexacion, ppvbi.base_calculo_indexacion,
                   ppvbi.tipo_generacion_indexada, ppvbi.politica_valor_no_disponible
            FROM plan_pago_venta ppv
            JOIN plan_pago_venta_bloque ppvb ON ppvb.id_plan_pago_venta = ppv.id_plan_pago_venta AND ppvb.deleted_at IS NULL
            JOIN plan_pago_venta_bloque_indexacion ppvbi ON ppvbi.id_plan_pago_venta_bloque = ppvb.id_plan_pago_venta_bloque AND ppvbi.deleted_at IS NULL
            WHERE ppv.deleted_at IS NULL
              AND ppv.id_plan_pago_venta = :id_plan
              AND ppvb.id_plan_pago_venta_bloque = :id_bloque
              AND ppvbi.id_plan_pago_venta_bloque_indexacion = :id_config
              AND ppvbi.id_indice_financiero = :id_indice
        """), {"id_plan": command.id_plan_pago_venta, "id_bloque": command.id_plan_pago_venta_bloque, "id_config": command.id_plan_pago_venta_bloque_indexacion, "id_indice": command.id_indice_financiero}).mappings().first()
        return dict(row) if row else None

    def get_valor_indice(self, id_valor: int) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT id_indice_financiero_valor, id_indice_financiero, fecha_valor, valor_indice, fecha_publicacion
            FROM indice_financiero_valor
            WHERE id_indice_financiero_valor = :id AND deleted_at IS NULL
              AND estado_valor_indice = 'PUBLICADO'
        """), {"id": id_valor}).mappings().first()
        return dict(row) if row else None

    def list_obligaciones_bloque(self, id_bloque: int) -> list[dict[str, Any]]:
        rows = self.db.execute(text("""
            SELECT o.id_obligacion_financiera, o.version_registro, o.estado_obligacion,
                   o.importe_total, o.saldo_pendiente, o.fecha_vencimiento,
                   cap.id_composicion_obligacion AS id_composicion_capital_venta,
                   COALESCE(cap.importe_componente, 0) AS capital_base,
                   aj.id_composicion_obligacion AS id_composicion_ajuste_indexacion,
                   COALESCE(aj.importe_componente, 0) AS ajuste_anterior,
                   ofi.id_obligacion_financiera_indexacion,
                   EXISTS (SELECT 1 FROM aplicacion_financiera a WHERE a.id_obligacion_financiera = o.id_obligacion_financiera AND a.deleted_at IS NULL) AS tiene_imputaciones,
                   EXISTS (
                       SELECT 1 FROM aplicacion_financiera a JOIN movimiento_financiero m ON m.id_movimiento_financiero = a.id_movimiento_financiero
                       WHERE a.id_obligacion_financiera = o.id_obligacion_financiera AND a.deleted_at IS NULL AND m.deleted_at IS NULL AND m.estado_movimiento = 'APLICADO'
                   ) AS tiene_pagos,
                   (o.fecha_vencimiento < CURRENT_DATE AND o.saldo_pendiente > 0) AS tiene_mora
            FROM obligacion_financiera o
            LEFT JOIN composicion_obligacion cap ON cap.id_obligacion_financiera = o.id_obligacion_financiera AND cap.deleted_at IS NULL AND cap.estado_composicion_obligacion = 'ACTIVA'
              AND cap.id_concepto_financiero = (SELECT id_concepto_financiero FROM concepto_financiero WHERE codigo_concepto_financiero = 'CAPITAL_VENTA' LIMIT 1)
            LEFT JOIN composicion_obligacion aj ON aj.id_obligacion_financiera = o.id_obligacion_financiera AND aj.deleted_at IS NULL AND aj.estado_composicion_obligacion = 'ACTIVA'
              AND aj.id_concepto_financiero = (SELECT id_concepto_financiero FROM concepto_financiero WHERE codigo_concepto_financiero = 'AJUSTE_INDEXACION' LIMIT 1)
            LEFT JOIN obligacion_financiera_indexacion ofi ON ofi.id_obligacion_financiera = o.id_obligacion_financiera AND ofi.deleted_at IS NULL
            WHERE o.id_plan_pago_venta_bloque = :id_bloque AND o.deleted_at IS NULL
            ORDER BY o.id_obligacion_financiera
        """), {"id_bloque": id_bloque}).mappings().all()
        return [dict(r) for r in rows]

    def get_corrida_by_op_id(self, op_id: Any) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT id_corrida_indexacion_financiera, payload_hash, hash_corrida
            FROM corrida_indexacion_financiera
            WHERE op_id = :op_id AND deleted_at IS NULL
        """), {"op_id": str(op_id)}).mappings().first()
        return dict(row) if row else None

    def create_corrida_preview(self, payload: dict[str, Any], detalles: list[dict[str, Any]]) -> dict[str, Any]:
        row = self.db.execute(text("""
            INSERT INTO corrida_indexacion_financiera (
                id_plan_pago_venta,id_plan_pago_venta_bloque,id_plan_pago_venta_bloque_indexacion,
                id_indice_financiero,id_indice_financiero_valor_base,id_indice_financiero_valor_aplicado,
                periodo_base,periodo_aplicado,fecha_corte,fecha_publicacion_indice,origen_corrida,estado_corrida,op_id,hash_corrida,payload_hash,
                snapshot_alcance,snapshot_versiones,id_usuario,id_sucursal,id_instalacion_origen,motivo,
                cantidad_analizada,cantidad_elegible,cantidad_excluida,cantidad_aplicada,importe_total_anterior,importe_total_nuevo,ajuste_anterior_total,ajuste_nuevo_total,saldo_anterior_total,saldo_nuevo_total)
            VALUES (:id_plan_pago_venta,:id_plan_pago_venta_bloque,:id_plan_pago_venta_bloque_indexacion,
                :id_indice_financiero,:id_indice_financiero_valor_base,:id_indice_financiero_valor_aplicado,
                :periodo_base,:periodo_aplicado,:fecha_corte,:fecha_publicacion_indice,:origen_corrida,:estado_corrida,:op_id,:hash_corrida,:payload_hash,
                CAST(:snapshot_alcance AS jsonb),CAST(:snapshot_versiones AS jsonb),:id_usuario,:id_sucursal,:id_instalacion_origen,:motivo,
                :cantidad_analizada,:cantidad_elegible,:cantidad_excluida,:cantidad_aplicada,:importe_total_anterior,:importe_total_nuevo,:ajuste_anterior_total,:ajuste_nuevo_total,:saldo_anterior_total,:saldo_nuevo_total)
            RETURNING id_corrida_indexacion_financiera
        """), {**payload, "snapshot_alcance": json.dumps(payload["snapshot_alcance"]), "snapshot_versiones": json.dumps(payload["snapshot_versiones"]), "fecha_publicacion_indice": None}).mappings().one()
        id_corrida = row["id_corrida_indexacion_financiera"]
        for d in detalles:
            self.db.execute(text("""
                INSERT INTO corrida_indexacion_financiera_detalle (
                    id_corrida_indexacion_financiera,id_obligacion_financiera,id_composicion_capital_venta,id_composicion_ajuste_indexacion,id_obligacion_financiera_indexacion,
                    version_esperada,capital_base,valor_indice_base,valor_indice_aplicado,coeficiente_indexacion,ajuste_anterior,ajuste_nuevo,diferencia_neta,importe_anterior,importe_nuevo,saldo_anterior,saldo_nuevo,
                    estado_elegibilidad,motivo_exclusion,advertencias,snapshot_antes,snapshot_despues)
                VALUES (:id_corrida,:id_obligacion_financiera,:id_composicion_capital_venta,:id_composicion_ajuste_indexacion,:id_obligacion_financiera_indexacion,
                    :version_esperada,:capital_base,:valor_indice_base,:valor_indice_aplicado,:coeficiente_indexacion,:ajuste_anterior,:ajuste_nuevo,:diferencia_neta,:importe_anterior,:importe_nuevo,:saldo_anterior,:saldo_nuevo,
                    :estado_elegibilidad,:motivo_exclusion,CAST(:advertencias AS jsonb),CAST(:snapshot_antes AS jsonb),CAST(:snapshot_despues AS jsonb))
            """), {**d, "id_corrida": id_corrida, "advertencias": json.dumps(d["advertencias"]), "snapshot_antes": json.dumps({}), "snapshot_despues": json.dumps({})})
        self.db.commit()
        return {"id_corrida_indexacion_financiera": id_corrida}
