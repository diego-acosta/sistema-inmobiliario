from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
import json
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.domain.financiero.resolver_mora import ResolucionMora, resolver_mora_params


def _calcular_mora_dinamica(
    saldo_pendiente: Any,
    fecha_vencimiento: date | None,
    fecha_corte: date,
    resolucion: ResolucionMora | None = None,
) -> dict[str, Any]:
    if resolucion is None:
        resolucion = resolver_mora_params()

    if fecha_vencimiento is None:
        return {
            "dias_atraso": 0,
            "mora_calculada": 0.0,
            "tasa_diaria_mora": float(resolucion.tasa_diaria),
        }

    saldo = Decimal(str(saldo_pendiente))
    if saldo <= 0:
        return {
            "dias_atraso": 0,
            "mora_calculada": 0.0,
            "tasa_diaria_mora": float(resolucion.tasa_diaria),
        }

    fecha_inicio_mora = fecha_vencimiento + timedelta(days=resolucion.dias_gracia)
    dias_atraso = max(0, (fecha_corte - fecha_inicio_mora).days)
    if dias_atraso == 0:
        return {
            "dias_atraso": 0,
            "mora_calculada": 0.0,
            "tasa_diaria_mora": float(resolucion.tasa_diaria),
        }

    mora = (saldo * resolucion.tasa_diaria * Decimal(dias_atraso)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    return {
        "dias_atraso": dias_atraso,
        "mora_calculada": float(mora),
        "tasa_diaria_mora": float(resolucion.tasa_diaria),
    }


class FinancieroRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    # ── existence checks ──────────────────────────────────────────────────────

    def persona_exists(self, id_persona: int) -> bool:
        stmt = text(
            "SELECT 1 FROM persona WHERE id_persona = :id AND deleted_at IS NULL"
        )
        return self.db.execute(stmt, {"id": id_persona}).scalar_one_or_none() is not None

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

    def get_relacion_generadora_by_origen(
        self, tipo_origen: str, id_origen: int
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
            WHERE tipo_origen = :tipo_origen
              AND id_origen = :id_origen
              AND deleted_at IS NULL
            ORDER BY id_relacion_generadora DESC
            LIMIT 1
            """
        )
        row = (
            self.db.execute(
                stmt,
                {"tipo_origen": tipo_origen.lower(), "id_origen": id_origen},
            )
            .mappings()
            .one_or_none()
        )
        return self._rg_row_to_dict(row) if row else None

    def obligaciones_exist_for_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> bool:
        stmt = text(
            """
            SELECT 1 FROM obligacion_financiera
            WHERE id_relacion_generadora = :id AND deleted_at IS NULL
            LIMIT 1
            """
        )
        return (
            self.db.execute(stmt, {"id": id_relacion_generadora}).scalar_one_or_none()
            is not None
        )

    def create_cronograma_obligaciones(self, periodos: list[Any]) -> int:
        ob_stmt = text(
            """
            INSERT INTO obligacion_financiera (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_relacion_generadora, fecha_emision, fecha_vencimiento,
                periodo_desde, periodo_hasta,
                importe_total, saldo_pendiente, moneda, estado_obligacion
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_relacion_generadora, :fecha_emision, :fecha_vencimiento,
                :periodo_desde, :periodo_hasta,
                :importe_total, :importe_total, :moneda, :estado_obligacion
            )
            ON CONFLICT (id_relacion_generadora, periodo_desde, periodo_hasta)
            WHERE (deleted_at IS NULL)
            DO NOTHING
            RETURNING id_obligacion_financiera
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
                1, :importe_componente, :importe_componente
            )
            """
        )

        obligado_stmt = text(
            """
            INSERT INTO obligacion_obligado (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_obligacion_financiera, id_persona,
                rol_obligado, porcentaje_responsabilidad
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_obligacion_financiera, :id_persona,
                :rol_obligado, 100.00
            )
            """
        )

        try:
            count = 0
            for periodo in periodos:
                pv = self._values(periodo)
                ob_row = self.db.execute(
                    ob_stmt,
                    {
                        "uid_global": pv["uid_global_obligacion"],
                        "version_registro": pv["version_registro"],
                        "created_at": pv["created_at"],
                        "updated_at": pv["updated_at"],
                        "id_instalacion_origen": pv["id_instalacion_origen"],
                        "id_instalacion_ultima_modificacion": pv["id_instalacion_ultima_modificacion"],
                        "op_id_alta": pv["op_id_alta"],
                        "op_id_ultima_modificacion": pv["op_id_ultima_modificacion"],
                        "id_relacion_generadora": pv["id_relacion_generadora"],
                        "fecha_emision": pv["fecha_emision"],
                        "fecha_vencimiento": pv["fecha_vencimiento"],
                        "periodo_desde": pv["periodo_desde"],
                        "periodo_hasta": pv["periodo_hasta"],
                        "importe_total": pv["importe_total"],
                        "moneda": pv["moneda"],
                        "estado_obligacion": pv["estado_obligacion"],
                    },
                ).mappings().one_or_none()

                if ob_row is None:
                    continue

                self.db.execute(
                    comp_stmt,
                    {
                        "uid_global": pv["uid_global_composicion"],
                        "version_registro": pv["version_registro"],
                        "created_at": pv["created_at"],
                        "updated_at": pv["updated_at"],
                        "id_instalacion_origen": pv["id_instalacion_origen"],
                        "id_instalacion_ultima_modificacion": pv["id_instalacion_ultima_modificacion"],
                        "op_id_alta": pv["op_id_alta"],
                        "op_id_ultima_modificacion": pv["op_id_ultima_modificacion"],
                        "id_obligacion_financiera": ob_row["id_obligacion_financiera"],
                        "id_concepto_financiero": pv["id_concepto_financiero"],
                        "importe_componente": pv["importe_total"],
                    },
                )
                self.db.execute(
                    obligado_stmt,
                    {
                        "uid_global": pv["uid_global_obligado"],
                        "version_registro": pv["version_registro"],
                        "created_at": pv["created_at"],
                        "updated_at": pv["updated_at"],
                        "id_instalacion_origen": pv["id_instalacion_origen"],
                        "id_instalacion_ultima_modificacion": pv["id_instalacion_ultima_modificacion"],
                        "op_id_alta": pv["op_id_alta"],
                        "op_id_ultima_modificacion": pv["op_id_ultima_modificacion"],
                        "id_obligacion_financiera": ob_row["id_obligacion_financiera"],
                        "id_persona": pv["id_persona_obligado"],
                        "rol_obligado": pv["rol_obligado"],
                    },
                )
                count += 1

            self.db.commit()
            return count
        except Exception:
            self.db.rollback()
            raise

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

    def get_venta_minima_para_financiero(
        self, id_venta: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_venta,
                fecha_venta,
                estado_venta,
                monto_total,
                deleted_at
            FROM venta
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """
        )
        row = (
            self.db.execute(stmt, {"id_venta": id_venta})
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    # ── contrato_alquiler / condicion_economica (lectura para financiero) ────────

    def get_contrato_alquiler_para_financiero(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT id_contrato_alquiler, fecha_inicio, estado_contrato, deleted_at
            FROM contrato_alquiler
            WHERE id_contrato_alquiler = :id AND deleted_at IS NULL
            """
        )
        row = self.db.execute(stmt, {"id": id_contrato_alquiler}).mappings().one_or_none()
        return dict(row) if row else None

    def get_condicion_economica_vigente_para_financiero(
        self, id_contrato_alquiler: int, fecha_referencia: date
    ) -> dict[str, Any] | None:
        # Condicion que cubre fecha_referencia
        stmt = text(
            """
            SELECT monto_base, moneda
            FROM condicion_economica_alquiler
            WHERE id_contrato_alquiler = :id
              AND deleted_at IS NULL
              AND fecha_desde <= :fecha
              AND (fecha_hasta IS NULL OR fecha_hasta >= :fecha)
            ORDER BY fecha_desde ASC
            LIMIT 1
            """
        )
        row = self.db.execute(
            stmt, {"id": id_contrato_alquiler, "fecha": fecha_referencia}
        ).mappings().one_or_none()
        if row is not None:
            return dict(row)
        # Fallback: primera condicion disponible
        stmt_fallback = text(
            """
            SELECT monto_base, moneda
            FROM condicion_economica_alquiler
            WHERE id_contrato_alquiler = :id AND deleted_at IS NULL
            ORDER BY fecha_desde ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt_fallback, {"id": id_contrato_alquiler}).mappings().one_or_none()
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
            ON CONFLICT (tipo_origen, id_origen) WHERE (deleted_at IS NULL)
            DO UPDATE SET updated_at = relacion_generadora.updated_at
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
        return self._rg_row_to_dict(row)

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

    def get_relacion_generadora_by_origen(
        self, tipo_origen: str, id_origen: int
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
            WHERE UPPER(tipo_origen) = :tipo_origen
              AND id_origen = :id_origen
              AND deleted_at IS NULL
            ORDER BY id_relacion_generadora ASC
            LIMIT 1
            """
        )
        row = (
            self.db.execute(
                stmt,
                {
                    "tipo_origen": tipo_origen.strip().upper(),
                    "id_origen": id_origen,
                },
            )
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

    # ── deuda consolidada ─────────────────────────────────────────────────────

    def list_deuda_consolidada(
        self,
        *,
        id_relacion_generadora: int | None,
        estado_obligacion: str | None,
        fecha_vencimiento_desde: date | None,
        fecha_vencimiento_hasta: date | None,
        con_saldo: bool | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        filters: list[str] = ["o.deleted_at IS NULL"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if id_relacion_generadora is not None:
            filters.append("o.id_relacion_generadora = :id_relacion_generadora")
            params["id_relacion_generadora"] = id_relacion_generadora

        if estado_obligacion is not None:
            filters.append("o.estado_obligacion = :estado_obligacion")
            params["estado_obligacion"] = estado_obligacion.strip().upper()

        if fecha_vencimiento_desde is not None:
            filters.append("o.fecha_vencimiento >= :fecha_desde")
            params["fecha_desde"] = fecha_vencimiento_desde

        if fecha_vencimiento_hasta is not None:
            filters.append("o.fecha_vencimiento <= :fecha_hasta")
            params["fecha_hasta"] = fecha_vencimiento_hasta

        if con_saldo is True:
            filters.append("o.saldo_pendiente > 0")

        where = " AND ".join(filters)

        ob_stmt = text(
            f"""
            SELECT
                o.id_obligacion_financiera,
                o.id_relacion_generadora,
                o.estado_obligacion,
                o.fecha_vencimiento,
                o.importe_total,
                o.saldo_pendiente
            FROM obligacion_financiera o
            WHERE {where}
            ORDER BY o.id_obligacion_financiera DESC
            LIMIT :limit OFFSET :offset
            """
        )
        total_stmt = text(
            f"SELECT COUNT(*) FROM obligacion_financiera o WHERE {where}"
        )

        ob_rows = self.db.execute(ob_stmt, params).mappings().all()
        total = self.db.execute(total_stmt, params).scalar_one()

        if not ob_rows:
            return {"items": [], "total": total}

        ids = [row["id_obligacion_financiera"] for row in ob_rows]

        comp_stmt = text(
            """
            SELECT
                c.id_composicion_obligacion,
                c.id_obligacion_financiera,
                cf.codigo_concepto_financiero,
                c.importe_componente,
                c.saldo_componente
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
                ON c.id_concepto_financiero = cf.id_concepto_financiero
            WHERE c.id_obligacion_financiera IN :ids
              AND c.deleted_at IS NULL
              AND cf.deleted_at IS NULL
            ORDER BY c.id_obligacion_financiera, c.orden_composicion ASC
            """
        ).bindparams(bindparam("ids", expanding=True))

        comp_rows = self.db.execute(comp_stmt, {"ids": ids}).mappings().all()

        comps_by_ob: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in comp_rows:
            comps_by_ob[row["id_obligacion_financiera"]].append(
                {
                    "id_composicion_obligacion": row["id_composicion_obligacion"],
                    "codigo_concepto_financiero": row["codigo_concepto_financiero"],
                    "importe_componente": float(row["importe_componente"]),
                    "saldo_componente": float(row["saldo_componente"]),
                }
            )

        fecha_corte = date.today()
        items = []
        for row in ob_rows:
            mora = _calcular_mora_dinamica(
                row["saldo_pendiente"],
                row["fecha_vencimiento"],
                fecha_corte,
            )
            items.append(
                {
                    "id_obligacion_financiera": row["id_obligacion_financiera"],
                    "id_relacion_generadora": row["id_relacion_generadora"],
                    "estado_obligacion": row["estado_obligacion"],
                    "fecha_vencimiento": row["fecha_vencimiento"],
                    "importe_total": float(row["importe_total"]),
                    "saldo_pendiente": float(row["saldo_pendiente"]),
                    **mora,
                    "composiciones": comps_by_ob[row["id_obligacion_financiera"]],
                }
            )

        return {"items": items, "total": total}

    # ── deuda consolidado global ─────────────────────────────────────────────

    def get_deuda_consolidado(
        self,
        *,
        tipo_origen: str | None,
        fecha_corte: date,
    ) -> dict[str, Any]:
        filters = [
            "o.deleted_at IS NULL",
            "rg.deleted_at IS NULL",
            "o.estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')",
            "o.saldo_pendiente > 0",
        ]
        params: dict[str, Any] = {}

        if tipo_origen is not None:
            filters.append("UPPER(rg.tipo_origen) = :tipo_origen")
            params["tipo_origen"] = tipo_origen.strip().upper()

        where = " AND ".join(filters)

        stmt = text(
            f"""
            SELECT
                o.id_relacion_generadora,
                rg.tipo_origen,
                rg.id_origen,
                o.fecha_vencimiento,
                o.saldo_pendiente
            FROM obligacion_financiera o
            JOIN relacion_generadora rg
                ON rg.id_relacion_generadora = o.id_relacion_generadora
            WHERE {where}
            ORDER BY rg.tipo_origen ASC, o.id_relacion_generadora ASC
            """
        )

        rows = self.db.execute(stmt, params).mappings().all()

        # Aggregate per relacion_generadora
        rg_map: dict[int, dict[str, Any]] = {}
        for row in rows:
            id_rg = row["id_relacion_generadora"]
            if id_rg not in rg_map:
                rg_map[id_rg] = {
                    "id_relacion_generadora": id_rg,
                    "tipo_origen": str(row["tipo_origen"]).upper(),
                    "id_origen": row["id_origen"],
                    "saldo_pendiente": Decimal("0"),
                    "saldo_vencido": Decimal("0"),
                    "saldo_futuro": Decimal("0"),
                    "mora_calculada": Decimal("0"),
                    "cantidad_obligaciones": 0,
                }

            resolucion = resolver_mora_params(
                tipo_origen=str(row["tipo_origen"]).upper(),
                id_origen=row["id_origen"],
            )
            mora = _calcular_mora_dinamica(
                row["saldo_pendiente"], row["fecha_vencimiento"], fecha_corte, resolucion
            )
            saldo = Decimal(str(row["saldo_pendiente"]))
            mora_dec = Decimal(str(mora["mora_calculada"]))
            fv = row["fecha_vencimiento"]

            rg_map[id_rg]["saldo_pendiente"] += saldo
            rg_map[id_rg]["mora_calculada"] += mora_dec
            rg_map[id_rg]["cantidad_obligaciones"] += 1
            if fv is not None and fv < fecha_corte and saldo > 0:
                rg_map[id_rg]["saldo_vencido"] += saldo
            else:
                rg_map[id_rg]["saldo_futuro"] += saldo

        relaciones: list[dict[str, Any]] = []
        for rg in rg_map.values():
            sp = rg["saldo_pendiente"]
            mc = rg["mora_calculada"]
            tc = (sp + mc).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            relaciones.append(
                {
                    "id_relacion_generadora": rg["id_relacion_generadora"],
                    "tipo_origen": rg["tipo_origen"],
                    "id_origen": rg["id_origen"],
                    "saldo_pendiente": float(sp),
                    "saldo_vencido": float(rg["saldo_vencido"]),
                    "saldo_futuro": float(rg["saldo_futuro"]),
                    "mora_calculada": float(mc),
                    "total_con_mora": float(tc),
                    "cantidad_obligaciones": rg["cantidad_obligaciones"],
                }
            )

        # Resumen global
        _D0 = Decimal("0")
        total_sp = sum((Decimal(str(r["saldo_pendiente"])) for r in relaciones), _D0)
        total_vencido = sum((Decimal(str(r["saldo_vencido"])) for r in relaciones), _D0)
        total_futuro = sum((Decimal(str(r["saldo_futuro"])) for r in relaciones), _D0)
        total_mora = sum((Decimal(str(r["mora_calculada"])) for r in relaciones), _D0)
        total_con_mora = (total_sp + total_mora).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        resumen = {
            "saldo_pendiente_total": float(total_sp),
            "saldo_vencido": float(total_vencido),
            "saldo_futuro": float(total_futuro),
            "mora_calculada": float(total_mora),
            "total_con_mora": float(total_con_mora),
        }

        # Agrupación por tipo_origen
        por_tipo: dict[str, dict[str, Any]] = {}
        for r in relaciones:
            t = r["tipo_origen"]
            if t not in por_tipo:
                por_tipo[t] = {
                    "saldo_pendiente_total": Decimal("0"),
                    "saldo_vencido": Decimal("0"),
                    "saldo_futuro": Decimal("0"),
                    "mora_calculada": Decimal("0"),
                    "cantidad_relaciones": 0,
                }
            por_tipo[t]["saldo_pendiente_total"] += Decimal(str(r["saldo_pendiente"]))
            por_tipo[t]["saldo_vencido"] += Decimal(str(r["saldo_vencido"]))
            por_tipo[t]["saldo_futuro"] += Decimal(str(r["saldo_futuro"]))
            por_tipo[t]["mora_calculada"] += Decimal(str(r["mora_calculada"]))
            por_tipo[t]["cantidad_relaciones"] += 1

        por_tipo_origen = {
            t: {
                "saldo_pendiente_total": float(v["saldo_pendiente_total"]),
                "saldo_vencido": float(v["saldo_vencido"]),
                "saldo_futuro": float(v["saldo_futuro"]),
                "mora_calculada": float(v["mora_calculada"]),
                "total_con_mora": float(
                    (v["saldo_pendiente_total"] + v["mora_calculada"]).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                ),
                "cantidad_relaciones": v["cantidad_relaciones"],
            }
            for t, v in por_tipo.items()
        }

        return {
            "fecha_corte": fecha_corte,
            "resumen": resumen,
            "por_tipo_origen": por_tipo_origen,
            "relaciones": relaciones,
        }

    # ── estado de cuenta ────────────────────────────────────────────────────

    def has_obligaciones_by_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM obligacion_financiera
            WHERE id_relacion_generadora = :id_relacion_generadora
              AND deleted_at IS NULL
            LIMIT 1
            """
        )
        return (
            self.db.execute(
                stmt,
                {"id_relacion_generadora": id_relacion_generadora},
            ).scalar_one_or_none()
            is not None
        )

    def get_estado_cuenta_financiero(
        self,
        *,
        id_relacion_generadora: int,
        incluir_canceladas: bool,
        fecha_desde: date | None,
        fecha_hasta: date | None,
    ) -> dict[str, Any]:
        filters = ["o.id_relacion_generadora = :id_relacion_generadora", "o.deleted_at IS NULL"]
        params: dict[str, Any] = {"id_relacion_generadora": id_relacion_generadora}

        if not incluir_canceladas:
            filters.append(
                "o.estado_obligacion NOT IN ('CANCELADA', 'ANULADA', 'REEMPLAZADA', 'PENDIENTE_AJUSTE')"
            )
        if fecha_desde is not None:
            filters.append("o.fecha_vencimiento >= :fecha_desde")
            params["fecha_desde"] = fecha_desde
        if fecha_hasta is not None:
            filters.append("o.fecha_vencimiento <= :fecha_hasta")
            params["fecha_hasta"] = fecha_hasta

        where = " AND ".join(filters)
        ob_stmt = text(
            f"""
            SELECT
                o.id_obligacion_financiera,
                o.estado_obligacion,
                o.fecha_emision,
                o.fecha_vencimiento,
                o.importe_total,
                o.saldo_pendiente,
                o.importe_cancelado_acumulado
            FROM obligacion_financiera o
            WHERE {where}
            ORDER BY o.fecha_vencimiento ASC NULLS LAST, o.id_obligacion_financiera ASC
            """
        )
        ob_rows = self.db.execute(ob_stmt, params).mappings().all()

        if not ob_rows:
            return {
                "id_relacion_generadora": id_relacion_generadora,
                "resumen": {
                    "importe_total": 0.0,
                    "saldo_pendiente": 0.0,
                    "importe_cancelado": 0.0,
                    "cantidad_obligaciones": 0,
                    "cantidad_vencidas": 0,
                },
                "obligaciones": [],
            }

        ids = [row["id_obligacion_financiera"] for row in ob_rows]

        comp_stmt = text(
            """
            SELECT
                c.id_composicion_obligacion,
                c.id_obligacion_financiera,
                cf.codigo_concepto_financiero,
                c.orden_composicion,
                c.estado_composicion_obligacion,
                c.importe_componente,
                c.saldo_componente
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
                ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE c.id_obligacion_financiera IN :ids
              AND c.deleted_at IS NULL
              AND cf.deleted_at IS NULL
            ORDER BY c.id_obligacion_financiera, c.orden_composicion ASC
            """
        ).bindparams(bindparam("ids", expanding=True))
        comp_rows = self.db.execute(comp_stmt, {"ids": ids}).mappings().all()

        aplic_stmt = text(
            """
            SELECT
                a.id_aplicacion_financiera,
                a.id_obligacion_financiera,
                a.id_movimiento_financiero,
                a.id_composicion_obligacion,
                a.fecha_aplicacion,
                a.tipo_aplicacion,
                a.orden_aplicacion,
                a.importe_aplicado,
                a.origen_automatico_o_manual
            FROM aplicacion_financiera a
            WHERE a.id_obligacion_financiera IN :ids
              AND a.deleted_at IS NULL
            ORDER BY
                a.id_obligacion_financiera,
                a.fecha_aplicacion ASC,
                a.orden_aplicacion ASC NULLS LAST,
                a.id_aplicacion_financiera ASC
            """
        ).bindparams(bindparam("ids", expanding=True))
        aplic_rows = self.db.execute(aplic_stmt, {"ids": ids}).mappings().all()

        comps_by_ob: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in comp_rows:
            comps_by_ob[row["id_obligacion_financiera"]].append(
                {
                    "id_composicion_obligacion": row["id_composicion_obligacion"],
                    "codigo_concepto_financiero": row["codigo_concepto_financiero"],
                    "orden_composicion": row["orden_composicion"],
                    "estado_composicion_obligacion": row[
                        "estado_composicion_obligacion"
                    ],
                    "importe_componente": float(row["importe_componente"]),
                    "saldo_componente": float(row["saldo_componente"]),
                }
            )

        aplics_by_ob: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for row in aplic_rows:
            aplics_by_ob[row["id_obligacion_financiera"]].append(
                {
                    "id_aplicacion_financiera": row["id_aplicacion_financiera"],
                    "id_movimiento_financiero": row["id_movimiento_financiero"],
                    "id_composicion_obligacion": row["id_composicion_obligacion"],
                    "fecha_aplicacion": row["fecha_aplicacion"],
                    "tipo_aplicacion": row["tipo_aplicacion"],
                    "orden_aplicacion": row["orden_aplicacion"],
                    "importe_aplicado": float(row["importe_aplicado"]),
                    "origen_automatico_o_manual": row["origen_automatico_o_manual"],
                }
            )

        fecha_corte = date.today()
        obligaciones = []
        for row in ob_rows:
            mora = _calcular_mora_dinamica(
                row["saldo_pendiente"],
                row["fecha_vencimiento"],
                fecha_corte,
            )
            obligaciones.append(
                {
                    "id_obligacion_financiera": row["id_obligacion_financiera"],
                    "estado_obligacion": row["estado_obligacion"],
                    "fecha_emision": row["fecha_emision"],
                    "fecha_vencimiento": row["fecha_vencimiento"],
                    "importe_total": float(row["importe_total"]),
                    "saldo_pendiente": float(row["saldo_pendiente"]),
                    **mora,
                    "composiciones": comps_by_ob[row["id_obligacion_financiera"]],
                    "aplicaciones": aplics_by_ob[row["id_obligacion_financiera"]],
                }
            )

        return {
            "id_relacion_generadora": id_relacion_generadora,
            "resumen": {
                "importe_total": float(sum(row["importe_total"] for row in ob_rows)),
                "saldo_pendiente": float(sum(row["saldo_pendiente"] for row in ob_rows)),
                "mora_calculada": float(
                    sum(obligacion["mora_calculada"] for obligacion in obligaciones)
                ),
                "importe_cancelado": float(
                    sum(row["importe_cancelado_acumulado"] for row in ob_rows)
                ),
                "cantidad_obligaciones": len(ob_rows),
                "cantidad_vencidas": sum(
                    1
                    for row in ob_rows
                    if row["fecha_vencimiento"] is not None
                    and row["fecha_vencimiento"] < date.today()
                    and row["saldo_pendiente"] > 0
                ),
            },
            "obligaciones": obligaciones,
        }

    # ── mora financiera ─────────────────────────────────────────────────────

    def buscar_obligaciones_elegibles_mora(
        self, fecha_proceso: date
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                o.id_obligacion_financiera,
                o.id_relacion_generadora,
                o.fecha_vencimiento,
                o.saldo_pendiente,
                o.estado_obligacion
            FROM obligacion_financiera o
            WHERE o.fecha_vencimiento < :fecha_proceso
              AND o.saldo_pendiente > 0
              AND o.deleted_at IS NULL
              AND o.estado_obligacion = 'EMITIDA'
            ORDER BY o.id_obligacion_financiera ASC
            FOR UPDATE
            """
        )
        rows = self.db.execute(
            stmt, {"fecha_proceso": fecha_proceso}
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_obligaciones_reemplazables(
        self, id_relacion_generadora: int, fecha_corte: date
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                o.id_obligacion_financiera,
                o.periodo_desde,
                o.periodo_hasta,
                o.estado_obligacion
            FROM obligacion_financiera o
            WHERE o.id_relacion_generadora = :id_rg
              AND o.deleted_at IS NULL
              AND o.periodo_desde >= :fecha_corte
              AND o.estado_obligacion NOT IN (
                  'CANCELADA', 'PARCIALMENTE_CANCELADA', 'ANULADA', 'REEMPLAZADA'
              )
              AND NOT EXISTS (
                  SELECT 1 FROM aplicacion_financiera a
                  WHERE a.id_obligacion_financiera = o.id_obligacion_financiera
                    AND a.deleted_at IS NULL
              )
            ORDER BY o.periodo_desde ASC
            """
        )
        rows = self.db.execute(
            stmt, {"id_rg": id_relacion_generadora, "fecha_corte": fecha_corte}
        ).mappings().all()
        return [dict(r) for r in rows]

    def marcar_obligaciones_reemplazadas(self, ids: list[int]) -> int:
        # CLOCK_TIMESTAMP() devuelve el tiempo real de ejecución (no el inicio
        # de transacción) para garantizar que deleted_at >= created_at.
        stmt = text(
            """
            UPDATE obligacion_financiera
            SET estado_obligacion = 'REEMPLAZADA',
                deleted_at = CLOCK_TIMESTAMP(),
                updated_at = CLOCK_TIMESTAMP()
            WHERE id_obligacion_financiera = ANY(:ids)
              AND estado_obligacion NOT IN ('CANCELADA', 'PARCIALMENTE_CANCELADA')
            """
        )
        result = self.db.execute(stmt, {"ids": ids})
        self.db.commit()
        return result.rowcount or 0

    def marcar_obligaciones_vencidas(self, fecha_proceso: date) -> int:
        stmt = text(
            """
            UPDATE obligacion_financiera
            SET estado_obligacion = 'VENCIDA',
                updated_at = CURRENT_TIMESTAMP
            WHERE fecha_vencimiento < :fecha_proceso
              AND saldo_pendiente > 0
              AND deleted_at IS NULL
              AND estado_obligacion = 'EMITIDA'
            """
        )
        result = self.db.execute(stmt, {"fecha_proceso": fecha_proceso})
        self.db.commit()
        return result.rowcount or 0

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
              AND cf.deleted_at IS NULL
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
              AND cf.deleted_at IS NULL
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

        result = dict(ob_row)
        result["uid_global"] = str(result["uid_global"])
        result["composiciones"] = comp_results
        return result

    # ── registro de pago (multi-obligación) ─────────────────────────────────

    def get_pago_persona_by_op_id(
        self, *, id_persona: int, op_id: Any
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                m.id_movimiento_financiero,
                m.fecha_movimiento,
                m.importe AS monto_consumido,
                m.observaciones,
                a.id_obligacion_financiera,
                COALESCE(SUM(a.importe_aplicado), 0) AS monto_aplicado,
                o.estado_obligacion AS estado_resultante
            FROM movimiento_financiero m
            JOIN aplicacion_financiera a
              ON a.id_movimiento_financiero = m.id_movimiento_financiero
             AND a.deleted_at IS NULL
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = a.id_obligacion_financiera
             AND o.deleted_at IS NULL
            JOIN obligacion_obligado oo
              ON oo.id_obligacion_financiera = o.id_obligacion_financiera
             AND oo.deleted_at IS NULL
             AND oo.id_persona = :id_persona
            WHERE m.op_id_alta = :op_id
              AND m.tipo_movimiento = 'PAGO'
              AND m.deleted_at IS NULL
            GROUP BY
                m.id_movimiento_financiero,
                m.fecha_movimiento,
                m.importe,
                m.observaciones,
                a.id_obligacion_financiera,
                o.estado_obligacion
            ORDER BY m.id_movimiento_financiero ASC
            """
        )
        rows = (
            self.db.execute(stmt, {"id_persona": id_persona, "op_id": op_id})
            .mappings()
            .all()
        )
        if not rows:
            return None

        obligaciones_pagadas = [
            {
                "id_obligacion_financiera": row["id_obligacion_financiera"],
                "id_movimiento_financiero": row["id_movimiento_financiero"],
                "monto_aplicado": float(row["monto_aplicado"]),
                "estado_resultante": row["estado_resultante"],
            }
            for row in rows
        ]
        resumen = None
        if rows[0]["observaciones"]:
            try:
                parsed = json.loads(rows[0]["observaciones"])
                if parsed.get("tipo") == "pago_persona":
                    resumen = parsed
            except (TypeError, ValueError):
                resumen = None

        return {
            "fecha_pago": (
                date.fromisoformat(resumen["fecha_pago"])
                if resumen is not None
                else rows[0]["fecha_movimiento"].date()
            ),
            "monto_aplicado": float(
                resumen["monto_aplicado"]
                if resumen is not None
                else sum(row["monto_aplicado"] for row in rows)
            ),
            "monto_consumido": float(
                (Decimal(str(resumen["monto_ingresado"])) - Decimal(str(resumen["remanente"])))
                if resumen is not None
                else sum(row["monto_consumido"] for row in rows)
            ),
            "obligaciones_pagadas": obligaciones_pagadas,
        }

    def get_ultima_fecha_pago_posterior_vencimiento(
        self, *, id_obligacion_financiera: int, fecha_vencimiento: date
    ) -> date | None:
        stmt = text(
            """
            SELECT MAX(m.fecha_movimiento::date) AS ultima_fecha
            FROM movimiento_financiero m
            JOIN aplicacion_financiera a
              ON a.id_movimiento_financiero = m.id_movimiento_financiero
             AND a.deleted_at IS NULL
            WHERE a.id_obligacion_financiera = :id_obligacion_financiera
              AND m.tipo_movimiento = 'PAGO'
              AND m.deleted_at IS NULL
              AND m.fecha_movimiento::date > :fecha_vencimiento
            """
        )
        return self.db.execute(
            stmt,
            {
                "id_obligacion_financiera": id_obligacion_financiera,
                "fecha_vencimiento": fecha_vencimiento,
            },
        ).scalar_one_or_none()

    def get_saldo_morable_pendiente(
        self, *, id_obligacion_financiera: int
    ) -> Decimal:
        stmt = text(
            """
            SELECT COALESCE(SUM(c.saldo_componente), 0) AS saldo_morable
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
             AND cf.deleted_at IS NULL
            WHERE c.id_obligacion_financiera = :id_obligacion_financiera
              AND c.estado_composicion_obligacion = 'ACTIVA'
              AND c.deleted_at IS NULL
              AND cf.aplica_punitorio = true
            """
        )
        saldo = self.db.execute(
            stmt, {"id_obligacion_financiera": id_obligacion_financiera}
        ).scalar_one()
        return Decimal(str(saldo))

    def liquidar_punitorio_obligacion(
        self,
        *,
        id_obligacion_financiera: int,
        importe_punitorio: Decimal,
        detalle_calculo: str,
        now: Any,
        id_instalacion: Any,
        op_id: Any,
        uid_global: str,
    ) -> dict[str, Any]:
        update_stmt = text(
            """
            UPDATE composicion_obligacion c
            SET importe_componente = c.importe_componente + :importe_punitorio,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id,
                detalle_calculo = :detalle_calculo
            FROM concepto_financiero cf
            WHERE c.id_concepto_financiero = cf.id_concepto_financiero
              AND c.id_obligacion_financiera = :id_obligacion_financiera
              AND c.estado_composicion_obligacion = 'ACTIVA'
              AND c.deleted_at IS NULL
              AND cf.codigo_concepto_financiero = 'PUNITORIO'
              AND cf.deleted_at IS NULL
            RETURNING
                c.id_composicion_obligacion,
                c.importe_componente,
                c.saldo_componente
            """
        )
        row = self.db.execute(
            update_stmt,
            {
                "id_obligacion_financiera": id_obligacion_financiera,
                "importe_punitorio": importe_punitorio,
                "updated_at": now,
                "id_instalacion": id_instalacion,
                "op_id": op_id,
                "detalle_calculo": detalle_calculo,
            },
        ).mappings().one_or_none()
        if row is not None:
            return dict(row)

        insert_stmt = text(
            """
            INSERT INTO composicion_obligacion (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_obligacion_financiera, id_concepto_financiero,
                orden_composicion, importe_componente, saldo_componente,
                detalle_calculo, observaciones
            )
            SELECT
                :uid_global, 1, :created_at, :updated_at,
                :id_instalacion, :id_instalacion,
                :op_id, :op_id,
                :id_obligacion_financiera, cf.id_concepto_financiero,
                COALESCE((
                    SELECT MAX(c2.orden_composicion) + 1
                    FROM composicion_obligacion c2
                    WHERE c2.id_obligacion_financiera = :id_obligacion_financiera
                      AND c2.deleted_at IS NULL
                ), 1),
                :importe_punitorio, :importe_punitorio,
                :detalle_calculo, 'Punitorio liquidado al registrar pago'
            FROM concepto_financiero cf
            WHERE cf.codigo_concepto_financiero = 'PUNITORIO'
              AND cf.deleted_at IS NULL
            RETURNING
                id_composicion_obligacion,
                importe_componente,
                saldo_componente
            """
        )
        inserted = self.db.execute(
            insert_stmt,
            {
                "uid_global": uid_global,
                "created_at": now,
                "updated_at": now,
                "id_instalacion": id_instalacion,
                "op_id": op_id,
                "id_obligacion_financiera": id_obligacion_financiera,
                "importe_punitorio": importe_punitorio,
                "detalle_calculo": detalle_calculo,
            },
        ).mappings().one_or_none()
        if inserted is None:
            raise ValueError("Concepto financiero PUNITORIO no encontrado")
        return dict(inserted)

    def registrar_pago_multipago(
        self,
        pagos: list[Any],
    ) -> list[dict[str, Any]]:
        """
        Persiste movimiento_financiero + aplicacion_financiera para una lista de
        obligaciones en una sola transacción. Commit único al final.
        """
        mov_stmt = text(
            """
            INSERT INTO movimiento_financiero (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                fecha_movimiento, tipo_movimiento, importe, signo, estado_movimiento,
                observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :fecha_movimiento, :tipo_movimiento, :importe, :signo, :estado_movimiento,
                :observaciones
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
            RETURNING id_aplicacion_financiera, id_composicion_obligacion,
                      importe_aplicado, orden_aplicacion
            """
        )

        estado_stmt = text(
            """
            UPDATE obligacion_financiera
            SET estado_obligacion = CASE
                    WHEN saldo_pendiente = 0             THEN 'CANCELADA'
                    WHEN saldo_pendiente < importe_total THEN 'PARCIALMENTE_CANCELADA'
                    ELSE estado_obligacion
                END
            WHERE id_obligacion_financiera = :id
              AND estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')
            RETURNING estado_obligacion, saldo_pendiente
            """
        )

        try:
            resultados: list[dict[str, Any]] = []

            for pago in pagos:
                pv = self._values(pago)
                mov_row = self.db.execute(
                    mov_stmt,
                    {
                        "uid_global": pv["uid_global_movimiento"],
                        "version_registro": pv["version_registro"],
                        "created_at": pv["created_at"],
                        "updated_at": pv["updated_at"],
                        "id_instalacion_origen": pv["id_instalacion_origen"],
                        "id_instalacion_ultima_modificacion": pv["id_instalacion_ultima_modificacion"],
                        "op_id_alta": pv["op_id_alta"],
                        "op_id_ultima_modificacion": pv["op_id_ultima_modificacion"],
                        "fecha_movimiento": pv["fecha_movimiento"],
                        "tipo_movimiento": "PAGO",
                        "importe": pv["monto_a_aplicar"],
                        "signo": "CREDITO",
                        "estado_movimiento": "APLICADO",
                        "observaciones": pv["observaciones"],
                    },
                ).mappings().one()

                id_movimiento = mov_row["id_movimiento_financiero"]
                aplics: list[dict[str, Any]] = []

                for i, linea in enumerate(pv["lineas"]):
                    lv = self._values(linea) if not isinstance(linea, dict) else linea
                    aplic_row = self.db.execute(
                        aplic_stmt,
                        {
                            "uid_global": lv["uid_global"],
                            "version_registro": pv["version_registro"],
                            "created_at": pv["created_at"],
                            "updated_at": pv["updated_at"],
                            "id_instalacion_origen": pv["id_instalacion_origen"],
                            "id_instalacion_ultima_modificacion": pv["id_instalacion_ultima_modificacion"],
                            "op_id_alta": pv["op_id_alta"],
                            "op_id_ultima_modificacion": pv["op_id_ultima_modificacion"],
                            "id_movimiento_financiero": id_movimiento,
                            "id_obligacion_financiera": pv["id_obligacion_financiera"],
                            "id_composicion_obligacion": lv["id_composicion_obligacion"],
                            "fecha_aplicacion": pv["fecha_movimiento"],
                            "tipo_aplicacion": "PAGO",
                            "orden_aplicacion": i + 1,
                            "importe_aplicado": lv["importe_aplicado"],
                            "origen_automatico_o_manual": "MANUAL",
                        },
                    ).mappings().one()
                    aplics.append(dict(aplic_row))

                estado_row = self.db.execute(
                    estado_stmt,
                    {"id": pv["id_obligacion_financiera"]},
                ).mappings().one_or_none()

                resultados.append(
                    {
                        "id_obligacion_financiera": pv["id_obligacion_financiera"],
                        "id_movimiento_financiero": id_movimiento,
                        "monto_aplicado": float(pv["monto_a_aplicar"]),
                        "estado_resultante": estado_row["estado_obligacion"] if estado_row else None,
                    }
                )

            self.db.commit()
            return resultados
        except Exception:
            self.db.rollback()
            raise

    # ── simulación de pago por persona ──────────────────────────────────────

    def get_obligaciones_para_simular_pago(
        self,
        *,
        id_persona: int,
        fecha_corte: date,
    ) -> list[dict[str, Any]]:
        """
        Obligaciones con saldo > 0 de la persona, ordenadas vencidas primero.
        Vencida = fecha_vencimiento < fecha_corte.
        """
        stmt = text(
            """
            SELECT
                o.id_obligacion_financiera,
                o.fecha_vencimiento,
                o.saldo_pendiente,
                oo.porcentaje_responsabilidad
            FROM obligacion_obligado oo
            JOIN obligacion_financiera o
                ON o.id_obligacion_financiera = oo.id_obligacion_financiera
            WHERE oo.id_persona = :id_persona
              AND oo.deleted_at IS NULL
              AND o.deleted_at IS NULL
              AND o.estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')
              AND o.saldo_pendiente > 0
            ORDER BY
              CASE WHEN o.fecha_vencimiento IS NOT NULL
                        AND o.fecha_vencimiento < :fecha_corte
                   THEN 0 ELSE 1 END ASC,
              o.fecha_vencimiento ASC NULLS LAST,
              o.id_obligacion_financiera ASC
            """
        )
        rows = self.db.execute(
            stmt, {"id_persona": id_persona, "fecha_corte": fecha_corte}
        ).mappings().all()
        return [dict(r) for r in rows]

    # ── estado de cuenta por persona ────────────────────────────────────────

    def get_estado_cuenta_por_persona(
        self,
        *,
        id_persona: int,
        estado: str | None,
        tipo_origen: str | None,
        id_origen: int | None,
        vencidas: bool | None,
        fecha_vencimiento_desde: date | None,
        fecha_vencimiento_hasta: date | None,
        fecha_corte: date,
    ) -> dict[str, Any]:
        filters = [
            "oo.id_persona = :id_persona",
            "oo.deleted_at IS NULL",
            "o.deleted_at IS NULL",
            "rg.deleted_at IS NULL",
            "o.estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')",
        ]
        params: dict[str, Any] = {"id_persona": id_persona}

        if estado is not None:
            filters.append("o.estado_obligacion = :estado")
            params["estado"] = estado.strip().upper()
        if tipo_origen is not None:
            filters.append("UPPER(rg.tipo_origen) = :tipo_origen")
            params["tipo_origen"] = tipo_origen.strip().upper()
        if id_origen is not None:
            filters.append("rg.id_origen = :id_origen")
            params["id_origen"] = id_origen
        if vencidas is True:
            filters.append("o.fecha_vencimiento < :fecha_corte_v AND o.saldo_pendiente > 0")
            params["fecha_corte_v"] = fecha_corte
        if fecha_vencimiento_desde is not None:
            filters.append("o.fecha_vencimiento >= :fec_desde")
            params["fec_desde"] = fecha_vencimiento_desde
        if fecha_vencimiento_hasta is not None:
            filters.append("o.fecha_vencimiento <= :fec_hasta")
            params["fec_hasta"] = fecha_vencimiento_hasta

        where = " AND ".join(filters)

        ob_stmt = text(
            f"""
            SELECT
                o.id_obligacion_financiera,
                o.id_relacion_generadora,
                rg.tipo_origen,
                rg.id_origen,
                o.periodo_desde,
                o.periodo_hasta,
                o.fecha_vencimiento,
                o.estado_obligacion,
                o.importe_total,
                o.saldo_pendiente,
                oo.porcentaje_responsabilidad
            FROM obligacion_obligado oo
            JOIN obligacion_financiera o
                ON o.id_obligacion_financiera = oo.id_obligacion_financiera
            JOIN relacion_generadora rg
                ON rg.id_relacion_generadora = o.id_relacion_generadora
            WHERE {where}
            ORDER BY o.fecha_vencimiento ASC NULLS LAST, o.id_obligacion_financiera ASC
            """
        )

        rows = self.db.execute(ob_stmt, params).mappings().all()

        obligaciones = []
        saldo_total = Decimal("0")
        saldo_vencido = Decimal("0")
        saldo_futuro = Decimal("0")
        mora_total = Decimal("0")

        for row in rows:
            saldo = Decimal(str(row["saldo_pendiente"]))
            pct = Decimal(str(row["porcentaje_responsabilidad"]))

            resolucion = resolver_mora_params(
                tipo_origen=str(row["tipo_origen"]).upper(),
                id_origen=row["id_origen"],
            )
            mora = _calcular_mora_dinamica(
                row["saldo_pendiente"], row["fecha_vencimiento"], fecha_corte, resolucion
            )
            mora_dec = Decimal(str(mora["mora_calculada"]))

            monto_resp = (saldo * pct / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            total_con_mora_ob = ((saldo + mora_dec) * pct / 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            saldo_total += saldo
            mora_total += mora_dec
            fv = row["fecha_vencimiento"]
            if fv is not None and fv < fecha_corte and saldo > 0:
                saldo_vencido += saldo
            else:
                saldo_futuro += saldo

            obligaciones.append(
                {
                    "id_obligacion_financiera": row["id_obligacion_financiera"],
                    "id_relacion_generadora": row["id_relacion_generadora"],
                    "tipo_origen": str(row["tipo_origen"]).upper(),
                    "id_origen": row["id_origen"],
                    "periodo_desde": row["periodo_desde"],
                    "periodo_hasta": row["periodo_hasta"],
                    "fecha_vencimiento": fv,
                    "estado_obligacion": row["estado_obligacion"],
                    "importe_total": float(row["importe_total"]),
                    "saldo_pendiente": float(saldo),
                    "porcentaje_responsabilidad": float(pct),
                    "monto_responsabilidad": float(monto_resp),
                    **mora,
                    "total_con_mora": float(total_con_mora_ob),
                }
            )

        total_con_mora_res = (saldo_total + mora_total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return {
            "id_persona": id_persona,
            "fecha_corte": fecha_corte,
            "resumen": {
                "saldo_pendiente_total": float(saldo_total),
                "saldo_vencido": float(saldo_vencido),
                "saldo_futuro": float(saldo_futuro),
                "mora_calculada": float(mora_total),
                "total_con_mora": float(total_con_mora_res),
            },
            "obligaciones": obligaciones,
        }

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
