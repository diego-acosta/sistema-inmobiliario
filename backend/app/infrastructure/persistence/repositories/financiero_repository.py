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
