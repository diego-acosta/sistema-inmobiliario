from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class AplicarIndexacionCuotasV2SqlAlchemyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_corrida_for_update(self, corrida_id: int) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT * FROM corrida_indexacion_financiera
            WHERE id_corrida_indexacion_financiera = :id AND deleted_at IS NULL
            FOR UPDATE
        """), {"id": corrida_id}).mappings().first()
        return dict(row) if row else None

    def get_corrida_by_apply_op(self, op_id: Any) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT id_corrida_indexacion_financiera, estado_corrida, hash_corrida, payload_hash, cantidad_aplicada, version_registro, op_id_ultima_modificacion
            FROM corrida_indexacion_financiera
            WHERE op_id_ultima_modificacion = CAST(:op_id AS uuid) AND deleted_at IS NULL
            ORDER BY updated_at DESC
            LIMIT 1
        """), {"op_id": str(op_id)}).mappings().first()
        return dict(row) if row else None

    def list_detalles_for_update(self, corrida_id: int) -> list[dict[str, Any]]:
        rows = self.db.execute(text("""
            SELECT * FROM corrida_indexacion_financiera_detalle
            WHERE id_corrida_indexacion_financiera = :id AND deleted_at IS NULL
            ORDER BY id_obligacion_financiera
            FOR UPDATE
        """), {"id": corrida_id}).mappings().all()
        return [dict(r) for r in rows]

    def get_obligacion_actual_for_update(self, obligacion_id: int) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT o.*, cap.id_composicion_obligacion AS id_composicion_capital_venta,
                   cap.importe_componente AS capital_base,
                   aj.id_composicion_obligacion AS id_composicion_ajuste_indexacion,
                   COALESCE(aj.importe_componente, 0) AS ajuste_anterior,
                   aj.version_registro AS ajuste_version,
                   ofi.id_obligacion_financiera_indexacion,
                   ofi.version_registro AS ofi_version_registro,
                   ofi.id_indice_financiero_valor AS ofi_id_indice_financiero_valor,
                   ofi.valor_aplicado_indice AS ofi_valor_aplicado_indice,
                   ofi.coeficiente_indexacion AS ofi_coeficiente_indexacion,
                   EXISTS (SELECT 1 FROM aplicacion_financiera a WHERE a.id_obligacion_financiera = o.id_obligacion_financiera AND a.deleted_at IS NULL) AS tiene_imputaciones,
                   EXISTS (
                       SELECT 1 FROM aplicacion_financiera a JOIN movimiento_financiero m ON m.id_movimiento_financiero = a.id_movimiento_financiero
                       WHERE a.id_obligacion_financiera = o.id_obligacion_financiera AND a.deleted_at IS NULL AND m.deleted_at IS NULL AND m.estado_movimiento = 'APLICADO'
                   ) AS tiene_pagos,
                   EXISTS (
                       SELECT 1 FROM composicion_obligacion cp JOIN concepto_financiero cfp ON cfp.id_concepto_financiero = cp.id_concepto_financiero
                       WHERE cp.id_obligacion_financiera = o.id_obligacion_financiera AND cp.deleted_at IS NULL AND cp.estado_composicion_obligacion = 'ACTIVA'
                         AND cfp.codigo_concepto_financiero = 'PUNITORIO' AND cp.saldo_componente > 0
                   ) AS tiene_punitorios
            FROM obligacion_financiera o
            LEFT JOIN composicion_obligacion cap ON cap.id_obligacion_financiera = o.id_obligacion_financiera AND cap.deleted_at IS NULL AND cap.estado_composicion_obligacion = 'ACTIVA'
              AND cap.id_concepto_financiero = (SELECT id_concepto_financiero FROM concepto_financiero WHERE codigo_concepto_financiero = 'CAPITAL_VENTA' LIMIT 1)
            LEFT JOIN composicion_obligacion aj ON aj.id_obligacion_financiera = o.id_obligacion_financiera AND aj.deleted_at IS NULL AND aj.estado_composicion_obligacion = 'ACTIVA'
              AND aj.id_concepto_financiero = (SELECT id_concepto_financiero FROM concepto_financiero WHERE codigo_concepto_financiero = 'AJUSTE_INDEXACION' LIMIT 1)
            LEFT JOIN obligacion_financiera_indexacion ofi ON ofi.id_obligacion_financiera = o.id_obligacion_financiera AND ofi.deleted_at IS NULL
            WHERE o.id_obligacion_financiera = :id AND o.deleted_at IS NULL
            FOR UPDATE OF o
        """), {"id": obligacion_id}).mappings().first()
        return dict(row) if row else None

    def get_obligacion_version_actual_for_update(self, obligacion_id: int) -> int | None:
        """Returns the persisted version without releasing the row lock.

        This read happens after every mutation that may refresh the obligation,
        so callers must not derive the result from the preview version.
        """
        row = self.db.execute(text("""
            SELECT version_registro
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id AND deleted_at IS NULL
            FOR UPDATE
        """), {"id": obligacion_id}).mappings().first()
        return int(row["version_registro"]) if row else None

    def get_lock_conflict(self, uid_entidad: Any, op_id: Any) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT * FROM lock_logico
            WHERE uid_entidad = :uid AND tipo_entidad = 'OBLIGACION_FINANCIERA'
              AND estado_lock = 'ACTIVO'
              AND (fecha_hora_expiracion IS NULL OR fecha_hora_expiracion > CURRENT_TIMESTAMP)
              AND op_id <> :op_id
            LIMIT 1
        """), {"uid": uid_entidad, "op_id": str(op_id)}).mappings().first()
        return dict(row) if row else None

    def acquire_lock(self, uid_entidad: Any, core_ef: Any) -> None:
        self.db.execute(text("""
            INSERT INTO lock_logico (tipo_entidad, uid_entidad, id_instalacion_origen, id_usuario_origen, op_id, motivo_lock, fecha_hora_lock, fecha_hora_expiracion, estado_lock, observaciones)
            VALUES ('OBLIGACION_FINANCIERA', :uid, :instalacion, :usuario, :op_id, 'APLICAR_INDEXACION_CUOTAS_V2', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '15 minutes', 'ACTIVO', 'Lock aplicacion corrida indexacion V2')
        """), {"uid": uid_entidad, "instalacion": core_ef.x_instalacion_id, "usuario": core_ef.x_usuario_id, "op_id": str(core_ef.x_op_id)})

    def release_locks(self, op_id: Any) -> None:
        self.db.execute(text("""UPDATE lock_logico SET estado_lock='LIBERADO', observaciones='Liberado por aplicacion indexacion V2' WHERE op_id=:op_id AND estado_lock='ACTIVO'"""), {"op_id": str(op_id)})

    def upsert_ajuste(self, obligacion_id: int, ajuste_id: int | None, ajuste_version: int | None, importe: Any, core_ef: Any) -> int:
        if ajuste_id:
            res = self.db.execute(text("""
                UPDATE composicion_obligacion SET importe_componente=:importe, saldo_componente=:importe,
                    op_id_ultima_modificacion=CAST(:op_id AS uuid), id_instalacion_ultima_modificacion=:inst
                WHERE id_composicion_obligacion=:id AND id_obligacion_financiera=:obl
                  AND version_registro=:version AND deleted_at IS NULL
            """), {"importe": importe, "op_id": str(core_ef.x_op_id), "inst": core_ef.x_instalacion_id, "id": ajuste_id, "obl": obligacion_id, "version": ajuste_version})
            if res.rowcount != 1:
                raise RuntimeError("VERSION_AJUSTE_INDEXACION_INCOMPATIBLE")
            return ajuste_id
        existing = self.db.execute(text("""
            SELECT id_composicion_obligacion
            FROM composicion_obligacion
            WHERE id_obligacion_financiera=:obl AND deleted_at IS NULL
              AND estado_composicion_obligacion='ACTIVA'
              AND id_concepto_financiero = (SELECT id_concepto_financiero FROM concepto_financiero WHERE codigo_concepto_financiero='AJUSTE_INDEXACION' AND deleted_at IS NULL LIMIT 1)
            FOR UPDATE
        """), {"obl": obligacion_id}).mappings().first()
        if existing is not None:
            raise RuntimeError("VERSION_AJUSTE_INDEXACION_INCOMPATIBLE")
        row = self.db.execute(text("""
            INSERT INTO composicion_obligacion (id_obligacion_financiera, id_concepto_financiero, orden_composicion, estado_composicion_obligacion, importe_componente, saldo_componente, moneda_componente, detalle_calculo, id_instalacion_origen, id_instalacion_ultima_modificacion, op_id_alta, op_id_ultima_modificacion)
            VALUES (:obl, (SELECT id_concepto_financiero FROM concepto_financiero WHERE codigo_concepto_financiero='AJUSTE_INDEXACION' AND deleted_at IS NULL LIMIT 1),
                    COALESCE((SELECT max(orden_composicion)+1 FROM composicion_obligacion WHERE id_obligacion_financiera=:obl AND deleted_at IS NULL), 1),
                    'ACTIVA', :importe, :importe, 'ARS', 'Aplicacion corrida indexacion V2', :inst, :inst, CAST(:op_id AS uuid), CAST(:op_id AS uuid))
            RETURNING id_composicion_obligacion
        """), {"obl": obligacion_id, "importe": importe, "inst": core_ef.x_instalacion_id, "op_id": str(core_ef.x_op_id)}).mappings().one()
        return int(row["id_composicion_obligacion"])

    def upsert_trazabilidad(self, detalle: dict[str, Any], corrida: dict[str, Any], actual: dict[str, Any], core_ef: Any) -> int:
        if actual.get("id_obligacion_financiera_indexacion") is not None:
            if actual.get("id_obligacion_financiera_indexacion") != detalle.get("id_obligacion_financiera_indexacion"):
                raise RuntimeError("TRAZABILIDAD_INDEXACION_INCOMPATIBLE")
            res = self.db.execute(text("""
                UPDATE obligacion_financiera_indexacion SET
                    id_indice_financiero_valor=:valor,
                    fecha_aplicacion_indice=:periodo_aplicado,
                    valor_aplicado_indice=:valor_aplicado,
                    coeficiente_indexacion=:coef,
                    observaciones=:obs,
                    id_instalacion_ultima_modificacion=:inst,
                    op_id_ultima_modificacion=CAST(:op_id AS uuid)
                WHERE id_obligacion_financiera_indexacion=:id AND version_registro=:version AND deleted_at IS NULL
            """), {"valor": corrida["id_indice_financiero_valor_aplicado"], "periodo_aplicado": corrida["periodo_aplicado"], "valor_aplicado": detalle["valor_indice_aplicado"], "coef": detalle["coeficiente_indexacion"], "obs": f"corrida_indexacion_financiera:{corrida['id_corrida_indexacion_financiera']}", "inst": core_ef.x_instalacion_id, "op_id": str(core_ef.x_op_id), "id": actual["id_obligacion_financiera_indexacion"], "version": actual["ofi_version_registro"]})
            if res.rowcount != 1:
                raise RuntimeError("TRAZABILIDAD_INDEXACION_INCOMPATIBLE")
            return int(actual["id_obligacion_financiera_indexacion"])
        existing = self.db.execute(text("""
            SELECT id_obligacion_financiera_indexacion
            FROM obligacion_financiera_indexacion
            WHERE id_obligacion_financiera=:obl AND deleted_at IS NULL
            FOR UPDATE
        """), {"obl": detalle["id_obligacion_financiera"]}).mappings().first()
        if existing is not None:
            raise RuntimeError("TRAZABILIDAD_INDEXACION_INCOMPATIBLE")
        row = self.db.execute(text("""
            INSERT INTO obligacion_financiera_indexacion (id_obligacion_financiera, id_plan_pago_venta_bloque_indexacion, id_indice_financiero, id_indice_financiero_valor, fecha_base_indice, valor_base_indice, fecha_aplicacion_indice, valor_aplicado_indice, coeficiente_indexacion, modo_indexacion, base_calculo_indexacion, tipo_generacion_indexada, observaciones, id_instalacion_origen, id_instalacion_ultima_modificacion, op_id_alta, op_id_ultima_modificacion)
            VALUES (:obl, :config, :indice, :valor, :periodo_base, :valor_base, :periodo_aplicado, :valor_aplicado, :coef, 'POR_COEFICIENTE', 'CAPITAL_INICIAL_BLOQUE', 'DEFINITIVA', :obs, :inst, :inst, CAST(:op_id AS uuid), CAST(:op_id AS uuid))
            RETURNING id_obligacion_financiera_indexacion
        """), {"obl": detalle["id_obligacion_financiera"], "config": corrida["id_plan_pago_venta_bloque_indexacion"], "indice": corrida["id_indice_financiero"], "valor": corrida["id_indice_financiero_valor_aplicado"], "periodo_base": corrida["periodo_base"], "valor_base": detalle["valor_indice_base"], "periodo_aplicado": corrida["periodo_aplicado"], "valor_aplicado": detalle["valor_indice_aplicado"], "coef": detalle["coeficiente_indexacion"], "obs": f"corrida_indexacion_financiera:{corrida['id_corrida_indexacion_financiera']}", "inst": core_ef.x_instalacion_id, "op_id": str(core_ef.x_op_id)}).mappings().one()
        return int(row["id_obligacion_financiera_indexacion"])

    def update_obligacion(self, detalle: dict[str, Any], core_ef: Any) -> bool:
        res = self.db.execute(text("""
            UPDATE obligacion_financiera SET importe_total=:importe, saldo_pendiente=:saldo,
                op_id_ultima_modificacion=CAST(:op_id AS uuid), id_instalacion_ultima_modificacion=:inst
            WHERE id_obligacion_financiera=:id AND version_registro=:version AND deleted_at IS NULL
        """), {"importe": detalle["importe_nuevo"], "saldo": detalle["saldo_nuevo"], "op_id": str(core_ef.x_op_id), "inst": core_ef.x_instalacion_id, "id": detalle["id_obligacion_financiera"], "version": detalle["version_esperada"]})
        return res.rowcount == 1

    def update_detalle_aplicado(self, detalle_id: int, version_resultante: int, ajuste_id: int, ofi_id: int, core_ef: Any) -> None:
        self.db.execute(text("""
            UPDATE corrida_indexacion_financiera_detalle SET version_resultante=:version_resultante,
                id_composicion_ajuste_indexacion=:ajuste_id, id_obligacion_financiera_indexacion=:ofi_id,
                codigo_error=NULL, detalle_controlado=NULL,
                op_id_ultima_modificacion=CAST(:op_id AS uuid), id_instalacion_ultima_modificacion=:inst
            WHERE id_corrida_indexacion_financiera_detalle=:id
        """), {"version_resultante": version_resultante, "ajuste_id": ajuste_id, "ofi_id": ofi_id, "op_id": str(core_ef.x_op_id), "inst": core_ef.x_instalacion_id, "id": detalle_id})

    def update_corrida_aplicada(self, corrida_id: int, version: int, cantidad: int, core_ef: Any) -> bool:
        res = self.db.execute(text("""
            UPDATE corrida_indexacion_financiera SET estado_corrida='APLICADA', fecha_aplicacion=CURRENT_TIMESTAMP,
                cantidad_aplicada=:cantidad, codigo_error=NULL, etapa_error=NULL, diagnostico_tecnico=NULL,
                op_id_ultima_modificacion=CAST(:op_id AS uuid), id_instalacion_ultima_modificacion=:inst,
                id_usuario=:usuario, id_sucursal=:sucursal
            WHERE id_corrida_indexacion_financiera=:id AND version_registro=:version AND deleted_at IS NULL
        """), {"cantidad": cantidad, "op_id": str(core_ef.x_op_id), "inst": core_ef.x_instalacion_id, "usuario": core_ef.x_usuario_id, "sucursal": core_ef.x_sucursal_id, "id": corrida_id, "version": version})
        return res.rowcount == 1

    def insert_outbox(self, corrida: dict[str, Any], cantidad: int, core_ef: Any) -> None:
        self.db.execute(text("""
            INSERT INTO outbox_event (event_type, aggregate_type, aggregate_id, payload, status)
            VALUES ('financiero.indexacion_cuotas_v2.corrida_aplicada', 'corrida_indexacion_financiera', :id, CAST(:payload AS jsonb), 'PENDING')
        """), {"id": corrida["id_corrida_indexacion_financiera"], "payload": json.dumps({"id_corrida_indexacion_financiera": corrida["id_corrida_indexacion_financiera"], "hash_corrida": corrida["hash_corrida"], "cantidad_aplicada": cantidad, "op_id": str(core_ef.x_op_id), "id_instalacion_origen": core_ef.x_instalacion_id}, sort_keys=True)})

    def commit(self) -> None:
        self.db.commit()

    def mark_failed_new_transaction(self, corrida_id: int, core_ef: Any, code: str, stage: str) -> None:
        self.db.rollback()
        self.db.execute(text("""
            UPDATE corrida_indexacion_financiera SET estado_corrida='FALLIDA', fecha_aplicacion=NULL,
                codigo_error=:code, etapa_error=:stage, diagnostico_tecnico=:diag,
                op_id_ultima_modificacion=CAST(:op_id AS uuid), id_instalacion_ultima_modificacion=:inst
            WHERE id_corrida_indexacion_financiera=:id AND deleted_at IS NULL AND estado_corrida <> 'APLICADA'
        """), {"code": code[:80], "stage": stage[:80], "diag": code, "op_id": str(core_ef.x_op_id), "inst": core_ef.x_instalacion_id, "id": corrida_id})
        self.db.commit()
