from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class FinancieroRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── existence checks ──────────────────────────────────────────────────────

    def venta_exists(self, id_venta: int) -> bool:
        stmt = text(
            "SELECT 1 FROM venta WHERE id_venta = :id AND deleted_at IS NULL"
        )
        return self.db.execute(stmt, {"id": id_venta}).scalar_one_or_none() is not None

    def contrato_alquiler_exists(self, id_contrato_alquiler: int) -> bool:
        stmt = text(
            "SELECT 1 FROM contrato_alquiler WHERE id_contrato_alquiler = :id AND deleted_at IS NULL"
        )
        return self.db.execute(stmt, {"id": id_contrato_alquiler}).scalar_one_or_none() is not None

    def factura_servicio_exists(self, id_factura_servicio: int) -> bool:
        stmt = text(
            "SELECT 1 FROM factura_servicio WHERE id_factura_servicio = :id AND deleted_at IS NULL"
        )
        return self.db.execute(stmt, {"id": id_factura_servicio}).scalar_one_or_none() is not None

    def relacion_generadora_exists(self, id_relacion_generadora: int) -> bool:
        stmt = text(
            "SELECT 1 FROM relacion_generadora WHERE id_relacion_generadora = :id AND deleted_at IS NULL"
        )
        return self.db.execute(stmt, {"id": id_relacion_generadora}).scalar_one_or_none() is not None

    def get_concepto_financiero_by_codigo(self, codigo: str) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT id_concepto_financiero, codigo_concepto_financiero
            FROM concepto_financiero
            WHERE codigo_concepto_financiero = :codigo AND deleted_at IS NULL
            """
        )
        row = self.db.execute(stmt, {"codigo": codigo}).mappings().one_or_none()
        return dict(row) if row else None

    # ── relacion_generadora ───────────────────────────────────────────────────

    def create_relacion_generadora(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text(
            """
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
                :uid_global,
                :version_registro,
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
            RETURNING
                id_relacion_generadora,
                uid_global,
                version_registro,
                tipo_origen,
                id_origen,
                descripcion,
                estado_relacion_generadora,
                fecha_alta,
                deleted_at
            """
        )
        try:
            row = self.db.execute(
                stmt,
                {
                    "uid_global": values["uid_global"],
                    "version_registro": values["version_registro"],
                    "created_at": values["created_at"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_origen": values["id_instalacion_origen"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_alta": values["op_id_alta"],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    "tipo_origen": values["tipo_origen"],
                    "id_origen": values["id_origen"],
                    "descripcion": values["descripcion"],
                },
            ).mappings().one()
            self.db.commit()
            return self._rg_row_to_dict(row)
        except Exception:
            self.db.rollback()
            raise

    def get_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_relacion_generadora,
                uid_global,
                version_registro,
                tipo_origen,
                id_origen,
                descripcion,
                estado_relacion_generadora,
                fecha_alta,
                deleted_at
            FROM relacion_generadora
            WHERE id_relacion_generadora = :id
            """
        )
        row = (
            self.db.execute(stmt, {"id": id_relacion_generadora})
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return self._rg_row_to_dict(row)

    def list_relaciones_generadoras(
        self,
        *,
        tipo_origen: str | None,
        id_origen: int | None,
        vigente: bool | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        filters: list[str] = []
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        # Default: only non-deleted unless vigente=False is explicit
        if vigente is False:
            filters.append("deleted_at IS NOT NULL")
        else:
            filters.append("deleted_at IS NULL")

        if tipo_origen is not None:
            filters.append("UPPER(tipo_origen) = :tipo_origen")
            params["tipo_origen"] = tipo_origen.strip().upper()

        if id_origen is not None:
            filters.append("id_origen = :id_origen")
            params["id_origen"] = id_origen

        where_clause = " AND ".join(filters)

        list_stmt = text(
            f"""
            SELECT
                id_relacion_generadora,
                uid_global,
                version_registro,
                tipo_origen,
                id_origen,
                descripcion,
                estado_relacion_generadora,
                fecha_alta,
                deleted_at
            FROM relacion_generadora
            WHERE {where_clause}
            ORDER BY id_relacion_generadora DESC
            LIMIT :limit
            OFFSET :offset
            """
        )
        total_stmt = text(
            f"SELECT COUNT(*) AS total FROM relacion_generadora WHERE {where_clause}"
        )

        rows = self.db.execute(list_stmt, params).mappings().all()
        total = self.db.execute(total_stmt, params).scalar_one()

        return {
            "items": [self._rg_row_to_dict(row) for row in rows],
            "total": total,
        }

    # ── concepto_financiero ───────────────────────────────────────────────────

    def list_conceptos_financieros(
        self,
        *,
        estado: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        filters: list[str] = ["deleted_at IS NULL"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if estado is not None:
            filters.append("estado_concepto_financiero = :estado")
            params["estado"] = estado.strip().upper()

        where_clause = " AND ".join(filters)

        list_stmt = text(
            f"""
            SELECT
                id_concepto_financiero,
                codigo_concepto_financiero,
                nombre_concepto_financiero,
                descripcion_concepto_financiero,
                tipo_concepto_financiero,
                naturaleza_concepto,
                estado_concepto_financiero
            FROM concepto_financiero
            WHERE {where_clause}
            ORDER BY codigo_concepto_financiero ASC
            LIMIT :limit OFFSET :offset
            """
        )
        total_stmt = text(
            f"SELECT COUNT(*) FROM concepto_financiero WHERE {where_clause}"
        )

        rows = self.db.execute(list_stmt, params).mappings().all()
        total = self.db.execute(total_stmt, params).scalar_one()

        return {
            "items": [dict(row) for row in rows],
            "total": total,
        }

    # ── imputacion / aplicacion_financiera ───────────────────────────────────

    def get_obligacion_para_imputacion(
        self, id_obligacion_financiera: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_obligacion_financiera,
                saldo_pendiente,
                estado_obligacion,
                deleted_at
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id
            """
        )
        row = (
            self.db.execute(stmt, {"id": id_obligacion_financiera})
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def get_composiciones_para_imputar(
        self, id_obligacion_financiera: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                c.id_composicion_obligacion,
                c.orden_composicion,
                c.saldo_componente,
                cf.codigo_concepto_financiero
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
                ON c.id_concepto_financiero = cf.id_concepto_financiero
            WHERE c.id_obligacion_financiera = :id
              AND c.estado_composicion_obligacion = 'ACTIVA'
              AND c.saldo_componente > 0
              AND c.deleted_at IS NULL
            ORDER BY c.orden_composicion ASC
            """
        )
        rows = (
            self.db.execute(stmt, {"id": id_obligacion_financiera})
            .mappings()
            .all()
        )
        return [dict(r) for r in rows]

    def create_imputacion(self, payload: Any) -> dict[str, Any]:
        mov = payload.movimiento
        mov_values = self._values(mov)

        mov_stmt = text(
            """
            INSERT INTO movimiento_financiero (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                fecha_movimiento, tipo_movimiento, importe, signo, estado_movimiento
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :fecha_movimiento, :tipo_movimiento, :importe, :signo, :estado_movimiento
            )
            RETURNING id_movimiento_financiero
            """
        )

        aplic_stmt = text(
            """
            INSERT INTO aplicacion_financiera (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_movimiento_financiero, id_obligacion_financiera,
                id_composicion_obligacion, fecha_aplicacion,
                tipo_aplicacion, orden_aplicacion, importe_aplicado,
                origen_automatico_o_manual
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_movimiento_financiero, :id_obligacion_financiera,
                :id_composicion_obligacion, :fecha_aplicacion,
                :tipo_aplicacion, :orden_aplicacion, :importe_aplicado,
                :origen_automatico_o_manual
            )
            RETURNING
                id_aplicacion_financiera, id_composicion_obligacion,
                importe_aplicado, orden_aplicacion
            """
        )

        try:
            mov_row = self.db.execute(
                mov_stmt,
                {
                    "uid_global": mov_values["uid_global"],
                    "version_registro": mov_values["version_registro"],
                    "created_at": mov_values["created_at"],
                    "updated_at": mov_values["updated_at"],
                    "id_instalacion_origen": mov_values["id_instalacion_origen"],
                    "id_instalacion_ultima_modificacion": mov_values["id_instalacion_ultima_modificacion"],
                    "op_id_alta": mov_values["op_id_alta"],
                    "op_id_ultima_modificacion": mov_values["op_id_ultima_modificacion"],
                    "fecha_movimiento": mov_values["fecha_movimiento"],
                    "tipo_movimiento": mov_values["tipo_movimiento"],
                    "importe": mov_values["importe"],
                    "signo": mov_values["signo"],
                    "estado_movimiento": mov_values["estado_movimiento"],
                },
            ).mappings().one()

            id_movimiento = mov_row["id_movimiento_financiero"]
            aplicaciones: list[dict[str, Any]] = []

            for linea in payload.lineas:
                lv = self._values(linea)
                aplic_row = self.db.execute(
                    aplic_stmt,
                    {
                        "uid_global": lv["uid_global"],
                        "version_registro": lv["version_registro"],
                        "created_at": lv["created_at"],
                        "updated_at": lv["updated_at"],
                        "id_instalacion_origen": lv["id_instalacion_origen"],
                        "id_instalacion_ultima_modificacion": lv["id_instalacion_ultima_modificacion"],
                        "op_id_alta": lv["op_id_alta"],
                        "op_id_ultima_modificacion": lv["op_id_ultima_modificacion"],
                        "id_movimiento_financiero": id_movimiento,
                        "id_obligacion_financiera": payload.id_obligacion_financiera,
                        "id_composicion_obligacion": lv["id_composicion_obligacion"],
                        "fecha_aplicacion": payload.fecha_aplicacion,
                        "tipo_aplicacion": payload.tipo_aplicacion,
                        "orden_aplicacion": lv["orden_aplicacion"],
                        "importe_aplicado": lv["importe_aplicado"],
                        "origen_automatico_o_manual": payload.origen_automatico_o_manual,
                    },
                ).mappings().one()
                aplicaciones.append(dict(aplic_row))

            # El trigger ya actualizó saldo_pendiente; leemos el valor final para
            # decidir el estado sin recalcular nada.
            self.db.execute(
                text(
                    """
                    UPDATE obligacion_financiera
                    SET estado_obligacion = CASE
                            WHEN saldo_pendiente = 0             THEN 'CANCELADA'
                            WHEN saldo_pendiente < importe_total THEN 'PARCIALMENTE_CANCELADA'
                            ELSE estado_obligacion
                        END
                    WHERE id_obligacion_financiera = :id
                      AND estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')
                    """
                ),
                {"id": payload.id_obligacion_financiera},
            )

            self.db.commit()

            return {
                "id_obligacion_financiera": payload.id_obligacion_financiera,
                "id_movimiento_financiero": id_movimiento,
                "monto_aplicado": float(sum(a["importe_aplicado"] for a in aplicaciones)),
                "aplicaciones": [
                    {
                        "id_aplicacion_financiera": a["id_aplicacion_financiera"],
                        "id_composicion_obligacion": a["id_composicion_obligacion"],
                        "importe_aplicado": float(a["importe_aplicado"]),
                        "orden_aplicacion": a["orden_aplicacion"],
                    }
                    for a in aplicaciones
                ],
            }
        except Exception:
            self.db.rollback()
            raise

    # ── obligacion_financiera ─────────────────────────────────────────────────

    def get_obligacion_financiera(
        self, id_obligacion_financiera: int
    ) -> dict[str, Any] | None:
        ob_stmt = text(
            """
            SELECT
                id_obligacion_financiera,
                uid_global,
                version_registro,
                id_relacion_generadora,
                codigo_obligacion_financiera,
                descripcion_operativa,
                fecha_emision,
                fecha_vencimiento,
                periodo_desde,
                periodo_hasta,
                importe_total,
                saldo_pendiente,
                estado_obligacion,
                deleted_at
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id
            """
        )
        row = (
            self.db.execute(ob_stmt, {"id": id_obligacion_financiera})
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None

        comp_stmt = text(
            """
            SELECT
                c.id_composicion_obligacion,
                c.orden_composicion,
                c.estado_composicion_obligacion,
                c.importe_componente,
                c.saldo_componente,
                c.moneda_componente,
                cf.codigo_concepto_financiero
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
                ON c.id_concepto_financiero = cf.id_concepto_financiero
            WHERE c.id_obligacion_financiera = :id
              AND c.deleted_at IS NULL
            ORDER BY c.orden_composicion ASC
            """
        )
        comp_rows = (
            self.db.execute(comp_stmt, {"id": id_obligacion_financiera})
            .mappings()
            .all()
        )

        result = dict(row)
        result["uid_global"] = str(result["uid_global"])
        result["composiciones"] = [dict(c) for c in comp_rows]
        return result

    def create_obligacion_financiera(
        self,
        obligacion: Any,
        composiciones: list[Any],
    ) -> dict[str, Any]:
        ob_values = self._values(obligacion)

        ob_stmt = text(
            """
            INSERT INTO obligacion_financiera (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_relacion_generadora, fecha_emision, fecha_vencimiento,
                importe_total, saldo_pendiente, estado_obligacion
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_relacion_generadora, :fecha_emision, :fecha_vencimiento,
                :importe_total, :importe_total, :estado_obligacion
            )
            RETURNING
                id_obligacion_financiera, uid_global, version_registro,
                id_relacion_generadora, codigo_obligacion_financiera,
                descripcion_operativa, fecha_emision, fecha_vencimiento,
                periodo_desde, periodo_hasta, importe_total, saldo_pendiente,
                estado_obligacion
            """
        )

        comp_stmt = text(
            """
            INSERT INTO composicion_obligacion (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_obligacion_financiera, id_concepto_financiero,
                orden_composicion, importe_componente, saldo_componente
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_obligacion_financiera, :id_concepto_financiero,
                :orden_composicion, :importe_componente, :importe_componente
            )
            RETURNING
                id_composicion_obligacion, orden_composicion,
                estado_composicion_obligacion, importe_componente,
                saldo_componente, moneda_componente
            """
        )

        try:
            ob_row = self.db.execute(
                ob_stmt,
                {
                    "uid_global": ob_values["uid_global"],
                    "version_registro": ob_values["version_registro"],
                    "created_at": ob_values["created_at"],
                    "updated_at": ob_values["updated_at"],
                    "id_instalacion_origen": ob_values["id_instalacion_origen"],
                    "id_instalacion_ultima_modificacion": ob_values["id_instalacion_ultima_modificacion"],
                    "op_id_alta": ob_values["op_id_alta"],
                    "op_id_ultima_modificacion": ob_values["op_id_ultima_modificacion"],
                    "id_relacion_generadora": ob_values["id_relacion_generadora"],
                    "fecha_emision": ob_values["fecha_emision"],
                    "fecha_vencimiento": ob_values["fecha_vencimiento"],
                    "importe_total": ob_values["importe_total"],
                    "estado_obligacion": ob_values["estado_obligacion"],
                },
            ).mappings().one()

            ob_id = ob_row["id_obligacion_financiera"]
            comp_results: list[dict[str, Any]] = []

            for comp in composiciones:
                cv = self._values(comp)
                comp_row = self.db.execute(
                    comp_stmt,
                    {
                        "uid_global": cv["uid_global"],
                        "version_registro": cv["version_registro"],
                        "created_at": cv["created_at"],
                        "updated_at": cv["updated_at"],
                        "id_instalacion_origen": cv["id_instalacion_origen"],
                        "id_instalacion_ultima_modificacion": cv["id_instalacion_ultima_modificacion"],
                        "op_id_alta": cv["op_id_alta"],
                        "op_id_ultima_modificacion": cv["op_id_ultima_modificacion"],
                        "id_obligacion_financiera": ob_id,
                        "id_concepto_financiero": cv["id_concepto_financiero"],
                        "orden_composicion": cv["orden_composicion"],
                        "importe_componente": cv["importe_componente"],
                    },
                ).mappings().one()
                comp_results.append(
                    {**dict(comp_row), "codigo_concepto_financiero": cv["codigo_concepto_financiero"]}
                )

            self.db.commit()

            result = dict(ob_row)
            result["uid_global"] = str(result["uid_global"])
            result["composiciones"] = comp_results
            return result
        except Exception:
            self.db.rollback()
            raise

    # ── helpers ───────────────────────────────────────────────────────────────

    def _rg_row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "id_relacion_generadora": row["id_relacion_generadora"],
            "uid_global": str(row["uid_global"]),
            "version_registro": row["version_registro"],
            "tipo_origen": row["tipo_origen"].upper(),
            "id_origen": row["id_origen"],
            "descripcion": row["descripcion"],
            "estado_relacion_generadora": row["estado_relacion_generadora"].upper(),
            "fecha_alta": row["fecha_alta"],
            "deleted_at": row["deleted_at"],
        }

    def _values(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        if is_dataclass(payload):
            return asdict(payload)
        return vars(payload)
