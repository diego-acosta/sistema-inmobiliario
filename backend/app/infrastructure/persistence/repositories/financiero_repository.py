from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import UTC, date, datetime, timedelta
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


def _append_motivo_anulacion(observaciones: str | None, motivo: str) -> str:
    payload: dict[str, Any]
    if observaciones:
        try:
            parsed = json.loads(observaciones)
            payload = parsed if isinstance(parsed, dict) else {"observaciones": observaciones}
        except (TypeError, ValueError):
            payload = {"observaciones": observaciones}
    else:
        payload = {}
    payload["anulacion"] = {
        "motivo": motivo,
        "fecha_anulacion": datetime.now(UTC).isoformat(),
    }
    return json.dumps(payload, separators=(",", ":"))


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

    def inmueble_exists(self, id_inmueble: int) -> bool:
        stmt = text(
            "SELECT 1 FROM inmueble WHERE id_inmueble = :id AND deleted_at IS NULL"
        )
        return self.db.execute(stmt, {"id": id_inmueble}).scalar_one_or_none() is not None

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        stmt = text(
            "SELECT 1 FROM unidad_funcional WHERE id_unidad_funcional = :id AND deleted_at IS NULL"
        )
        return (
            self.db.execute(stmt, {"id": id_unidad_funcional}).scalar_one_or_none()
            is not None
        )

    def comprobante_impuesto_activo_exists(
        self, organismo: str, numero_comprobante: str
    ) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM comprobante_impuesto
            WHERE organismo = :organismo
              AND numero_comprobante = :numero_comprobante
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(
                stmt,
                {"organismo": organismo, "numero_comprobante": numero_comprobante},
            ).scalar_one_or_none()
            is not None
        )

    def _comprobante_impuesto_row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "id_comprobante_impuesto": row["id_comprobante_impuesto"],
            "uid_global": str(row["uid_global"]),
            "version_registro": row["version_registro"],
            "id_inmueble": row["id_inmueble"],
            "id_unidad_funcional": row["id_unidad_funcional"],
            "organismo": row["organismo"],
            "tipo_impuesto": row["tipo_impuesto"],
            "partida_nomenclatura": row["partida_nomenclatura"],
            "numero_comprobante": row["numero_comprobante"],
            "periodo_desde": (
                row["periodo_desde"].isoformat()
                if row["periodo_desde"] is not None
                else None
            ),
            "periodo_hasta": (
                row["periodo_hasta"].isoformat()
                if row["periodo_hasta"] is not None
                else None
            ),
            "fecha_emision": (
                row["fecha_emision"].isoformat()
                if row["fecha_emision"] is not None
                else None
            ),
            "fecha_vencimiento": row["fecha_vencimiento"].isoformat(),
            "importe_total": float(row["importe_total"]),
            "modalidad_gestion_impuesto": row["modalidad_gestion_impuesto"],
            "estado_comprobante_impuesto": row["estado_comprobante_impuesto"],
            "observaciones": row["observaciones"],
        }

    def create_comprobante_impuesto(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        stmt = text(
            """
            INSERT INTO comprobante_impuesto (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_inmueble,
                id_unidad_funcional,
                organismo,
                tipo_impuesto,
                partida_nomenclatura,
                numero_comprobante,
                periodo_desde,
                periodo_hasta,
                fecha_emision,
                fecha_vencimiento,
                importe_total,
                modalidad_gestion_impuesto,
                observaciones
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
                :id_inmueble,
                :id_unidad_funcional,
                :organismo,
                :tipo_impuesto,
                :partida_nomenclatura,
                :numero_comprobante,
                :periodo_desde,
                :periodo_hasta,
                :fecha_emision,
                :fecha_vencimiento,
                :importe_total,
                :modalidad_gestion_impuesto,
                :observaciones
            )
            RETURNING
                id_comprobante_impuesto,
                uid_global,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                organismo,
                tipo_impuesto,
                partida_nomenclatura,
                numero_comprobante,
                periodo_desde,
                periodo_hasta,
                fecha_emision,
                fecha_vencimiento,
                importe_total,
                modalidad_gestion_impuesto,
                estado_comprobante_impuesto,
                observaciones
            """
        )
        try:
            row = self.db.execute(stmt, values).mappings().one()
            self.db.commit()
            return self._comprobante_impuesto_row_to_dict(row)
        except Exception:
            self.db.rollback()
            raise

    def get_comprobante_impuesto(
        self, id_comprobante_impuesto: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_comprobante_impuesto,
                uid_global,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                organismo,
                tipo_impuesto,
                partida_nomenclatura,
                numero_comprobante,
                periodo_desde,
                periodo_hasta,
                fecha_emision,
                fecha_vencimiento,
                importe_total,
                modalidad_gestion_impuesto,
                estado_comprobante_impuesto,
                observaciones
            FROM comprobante_impuesto
            WHERE id_comprobante_impuesto = :id
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(stmt, {"id": id_comprobante_impuesto}).mappings().one_or_none()
        if row is None:
            return None
        return self._comprobante_impuesto_row_to_dict(row)

    def list_comprobantes_impuesto(self) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                id_comprobante_impuesto,
                uid_global,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                organismo,
                tipo_impuesto,
                partida_nomenclatura,
                numero_comprobante,
                periodo_desde,
                periodo_hasta,
                fecha_emision,
                fecha_vencimiento,
                importe_total,
                modalidad_gestion_impuesto,
                estado_comprobante_impuesto,
                observaciones
            FROM comprobante_impuesto
            WHERE deleted_at IS NULL
            ORDER BY id_comprobante_impuesto
            """
        )
        rows = self.db.execute(stmt).mappings().all()
        return [self._comprobante_impuesto_row_to_dict(row) for row in rows]

    def liquidacion_recupero_exists(self, id_liquidacion_recupero: int) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM liquidacion_recupero
            WHERE id_liquidacion_recupero = :id
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(stmt, {"id": id_liquidacion_recupero}).scalar_one_or_none()
            is not None
        )

    def liquidacion_impuesto_trasladado_exists(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM liquidacion_impuesto_trasladado
            WHERE id_liquidacion_impuesto_trasladado = :id
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(
                stmt, {"id": id_liquidacion_impuesto_trasladado}
            ).scalar_one_or_none()
            is not None
        )

    def get_factura_servicio_para_materializar(
        self, id_factura_servicio: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_factura_servicio,
                id_servicio,
                id_inmueble,
                id_unidad_funcional,
                fecha_emision,
                fecha_vencimiento,
                periodo_desde,
                periodo_hasta,
                importe_total,
                estado_factura_servicio,
                proveedor,
                numero_factura
            FROM factura_servicio
            WHERE id_factura_servicio = :id
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(stmt, {"id": id_factura_servicio}).mappings().one_or_none()
        return dict(row) if row else None

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

    def get_obligacion_activa_by_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_obligacion_financiera,
                id_relacion_generadora,
                estado_obligacion
            FROM obligacion_financiera
            WHERE id_relacion_generadora = :id
              AND deleted_at IS NULL
              AND estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')
            ORDER BY id_obligacion_financiera ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, {"id": id_relacion_generadora}).mappings().one_or_none()
        return dict(row) if row else None

    def get_asignaciones_responsables_para_factura(
        self,
        *,
        id_servicio: int,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        periodo_desde: date,
        periodo_hasta: date,
    ) -> list[dict[str, Any]]:
        objeto_filter = (
            "id_inmueble = :id_objeto"
            if id_inmueble is not None
            else "id_unidad_funcional = :id_objeto"
        )
        stmt = text(
            f"""
            SELECT
                id_asignacion_servicio_responsable,
                id_persona,
                porcentaje_responsabilidad,
                fecha_desde,
                fecha_hasta
            FROM asignacion_servicio_responsable
            WHERE id_servicio = :id_servicio
              AND {objeto_filter}
              AND estado_asignacion = 'ACTIVA'
              AND deleted_at IS NULL
              AND fecha_desde <= :periodo_hasta
              AND COALESCE(fecha_hasta, DATE '9999-12-31') >= :periodo_desde
            ORDER BY fecha_desde ASC, id_asignacion_servicio_responsable ASC
            """
        )
        rows = self.db.execute(
            stmt,
            {
                "id_servicio": id_servicio,
                "id_objeto": id_inmueble if id_inmueble is not None else id_unidad_funcional,
                "periodo_desde": periodo_desde,
                "periodo_hasta": periodo_hasta,
            },
        ).mappings().all()
        return [dict(row) for row in rows]

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
            WHERE codigo_concepto_financiero = :codigo
              AND estado_concepto_financiero = 'ACTIVO'
              AND deleted_at IS NULL
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
        else:
            filters.append("o.estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')")

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
              AND o.periodo_hasta >= :fecha_corte
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

    def get_obligaciones_activas_desde(
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
            ORDER BY o.periodo_desde ASC, o.id_obligacion_financiera ASC
            """
        )
        rows = self.db.execute(
            stmt, {"id_rg": id_relacion_generadora, "fecha_corte": fecha_corte}
        ).mappings().all()
        return [dict(r) for r in rows]

    def vincular_obligaciones_reemplazo_1_a_1(
        self, pares: list[tuple[int, int]]
    ) -> int:
        if not pares:
            return 0

        stmt_vieja = text(
            """
            UPDATE obligacion_financiera vieja
            SET id_obligacion_reemplazante = :id_nueva,
                updated_at = CLOCK_TIMESTAMP()
            WHERE vieja.id_obligacion_financiera = :id_vieja
              AND vieja.estado_obligacion = 'REEMPLAZADA'
              AND vieja.deleted_at IS NOT NULL
            """
        )
        stmt_nueva = text(
            """
            UPDATE obligacion_financiera nueva
            SET id_obligacion_reemplazada = :id_vieja,
                updated_at = CLOCK_TIMESTAMP()
            WHERE nueva.id_obligacion_financiera = :id_nueva
              AND nueva.estado_obligacion = 'EMITIDA'
              AND nueva.deleted_at IS NULL
            """
        )
        try:
            vinculadas = 0
            for id_vieja, id_nueva in pares:
                params = {"id_vieja": id_vieja, "id_nueva": id_nueva}
                result_vieja = self.db.execute(stmt_vieja, params)
                result_nueva = self.db.execute(stmt_nueva, params)
                if (result_vieja.rowcount or 0) == 1 and (result_nueva.rowcount or 0) == 1:
                    vinculadas += 1
            self.db.commit()
            return vinculadas
        except Exception:
            self.db.rollback()
            raise

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

    def get_composicion_servicio_trasladado_con_saldo(
        self, id_obligacion_financiera: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                c.id_composicion_obligacion,
                c.id_obligacion_financiera,
                c.orden_composicion,
                c.importe_componente,
                c.saldo_componente,
                cf.codigo_concepto_financiero
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE c.id_obligacion_financiera = :id
              AND c.estado_composicion_obligacion = 'ACTIVA'
              AND c.deleted_at IS NULL
              AND cf.deleted_at IS NULL
              AND cf.codigo_concepto_financiero = 'SERVICIO_TRASLADADO'
              AND c.saldo_componente > 0
            ORDER BY c.orden_composicion ASC, c.id_composicion_obligacion ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, {"id": id_obligacion_financiera}).mappings().one_or_none()
        return dict(row) if row else None

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

    def obligacion_tiene_aplicaciones_activas(
        self, id_obligacion_financiera: int
    ) -> bool:
        stmt = text(
            """
            SELECT EXISTS (
                SELECT 1
                FROM aplicacion_financiera a
                WHERE a.id_obligacion_financiera = :id
                  AND a.deleted_at IS NULL
            )
            """
        )
        return bool(self.db.execute(stmt, {"id": id_obligacion_financiera}).scalar())

    def aplicar_ajuste_indexacion_obligacion(
        self,
        *,
        id_obligacion_financiera: int,
        importe_ajuste: Decimal,
        motivo: str,
        fecha_ajuste: date,
        uid_global: str,
        id_instalacion: Any,
        op_id: Any,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        ob_stmt = text(
            """
            SELECT
                id_obligacion_financiera,
                estado_obligacion,
                fecha_vencimiento,
                deleted_at
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id
            FOR UPDATE
            """
        )
        concepto_stmt = text(
            """
            SELECT id_concepto_financiero
            FROM concepto_financiero
            WHERE codigo_concepto_financiero = 'AJUSTE_INDEXACION'
              AND estado_concepto_financiero = 'ACTIVO'
              AND deleted_at IS NULL
            """
        )
        duplicado_stmt = text(
            """
            SELECT 1
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE c.id_obligacion_financiera = :id
              AND c.estado_composicion_obligacion = 'ACTIVA'
              AND c.deleted_at IS NULL
              AND cf.codigo_concepto_financiero = 'AJUSTE_INDEXACION'
              AND cf.deleted_at IS NULL
            LIMIT 1
            """
        )
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
            VALUES (
                :uid_global, 1, :created_at, :updated_at,
                :id_instalacion, :id_instalacion,
                :op_id, :op_id,
                :id_obligacion_financiera, :id_concepto_financiero,
                COALESCE((
                    SELECT MAX(c.orden_composicion) + 1
                    FROM composicion_obligacion c
                    WHERE c.id_obligacion_financiera = :id_obligacion_financiera
                      AND c.deleted_at IS NULL
                ), 1),
                :importe_ajuste, :importe_ajuste,
                :detalle_calculo, :observaciones
            )
            RETURNING id_composicion_obligacion
            """
        )
        estado_stmt = text(
            """
            UPDATE obligacion_financiera
            SET estado_obligacion = CASE
                    WHEN saldo_pendiente = 0 THEN 'CANCELADA'
                    WHEN EXISTS (
                        SELECT 1
                        FROM aplicacion_financiera a
                        WHERE a.id_obligacion_financiera = :id_obligacion_financiera
                          AND a.deleted_at IS NULL
                    ) THEN 'PARCIALMENTE_CANCELADA'
                    WHEN fecha_vencimiento IS NOT NULL
                         AND fecha_vencimiento < :fecha_ajuste THEN 'VENCIDA'
                    ELSE 'EMITIDA'
                END,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')
            RETURNING estado_obligacion, saldo_pendiente
            """
        )

        try:
            obligacion = self.db.execute(
                ob_stmt, {"id": id_obligacion_financiera}
            ).mappings().one_or_none()
            if obligacion is None or obligacion["deleted_at"] is not None:
                raise ValueError("NOT_FOUND_OBLIGACION")
            if obligacion["estado_obligacion"] in {"ANULADA", "REEMPLAZADA"}:
                raise ValueError("ESTADO_NO_ACEPTA_AJUSTE")

            id_concepto = self.db.execute(concepto_stmt).scalar_one_or_none()
            if id_concepto is None:
                raise ValueError("NOT_FOUND_CONCEPTO_AJUSTE_INDEXACION")

            duplicado = self.db.execute(
                duplicado_stmt, {"id": id_obligacion_financiera}
            ).scalar_one_or_none()
            if duplicado is not None:
                raise ValueError("AJUSTE_INDEXACION_DUPLICADO")

            detalle = json.dumps(
                {
                    "tipo": "AJUSTE_INDEXACION",
                    "fecha_ajuste": fecha_ajuste.isoformat(),
                    "motivo": motivo,
                    "importe_ajuste": float(importe_ajuste),
                },
                separators=(",", ":"),
            )
            composicion = self.db.execute(
                insert_stmt,
                {
                    "uid_global": uid_global,
                    "created_at": now,
                    "updated_at": now,
                    "id_instalacion": id_instalacion,
                    "op_id": op_id,
                    "id_obligacion_financiera": id_obligacion_financiera,
                    "id_concepto_financiero": id_concepto,
                    "importe_ajuste": importe_ajuste,
                    "detalle_calculo": detalle,
                    "observaciones": motivo,
                },
            ).mappings().one()

            estado = self.db.execute(
                estado_stmt,
                {
                    "id_obligacion_financiera": id_obligacion_financiera,
                    "fecha_ajuste": fecha_ajuste,
                    "updated_at": now,
                    "id_instalacion": id_instalacion,
                    "op_id": op_id,
                },
            ).mappings().one()

            self.db.commit()
            return {
                "id_obligacion_financiera": id_obligacion_financiera,
                "id_composicion_obligacion": composicion[
                    "id_composicion_obligacion"
                ],
                "importe_ajuste": float(importe_ajuste),
                "saldo_pendiente_actualizado": float(estado["saldo_pendiente"]),
                "estado_obligacion": estado["estado_obligacion"],
            }
        except Exception:
            self.db.rollback()
            raise

    def aplicar_bonificacion_indexacion_obligacion(
        self,
        *,
        id_obligacion_financiera: int,
        importe_bonificacion: Decimal,
        motivo: str,
        fecha_bonificacion: date,
        uid_movimiento: str,
        uuid_generator: Any,
        id_instalacion: Any,
        op_id: Any,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        fecha_movimiento = datetime.combine(fecha_bonificacion, datetime.min.time())
        ob_stmt = text(
            """
            SELECT
                id_obligacion_financiera,
                estado_obligacion,
                fecha_vencimiento,
                deleted_at
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id
            FOR UPDATE
            """
        )
        idempotente_stmt = text(
            """
            SELECT
                m.id_movimiento_financiero,
                m.importe,
                o.id_obligacion_financiera,
                o.saldo_pendiente,
                o.estado_obligacion,
                COALESCE(SUM(a.importe_aplicado), 0) AS monto_aplicado
            FROM movimiento_financiero m
            JOIN aplicacion_financiera a
              ON a.id_movimiento_financiero = m.id_movimiento_financiero
             AND a.deleted_at IS NULL
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = a.id_obligacion_financiera
            WHERE m.op_id_alta = :op_id
              AND m.tipo_movimiento = 'BONIFICACION'
              AND m.deleted_at IS NULL
            GROUP BY
                m.id_movimiento_financiero,
                m.importe,
                o.id_obligacion_financiera,
                o.saldo_pendiente,
                o.estado_obligacion
            """
        )
        comps_stmt = text(
            """
            SELECT
                c.id_composicion_obligacion,
                c.saldo_componente,
                c.orden_composicion,
                cf.codigo_concepto_financiero
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            WHERE c.id_obligacion_financiera = :id
              AND c.estado_composicion_obligacion = 'ACTIVA'
              AND c.deleted_at IS NULL
              AND c.saldo_componente > 0
              AND cf.deleted_at IS NULL
              AND cf.estado_concepto_financiero = 'ACTIVO'
              AND cf.codigo_concepto_financiero <> 'PUNITORIO'
              AND (
                    cf.aplica_punitorio = true
                    OR cf.codigo_concepto_financiero = 'AJUSTE_INDEXACION'
                  )
            ORDER BY c.orden_composicion ASC, c.id_composicion_obligacion ASC
            """
        )
        mov_stmt = text(
            """
            INSERT INTO movimiento_financiero (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                fecha_movimiento, tipo_movimiento, importe, signo,
                estado_movimiento, observaciones
            )
            VALUES (
                :uid_global, 1, :created_at, :updated_at,
                :id_instalacion, :id_instalacion,
                :op_id, :op_id,
                :fecha_movimiento, 'BONIFICACION', :importe, 'CREDITO',
                'APLICADO', :observaciones
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
                origen_automatico_o_manual, observaciones
            )
            VALUES (
                :uid_global, 1, :created_at, :updated_at,
                :id_instalacion, :id_instalacion,
                :op_id, :op_id,
                :id_movimiento_financiero, :id_obligacion_financiera,
                :id_composicion_obligacion, :fecha_aplicacion,
                'BONIFICACION_INDEXACION', :orden_aplicacion, :importe_aplicado,
                'MANUAL', :observaciones
            )
            """
        )
        estado_stmt = text(
            """
            UPDATE obligacion_financiera
            SET estado_obligacion = CASE
                    WHEN saldo_pendiente = 0 THEN 'CANCELADA'
                    WHEN saldo_pendiente < importe_total THEN
                        'PARCIALMENTE_CANCELADA'
                    WHEN fecha_vencimiento IS NOT NULL
                         AND fecha_vencimiento < :fecha_bonificacion THEN 'VENCIDA'
                    ELSE 'EMITIDA'
                END,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')
            RETURNING estado_obligacion, saldo_pendiente
            """
        )

        try:
            if op_id is not None:
                existente = (
                    self.db.execute(idempotente_stmt, {"op_id": op_id})
                    .mappings()
                    .one_or_none()
                )
                if existente is not None:
                    if (
                        existente["id_obligacion_financiera"]
                        != id_obligacion_financiera
                    ):
                        raise ValueError("BONIFICACION_OP_ID_CONFLICT")
                    monto_aplicado = Decimal(str(existente["monto_aplicado"]))
                    remanente = Decimal(str(existente["importe"])) - monto_aplicado
                    return {
                        "id_obligacion_financiera": id_obligacion_financiera,
                        "id_movimiento_financiero": existente[
                            "id_movimiento_financiero"
                        ],
                        "importe_bonificacion": float(existente["importe"]),
                        "monto_aplicado": float(monto_aplicado),
                        "remanente_no_aplicado": float(remanente),
                        "saldo_pendiente_actualizado": float(
                            existente["saldo_pendiente"]
                        ),
                        "estado_obligacion": existente["estado_obligacion"],
                    }

            obligacion = self.db.execute(
                ob_stmt, {"id": id_obligacion_financiera}
            ).mappings().one_or_none()
            if obligacion is None or obligacion["deleted_at"] is not None:
                raise ValueError("NOT_FOUND_OBLIGACION")
            if obligacion["estado_obligacion"] in {"ANULADA", "REEMPLAZADA"}:
                raise ValueError("ESTADO_NO_ACEPTA_BONIFICACION")

            comps = (
                self.db.execute(comps_stmt, {"id": id_obligacion_financiera})
                .mappings()
                .all()
            )
            if not comps:
                raise ValueError("SIN_SALDO_APLICABLE")

            restante = importe_bonificacion
            lineas: list[dict[str, Any]] = []
            for comp in comps:
                if restante <= 0:
                    break
                saldo = Decimal(str(comp["saldo_componente"]))
                aplicado = min(saldo, restante).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if aplicado <= 0:
                    continue
                lineas.append(
                    {
                        "id_composicion_obligacion": comp[
                            "id_composicion_obligacion"
                        ],
                        "importe_aplicado": aplicado,
                    }
                )
                restante = (restante - aplicado).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

            monto_aplicado = (importe_bonificacion - restante).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if monto_aplicado <= 0:
                raise ValueError("SIN_SALDO_APLICABLE")

            mov_row = self.db.execute(
                mov_stmt,
                {
                    "uid_global": uid_movimiento,
                    "created_at": now,
                    "updated_at": now,
                    "id_instalacion": id_instalacion,
                    "op_id": op_id,
                    "fecha_movimiento": fecha_movimiento,
                    "importe": importe_bonificacion,
                    "observaciones": motivo,
                },
            ).mappings().one()

            for i, linea in enumerate(lineas, start=1):
                self.db.execute(
                    aplic_stmt,
                    {
                        "uid_global": str(uuid_generator()),
                        "created_at": now,
                        "updated_at": now,
                        "id_instalacion": id_instalacion,
                        "op_id": op_id,
                        "id_movimiento_financiero": mov_row[
                            "id_movimiento_financiero"
                        ],
                        "id_obligacion_financiera": id_obligacion_financiera,
                        "id_composicion_obligacion": linea[
                            "id_composicion_obligacion"
                        ],
                        "fecha_aplicacion": fecha_movimiento,
                        "orden_aplicacion": i,
                        "importe_aplicado": linea["importe_aplicado"],
                        "observaciones": motivo,
                    },
                )

            estado = self.db.execute(
                estado_stmt,
                {
                    "id_obligacion_financiera": id_obligacion_financiera,
                    "fecha_bonificacion": fecha_bonificacion,
                    "updated_at": now,
                    "id_instalacion": id_instalacion,
                    "op_id": op_id,
                },
            ).mappings().one()

            self.db.commit()
            return {
                "id_obligacion_financiera": id_obligacion_financiera,
                "id_movimiento_financiero": mov_row["id_movimiento_financiero"],
                "importe_bonificacion": float(importe_bonificacion),
                "monto_aplicado": float(monto_aplicado),
                "remanente_no_aplicado": float(restante),
                "saldo_pendiente_actualizado": float(estado["saldo_pendiente"]),
                "estado_obligacion": estado["estado_obligacion"],
            }
        except Exception:
            self.db.rollback()
            raise

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

    def create_obligacion_servicio_trasladado(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)

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
            RETURNING
                id_obligacion_financiera,
                uid_global,
                version_registro,
                id_relacion_generadora,
                fecha_emision,
                fecha_vencimiento,
                periodo_desde,
                periodo_hasta,
                importe_total,
                saldo_pendiente,
                moneda,
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
                1, :importe_componente, :importe_componente
            )
            RETURNING id_composicion_obligacion
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
                :rol_obligado, :porcentaje_responsabilidad
            )
            RETURNING id_obligacion_obligado
            """
        )

        ob_row = self.db.execute(
            ob_stmt,
            {
                "uid_global": values["uid_global_obligacion"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_relacion_generadora": values["id_relacion_generadora"],
                "fecha_emision": values["fecha_emision"],
                "fecha_vencimiento": values["fecha_vencimiento"],
                "periodo_desde": values["periodo_desde"],
                "periodo_hasta": values["periodo_hasta"],
                "importe_total": values["importe_total"],
                "moneda": values["moneda"],
                "estado_obligacion": values["estado_obligacion"],
            },
        ).mappings().one_or_none()

        if ob_row is None:
            existing = self.get_obligacion_activa_by_relacion_generadora(
                values["id_relacion_generadora"]
            )
            if existing is None:
                raise RuntimeError("OBLIGACION_SERVICIO_TRASLADADO_CONFLICT")
            return existing

        self.db.execute(
            comp_stmt,
            {
                "uid_global": values["uid_global_composicion"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_obligacion_financiera": ob_row["id_obligacion_financiera"],
                "id_concepto_financiero": values["id_concepto_financiero"],
                "importe_componente": values["importe_total"],
            },
        ).mappings().one()

        for obligado in values["obligados"]:
            ov = self._values(obligado)
            self.db.execute(
                obligado_stmt,
                {
                    "uid_global": ov["uid_global"],
                    "version_registro": ov["version_registro"],
                    "created_at": ov["created_at"],
                    "updated_at": ov["updated_at"],
                    "id_instalacion_origen": ov["id_instalacion_origen"],
                    "id_instalacion_ultima_modificacion": ov[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_alta": ov["op_id_alta"],
                    "op_id_ultima_modificacion": ov["op_id_ultima_modificacion"],
                    "id_obligacion_financiera": ob_row["id_obligacion_financiera"],
                    "id_persona": ov["id_persona"],
                    "rol_obligado": ov["rol_obligado"],
                    "porcentaje_responsabilidad": ov["porcentaje_responsabilidad"],
                },
            ).mappings().one()

        result = dict(ob_row)
        result["uid_global"] = str(result["uid_global"])
        result["codigo_concepto_financiero"] = values["codigo_concepto_financiero"]
        return result

    # ── registro de pago (multi-obligación) ─────────────────────────────────

    def get_pago_persona_by_op_id(
        self, *, op_id: Any
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                m.id_movimiento_financiero,
                m.fecha_movimiento,
                m.importe AS monto_consumido,
                m.estado_movimiento,
                m.observaciones,
                m.uid_pago_grupo,
                m.codigo_pago_grupo,
                oo.id_persona,
                a.id_obligacion_financiera,
                COALESCE(SUM(
                    CASE
                        WHEN a.deleted_at IS NULL THEN a.importe_aplicado
                        ELSE 0
                    END
                ), 0) AS monto_aplicado,
                CASE
                    WHEN m.estado_movimiento = 'ANULADO'
                      OR BOOL_AND(a.deleted_at IS NOT NULL) THEN 'ANULADO'
                    ELSE o.estado_obligacion
                END AS estado_resultante
            FROM movimiento_financiero m
            JOIN aplicacion_financiera a
              ON a.id_movimiento_financiero = m.id_movimiento_financiero
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = a.id_obligacion_financiera
             AND o.deleted_at IS NULL
            JOIN obligacion_obligado oo
              ON oo.id_obligacion_financiera = o.id_obligacion_financiera
             AND oo.deleted_at IS NULL
            WHERE m.op_id_alta = :op_id
              AND m.tipo_movimiento = 'PAGO'
              AND m.deleted_at IS NULL
            GROUP BY
                m.id_movimiento_financiero,
                m.fecha_movimiento,
                m.importe,
                m.estado_movimiento,
                m.observaciones,
                m.uid_pago_grupo,
                m.codigo_pago_grupo,
                oo.id_persona,
                a.id_obligacion_financiera,
                o.estado_obligacion
            ORDER BY m.id_movimiento_financiero ASC
            """
        )
        rows = (
            self.db.execute(stmt, {"op_id": op_id})
            .mappings()
            .all()
        )
        if not rows:
            return None

        obligaciones_pagadas = [
            {
                "id_obligacion_financiera": row["id_obligacion_financiera"],
                "id_movimiento_financiero": row["id_movimiento_financiero"],
                "uid_pago_grupo": row["uid_pago_grupo"],
                "codigo_pago_grupo": row["codigo_pago_grupo"],
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
            "id_persona": (
                int(resumen["id_persona"])
                if resumen is not None and "id_persona" in resumen
                else rows[0]["id_persona"]
            ),
            "fecha_pago": (
                date.fromisoformat(resumen["fecha_pago"])
                if resumen is not None
                else rows[0]["fecha_movimiento"].date()
            ),
            "monto_ingresado": float(
                resumen["monto_ingresado"]
                if resumen is not None and "monto_ingresado" in resumen
                else sum(row["monto_consumido"] for row in rows)
            ),
            "uid_pago_grupo": (
                resumen["uid_pago_grupo"]
                if resumen is not None and "uid_pago_grupo" in resumen
                else rows[0]["uid_pago_grupo"]
            ),
            "codigo_pago_grupo": (
                resumen["codigo_pago_grupo"]
                if resumen is not None and "codigo_pago_grupo" in resumen
                else rows[0]["codigo_pago_grupo"]
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
            "payload_idempotencia": resumen,
            "estado_pago_grupo": (
                "ANULADO"
                if all(row["estado_movimiento"] == "ANULADO" for row in rows)
                else "APLICADO"
            ),
        }

    def get_pago_externo_factura_servicio_by_op_id(
        self, *, op_id: Any
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                m.id_movimiento_financiero,
                m.fecha_movimiento,
                m.importe AS monto_aplicado,
                m.observaciones,
                a.id_obligacion_financiera,
                o.id_relacion_generadora,
                o.estado_obligacion AS estado_obligacion_resultante
            FROM movimiento_financiero m
            JOIN aplicacion_financiera a
              ON a.id_movimiento_financiero = m.id_movimiento_financiero
             AND a.deleted_at IS NULL
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = a.id_obligacion_financiera
             AND o.deleted_at IS NULL
            WHERE m.op_id_alta = :op_id
              AND m.tipo_movimiento = 'PAGO_EXTERNO_INFORMADO'
              AND m.deleted_at IS NULL
            ORDER BY m.id_movimiento_financiero ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, {"op_id": op_id}).mappings().one_or_none()
        if row is None:
            return None

        payload = None
        if row["observaciones"]:
            try:
                parsed = json.loads(row["observaciones"])
                if parsed.get("tipo") == "pago_externo_factura_servicio":
                    payload = parsed
            except (TypeError, ValueError):
                payload = None

        id_factura_servicio = (
            int(payload["id_factura_servicio"])
            if payload is not None and "id_factura_servicio" in payload
            else None
        )
        monto_ingresado = (
            payload["importe_pagado"]
            if payload is not None and "importe_pagado" in payload
            else row["monto_aplicado"]
        )
        remanente = (
            payload["remanente_no_aplicado"]
            if payload is not None and "remanente_no_aplicado" in payload
            else 0
        )
        return {
            "id_factura_servicio": id_factura_servicio,
            "id_relacion_generadora": row["id_relacion_generadora"],
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "id_movimiento_financiero": row["id_movimiento_financiero"],
            "monto_ingresado": float(monto_ingresado),
            "monto_aplicado": float(row["monto_aplicado"]),
            "remanente_no_aplicado": float(remanente),
            "estado_obligacion_resultante": row["estado_obligacion_resultante"],
            "impacta_caja": False,
            "genera_recibo_interno": False,
            "payload_idempotencia": payload,
        }

    def get_cuenta_financiera_by_id(
        self, id_cuenta_financiera: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_cuenta_financiera,
                tipo_cuenta,
                nombre_cuenta,
                moneda,
                estado
            FROM cuenta_financiera
            WHERE id_cuenta_financiera = :id
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(stmt, {"id": id_cuenta_financiera}).mappings().one_or_none()
        return dict(row) if row else None

    def get_total_egresos_proveedor_factura_servicio(
        self, id_factura_servicio: int
    ) -> Decimal:
        stmt = text(
            """
            SELECT COALESCE(SUM(importe_pagado), 0) AS total
            FROM egreso_proveedor_factura_servicio
            WHERE id_factura_servicio = :id_factura_servicio
              AND estado_egreso = 'REGISTRADO'
              AND deleted_at IS NULL
            """
        )
        total = self.db.execute(
            stmt, {"id_factura_servicio": id_factura_servicio}
        ).scalar_one()
        return Decimal(str(total or 0))

    def get_total_egresos_impuesto_empresa(
        self, id_comprobante_impuesto: int
    ) -> Decimal:
        stmt = text(
            """
            SELECT COALESCE(SUM(importe_pagado), 0) AS total
            FROM egreso_impuesto_empresa
            WHERE id_comprobante_impuesto = :id_comprobante_impuesto
              AND estado_egreso = 'REGISTRADO'
              AND deleted_at IS NULL
            """
        )
        total = self.db.execute(
            stmt, {"id_comprobante_impuesto": id_comprobante_impuesto}
        ).scalar_one()
        return Decimal(str(total or 0))

    def get_egreso_impuesto_empresa_by_op_id(
        self, *, op_id: Any
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                e.id_egreso_impuesto_empresa,
                e.id_comprobante_impuesto,
                e.id_movimiento_tesoreria,
                e.fecha_pago,
                e.importe_pagado,
                e.medio_pago,
                e.referencia_comprobante,
                e.estado_egreso,
                e.observaciones,
                mt.id_cuenta_financiera_origen
            FROM egreso_impuesto_empresa e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
             AND mt.deleted_at IS NULL
            WHERE e.op_id_alta = :op_id
              AND e.deleted_at IS NULL
            ORDER BY e.id_egreso_impuesto_empresa ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, {"op_id": op_id}).mappings().one_or_none()
        if row is None:
            return None

        payload = None
        if row["observaciones"]:
            try:
                parsed = json.loads(row["observaciones"])
                if parsed.get("tipo") == "egreso_impuesto_empresa":
                    payload = parsed
            except (TypeError, ValueError):
                payload = None

        return {
            "id_egreso_impuesto_empresa": row["id_egreso_impuesto_empresa"],
            "id_comprobante_impuesto": row["id_comprobante_impuesto"],
            "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
            "id_cuenta_financiera_origen": row["id_cuenta_financiera_origen"],
            "fecha_pago": row["fecha_pago"],
            "importe_pagado": float(row["importe_pagado"]),
            "medio_pago": row["medio_pago"],
            "referencia_comprobante": row["referencia_comprobante"],
            "estado_egreso": row["estado_egreso"],
            "impacta_tesoreria": True,
            "crea_movimiento_financiero": False,
            "crea_relacion_generadora": False,
            "crea_obligacion_financiera": False,
            "payload_idempotencia": payload,
        }

    def list_egresos_impuesto_empresa(
        self, id_comprobante_impuesto: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                e.id_egreso_impuesto_empresa,
                e.id_movimiento_tesoreria,
                e.fecha_pago,
                e.importe_pagado,
                e.medio_pago,
                e.referencia_comprobante,
                e.estado_egreso,
                e.observaciones
            FROM egreso_impuesto_empresa e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
             AND mt.deleted_at IS NULL
            WHERE e.id_comprobante_impuesto = :id_comprobante_impuesto
              AND e.deleted_at IS NULL
            ORDER BY e.fecha_pago ASC, e.id_egreso_impuesto_empresa ASC
            """
        )
        rows = self.db.execute(
            stmt, {"id_comprobante_impuesto": id_comprobante_impuesto}
        ).mappings().all()
        egresos: list[dict[str, Any]] = []
        for row in rows:
            observaciones = row["observaciones"]
            if observaciones:
                try:
                    parsed = json.loads(observaciones)
                    if isinstance(parsed, dict) and parsed.get("observaciones") is not None:
                        observaciones = parsed.get("observaciones")
                except (TypeError, ValueError):
                    pass
            egresos.append(
                {
                    "id_egreso_impuesto_empresa": row["id_egreso_impuesto_empresa"],
                    "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
                    "fecha_pago": row["fecha_pago"],
                    "importe_pagado": float(row["importe_pagado"]),
                    "medio_pago": row["medio_pago"],
                    "referencia_comprobante": row["referencia_comprobante"],
                    "estado_egreso": row["estado_egreso"],
                    "observaciones": observaciones,
                }
            )
        return egresos

    def list_egresos_impuesto_disponibles_para_liquidacion(
        self, id_comprobante_impuesto: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                e.id_egreso_impuesto_empresa,
                e.id_movimiento_tesoreria,
                e.fecha_pago,
                e.importe_pagado,
                e.medio_pago,
                e.referencia_comprobante,
                e.estado_egreso
            FROM egreso_impuesto_empresa e
            WHERE e.id_comprobante_impuesto = :id_comprobante_impuesto
              AND e.estado_egreso = 'REGISTRADO'
              AND e.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM liquidacion_impuesto_trasladado_egreso lite
                  JOIN liquidacion_impuesto_trasladado lit
                    ON lit.id_liquidacion_impuesto_trasladado =
                       lite.id_liquidacion_impuesto_trasladado
                   AND lit.deleted_at IS NULL
                   AND lit.estado_liquidacion = 'EMITIDA'
                  WHERE lite.id_egreso_impuesto_empresa = e.id_egreso_impuesto_empresa
                    AND lite.deleted_at IS NULL
                    AND lite.estado_liquidacion_impuesto_egreso = 'ACTIVO'
              )
            ORDER BY e.fecha_pago ASC, e.id_egreso_impuesto_empresa ASC
            """
        )
        rows = self.db.execute(
            stmt, {"id_comprobante_impuesto": id_comprobante_impuesto}
        ).mappings().all()
        return [
            {
                "id_egreso_impuesto_empresa": row["id_egreso_impuesto_empresa"],
                "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
                "fecha_pago": row["fecha_pago"],
                "importe_pagado": Decimal(str(row["importe_pagado"])),
                "medio_pago": row["medio_pago"],
                "referencia_comprobante": row["referencia_comprobante"],
                "estado_egreso": row["estado_egreso"],
            }
            for row in rows
        ]

    def get_egreso_proveedor_factura_servicio_by_op_id(
        self, *, op_id: Any
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                e.id_egreso_proveedor_factura_servicio,
                e.id_factura_servicio,
                e.id_movimiento_tesoreria,
                e.fecha_pago,
                e.importe_pagado,
                e.medio_pago,
                e.referencia_comprobante,
                e.estado_egreso,
                e.observaciones,
                mt.id_cuenta_financiera_origen
            FROM egreso_proveedor_factura_servicio e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
             AND mt.deleted_at IS NULL
            WHERE e.op_id_alta = :op_id
              AND e.deleted_at IS NULL
            ORDER BY e.id_egreso_proveedor_factura_servicio ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, {"op_id": op_id}).mappings().one_or_none()
        if row is None:
            return None

        payload = None
        if row["observaciones"]:
            try:
                parsed = json.loads(row["observaciones"])
                if parsed.get("tipo") == "egreso_proveedor_factura_servicio":
                    payload = parsed
            except (TypeError, ValueError):
                payload = None

        return {
            "id_egreso_proveedor_factura_servicio": row[
                "id_egreso_proveedor_factura_servicio"
            ],
            "id_factura_servicio": row["id_factura_servicio"],
            "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
            "id_cuenta_financiera_origen": row["id_cuenta_financiera_origen"],
            "fecha_pago": row["fecha_pago"],
            "importe_pagado": float(row["importe_pagado"]),
            "medio_pago": row["medio_pago"],
            "referencia_comprobante": row["referencia_comprobante"],
            "estado_egreso": row["estado_egreso"],
            "impacta_tesoreria": True,
            "crea_movimiento_financiero": False,
            "crea_obligacion_financiera": False,
            "payload_idempotencia": payload,
        }

    def list_egresos_proveedor_factura_servicio(
        self, id_factura_servicio: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                e.id_egreso_proveedor_factura_servicio,
                e.id_movimiento_tesoreria,
                e.fecha_pago,
                e.importe_pagado,
                e.medio_pago,
                e.referencia_comprobante,
                e.estado_egreso,
                e.observaciones
            FROM egreso_proveedor_factura_servicio e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
             AND mt.deleted_at IS NULL
            WHERE e.id_factura_servicio = :id_factura_servicio
              AND e.deleted_at IS NULL
            ORDER BY e.fecha_pago ASC, e.id_egreso_proveedor_factura_servicio ASC
            """
        )
        rows = self.db.execute(
            stmt, {"id_factura_servicio": id_factura_servicio}
        ).mappings().all()
        egresos: list[dict[str, Any]] = []
        for row in rows:
            observaciones = row["observaciones"]
            if observaciones:
                try:
                    parsed = json.loads(observaciones)
                    if isinstance(parsed, dict) and parsed.get("observaciones") is not None:
                        observaciones = parsed.get("observaciones")
                except (TypeError, ValueError):
                    pass
            egresos.append(
                {
                    "id_egreso_proveedor_factura_servicio": row[
                        "id_egreso_proveedor_factura_servicio"
                    ],
                    "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
                    "fecha_pago": row["fecha_pago"],
                    "importe_pagado": float(row["importe_pagado"]),
                    "medio_pago": row["medio_pago"],
                    "referencia_comprobante": row["referencia_comprobante"],
                    "estado_egreso": row["estado_egreso"],
                    "observaciones": observaciones,
                }
            )
        return egresos

    def list_egresos_proveedor_disponibles_para_recupero(
        self, id_factura_servicio: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                e.id_egreso_proveedor_factura_servicio,
                e.id_movimiento_tesoreria,
                e.fecha_pago,
                e.importe_pagado,
                e.medio_pago,
                e.referencia_comprobante,
                e.estado_egreso
            FROM egreso_proveedor_factura_servicio e
            WHERE e.id_factura_servicio = :id_factura_servicio
              AND e.estado_egreso = 'REGISTRADO'
              AND e.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM liquidacion_recupero_egreso lre
                  JOIN liquidacion_recupero lr
                    ON lr.id_liquidacion_recupero = lre.id_liquidacion_recupero
                   AND lr.deleted_at IS NULL
                   AND lr.estado_liquidacion = 'EMITIDA'
                  WHERE lre.id_egreso_proveedor_factura_servicio =
                        e.id_egreso_proveedor_factura_servicio
                    AND lre.deleted_at IS NULL
                    AND lre.estado_liquidacion_recupero_egreso = 'ACTIVO'
              )
            ORDER BY e.fecha_pago ASC, e.id_egreso_proveedor_factura_servicio ASC
            """
        )
        rows = self.db.execute(
            stmt, {"id_factura_servicio": id_factura_servicio}
        ).mappings().all()
        return [
            {
                "id_egreso_proveedor_factura_servicio": row[
                    "id_egreso_proveedor_factura_servicio"
                ],
                "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
                "fecha_pago": row["fecha_pago"],
                "importe_pagado": Decimal(str(row["importe_pagado"])),
                "medio_pago": row["medio_pago"],
                "referencia_comprobante": row["referencia_comprobante"],
                "estado_egreso": row["estado_egreso"],
            }
            for row in rows
        ]

    def get_liquidacion_recupero_by_op_id(
        self, *, op_id: Any
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT id_liquidacion_recupero
            FROM liquidacion_recupero
            WHERE op_id_alta = :op_id
              AND deleted_at IS NULL
            ORDER BY id_liquidacion_recupero ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, {"op_id": op_id}).mappings().one_or_none()
        if row is None:
            return None
        return self.get_liquidacion_recupero_by_id(row["id_liquidacion_recupero"])

    def get_liquidacion_recupero_by_id(
        self, id_liquidacion_recupero: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                lr.id_liquidacion_recupero,
                lr.codigo_liquidacion_recupero,
                lr.fecha_liquidacion,
                lr.fecha_vencimiento,
                lr.estado_liquidacion,
                lr.importe_total_egresado_base,
                lr.importe_total_recuperar,
                lr.importe_absorbido_empresa,
                lr.id_relacion_generadora,
                lr.id_obligacion_financiera,
                lr.observaciones,
                lrf.id_factura_servicio
            FROM liquidacion_recupero lr
            JOIN liquidacion_recupero_factura lrf
              ON lrf.id_liquidacion_recupero = lr.id_liquidacion_recupero
            WHERE lr.id_liquidacion_recupero = :id
              AND lr.deleted_at IS NULL
            """
        )
        row = self.db.execute(stmt, {"id": id_liquidacion_recupero}).mappings().one_or_none()
        if row is None:
            return None

        responsables_stmt = text(
            """
            SELECT
                id_liquidacion_recupero_responsable,
                id_persona,
                porcentaje_responsabilidad,
                importe_responsable,
                origen_responsable,
                id_asignacion_servicio_responsable
            FROM liquidacion_recupero_responsable
            WHERE id_liquidacion_recupero = :id
            ORDER BY id_liquidacion_recupero_responsable ASC
            """
        )
        egresos_stmt = text(
            """
            SELECT
                lre.id_liquidacion_recupero_egreso,
                lre.id_egreso_proveedor_factura_servicio,
                lre.importe_imputado_base
            FROM liquidacion_recupero_egreso lre
            WHERE lre.id_liquidacion_recupero = :id
              AND lre.deleted_at IS NULL
              AND lre.estado_liquidacion_recupero_egreso = 'ACTIVO'
            ORDER BY lre.id_liquidacion_recupero_egreso ASC
            """
        )
        responsables = [
            {
                "id_liquidacion_recupero_responsable": r[
                    "id_liquidacion_recupero_responsable"
                ],
                "id_persona": r["id_persona"],
                "porcentaje_responsabilidad": float(r["porcentaje_responsabilidad"]),
                "importe_responsable": float(r["importe_responsable"]),
                "origen_responsable": r["origen_responsable"],
                "id_asignacion_servicio_responsable": r[
                    "id_asignacion_servicio_responsable"
                ],
            }
            for r in self.db.execute(
                responsables_stmt, {"id": id_liquidacion_recupero}
            ).mappings().all()
        ]
        egresos = [
            {
                "id_liquidacion_recupero_egreso": e[
                    "id_liquidacion_recupero_egreso"
                ],
                "id_egreso_proveedor_factura_servicio": e[
                    "id_egreso_proveedor_factura_servicio"
                ],
                "importe_imputado_base": float(e["importe_imputado_base"]),
            }
            for e in self.db.execute(
                egresos_stmt, {"id": id_liquidacion_recupero}
            ).mappings().all()
        ]
        payload = None
        if row["observaciones"]:
            try:
                parsed = json.loads(row["observaciones"])
                if parsed.get("tipo") == "liquidacion_recupero":
                    payload = parsed
            except (TypeError, ValueError):
                payload = None
        return {
            "id_liquidacion_recupero": row["id_liquidacion_recupero"],
            "codigo_liquidacion_recupero": row["codigo_liquidacion_recupero"],
            "id_factura_servicio": row["id_factura_servicio"],
            "id_relacion_generadora": row["id_relacion_generadora"],
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "fecha_liquidacion": row["fecha_liquidacion"],
            "fecha_vencimiento": row["fecha_vencimiento"],
            "estado_liquidacion": row["estado_liquidacion"],
            "importe_total_egresado_base": float(row["importe_total_egresado_base"]),
            "importe_total_recuperar": float(row["importe_total_recuperar"]),
            "importe_absorbido_empresa": float(row["importe_absorbido_empresa"]),
            "responsables": responsables,
            "egresos": egresos,
            "payload_idempotencia": payload,
        }

    def get_liquidacion_recupero_detalle(
        self, id_liquidacion_recupero: int
    ) -> dict[str, Any] | None:
        base_stmt = text(
            """
            SELECT
                lr.id_liquidacion_recupero,
                lr.codigo_liquidacion_recupero,
                lr.fecha_liquidacion,
                lr.fecha_vencimiento,
                lr.estado_liquidacion,
                lr.importe_total_egresado_base,
                lr.importe_total_recuperar,
                lr.importe_absorbido_empresa,
                lr.id_relacion_generadora,
                lr.id_obligacion_financiera
            FROM liquidacion_recupero lr
            WHERE lr.id_liquidacion_recupero = :id
              AND lr.deleted_at IS NULL
            """
        )
        row = self.db.execute(
            base_stmt, {"id": id_liquidacion_recupero}
        ).mappings().one_or_none()
        if row is None:
            return None

        facturas_stmt = text(
            """
            SELECT
                lrf.id_factura_servicio,
                fs.proveedor,
                fs.numero_factura,
                fs.importe_total,
                lrf.importe_egresado_base,
                lrf.importe_recuperar
            FROM liquidacion_recupero_factura lrf
            JOIN factura_servicio fs
              ON fs.id_factura_servicio = lrf.id_factura_servicio
             AND fs.deleted_at IS NULL
            WHERE lrf.id_liquidacion_recupero = :id
            ORDER BY lrf.id_liquidacion_recupero_factura ASC
            """
        )
        egresos_stmt = text(
            """
            SELECT
                lre.id_egreso_proveedor_factura_servicio,
                e.id_movimiento_tesoreria,
                e.fecha_pago,
                e.importe_pagado,
                lre.importe_imputado_base,
                e.estado_egreso
            FROM liquidacion_recupero_egreso lre
            JOIN egreso_proveedor_factura_servicio e
              ON e.id_egreso_proveedor_factura_servicio =
                 lre.id_egreso_proveedor_factura_servicio
             AND e.deleted_at IS NULL
            WHERE lre.id_liquidacion_recupero = :id
              AND lre.deleted_at IS NULL
              AND lre.estado_liquidacion_recupero_egreso = 'ACTIVO'
            ORDER BY lre.id_liquidacion_recupero_egreso ASC
            """
        )
        responsables_stmt = text(
            """
            SELECT
                id_liquidacion_recupero_responsable,
                id_persona,
                porcentaje_responsabilidad,
                importe_responsable,
                origen_responsable,
                id_asignacion_servicio_responsable
            FROM liquidacion_recupero_responsable
            WHERE id_liquidacion_recupero = :id
            ORDER BY id_liquidacion_recupero_responsable ASC
            """
        )
        composiciones_stmt = text(
            """
            SELECT
                cf.codigo_concepto_financiero,
                c.importe_componente,
                c.saldo_componente
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
             AND cf.deleted_at IS NULL
            WHERE c.id_obligacion_financiera = :id_obligacion
              AND c.deleted_at IS NULL
            ORDER BY c.orden_composicion ASC, c.id_composicion_obligacion ASC
            """
        )
        obligados_stmt = text(
            """
            SELECT
                id_persona,
                rol_obligado,
                porcentaje_responsabilidad
            FROM obligacion_obligado
            WHERE id_obligacion_financiera = :id_obligacion
              AND deleted_at IS NULL
            ORDER BY id_obligacion_obligado ASC
            """
        )
        obligacion_stmt = text(
            """
            SELECT
                id_obligacion_financiera,
                estado_obligacion,
                saldo_pendiente
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id_obligacion
              AND deleted_at IS NULL
            """
        )

        params = {"id": id_liquidacion_recupero}
        facturas = [
            {
                "id_factura_servicio": f["id_factura_servicio"],
                "proveedor": f["proveedor"],
                "numero_factura": f["numero_factura"],
                "importe_total": float(f["importe_total"]),
                "importe_egresado_base": float(f["importe_egresado_base"]),
                "importe_recuperar": float(f["importe_recuperar"]),
            }
            for f in self.db.execute(facturas_stmt, params).mappings().all()
        ]
        egresos = [
            {
                "id_egreso_proveedor_factura_servicio": e[
                    "id_egreso_proveedor_factura_servicio"
                ],
                "id_movimiento_tesoreria": e["id_movimiento_tesoreria"],
                "fecha_pago": e["fecha_pago"],
                "importe_pagado": float(e["importe_pagado"]),
                "importe_imputado_base": float(e["importe_imputado_base"]),
                "estado_egreso": e["estado_egreso"],
            }
            for e in self.db.execute(egresos_stmt, params).mappings().all()
        ]
        responsables = [
            {
                "id_liquidacion_recupero_responsable": r[
                    "id_liquidacion_recupero_responsable"
                ],
                "id_persona": r["id_persona"],
                "porcentaje_responsabilidad": float(r["porcentaje_responsabilidad"]),
                "importe_responsable": float(r["importe_responsable"]),
                "origen_responsable": r["origen_responsable"],
                "id_asignacion_servicio_responsable": r[
                    "id_asignacion_servicio_responsable"
                ],
            }
            for r in self.db.execute(responsables_stmt, params).mappings().all()
        ]

        obligacion = None
        id_obligacion = row["id_obligacion_financiera"]
        if id_obligacion is not None:
            ob_params = {"id_obligacion": id_obligacion}
            ob_row = self.db.execute(
                obligacion_stmt, ob_params
            ).mappings().one_or_none()
            if ob_row is not None:
                obligacion = {
                    "id_obligacion_financiera": ob_row[
                        "id_obligacion_financiera"
                    ],
                    "estado_obligacion": ob_row["estado_obligacion"],
                    "saldo_pendiente": float(ob_row["saldo_pendiente"]),
                    "composiciones": [
                        {
                            "codigo_concepto_financiero": c[
                                "codigo_concepto_financiero"
                            ],
                            "importe_componente": float(c["importe_componente"]),
                            "saldo_componente": float(c["saldo_componente"]),
                        }
                        for c in self.db.execute(
                            composiciones_stmt, ob_params
                        ).mappings().all()
                    ],
                    "obligados": [
                        {
                            "id_persona": o["id_persona"],
                            "rol_obligado": o["rol_obligado"],
                            "porcentaje_responsabilidad": (
                                float(o["porcentaje_responsabilidad"])
                                if o["porcentaje_responsabilidad"] is not None
                                else None
                            ),
                        }
                        for o in self.db.execute(
                            obligados_stmt, ob_params
                        ).mappings().all()
                    ],
                }

        return {
            "id_liquidacion_recupero": row["id_liquidacion_recupero"],
            "codigo_liquidacion_recupero": row["codigo_liquidacion_recupero"],
            "estado_liquidacion": row["estado_liquidacion"],
            "fecha_liquidacion": row["fecha_liquidacion"],
            "fecha_vencimiento": row["fecha_vencimiento"],
            "importe_total_egresado_base": float(row["importe_total_egresado_base"]),
            "importe_total_recuperar": float(row["importe_total_recuperar"]),
            "importe_absorbido_empresa": float(row["importe_absorbido_empresa"]),
            "id_relacion_generadora": row["id_relacion_generadora"],
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "facturas": facturas,
            "egresos": egresos,
            "responsables": responsables,
            "obligacion": obligacion,
        }

    def list_liquidaciones_recupero_by_factura_servicio(
        self, id_factura_servicio: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                lr.id_liquidacion_recupero,
                lr.codigo_liquidacion_recupero,
                lr.estado_liquidacion,
                lr.fecha_liquidacion,
                lr.fecha_vencimiento,
                lr.importe_total_recuperar,
                lr.importe_absorbido_empresa,
                lr.id_obligacion_financiera,
                o.saldo_pendiente,
                COUNT(lrr.id_liquidacion_recupero_responsable) AS cantidad_responsables
            FROM liquidacion_recupero lr
            JOIN liquidacion_recupero_factura lrf
              ON lrf.id_liquidacion_recupero = lr.id_liquidacion_recupero
            LEFT JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = lr.id_obligacion_financiera
             AND o.deleted_at IS NULL
            LEFT JOIN liquidacion_recupero_responsable lrr
              ON lrr.id_liquidacion_recupero = lr.id_liquidacion_recupero
            WHERE lrf.id_factura_servicio = :id_factura_servicio
              AND lr.deleted_at IS NULL
            GROUP BY
                lr.id_liquidacion_recupero,
                lr.codigo_liquidacion_recupero,
                lr.estado_liquidacion,
                lr.fecha_liquidacion,
                lr.fecha_vencimiento,
                lr.importe_total_recuperar,
                lr.importe_absorbido_empresa,
                lr.id_obligacion_financiera,
                o.saldo_pendiente
            ORDER BY lr.fecha_liquidacion ASC, lr.id_liquidacion_recupero ASC
            """
        )
        rows = self.db.execute(
            stmt, {"id_factura_servicio": id_factura_servicio}
        ).mappings().all()
        return [
            {
                "id_liquidacion_recupero": row["id_liquidacion_recupero"],
                "codigo_liquidacion_recupero": row["codigo_liquidacion_recupero"],
                "estado_liquidacion": row["estado_liquidacion"],
                "fecha_liquidacion": row["fecha_liquidacion"],
                "fecha_vencimiento": row["fecha_vencimiento"],
                "importe_total_recuperar": float(row["importe_total_recuperar"]),
                "importe_absorbido_empresa": float(row["importe_absorbido_empresa"]),
                "id_obligacion_financiera": row["id_obligacion_financiera"],
                "saldo_pendiente": (
                    float(row["saldo_pendiente"])
                    if row["saldo_pendiente"] is not None
                    else None
                ),
                "cantidad_responsables": int(row["cantidad_responsables"]),
            }
            for row in rows
        ]

    def get_liquidacion_impuesto_trasladado_by_op_id(
        self, *, op_id: Any
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT id_liquidacion_impuesto_trasladado
            FROM liquidacion_impuesto_trasladado
            WHERE op_id_alta = :op_id
              AND deleted_at IS NULL
            ORDER BY id_liquidacion_impuesto_trasladado ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, {"op_id": op_id}).mappings().one_or_none()
        if row is None:
            return None
        return self.get_liquidacion_impuesto_trasladado_by_id(
            row["id_liquidacion_impuesto_trasladado"]
        )

    def get_liquidacion_impuesto_trasladado_by_id(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                lit.id_liquidacion_impuesto_trasladado,
                lit.codigo_liquidacion_impuesto_trasladado,
                lit.estado_liquidacion,
                lit.modalidad_gestion_impuesto,
                lit.fecha_liquidacion,
                lit.fecha_vencimiento,
                lit.importe_total_base,
                lit.importe_total_trasladar,
                lit.importe_absorbido_empresa,
                lit.id_relacion_generadora,
                lit.id_obligacion_financiera,
                lit.observaciones
            FROM liquidacion_impuesto_trasladado lit
            WHERE lit.id_liquidacion_impuesto_trasladado = :id
              AND lit.deleted_at IS NULL
            """
        )
        row = self.db.execute(
            stmt, {"id": id_liquidacion_impuesto_trasladado}
        ).mappings().one_or_none()
        if row is None:
            return None

        payload = None
        if row["observaciones"]:
            try:
                parsed = json.loads(row["observaciones"])
                if parsed.get("tipo") == "liquidacion_impuesto_trasladado":
                    payload = parsed
            except (TypeError, ValueError):
                payload = None

        return {
            "id_liquidacion_impuesto_trasladado": row[
                "id_liquidacion_impuesto_trasladado"
            ],
            "codigo_liquidacion_impuesto_trasladado": row[
                "codigo_liquidacion_impuesto_trasladado"
            ],
            "estado_liquidacion": row["estado_liquidacion"],
            "modalidad_gestion_impuesto": row["modalidad_gestion_impuesto"],
            "fecha_liquidacion": row["fecha_liquidacion"],
            "fecha_vencimiento": row["fecha_vencimiento"],
            "importe_total_base": float(row["importe_total_base"]),
            "importe_total_trasladar": float(row["importe_total_trasladar"]),
            "importe_absorbido_empresa": float(row["importe_absorbido_empresa"]),
            "id_relacion_generadora": row["id_relacion_generadora"],
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "payload_idempotencia": payload,
        }

    def get_liquidacion_impuesto_trasladado_detalle(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> dict[str, Any] | None:
        base_stmt = text(
            """
            SELECT
                lit.id_liquidacion_impuesto_trasladado,
                lit.codigo_liquidacion_impuesto_trasladado,
                lit.estado_liquidacion,
                lit.modalidad_gestion_impuesto,
                lit.fecha_liquidacion,
                lit.fecha_vencimiento,
                lit.importe_total_base,
                lit.importe_total_trasladar,
                lit.importe_absorbido_empresa,
                lit.id_relacion_generadora,
                lit.id_obligacion_financiera
            FROM liquidacion_impuesto_trasladado lit
            WHERE lit.id_liquidacion_impuesto_trasladado = :id
              AND lit.deleted_at IS NULL
            """
        )
        row = self.db.execute(
            base_stmt, {"id": id_liquidacion_impuesto_trasladado}
        ).mappings().one_or_none()
        if row is None:
            return None

        comprobantes_stmt = text(
            """
            SELECT
                id_comprobante_impuesto,
                organismo,
                tipo_impuesto,
                partida_nomenclatura,
                numero_comprobante,
                periodo_desde,
                periodo_hasta,
                fecha_vencimiento,
                importe_comprobante,
                importe_base,
                importe_trasladar
            FROM liquidacion_impuesto_trasladado_comprobante
            WHERE id_liquidacion_impuesto_trasladado = :id
            ORDER BY id_liquidacion_impuesto_trasladado_comprobante ASC
            """
        )
        egresos_stmt = text(
            """
            SELECT
                lite.id_egreso_impuesto_empresa,
                eie.id_movimiento_tesoreria,
                eie.fecha_pago,
                eie.importe_pagado,
                lite.importe_imputado_base,
                eie.estado_egreso
            FROM liquidacion_impuesto_trasladado_egreso lite
            JOIN egreso_impuesto_empresa eie
              ON eie.id_egreso_impuesto_empresa = lite.id_egreso_impuesto_empresa
             AND eie.deleted_at IS NULL
            WHERE lite.id_liquidacion_impuesto_trasladado = :id
              AND lite.deleted_at IS NULL
            ORDER BY lite.id_liquidacion_impuesto_trasladado_egreso ASC
            """
        )
        responsables_stmt = text(
            """
            SELECT
                id_liquidacion_impuesto_trasladado_responsable,
                id_persona,
                porcentaje_responsabilidad,
                importe_responsable,
                origen_responsable
            FROM liquidacion_impuesto_trasladado_responsable
            WHERE id_liquidacion_impuesto_trasladado = :id
            ORDER BY id_liquidacion_impuesto_trasladado_responsable ASC
            """
        )
        obligacion_stmt = text(
            """
            SELECT
                id_obligacion_financiera,
                estado_obligacion,
                saldo_pendiente
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id_obligacion
              AND deleted_at IS NULL
            """
        )
        composiciones_stmt = text(
            """
            SELECT
                cf.codigo_concepto_financiero,
                c.importe_componente,
                c.saldo_componente
            FROM composicion_obligacion c
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
             AND cf.deleted_at IS NULL
            WHERE c.id_obligacion_financiera = :id_obligacion
              AND c.deleted_at IS NULL
            ORDER BY c.orden_composicion ASC, c.id_composicion_obligacion ASC
            """
        )
        obligados_stmt = text(
            """
            SELECT
                id_persona,
                rol_obligado,
                porcentaje_responsabilidad
            FROM obligacion_obligado
            WHERE id_obligacion_financiera = :id_obligacion
              AND deleted_at IS NULL
            ORDER BY id_obligacion_obligado ASC
            """
        )

        params = {"id": id_liquidacion_impuesto_trasladado}
        comprobantes = [
            {
                "id_comprobante_impuesto": c["id_comprobante_impuesto"],
                "organismo": c["organismo"],
                "tipo_impuesto": c["tipo_impuesto"],
                "partida_nomenclatura": c["partida_nomenclatura"],
                "numero_comprobante": c["numero_comprobante"],
                "periodo_desde": c["periodo_desde"],
                "periodo_hasta": c["periodo_hasta"],
                "fecha_vencimiento": c["fecha_vencimiento"],
                "importe_comprobante": float(c["importe_comprobante"]),
                "importe_base": float(c["importe_base"]),
                "importe_trasladar": float(c["importe_trasladar"]),
            }
            for c in self.db.execute(comprobantes_stmt, params).mappings().all()
        ]
        egresos = [
            {
                "id_egreso_impuesto_empresa": e["id_egreso_impuesto_empresa"],
                "id_movimiento_tesoreria": e["id_movimiento_tesoreria"],
                "fecha_pago": e["fecha_pago"],
                "importe_pagado": float(e["importe_pagado"]),
                "importe_imputado_base": float(e["importe_imputado_base"]),
                "estado_egreso": e["estado_egreso"],
            }
            for e in self.db.execute(egresos_stmt, params).mappings().all()
        ]
        responsables = [
            {
                "id_liquidacion_impuesto_trasladado_responsable": r[
                    "id_liquidacion_impuesto_trasladado_responsable"
                ],
                "id_persona": r["id_persona"],
                "porcentaje_responsabilidad": float(r["porcentaje_responsabilidad"]),
                "importe_responsable": float(r["importe_responsable"]),
                "origen_responsable": r["origen_responsable"],
            }
            for r in self.db.execute(responsables_stmt, params).mappings().all()
        ]

        obligacion = None
        id_obligacion = row["id_obligacion_financiera"]
        if id_obligacion is not None:
            ob_params = {"id_obligacion": id_obligacion}
            ob_row = self.db.execute(
                obligacion_stmt, ob_params
            ).mappings().one_or_none()
            if ob_row is not None:
                obligacion = {
                    "id_obligacion_financiera": ob_row[
                        "id_obligacion_financiera"
                    ],
                    "estado_obligacion": ob_row["estado_obligacion"],
                    "saldo_pendiente": float(ob_row["saldo_pendiente"]),
                    "composiciones": [
                        {
                            "codigo_concepto_financiero": c[
                                "codigo_concepto_financiero"
                            ],
                            "importe_componente": float(c["importe_componente"]),
                            "saldo_componente": float(c["saldo_componente"]),
                        }
                        for c in self.db.execute(
                            composiciones_stmt, ob_params
                        ).mappings().all()
                    ],
                    "obligados": [
                        {
                            "id_persona": o["id_persona"],
                            "rol_obligado": o["rol_obligado"],
                            "porcentaje_responsabilidad": (
                                float(o["porcentaje_responsabilidad"])
                                if o["porcentaje_responsabilidad"] is not None
                                else None
                            ),
                        }
                        for o in self.db.execute(
                            obligados_stmt, ob_params
                        ).mappings().all()
                    ],
                }

        return {
            "id_liquidacion_impuesto_trasladado": row[
                "id_liquidacion_impuesto_trasladado"
            ],
            "codigo_liquidacion_impuesto_trasladado": row[
                "codigo_liquidacion_impuesto_trasladado"
            ],
            "estado_liquidacion": row["estado_liquidacion"],
            "modalidad_gestion_impuesto": row["modalidad_gestion_impuesto"],
            "fecha_liquidacion": row["fecha_liquidacion"],
            "fecha_vencimiento": row["fecha_vencimiento"],
            "importe_total_base": float(row["importe_total_base"]),
            "importe_total_trasladar": float(row["importe_total_trasladar"]),
            "importe_absorbido_empresa": float(row["importe_absorbido_empresa"]),
            "id_relacion_generadora": row["id_relacion_generadora"],
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "comprobantes": comprobantes,
            "egresos": egresos,
            "responsables": responsables,
            "obligacion": obligacion,
        }

    def list_liquidaciones_impuesto_trasladado_by_comprobante(
        self, id_comprobante_impuesto: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                lit.id_liquidacion_impuesto_trasladado,
                lit.codigo_liquidacion_impuesto_trasladado,
                lit.estado_liquidacion,
                lit.modalidad_gestion_impuesto,
                lit.fecha_liquidacion,
                lit.fecha_vencimiento,
                lit.importe_total_trasladar,
                lit.importe_absorbido_empresa,
                lit.id_obligacion_financiera,
                o.saldo_pendiente,
                COUNT(litr.id_liquidacion_impuesto_trasladado_responsable)
                    AS cantidad_responsables
            FROM liquidacion_impuesto_trasladado lit
            JOIN liquidacion_impuesto_trasladado_comprobante litc
              ON litc.id_liquidacion_impuesto_trasladado =
                 lit.id_liquidacion_impuesto_trasladado
            LEFT JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = lit.id_obligacion_financiera
             AND o.deleted_at IS NULL
            LEFT JOIN liquidacion_impuesto_trasladado_responsable litr
              ON litr.id_liquidacion_impuesto_trasladado =
                 lit.id_liquidacion_impuesto_trasladado
            WHERE litc.id_comprobante_impuesto = :id_comprobante_impuesto
              AND lit.deleted_at IS NULL
            GROUP BY
                lit.id_liquidacion_impuesto_trasladado,
                lit.codigo_liquidacion_impuesto_trasladado,
                lit.estado_liquidacion,
                lit.modalidad_gestion_impuesto,
                lit.fecha_liquidacion,
                lit.fecha_vencimiento,
                lit.importe_total_trasladar,
                lit.importe_absorbido_empresa,
                lit.id_obligacion_financiera,
                o.saldo_pendiente
            ORDER BY lit.fecha_liquidacion ASC,
                     lit.id_liquidacion_impuesto_trasladado ASC
            """
        )
        rows = self.db.execute(
            stmt, {"id_comprobante_impuesto": id_comprobante_impuesto}
        ).mappings().all()
        return [
            {
                "id_liquidacion_impuesto_trasladado": row[
                    "id_liquidacion_impuesto_trasladado"
                ],
                "codigo_liquidacion_impuesto_trasladado": row[
                    "codigo_liquidacion_impuesto_trasladado"
                ],
                "estado_liquidacion": row["estado_liquidacion"],
                "modalidad_gestion_impuesto": row["modalidad_gestion_impuesto"],
                "fecha_liquidacion": row["fecha_liquidacion"],
                "fecha_vencimiento": row["fecha_vencimiento"],
                "importe_total_trasladar": float(row["importe_total_trasladar"]),
                "importe_absorbido_empresa": float(row["importe_absorbido_empresa"]),
                "id_obligacion_financiera": row["id_obligacion_financiera"],
                "saldo_pendiente": (
                    float(row["saldo_pendiente"])
                    if row["saldo_pendiente"] is not None
                    else None
                ),
                "cantidad_responsables": int(row["cantidad_responsables"]),
            }
            for row in rows
        ]

    def get_liquidacion_impuesto_trasladado_para_anular(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                lit.id_liquidacion_impuesto_trasladado,
                lit.estado_liquidacion,
                lit.id_relacion_generadora,
                rg.estado_relacion_generadora,
                lit.id_obligacion_financiera,
                o.estado_obligacion,
                lit.observaciones
            FROM liquidacion_impuesto_trasladado lit
            LEFT JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = lit.id_relacion_generadora
             AND rg.deleted_at IS NULL
            LEFT JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = lit.id_obligacion_financiera
             AND o.deleted_at IS NULL
            WHERE lit.id_liquidacion_impuesto_trasladado =
                  :id_liquidacion_impuesto_trasladado
              AND lit.deleted_at IS NULL
            """
        )
        row = self.db.execute(
            stmt,
            {
                "id_liquidacion_impuesto_trasladado": (
                    id_liquidacion_impuesto_trasladado
                )
            },
        ).mappings().one_or_none()
        if row is None:
            return None

        motivo_anulacion = None
        if row["observaciones"]:
            try:
                parsed = json.loads(row["observaciones"])
                anulacion = parsed.get("anulacion") if isinstance(parsed, dict) else None
                if isinstance(anulacion, dict):
                    motivo_anulacion = anulacion.get("motivo")
            except (TypeError, ValueError):
                motivo_anulacion = None

        return {
            "id_liquidacion_impuesto_trasladado": row[
                "id_liquidacion_impuesto_trasladado"
            ],
            "estado_liquidacion": row["estado_liquidacion"],
            "id_relacion_generadora": row["id_relacion_generadora"],
            "estado_relacion_generadora": row["estado_relacion_generadora"],
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "estado_obligacion": row["estado_obligacion"],
            "motivo_anulacion": motivo_anulacion,
        }

    def get_operaciones_activas_liquidacion_impuesto_trasladado(
        self, id_liquidacion_impuesto_trasladado: int
    ) -> dict[str, Any]:
        stmt = text(
            """
            WITH liq AS (
                SELECT
                    id_liquidacion_impuesto_trasladado,
                    id_obligacion_financiera,
                    updated_at,
                    op_id_alta
                FROM liquidacion_impuesto_trasladado
                WHERE id_liquidacion_impuesto_trasladado =
                      :id_liquidacion_impuesto_trasladado
                  AND deleted_at IS NULL
            ),
            comps AS (
                SELECT c.id_composicion_obligacion
                FROM composicion_obligacion c
                JOIN liq ON liq.id_obligacion_financiera =
                    c.id_obligacion_financiera
                WHERE c.deleted_at IS NULL
            ),
            apps AS (
                SELECT a.id_aplicacion_financiera, a.id_movimiento_financiero
                FROM aplicacion_financiera a
                JOIN liq ON liq.id_obligacion_financiera =
                    a.id_obligacion_financiera
                WHERE a.deleted_at IS NULL
                  AND (
                      a.id_obligacion_financiera =
                          liq.id_obligacion_financiera
                      OR a.id_composicion_obligacion IN (
                          SELECT id_composicion_obligacion FROM comps
                      )
                  )
            )
            SELECT
                (SELECT COUNT(*) FROM apps) AS aplicaciones,
                (
                    SELECT COUNT(DISTINCT mf.id_movimiento_financiero)
                    FROM apps a
                    JOIN movimiento_financiero mf
                      ON mf.id_movimiento_financiero =
                         a.id_movimiento_financiero
                     AND mf.deleted_at IS NULL
                     AND COALESCE(mf.estado_movimiento, 'ACTIVO') <> 'ANULADO'
                ) AS movimientos,
                (
                    SELECT COUNT(*)
                    FROM liquidacion_punitorio lp
                    JOIN liq ON liq.id_obligacion_financiera =
                        lp.id_obligacion_financiera
                    WHERE lp.deleted_at IS NULL
                      AND lp.estado_liquidacion = 'ACTIVA'
                ) AS punitorios,
                (
                    SELECT COUNT(*)
                    FROM composicion_obligacion c
                    JOIN liq ON liq.id_obligacion_financiera =
                        c.id_obligacion_financiera
                    JOIN concepto_financiero cf
                      ON cf.id_concepto_financiero = c.id_concepto_financiero
                     AND cf.deleted_at IS NULL
                    WHERE c.deleted_at IS NULL
                      AND c.estado_composicion_obligacion = 'ACTIVA'
                      AND (
                          c.created_at > liq.updated_at
                          OR c.updated_at > liq.updated_at
                      )
                      AND NOT (
                          cf.codigo_concepto_financiero = 'IMPUESTO_TRASLADADO'
                          AND c.op_id_alta = liq.op_id_alta
                          AND c.op_id_ultima_modificacion = liq.op_id_alta
                      )
                ) AS composiciones_posteriores
            """
        )
        row = self.db.execute(
            stmt,
            {
                "id_liquidacion_impuesto_trasladado": (
                    id_liquidacion_impuesto_trasladado
                )
            },
        ).mappings().one()
        counts = {
            "aplicaciones": int(row["aplicaciones"]),
            "movimientos": int(row["movimientos"]),
            "punitorios": int(row["punitorios"]),
            "composiciones_posteriores": int(row["composiciones_posteriores"]),
        }
        counts["tiene_operaciones"] = any(counts.values())
        return counts

    def anular_liquidacion_impuesto_trasladado(
        self,
        *,
        id_liquidacion_impuesto_trasladado: int,
        motivo: str,
        context: Any,
    ) -> dict[str, Any]:
        row_stmt = text(
            """
            SELECT
                lit.id_liquidacion_impuesto_trasladado,
                lit.estado_liquidacion,
                lit.id_relacion_generadora,
                lit.id_obligacion_financiera,
                lit.observaciones
            FROM liquidacion_impuesto_trasladado lit
            WHERE lit.id_liquidacion_impuesto_trasladado =
                  :id_liquidacion_impuesto_trasladado
              AND lit.deleted_at IS NULL
            FOR UPDATE
            """
        )
        row = self.db.execute(
            row_stmt,
            {
                "id_liquidacion_impuesto_trasladado": (
                    id_liquidacion_impuesto_trasladado
                )
            },
        ).mappings().one()
        observaciones = _append_motivo_anulacion(row["observaciones"], motivo)
        op_id = getattr(context, "op_id", None)
        id_instalacion = getattr(context, "id_instalacion", None)

        lit_row = self.db.execute(
            text(
                """
                UPDATE liquidacion_impuesto_trasladado
                SET estado_liquidacion = 'ANULADA',
                    observaciones = :observaciones,
                    id_instalacion_ultima_modificacion = :id_instalacion,
                    op_id_ultima_modificacion = :op_id
                WHERE id_liquidacion_impuesto_trasladado =
                      :id_liquidacion_impuesto_trasladado
                RETURNING estado_liquidacion
                """
            ),
            {
                "id_liquidacion_impuesto_trasladado": (
                    id_liquidacion_impuesto_trasladado
                ),
                "observaciones": observaciones,
                "id_instalacion": id_instalacion,
                "op_id": op_id,
            },
        ).mappings().one()

        rg_row = None
        if row["id_relacion_generadora"] is not None:
            rg_row = self.db.execute(
                text(
                    """
                    UPDATE relacion_generadora
                    SET estado_relacion_generadora = 'CANCELADA',
                        id_instalacion_ultima_modificacion = :id_instalacion,
                        op_id_ultima_modificacion = :op_id
                    WHERE id_relacion_generadora = :id_relacion_generadora
                      AND deleted_at IS NULL
                    RETURNING estado_relacion_generadora
                    """
                ),
                {
                    "id_relacion_generadora": row["id_relacion_generadora"],
                    "id_instalacion": id_instalacion,
                    "op_id": op_id,
                },
            ).mappings().one_or_none()

        ob_row = None
        if row["id_obligacion_financiera"] is not None:
            ob_row = self.db.execute(
                text(
                    """
                    UPDATE obligacion_financiera
                    SET estado_obligacion = 'ANULADA',
                        id_instalacion_ultima_modificacion = :id_instalacion,
                        op_id_ultima_modificacion = :op_id
                    WHERE id_obligacion_financiera = :id_obligacion_financiera
                      AND deleted_at IS NULL
                    RETURNING estado_obligacion
                    """
                ),
                {
                    "id_obligacion_financiera": row["id_obligacion_financiera"],
                    "id_instalacion": id_instalacion,
                    "op_id": op_id,
                },
            ).mappings().one_or_none()
            self.db.execute(
                text(
                    """
                    UPDATE composicion_obligacion
                    SET estado_composicion_obligacion = 'ANULADA',
                        id_instalacion_ultima_modificacion = :id_instalacion,
                        op_id_ultima_modificacion = :op_id
                    WHERE id_obligacion_financiera = :id_obligacion_financiera
                      AND deleted_at IS NULL
                    """
                ),
                {
                    "id_obligacion_financiera": row["id_obligacion_financiera"],
                    "id_instalacion": id_instalacion,
                    "op_id": op_id,
                },
            )

        egresos_liberados = self.db.execute(
            text(
                """
                UPDATE liquidacion_impuesto_trasladado_egreso
                SET estado_liquidacion_impuesto_egreso = 'ANULADO',
                    deleted_at = CURRENT_TIMESTAMP,
                    id_instalacion_ultima_modificacion = :id_instalacion,
                    op_id_ultima_modificacion = :op_id
                WHERE id_liquidacion_impuesto_trasladado =
                      :id_liquidacion_impuesto_trasladado
                  AND deleted_at IS NULL
                  AND estado_liquidacion_impuesto_egreso = 'ACTIVO'
                """
            ),
            {
                "id_liquidacion_impuesto_trasladado": (
                    id_liquidacion_impuesto_trasladado
                ),
                "id_instalacion": id_instalacion,
                "op_id": op_id,
            },
        ).rowcount

        return {
            "id_liquidacion_impuesto_trasladado": row[
                "id_liquidacion_impuesto_trasladado"
            ],
            "estado_liquidacion": lit_row["estado_liquidacion"],
            "id_relacion_generadora": row["id_relacion_generadora"],
            "estado_relacion_generadora": (
                rg_row["estado_relacion_generadora"] if rg_row is not None else None
            ),
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "estado_obligacion": (
                ob_row["estado_obligacion"] if ob_row is not None else None
            ),
            "egresos_liberados": int(egresos_liberados or 0),
        }

    def get_liquidacion_recupero_para_anular(
        self, id_liquidacion_recupero: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                lr.id_liquidacion_recupero,
                lr.estado_liquidacion,
                lr.id_relacion_generadora,
                rg.estado_relacion_generadora,
                lr.id_obligacion_financiera,
                o.estado_obligacion,
                lr.observaciones
            FROM liquidacion_recupero lr
            LEFT JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = lr.id_relacion_generadora
             AND rg.deleted_at IS NULL
            LEFT JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = lr.id_obligacion_financiera
             AND o.deleted_at IS NULL
            WHERE lr.id_liquidacion_recupero = :id_liquidacion_recupero
              AND lr.deleted_at IS NULL
            """
        )
        row = self.db.execute(
            stmt, {"id_liquidacion_recupero": id_liquidacion_recupero}
        ).mappings().one_or_none()
        if row is None:
            return None

        motivo_anulacion = None
        if row["observaciones"]:
            try:
                parsed = json.loads(row["observaciones"])
                anulacion = parsed.get("anulacion") if isinstance(parsed, dict) else None
                if isinstance(anulacion, dict):
                    motivo_anulacion = anulacion.get("motivo")
            except (TypeError, ValueError):
                motivo_anulacion = None

        return {
            "id_liquidacion_recupero": row["id_liquidacion_recupero"],
            "estado_liquidacion": row["estado_liquidacion"],
            "id_relacion_generadora": row["id_relacion_generadora"],
            "estado_relacion_generadora": row["estado_relacion_generadora"],
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "estado_obligacion": row["estado_obligacion"],
            "motivo_anulacion": motivo_anulacion,
        }

    def get_operaciones_activas_liquidacion_recupero(
        self, id_liquidacion_recupero: int
    ) -> dict[str, Any]:
        stmt = text(
            """
            WITH liq AS (
                SELECT
                    id_liquidacion_recupero,
                    id_obligacion_financiera,
                    updated_at,
                    op_id_alta
                FROM liquidacion_recupero
                WHERE id_liquidacion_recupero = :id_liquidacion_recupero
                  AND deleted_at IS NULL
            ),
            comps AS (
                SELECT c.id_composicion_obligacion
                FROM composicion_obligacion c
                JOIN liq ON liq.id_obligacion_financiera = c.id_obligacion_financiera
                WHERE c.deleted_at IS NULL
            ),
            apps AS (
                SELECT a.id_aplicacion_financiera, a.id_movimiento_financiero
                FROM aplicacion_financiera a
                JOIN liq ON liq.id_obligacion_financiera = a.id_obligacion_financiera
                WHERE a.deleted_at IS NULL
                  AND (
                      a.id_obligacion_financiera = liq.id_obligacion_financiera
                      OR a.id_composicion_obligacion IN (
                          SELECT id_composicion_obligacion FROM comps
                      )
                  )
            )
            SELECT
                (SELECT COUNT(*) FROM apps) AS aplicaciones,
                (
                    SELECT COUNT(DISTINCT mf.id_movimiento_financiero)
                    FROM apps a
                    JOIN movimiento_financiero mf
                      ON mf.id_movimiento_financiero = a.id_movimiento_financiero
                     AND mf.deleted_at IS NULL
                     AND COALESCE(mf.estado_movimiento, 'ACTIVO') <> 'ANULADO'
                ) AS movimientos,
                (
                    SELECT COUNT(*)
                    FROM liquidacion_punitorio lp
                    JOIN liq ON liq.id_obligacion_financiera = lp.id_obligacion_financiera
                    WHERE lp.deleted_at IS NULL
                      AND lp.estado_liquidacion = 'ACTIVA'
                ) AS punitorios,
                (
                    SELECT COUNT(*)
                    FROM composicion_obligacion c
                    JOIN liq ON liq.id_obligacion_financiera = c.id_obligacion_financiera
                    JOIN concepto_financiero cf
                      ON cf.id_concepto_financiero = c.id_concepto_financiero
                     AND cf.deleted_at IS NULL
                    WHERE c.deleted_at IS NULL
                      AND c.estado_composicion_obligacion = 'ACTIVA'
                      AND (c.created_at > liq.updated_at OR c.updated_at > liq.updated_at)
                      AND NOT (
                          cf.codigo_concepto_financiero = 'SERVICIO_RECUPERADO'
                          AND c.op_id_alta = liq.op_id_alta
                          AND c.op_id_ultima_modificacion = liq.op_id_alta
                      )
                ) AS composiciones_posteriores
            """
        )
        row = self.db.execute(
            stmt, {"id_liquidacion_recupero": id_liquidacion_recupero}
        ).mappings().one()
        counts = {
            "aplicaciones": int(row["aplicaciones"]),
            "movimientos": int(row["movimientos"]),
            "punitorios": int(row["punitorios"]),
            "composiciones_posteriores": int(row["composiciones_posteriores"]),
        }
        counts["tiene_operaciones"] = any(counts.values())
        return counts

    def anular_liquidacion_recupero(
        self, *, id_liquidacion_recupero: int, motivo: str, context: Any
    ) -> dict[str, Any]:
        row_stmt = text(
            """
            SELECT
                lr.id_liquidacion_recupero,
                lr.estado_liquidacion,
                lr.id_relacion_generadora,
                lr.id_obligacion_financiera,
                lr.observaciones
            FROM liquidacion_recupero lr
            WHERE lr.id_liquidacion_recupero = :id_liquidacion_recupero
              AND lr.deleted_at IS NULL
            FOR UPDATE
            """
        )
        row = self.db.execute(
            row_stmt, {"id_liquidacion_recupero": id_liquidacion_recupero}
        ).mappings().one()
        observaciones = _append_motivo_anulacion(row["observaciones"], motivo)
        op_id = getattr(context, "op_id", None)
        id_instalacion = getattr(context, "id_instalacion", None)

        lr_row = self.db.execute(
            text(
                """
                UPDATE liquidacion_recupero
                SET estado_liquidacion = 'ANULADA',
                    observaciones = :observaciones,
                    id_instalacion_ultima_modificacion = :id_instalacion,
                    op_id_ultima_modificacion = :op_id
                WHERE id_liquidacion_recupero = :id_liquidacion_recupero
                RETURNING estado_liquidacion
                """
            ),
            {
                "id_liquidacion_recupero": id_liquidacion_recupero,
                "observaciones": observaciones,
                "id_instalacion": id_instalacion,
                "op_id": op_id,
            },
        ).mappings().one()

        rg_row = None
        if row["id_relacion_generadora"] is not None:
            rg_row = self.db.execute(
                text(
                    """
                    UPDATE relacion_generadora
                    SET estado_relacion_generadora = 'CANCELADA',
                        id_instalacion_ultima_modificacion = :id_instalacion,
                        op_id_ultima_modificacion = :op_id
                    WHERE id_relacion_generadora = :id_relacion_generadora
                      AND deleted_at IS NULL
                    RETURNING estado_relacion_generadora
                    """
                ),
                {
                    "id_relacion_generadora": row["id_relacion_generadora"],
                    "id_instalacion": id_instalacion,
                    "op_id": op_id,
                },
            ).mappings().one_or_none()

        ob_row = None
        if row["id_obligacion_financiera"] is not None:
            ob_row = self.db.execute(
                text(
                    """
                    UPDATE obligacion_financiera
                    SET estado_obligacion = 'ANULADA',
                        id_instalacion_ultima_modificacion = :id_instalacion,
                        op_id_ultima_modificacion = :op_id
                    WHERE id_obligacion_financiera = :id_obligacion_financiera
                      AND deleted_at IS NULL
                    RETURNING estado_obligacion
                    """
                ),
                {
                    "id_obligacion_financiera": row["id_obligacion_financiera"],
                    "id_instalacion": id_instalacion,
                    "op_id": op_id,
                },
            ).mappings().one_or_none()
            self.db.execute(
                text(
                    """
                    UPDATE composicion_obligacion
                    SET estado_composicion_obligacion = 'ANULADA',
                        id_instalacion_ultima_modificacion = :id_instalacion,
                        op_id_ultima_modificacion = :op_id
                    WHERE id_obligacion_financiera = :id_obligacion_financiera
                      AND deleted_at IS NULL
                    """
                ),
                {
                    "id_obligacion_financiera": row["id_obligacion_financiera"],
                    "id_instalacion": id_instalacion,
                    "op_id": op_id,
                },
            )

        egresos_liberados = self.db.execute(
            text(
                """
                UPDATE liquidacion_recupero_egreso
                SET estado_liquidacion_recupero_egreso = 'ANULADO',
                    deleted_at = CURRENT_TIMESTAMP,
                    id_instalacion_ultima_modificacion = :id_instalacion,
                    op_id_ultima_modificacion = :op_id
                WHERE id_liquidacion_recupero = :id_liquidacion_recupero
                  AND deleted_at IS NULL
                  AND estado_liquidacion_recupero_egreso = 'ACTIVO'
                """
            ),
            {
                "id_liquidacion_recupero": id_liquidacion_recupero,
                "id_instalacion": id_instalacion,
                "op_id": op_id,
            },
        ).rowcount

        return {
            "id_liquidacion_recupero": row["id_liquidacion_recupero"],
            "estado_liquidacion": lr_row["estado_liquidacion"],
            "id_relacion_generadora": row["id_relacion_generadora"],
            "estado_relacion_generadora": (
                rg_row["estado_relacion_generadora"] if rg_row is not None else None
            ),
            "id_obligacion_financiera": row["id_obligacion_financiera"],
            "estado_obligacion": (
                ob_row["estado_obligacion"] if ob_row is not None else None
            ),
            "egresos_liberados": int(egresos_liberados or 0),
        }

    def crear_liquidacion_recupero(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text(
            """
            INSERT INTO liquidacion_recupero (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                codigo_liquidacion_recupero, fecha_liquidacion,
                fecha_vencimiento, estado_liquidacion,
                importe_total_egresado_base, importe_total_recuperar,
                importe_absorbido_empresa, observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :codigo_liquidacion_recupero, :fecha_liquidacion,
                :fecha_vencimiento, 'EMITIDA',
                :importe_total_egresado_base, :importe_total_recuperar,
                :importe_absorbido_empresa, :observaciones
            )
            RETURNING id_liquidacion_recupero
            """
        )
        row = self.db.execute(
            stmt,
            {
                "uid_global": values["uid_global_liquidacion"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "codigo_liquidacion_recupero": values["codigo_liquidacion_recupero"],
                "fecha_liquidacion": values["fecha_liquidacion"],
                "fecha_vencimiento": values["fecha_vencimiento"],
                "importe_total_egresado_base": values[
                    "importe_total_egresado_base"
                ],
                "importe_total_recuperar": values["importe_total_recuperar"],
                "importe_absorbido_empresa": values["importe_absorbido_empresa"],
                "observaciones": values["observaciones"],
            },
        ).mappings().one()
        id_liquidacion = row["id_liquidacion_recupero"]

        self.db.execute(
            text(
                """
                INSERT INTO liquidacion_recupero_factura (
                    id_liquidacion_recupero, id_factura_servicio,
                    importe_egresado_base, importe_recuperar
                )
                VALUES (
                    :id_liquidacion_recupero, :id_factura_servicio,
                    :importe_egresado_base, :importe_recuperar
                )
                """
            ),
            {
                "id_liquidacion_recupero": id_liquidacion,
                "id_factura_servicio": values["id_factura_servicio"],
                "importe_egresado_base": values["importe_total_egresado_base"],
                "importe_recuperar": values["importe_total_recuperar"],
            },
        )
        egreso_stmt = text(
            """
            INSERT INTO liquidacion_recupero_egreso (
                id_liquidacion_recupero,
                id_egreso_proveedor_factura_servicio,
                importe_imputado_base
            )
            VALUES (
                :id_liquidacion_recupero,
                :id_egreso_proveedor_factura_servicio,
                :importe_imputado_base
            )
            """
        )
        for egreso in values["egresos"]:
            self.db.execute(
                egreso_stmt,
                {
                    "id_liquidacion_recupero": id_liquidacion,
                    "id_egreso_proveedor_factura_servicio": egreso[
                        "id_egreso_proveedor_factura_servicio"
                    ],
                    "importe_imputado_base": egreso["importe_pagado"],
                },
            )
        responsable_stmt = text(
            """
            INSERT INTO liquidacion_recupero_responsable (
                id_liquidacion_recupero, id_persona,
                porcentaje_responsabilidad, importe_responsable,
                origen_responsable, id_asignacion_servicio_responsable
            )
            VALUES (
                :id_liquidacion_recupero, :id_persona,
                :porcentaje_responsabilidad, :importe_responsable,
                :origen_responsable, :id_asignacion_servicio_responsable
            )
            """
        )
        for responsable in values["responsables"]:
            rv = self._values(responsable)
            self.db.execute(
                responsable_stmt,
                {
                    "id_liquidacion_recupero": id_liquidacion,
                    "id_persona": rv["id_persona"],
                    "porcentaje_responsabilidad": rv["porcentaje_responsabilidad"],
                    "importe_responsable": rv["importe_responsable"],
                    "origen_responsable": rv["origen_responsable"],
                    "id_asignacion_servicio_responsable": rv[
                        "id_asignacion_servicio_responsable"
                    ],
                },
            )
        return {"id_liquidacion_recupero": id_liquidacion}

    def completar_liquidacion_recupero_financiera(
        self, *, id_liquidacion_recupero: int, id_relacion_generadora: int, payload: Any
    ) -> None:
        values = self._values(payload)
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
                NULL, NULL,
                :importe_total, :importe_total, 'ARS', 'EMITIDA'
            )
            RETURNING id_obligacion_financiera
            """
        )
        ob_row = self.db.execute(
            ob_stmt,
            {
                "uid_global": values["uid_global_obligacion"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_relacion_generadora": id_relacion_generadora,
                "fecha_emision": values["fecha_liquidacion"],
                "fecha_vencimiento": values["fecha_vencimiento"],
                "importe_total": values["importe_total_recuperar"],
            },
        ).mappings().one()
        id_obligacion = ob_row["id_obligacion_financiera"]

        self.db.execute(
            text(
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
            ),
            {
                "uid_global": values["uid_global_composicion"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_obligacion_financiera": id_obligacion,
                "id_concepto_financiero": values["id_concepto_financiero"],
                "importe_componente": values["importe_total_recuperar"],
            },
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
                gen_random_uuid(), :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_obligacion_financiera, :id_persona,
                'RESPONSABLE_RECUPERO', :porcentaje_responsabilidad
            )
            """
        )
        for responsable in values["responsables"]:
            rv = self._values(responsable)
            self.db.execute(
                obligado_stmt,
                {
                    "version_registro": values["version_registro"],
                    "created_at": values["created_at"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_origen": values["id_instalacion_origen"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_alta": values["op_id_alta"],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    "id_obligacion_financiera": id_obligacion,
                    "id_persona": rv["id_persona"],
                    "porcentaje_responsabilidad": rv[
                        "porcentaje_responsabilidad"
                    ],
                },
            )
        self.db.execute(
            text(
                """
                UPDATE liquidacion_recupero
                SET id_relacion_generadora = :id_relacion_generadora,
                    id_obligacion_financiera = :id_obligacion_financiera
                WHERE id_liquidacion_recupero = :id_liquidacion_recupero
                """
            ),
            {
                "id_liquidacion_recupero": id_liquidacion_recupero,
                "id_relacion_generadora": id_relacion_generadora,
                "id_obligacion_financiera": id_obligacion,
            },
        )

    def crear_liquidacion_impuesto_trasladado(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        comprobante = values["comprobante"]
        stmt = text(
            """
            INSERT INTO liquidacion_impuesto_trasladado (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                codigo_liquidacion_impuesto_trasladado, estado_liquidacion,
                modalidad_gestion_impuesto, fecha_liquidacion, fecha_vencimiento,
                importe_total_base, importe_total_trasladar,
                importe_absorbido_empresa, observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :codigo_liquidacion_impuesto_trasladado, 'EMITIDA',
                :modalidad_gestion_impuesto, :fecha_liquidacion, :fecha_vencimiento,
                :importe_total_base, :importe_total_trasladar,
                :importe_absorbido_empresa, :observaciones
            )
            RETURNING id_liquidacion_impuesto_trasladado
            """
        )
        row = self.db.execute(
            stmt,
            {
                "uid_global": values["uid_global_liquidacion"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "codigo_liquidacion_impuesto_trasladado": values[
                    "codigo_liquidacion_impuesto_trasladado"
                ],
                "modalidad_gestion_impuesto": values["modalidad_gestion_impuesto"],
                "fecha_liquidacion": values["fecha_liquidacion"],
                "fecha_vencimiento": values["fecha_vencimiento"],
                "importe_total_base": values["importe_total_base"],
                "importe_total_trasladar": values["importe_total_trasladar"],
                "importe_absorbido_empresa": values["importe_absorbido_empresa"],
                "observaciones": values["observaciones"],
            },
        ).mappings().one()
        id_liquidacion = row["id_liquidacion_impuesto_trasladado"]

        self.db.execute(
            text(
                """
                INSERT INTO liquidacion_impuesto_trasladado_comprobante (
                    id_liquidacion_impuesto_trasladado,
                    id_comprobante_impuesto,
                    organismo,
                    tipo_impuesto,
                    partida_nomenclatura,
                    numero_comprobante,
                    periodo_desde,
                    periodo_hasta,
                    fecha_vencimiento,
                    importe_comprobante,
                    importe_base,
                    importe_trasladar
                )
                VALUES (
                    :id_liquidacion,
                    :id_comprobante_impuesto,
                    :organismo,
                    :tipo_impuesto,
                    :partida_nomenclatura,
                    :numero_comprobante,
                    :periodo_desde,
                    :periodo_hasta,
                    :fecha_vencimiento,
                    :importe_comprobante,
                    :importe_base,
                    :importe_trasladar
                )
                """
            ),
            {
                "id_liquidacion": id_liquidacion,
                "id_comprobante_impuesto": values["id_comprobante_impuesto"],
                "organismo": comprobante["organismo"],
                "tipo_impuesto": comprobante["tipo_impuesto"],
                "partida_nomenclatura": comprobante["partida_nomenclatura"],
                "numero_comprobante": comprobante["numero_comprobante"],
                "periodo_desde": comprobante["periodo_desde"],
                "periodo_hasta": comprobante["periodo_hasta"],
                "fecha_vencimiento": comprobante["fecha_vencimiento"],
                "importe_comprobante": comprobante["importe_total"],
                "importe_base": values["importe_total_base"],
                "importe_trasladar": values["importe_total_trasladar"],
            },
        )

        egreso_stmt = text(
            """
            INSERT INTO liquidacion_impuesto_trasladado_egreso (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_liquidacion_impuesto_trasladado,
                id_egreso_impuesto_empresa,
                importe_imputado_base
            )
            VALUES (
                gen_random_uuid(), :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_liquidacion,
                :id_egreso_impuesto_empresa,
                :importe_imputado_base
            )
            """
        )
        for egreso in values["egresos"]:
            self.db.execute(
                egreso_stmt,
                {
                    "version_registro": values["version_registro"],
                    "created_at": values["created_at"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_origen": values["id_instalacion_origen"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_alta": values["op_id_alta"],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    "id_liquidacion": id_liquidacion,
                    "id_egreso_impuesto_empresa": egreso[
                        "id_egreso_impuesto_empresa"
                    ],
                    "importe_imputado_base": egreso["importe_pagado"],
                },
            )

        responsable_stmt = text(
            """
            INSERT INTO liquidacion_impuesto_trasladado_responsable (
                id_liquidacion_impuesto_trasladado,
                id_persona,
                porcentaje_responsabilidad,
                importe_responsable,
                origen_responsable
            )
            VALUES (
                :id_liquidacion,
                :id_persona,
                :porcentaje_responsabilidad,
                :importe_responsable,
                :origen_responsable
            )
            """
        )
        for responsable in values["responsables"]:
            rv = self._values(responsable)
            self.db.execute(
                responsable_stmt,
                {
                    "id_liquidacion": id_liquidacion,
                    "id_persona": rv["id_persona"],
                    "porcentaje_responsabilidad": rv["porcentaje_responsabilidad"],
                    "importe_responsable": rv["importe_responsable"],
                    "origen_responsable": rv["origen_responsable"],
                },
            )
        return {"id_liquidacion_impuesto_trasladado": id_liquidacion}

    def completar_liquidacion_impuesto_trasladado_financiera(
        self,
        *,
        id_liquidacion_impuesto_trasladado: int,
        id_relacion_generadora: int,
        payload: Any,
    ) -> None:
        values = self._values(payload)
        ob_row = self.db.execute(
            text(
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
                    NULL, NULL,
                    :importe_total, :importe_total, 'ARS', 'EMITIDA'
                )
                RETURNING id_obligacion_financiera
                """
            ),
            {
                "uid_global": values["uid_global_obligacion"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_relacion_generadora": id_relacion_generadora,
                "fecha_emision": values["fecha_liquidacion"],
                "fecha_vencimiento": values["fecha_vencimiento"],
                "importe_total": values["importe_total_trasladar"],
            },
        ).mappings().one()
        id_obligacion = ob_row["id_obligacion_financiera"]
        self.db.execute(
            text(
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
            ),
            {
                "uid_global": values["uid_global_composicion"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_obligacion_financiera": id_obligacion,
                "id_concepto_financiero": values["id_concepto_financiero"],
                "importe_componente": values["importe_total_trasladar"],
            },
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
                gen_random_uuid(), :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_obligacion_financiera, :id_persona,
                'RESPONSABLE_IMPUESTO_TRASLADADO', :porcentaje_responsabilidad
            )
            """
        )
        for responsable in values["responsables"]:
            rv = self._values(responsable)
            self.db.execute(
                obligado_stmt,
                {
                    "version_registro": values["version_registro"],
                    "created_at": values["created_at"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_origen": values["id_instalacion_origen"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_alta": values["op_id_alta"],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    "id_obligacion_financiera": id_obligacion,
                    "id_persona": rv["id_persona"],
                    "porcentaje_responsabilidad": rv[
                        "porcentaje_responsabilidad"
                    ],
                },
            )

        self.db.execute(
            text(
                """
                UPDATE liquidacion_impuesto_trasladado
                SET id_relacion_generadora = :id_relacion_generadora,
                    id_obligacion_financiera = :id_obligacion_financiera
                WHERE id_liquidacion_impuesto_trasladado =
                      :id_liquidacion_impuesto_trasladado
                """
            ),
            {
                "id_liquidacion_impuesto_trasladado": (
                    id_liquidacion_impuesto_trasladado
                ),
                "id_relacion_generadora": id_relacion_generadora,
                "id_obligacion_financiera": id_obligacion,
            },
        )

    def get_egreso_proveedor_factura_servicio_by_id(
        self, id_egreso: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                e.id_egreso_proveedor_factura_servicio,
                e.id_factura_servicio,
                e.id_movimiento_tesoreria,
                e.estado_egreso,
                e.observaciones,
                mt.estado AS estado_movimiento_tesoreria
            FROM egreso_proveedor_factura_servicio e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
             AND mt.deleted_at IS NULL
            WHERE e.id_egreso_proveedor_factura_servicio = :id_egreso
              AND e.deleted_at IS NULL
            """
        )
        row = self.db.execute(stmt, {"id_egreso": id_egreso}).mappings().one_or_none()
        if row is None:
            return None
        motivo_anulacion = None
        if row["observaciones"]:
            try:
                parsed = json.loads(row["observaciones"])
                anulacion = parsed.get("anulacion") if isinstance(parsed, dict) else None
                if isinstance(anulacion, dict):
                    motivo_anulacion = anulacion.get("motivo")
            except (TypeError, ValueError):
                motivo_anulacion = None
        return {
            "id_egreso_proveedor_factura_servicio": row[
                "id_egreso_proveedor_factura_servicio"
            ],
            "id_factura_servicio": row["id_factura_servicio"],
            "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
            "estado_egreso": row["estado_egreso"],
            "estado_movimiento_tesoreria": row["estado_movimiento_tesoreria"],
            "motivo_anulacion": motivo_anulacion,
        }

    def get_egreso_impuesto_empresa_by_id(
        self, id_egreso: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                e.id_egreso_impuesto_empresa,
                e.id_comprobante_impuesto,
                e.id_movimiento_tesoreria,
                e.estado_egreso,
                e.observaciones,
                mt.estado AS estado_movimiento_tesoreria
            FROM egreso_impuesto_empresa e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
             AND mt.deleted_at IS NULL
            WHERE e.id_egreso_impuesto_empresa = :id_egreso
              AND e.deleted_at IS NULL
            """
        )
        row = self.db.execute(stmt, {"id_egreso": id_egreso}).mappings().one_or_none()
        if row is None:
            return None
        motivo_anulacion = None
        if row["observaciones"]:
            try:
                parsed = json.loads(row["observaciones"])
                anulacion = parsed.get("anulacion") if isinstance(parsed, dict) else None
                if isinstance(anulacion, dict):
                    motivo_anulacion = anulacion.get("motivo")
            except (TypeError, ValueError):
                motivo_anulacion = None
        return {
            "id_egreso_impuesto_empresa": row["id_egreso_impuesto_empresa"],
            "id_comprobante_impuesto": row["id_comprobante_impuesto"],
            "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
            "estado_egreso": row["estado_egreso"],
            "estado_movimiento_tesoreria": row["estado_movimiento_tesoreria"],
            "motivo_anulacion": motivo_anulacion,
        }

    def egreso_proveedor_usado_en_liquidacion_recupero(self, id_egreso: int) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM liquidacion_recupero_egreso lre
            JOIN liquidacion_recupero lr
              ON lr.id_liquidacion_recupero = lre.id_liquidacion_recupero
             AND lr.deleted_at IS NULL
             AND lr.estado_liquidacion = 'EMITIDA'
            WHERE lre.id_egreso_proveedor_factura_servicio = :id_egreso
              AND lre.deleted_at IS NULL
              AND lre.estado_liquidacion_recupero_egreso = 'ACTIVO'
            LIMIT 1
            """
        )
        return (
            self.db.execute(stmt, {"id_egreso": id_egreso}).scalar_one_or_none()
            is not None
        )

    def egreso_impuesto_usado_en_liquidacion_trasladada(
        self, id_egreso: int
    ) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM liquidacion_impuesto_trasladado_egreso lite
            JOIN liquidacion_impuesto_trasladado lit
              ON lit.id_liquidacion_impuesto_trasladado =
                 lite.id_liquidacion_impuesto_trasladado
             AND lit.deleted_at IS NULL
             AND lit.estado_liquidacion = 'EMITIDA'
            WHERE lite.id_egreso_impuesto_empresa = :id_egreso
              AND lite.deleted_at IS NULL
              AND lite.estado_liquidacion_impuesto_egreso = 'ACTIVO'
            LIMIT 1
            """
        )
        return (
            self.db.execute(stmt, {"id_egreso": id_egreso}).scalar_one_or_none()
            is not None
        )

    def anular_egreso_proveedor_factura_servicio(
        self, *, id_egreso: int, motivo: str, context: Any
    ) -> dict[str, Any]:
        row_stmt = text(
            """
            SELECT
                e.id_egreso_proveedor_factura_servicio,
                e.id_factura_servicio,
                e.id_movimiento_tesoreria,
                e.observaciones
            FROM egreso_proveedor_factura_servicio e
            WHERE e.id_egreso_proveedor_factura_servicio = :id_egreso
              AND e.deleted_at IS NULL
            FOR UPDATE
            """
        )
        row = self.db.execute(row_stmt, {"id_egreso": id_egreso}).mappings().one()
        observaciones = _append_motivo_anulacion(row["observaciones"], motivo)
        op_id = getattr(context, "op_id", None)
        update_egreso_stmt = text(
            """
            UPDATE egreso_proveedor_factura_servicio
            SET estado_egreso = 'ANULADO',
                observaciones = :observaciones,
                op_id_ultima_modificacion = :op_id
            WHERE id_egreso_proveedor_factura_servicio = :id_egreso
            RETURNING estado_egreso
            """
        )
        update_mt_stmt = text(
            """
            UPDATE movimiento_tesoreria
            SET estado = 'ANULADO',
                observaciones = :observaciones,
                op_id_ultima_modificacion = :op_id
            WHERE id_movimiento_tesoreria = :id_movimiento_tesoreria
            RETURNING estado
            """
        )
        egreso_row = self.db.execute(
            update_egreso_stmt,
            {
                "id_egreso": id_egreso,
                "observaciones": observaciones,
                "op_id": op_id,
            },
        ).mappings().one()
        mt_row = self.db.execute(
            update_mt_stmt,
            {
                "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
                "observaciones": observaciones,
                "op_id": op_id,
            },
        ).mappings().one()

        return {
            "id_egreso_proveedor_factura_servicio": row[
                "id_egreso_proveedor_factura_servicio"
            ],
            "id_factura_servicio": row["id_factura_servicio"],
            "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
            "estado_egreso": egreso_row["estado_egreso"],
            "estado_movimiento_tesoreria": mt_row["estado"],
        }

    def anular_egreso_impuesto_empresa(
        self, *, id_egreso: int, motivo: str, context: Any
    ) -> dict[str, Any]:
        row_stmt = text(
            """
            SELECT
                e.id_egreso_impuesto_empresa,
                e.id_comprobante_impuesto,
                e.id_movimiento_tesoreria,
                e.observaciones
            FROM egreso_impuesto_empresa e
            WHERE e.id_egreso_impuesto_empresa = :id_egreso
              AND e.deleted_at IS NULL
            FOR UPDATE
            """
        )
        row = self.db.execute(row_stmt, {"id_egreso": id_egreso}).mappings().one()
        observaciones = _append_motivo_anulacion(row["observaciones"], motivo)
        op_id = getattr(context, "op_id", None)
        update_egreso_stmt = text(
            """
            UPDATE egreso_impuesto_empresa
            SET estado_egreso = 'ANULADO',
                observaciones = :observaciones,
                op_id_ultima_modificacion = :op_id
            WHERE id_egreso_impuesto_empresa = :id_egreso
            RETURNING estado_egreso
            """
        )
        update_mt_stmt = text(
            """
            UPDATE movimiento_tesoreria
            SET estado = 'ANULADO',
                observaciones = :observaciones,
                op_id_ultima_modificacion = :op_id
            WHERE id_movimiento_tesoreria = :id_movimiento_tesoreria
            RETURNING estado
            """
        )
        egreso_row = self.db.execute(
            update_egreso_stmt,
            {
                "id_egreso": id_egreso,
                "observaciones": observaciones,
                "op_id": op_id,
            },
        ).mappings().one()
        mt_row = self.db.execute(
            update_mt_stmt,
            {
                "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
                "observaciones": observaciones,
                "op_id": op_id,
            },
        ).mappings().one()

        return {
            "id_egreso_impuesto_empresa": row["id_egreso_impuesto_empresa"],
            "id_comprobante_impuesto": row["id_comprobante_impuesto"],
            "id_movimiento_tesoreria": row["id_movimiento_tesoreria"],
            "estado_egreso": egreso_row["estado_egreso"],
            "estado_movimiento_tesoreria": mt_row["estado"],
        }

    def get_obligados_activos_by_obligacion(
        self, id_obligacion_financiera: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                id_obligacion_obligado,
                id_persona,
                rol_obligado,
                porcentaje_responsabilidad
            FROM obligacion_obligado
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND deleted_at IS NULL
            ORDER BY id_obligacion_obligado ASC
            """
        )
        rows = self.db.execute(
            stmt, {"id_obligacion_financiera": id_obligacion_financiera}
        ).mappings().all()
        return [dict(row) for row in rows]

    def registrar_pago_externo_factura_servicio(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
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
                :fecha_movimiento, :tipo_movimiento, :importe, :signo,
                :estado_movimiento, :observaciones
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
                origen_automatico_o_manual, observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_movimiento_financiero, :id_obligacion_financiera,
                :id_composicion_obligacion, :fecha_aplicacion,
                :tipo_aplicacion, :orden_aplicacion, :importe_aplicado,
                :origen_automatico_o_manual, :observaciones
            )
            RETURNING id_aplicacion_financiera
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

        mov_row = self.db.execute(
            mov_stmt,
            {
                "uid_global": values["uid_global_movimiento"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "fecha_movimiento": datetime.combine(
                    values["fecha_pago"], datetime.min.time()
                ),
                "tipo_movimiento": "PAGO_EXTERNO_INFORMADO",
                "importe": values["monto_aplicado"],
                "signo": "CREDITO",
                "estado_movimiento": "APLICADO",
                "observaciones": values["observaciones"],
            },
        ).mappings().one()
        id_movimiento = mov_row["id_movimiento_financiero"]

        self.db.execute(
            aplic_stmt,
            {
                "uid_global": values["uid_global_aplicacion"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_movimiento_financiero": id_movimiento,
                "id_obligacion_financiera": values["id_obligacion_financiera"],
                "id_composicion_obligacion": values["id_composicion_obligacion"],
                "fecha_aplicacion": datetime.combine(
                    values["fecha_pago"], datetime.min.time()
                ),
                "tipo_aplicacion": "PAGO_EXTERNO_INFORMADO",
                "orden_aplicacion": 1,
                "importe_aplicado": values["monto_aplicado"],
                "origen_automatico_o_manual": "MANUAL",
                "observaciones": values["observaciones"],
            },
        ).mappings().one()

        estado_row = self.db.execute(
            estado_stmt,
            {"id": values["id_obligacion_financiera"]},
        ).mappings().one()

        return {
            "id_factura_servicio": values["id_factura_servicio"],
            "id_relacion_generadora": values["id_relacion_generadora"],
            "id_obligacion_financiera": values["id_obligacion_financiera"],
            "id_movimiento_financiero": id_movimiento,
            "monto_ingresado": float(values["monto_ingresado"]),
            "monto_aplicado": float(values["monto_aplicado"]),
            "remanente_no_aplicado": float(values["remanente_no_aplicado"]),
            "estado_obligacion_resultante": estado_row["estado_obligacion"],
            "impacta_caja": False,
            "genera_recibo_interno": False,
        }

    def registrar_egreso_proveedor_factura_servicio(
        self, payload: Any
    ) -> dict[str, Any]:
        values = self._values(payload)
        fecha_movimiento = datetime.combine(values["fecha_pago"], datetime.min.time())
        movimiento_stmt = text(
            """
            INSERT INTO movimiento_tesoreria (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_movimiento_financiero,
                id_cuenta_financiera_origen,
                id_cuenta_financiera_destino,
                tipo_movimiento_tesoreria,
                fecha_movimiento,
                importe,
                estado,
                referencia_externa,
                observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                NULL,
                :id_cuenta_financiera_origen,
                NULL,
                'EGRESO_PROVEEDOR_FACTURA_SERVICIO',
                :fecha_movimiento,
                :importe,
                'REGISTRADO',
                :referencia_externa,
                :observaciones
            )
            RETURNING id_movimiento_tesoreria
            """
        )
        egreso_stmt = text(
            """
            INSERT INTO egreso_proveedor_factura_servicio (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_factura_servicio,
                id_movimiento_tesoreria,
                fecha_pago,
                importe_pagado,
                medio_pago,
                referencia_comprobante,
                estado_egreso,
                observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_factura_servicio,
                :id_movimiento_tesoreria,
                :fecha_pago,
                :importe_pagado,
                :medio_pago,
                :referencia_comprobante,
                'REGISTRADO',
                :observaciones
            )
            RETURNING id_egreso_proveedor_factura_servicio
            """
        )
        mov_row = self.db.execute(
            movimiento_stmt,
            {
                "uid_global": values["uid_global_movimiento_tesoreria"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_cuenta_financiera_origen": values["id_cuenta_financiera_origen"],
                "fecha_movimiento": fecha_movimiento,
                "importe": values["importe_pagado"],
                "referencia_externa": f"FACTURA_SERVICIO:{values['id_factura_servicio']}",
                "observaciones": values["observaciones"],
            },
        ).mappings().one()
        id_movimiento = mov_row["id_movimiento_tesoreria"]

        egreso_row = self.db.execute(
            egreso_stmt,
            {
                "uid_global": values["uid_global_egreso"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_factura_servicio": values["id_factura_servicio"],
                "id_movimiento_tesoreria": id_movimiento,
                "fecha_pago": values["fecha_pago"],
                "importe_pagado": values["importe_pagado"],
                "medio_pago": values["medio_pago"],
                "referencia_comprobante": values["referencia_comprobante"],
                "observaciones": values["observaciones"],
            },
        ).mappings().one()

        return {
            "id_egreso_proveedor_factura_servicio": egreso_row[
                "id_egreso_proveedor_factura_servicio"
            ],
            "id_factura_servicio": values["id_factura_servicio"],
            "id_movimiento_tesoreria": id_movimiento,
            "id_cuenta_financiera_origen": values["id_cuenta_financiera_origen"],
            "fecha_pago": values["fecha_pago"],
            "importe_pagado": float(values["importe_pagado"]),
            "medio_pago": values["medio_pago"],
            "referencia_comprobante": values["referencia_comprobante"],
            "estado_egreso": "REGISTRADO",
            "impacta_tesoreria": True,
            "crea_movimiento_financiero": False,
            "crea_obligacion_financiera": False,
        }

    def registrar_egreso_impuesto_empresa(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        fecha_movimiento = datetime.combine(values["fecha_pago"], datetime.min.time())
        movimiento_stmt = text(
            """
            INSERT INTO movimiento_tesoreria (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_movimiento_financiero,
                id_cuenta_financiera_origen,
                id_cuenta_financiera_destino,
                tipo_movimiento_tesoreria,
                fecha_movimiento,
                importe,
                estado,
                referencia_externa,
                observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                NULL,
                :id_cuenta_financiera_origen,
                NULL,
                'EGRESO_IMPUESTO_EMPRESA',
                :fecha_movimiento,
                :importe,
                'REGISTRADO',
                :referencia_externa,
                :observaciones
            )
            RETURNING id_movimiento_tesoreria
            """
        )
        egreso_stmt = text(
            """
            INSERT INTO egreso_impuesto_empresa (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_comprobante_impuesto,
                id_movimiento_tesoreria,
                fecha_pago,
                importe_pagado,
                medio_pago,
                referencia_comprobante,
                estado_egreso,
                observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_comprobante_impuesto,
                :id_movimiento_tesoreria,
                :fecha_pago,
                :importe_pagado,
                :medio_pago,
                :referencia_comprobante,
                'REGISTRADO',
                :observaciones
            )
            RETURNING id_egreso_impuesto_empresa
            """
        )
        mov_row = self.db.execute(
            movimiento_stmt,
            {
                "uid_global": values["uid_global_movimiento_tesoreria"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_cuenta_financiera_origen": values["id_cuenta_financiera_origen"],
                "fecha_movimiento": fecha_movimiento,
                "importe": values["importe_pagado"],
                "referencia_externa": (
                    f"COMPROBANTE_IMPUESTO:{values['id_comprobante_impuesto']}"
                ),
                "observaciones": values["observaciones"],
            },
        ).mappings().one()
        id_movimiento = mov_row["id_movimiento_tesoreria"]

        egreso_row = self.db.execute(
            egreso_stmt,
            {
                "uid_global": values["uid_global_egreso"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_comprobante_impuesto": values["id_comprobante_impuesto"],
                "id_movimiento_tesoreria": id_movimiento,
                "fecha_pago": values["fecha_pago"],
                "importe_pagado": values["importe_pagado"],
                "medio_pago": values["medio_pago"],
                "referencia_comprobante": values["referencia_comprobante"],
                "observaciones": values["observaciones"],
            },
        ).mappings().one()

        return {
            "id_egreso_impuesto_empresa": egreso_row["id_egreso_impuesto_empresa"],
            "id_comprobante_impuesto": values["id_comprobante_impuesto"],
            "id_movimiento_tesoreria": id_movimiento,
            "id_cuenta_financiera_origen": values["id_cuenta_financiera_origen"],
            "fecha_pago": values["fecha_pago"],
            "importe_pagado": float(values["importe_pagado"]),
            "medio_pago": values["medio_pago"],
            "referencia_comprobante": values["referencia_comprobante"],
            "estado_egreso": "REGISTRADO",
            "impacta_tesoreria": True,
            "crea_movimiento_financiero": False,
            "crea_relacion_generadora": False,
            "crea_obligacion_financiera": False,
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

    def list_pagos_agrupados_persona(self, *, id_persona: int) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                m.codigo_pago_grupo,
                m.uid_pago_grupo,
                MIN(m.fecha_movimiento)::date AS fecha_pago,
                SUM(m.importe) AS monto_total,
                COALESCE(SUM(a.importe_aplicado), 0) AS monto_aplicado,
                COUNT(DISTINCT m.id_movimiento_financiero) AS cantidad_movimientos,
                COUNT(DISTINCT a.id_obligacion_financiera) AS cantidad_obligaciones
            FROM movimiento_financiero m
            JOIN aplicacion_financiera a
              ON a.id_movimiento_financiero = m.id_movimiento_financiero
             AND a.deleted_at IS NULL
            JOIN obligacion_obligado oo
              ON oo.id_obligacion_financiera = a.id_obligacion_financiera
             AND oo.deleted_at IS NULL
            WHERE oo.id_persona = :id_persona
              AND m.tipo_movimiento = 'PAGO'
              AND m.deleted_at IS NULL
              AND m.uid_pago_grupo IS NOT NULL
              AND m.codigo_pago_grupo IS NOT NULL
            GROUP BY m.uid_pago_grupo, m.codigo_pago_grupo
            ORDER BY fecha_pago DESC, m.codigo_pago_grupo DESC
            """
        )
        rows = self.db.execute(stmt, {"id_persona": id_persona}).mappings().all()
        return [dict(r) for r in rows]

    def get_pago_agrupado_by_codigo(self, *, codigo_pago_grupo: str) -> dict[str, Any] | None:
        mov_stmt = text(
            """
            SELECT
                m.id_movimiento_financiero,
                m.uid_pago_grupo,
                m.codigo_pago_grupo,
                m.fecha_movimiento::date AS fecha_pago,
                m.importe,
                m.estado_movimiento
            FROM movimiento_financiero m
            WHERE m.codigo_pago_grupo = :codigo_pago_grupo
              AND m.tipo_movimiento = 'PAGO'
              AND m.deleted_at IS NULL
            ORDER BY m.id_movimiento_financiero ASC
            """
        )
        movimientos = self.db.execute(
            mov_stmt, {"codigo_pago_grupo": codigo_pago_grupo}
        ).mappings().all()
        if not movimientos:
            return None
        ids_mov = [r["id_movimiento_financiero"] for r in movimientos]
        app_stmt = text(
            """
            SELECT
                a.id_aplicacion_financiera,
                a.id_movimiento_financiero,
                a.id_obligacion_financiera,
                a.id_composicion_obligacion,
                a.importe_aplicado,
                CASE
                    WHEN m.estado_movimiento = 'ANULADO'
                      OR a.deleted_at IS NOT NULL THEN 'ANULADO'
                    ELSE o.estado_obligacion
                END AS estado_resultante,
                cf.codigo_concepto_financiero
            FROM aplicacion_financiera a
            JOIN movimiento_financiero m
              ON m.id_movimiento_financiero = a.id_movimiento_financiero
            JOIN obligacion_financiera o ON o.id_obligacion_financiera = a.id_obligacion_financiera
            JOIN composicion_obligacion co ON co.id_composicion_obligacion = a.id_composicion_obligacion
            JOIN concepto_financiero cf ON cf.id_concepto_financiero = co.id_concepto_financiero
            WHERE a.id_movimiento_financiero IN :ids
            ORDER BY a.id_aplicacion_financiera ASC
            """
        ).bindparams(bindparam("ids", expanding=True))
        aplicaciones = self.db.execute(app_stmt, {"ids": ids_mov}).mappings().all()
        estado_pago_grupo = (
            "ANULADO"
            if all(r["estado_movimiento"] == "ANULADO" for r in movimientos)
            else "APLICADO"
        )
        return {
            "codigo_pago_grupo": movimientos[0]["codigo_pago_grupo"],
            "uid_pago_grupo": movimientos[0]["uid_pago_grupo"],
            "fecha_pago": movimientos[0]["fecha_pago"],
            "monto_total": float(sum(r["importe"] for r in movimientos)),
            "monto_aplicado": float(sum(r["importe_aplicado"] for r in aplicaciones)),
            "estado_pago_grupo": estado_pago_grupo,
            "movimientos": [dict(r) for r in movimientos],
            "aplicaciones": [dict(r) for r in aplicaciones],
            "obligaciones_afectadas": sorted({r["id_obligacion_financiera"] for r in aplicaciones}),
        }

    def get_operaciones_posteriores_pago_agrupado(
        self, *, codigo_pago_grupo: str
    ) -> dict[str, Any]:
        contexto_stmt = text(
            """
            WITH grupo_mov AS (
                SELECT id_movimiento_financiero, fecha_movimiento, created_at
                FROM movimiento_financiero
                WHERE codigo_pago_grupo = :codigo_pago_grupo
                  AND tipo_movimiento = 'PAGO'
                  AND deleted_at IS NULL
            ),
            grupo_apps AS (
                SELECT DISTINCT
                    a.id_obligacion_financiera,
                    a.id_composicion_obligacion
                FROM aplicacion_financiera a
                JOIN grupo_mov gm
                  ON gm.id_movimiento_financiero = a.id_movimiento_financiero
                WHERE a.deleted_at IS NULL
            )
            SELECT
                MAX(gm.fecha_movimiento) AS fecha_grupo,
                MAX(gm.id_movimiento_financiero) AS max_movimiento_grupo,
                MAX(gm.created_at) AS created_at_grupo,
                COALESCE(MAX(lp.id_liquidacion_punitorio), 0) AS max_liquidacion_grupo,
                ARRAY_AGG(DISTINCT ga.id_obligacion_financiera)
                    FILTER (WHERE ga.id_obligacion_financiera IS NOT NULL) AS obligaciones,
                ARRAY_AGG(DISTINCT ga.id_composicion_obligacion)
                    FILTER (WHERE ga.id_composicion_obligacion IS NOT NULL) AS composiciones
            FROM grupo_mov gm
            LEFT JOIN grupo_apps ga ON TRUE
            LEFT JOIN liquidacion_punitorio lp
              ON lp.codigo_pago_grupo = :codigo_pago_grupo
             AND lp.deleted_at IS NULL
            """
        )
        contexto = self.db.execute(
            contexto_stmt, {"codigo_pago_grupo": codigo_pago_grupo}
        ).mappings().one()
        if contexto["fecha_grupo"] is None:
            return {
                "tiene_operaciones_posteriores": False,
                "movimientos_posteriores": 0,
                "aplicaciones_posteriores": 0,
                "liquidaciones_punitorio_posteriores": 0,
            }

        obligaciones = contexto["obligaciones"] or []
        composiciones = contexto["composiciones"] or []
        if not obligaciones:
            return {
                "tiene_operaciones_posteriores": False,
                "movimientos_posteriores": 0,
                "aplicaciones_posteriores": 0,
                "liquidaciones_punitorio_posteriores": 0,
            }

        params = {
            "codigo_pago_grupo": codigo_pago_grupo,
            "fecha_grupo": contexto["fecha_grupo"],
            "max_movimiento_grupo": contexto["max_movimiento_grupo"],
            "created_at_grupo": contexto["created_at_grupo"],
            "max_liquidacion_grupo": contexto["max_liquidacion_grupo"],
            "obligaciones": obligaciones,
            "composiciones": composiciones,
        }
        movimientos_stmt = text(
            """
            SELECT COUNT(DISTINCT m.id_movimiento_financiero)
            FROM movimiento_financiero m
            JOIN aplicacion_financiera a
              ON a.id_movimiento_financiero = m.id_movimiento_financiero
             AND a.deleted_at IS NULL
            WHERE m.tipo_movimiento = 'PAGO'
              AND m.estado_movimiento <> 'ANULADO'
              AND m.deleted_at IS NULL
              AND m.codigo_pago_grupo IS DISTINCT FROM :codigo_pago_grupo
              AND a.id_obligacion_financiera IN :obligaciones
              AND (
                    m.fecha_movimiento > :fecha_grupo
                    OR (
                        m.fecha_movimiento = :fecha_grupo
                        AND m.id_movimiento_financiero > :max_movimiento_grupo
                    )
                  )
            """
        ).bindparams(bindparam("obligaciones", expanding=True))
        aplicaciones_stmt = text(
            """
            SELECT COUNT(DISTINCT a.id_aplicacion_financiera)
            FROM aplicacion_financiera a
            JOIN movimiento_financiero m
              ON m.id_movimiento_financiero = a.id_movimiento_financiero
            WHERE a.deleted_at IS NULL
              AND m.deleted_at IS NULL
              AND m.estado_movimiento <> 'ANULADO'
              AND m.codigo_pago_grupo IS DISTINCT FROM :codigo_pago_grupo
              AND a.id_obligacion_financiera IN :obligaciones
              AND (
                    a.id_composicion_obligacion IN :composiciones
                    OR a.id_obligacion_financiera IN :obligaciones
                  )
              AND (
                    a.fecha_aplicacion > :fecha_grupo
                    OR (
                        a.fecha_aplicacion = :fecha_grupo
                        AND m.id_movimiento_financiero > :max_movimiento_grupo
                    )
                  )
            """
        ).bindparams(
            bindparam("obligaciones", expanding=True),
            bindparam("composiciones", expanding=True),
        )
        liquidaciones_stmt = text(
            """
            SELECT COUNT(DISTINCT lp.id_liquidacion_punitorio)
            FROM liquidacion_punitorio lp
            WHERE lp.estado_liquidacion = 'ACTIVA'
              AND lp.deleted_at IS NULL
              AND lp.codigo_pago_grupo IS DISTINCT FROM :codigo_pago_grupo
              AND lp.id_obligacion_financiera IN :obligaciones
              AND (
                    lp.id_composicion_obligacion IN :composiciones
                    OR lp.id_obligacion_financiera IN :obligaciones
                  )
              AND (
                    lp.fecha_fin_calculo > CAST(:fecha_grupo AS date)
                    OR (
                        lp.fecha_fin_calculo = CAST(:fecha_grupo AS date)
                        AND lp.id_liquidacion_punitorio > :max_liquidacion_grupo
                    )
                  )
            """
        ).bindparams(
            bindparam("obligaciones", expanding=True),
            bindparam("composiciones", expanding=True),
        )
        composiciones_stmt = text(
            """
            SELECT COUNT(DISTINCT co.id_composicion_obligacion)
            FROM composicion_obligacion co
            WHERE co.deleted_at IS NULL
              AND co.estado_composicion_obligacion = 'ACTIVA'
              AND co.id_obligacion_financiera IN :obligaciones
              AND co.id_composicion_obligacion NOT IN :composiciones
              AND (
                    co.created_at > :created_at_grupo
                    OR co.updated_at > :created_at_grupo
                  )
            """
        ).bindparams(
            bindparam("obligaciones", expanding=True),
            bindparam("composiciones", expanding=True),
        )

        movimientos = self.db.execute(movimientos_stmt, params).scalar_one()
        aplicaciones = self.db.execute(aplicaciones_stmt, params).scalar_one()
        liquidaciones = self.db.execute(liquidaciones_stmt, params).scalar_one()
        composiciones_posteriores = self.db.execute(
            composiciones_stmt, params
        ).scalar_one()
        return {
            "tiene_operaciones_posteriores": any(
                count > 0
                for count in [
                    movimientos,
                    aplicaciones,
                    liquidaciones,
                    composiciones_posteriores,
                ]
            ),
            "movimientos_posteriores": movimientos,
            "aplicaciones_posteriores": aplicaciones,
            "liquidaciones_punitorio_posteriores": liquidaciones,
            "composiciones_posteriores": composiciones_posteriores,
        }

    def _json_observaciones_reversion(self, observaciones: Any, *, motivo: str) -> str:
        payload: dict[str, Any]
        if observaciones:
            try:
                parsed = json.loads(observaciones)
                payload = parsed if isinstance(parsed, dict) else {"original": observaciones}
            except (TypeError, ValueError):
                payload = {"original": observaciones}
        else:
            payload = {}
        payload["reversion"] = {"motivo": motivo}
        return json.dumps(payload, separators=(",", ":"))

    def revertir_pago_agrupado(
        self,
        *,
        codigo_pago_grupo: str,
        motivo: str,
        id_instalacion: Any,
        op_id: Any,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        mov_stmt = text(
            """
            SELECT
                id_movimiento_financiero,
                estado_movimiento,
                observaciones
            FROM movimiento_financiero
            WHERE codigo_pago_grupo = :codigo_pago_grupo
              AND tipo_movimiento = 'PAGO'
              AND deleted_at IS NULL
            ORDER BY id_movimiento_financiero ASC
            FOR UPDATE
            """
        )
        app_stmt = text(
            """
            SELECT DISTINCT
                a.id_aplicacion_financiera,
                a.id_obligacion_financiera,
                a.id_composicion_obligacion,
                a.observaciones
            FROM aplicacion_financiera a
            WHERE a.id_movimiento_financiero IN :ids
              AND a.deleted_at IS NULL
            ORDER BY a.id_aplicacion_financiera ASC
            """
        ).bindparams(bindparam("ids", expanding=True))
        liquidaciones_stmt = text(
            """
            SELECT
                id_liquidacion_punitorio,
                id_obligacion_financiera,
                id_composicion_obligacion,
                importe_liquidado
            FROM liquidacion_punitorio
            WHERE codigo_pago_grupo = :codigo_pago_grupo
              AND deleted_at IS NULL
              AND estado_liquidacion = 'ACTIVA'
            ORDER BY id_liquidacion_punitorio ASC
            FOR UPDATE
            """
        )
        update_app_stmt = text(
            """
            UPDATE aplicacion_financiera
            SET deleted_at = :now,
                updated_at = :now,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id,
                observaciones = :observaciones
            WHERE id_aplicacion_financiera = :id_aplicacion_financiera
              AND deleted_at IS NULL
            """
        )
        update_mov_stmt = text(
            """
            UPDATE movimiento_financiero
            SET estado_movimiento = 'ANULADO',
                updated_at = :now,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id,
                observaciones = :observaciones
            WHERE id_movimiento_financiero = :id_movimiento_financiero
              AND deleted_at IS NULL
            """
        )
        anular_liq_stmt = text(
            """
            UPDATE liquidacion_punitorio
            SET estado_liquidacion = 'ANULADA',
                updated_at = :now,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id
            WHERE id_liquidacion_punitorio = :id_liquidacion_punitorio
              AND estado_liquidacion = 'ACTIVA'
              AND deleted_at IS NULL
            """
        )
        reducir_comp_stmt = text(
            """
            UPDATE composicion_obligacion
            SET importe_componente = GREATEST(
                    0,
                    importe_componente - :importe_liquidado
                ),
                updated_at = :now,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id
            WHERE id_composicion_obligacion = :id_composicion_obligacion
              AND deleted_at IS NULL
            """
        )
        estado_stmt = text(
            """
            UPDATE obligacion_financiera
            SET estado_obligacion = CASE
                    WHEN saldo_pendiente = 0 THEN 'CANCELADA'
                    WHEN importe_cancelado_acumulado > 0 THEN 'PARCIALMENTE_CANCELADA'
                    WHEN fecha_vencimiento IS NOT NULL
                         AND fecha_vencimiento < CURRENT_DATE THEN 'VENCIDA'
                    ELSE 'EMITIDA'
                END,
                updated_at = :now,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')
            RETURNING id_obligacion_financiera, estado_obligacion, saldo_pendiente
            """
        )

        try:
            movimientos = self.db.execute(
                mov_stmt, {"codigo_pago_grupo": codigo_pago_grupo}
            ).mappings().all()
            if not movimientos:
                raise ValueError("NOT_FOUND_PAGO")

            ids_mov = [m["id_movimiento_financiero"] for m in movimientos]
            if all(m["estado_movimiento"] == "ANULADO" for m in movimientos):
                obligaciones_ids = sorted(
                    {
                        row["id_obligacion_financiera"]
                        for row in self.db.execute(
                            text(
                                """
                                SELECT DISTINCT id_obligacion_financiera
                                FROM aplicacion_financiera
                                WHERE id_movimiento_financiero IN :ids
                                """
                            ).bindparams(bindparam("ids", expanding=True)),
                            {"ids": ids_mov},
                        ).mappings()
                    }
                )
                return {
                    "codigo_pago_grupo": codigo_pago_grupo,
                    "estado_reversion": "YA_ANULADO",
                    "movimientos_anulados": 0,
                    "aplicaciones_anuladas": 0,
                    "liquidaciones_punitorio_anuladas": 0,
                    "importe_punitorio_revertido": 0.0,
                    "obligaciones_afectadas": obligaciones_ids,
                    "estados_obligaciones": [],
                }

            aplicaciones = self.db.execute(app_stmt, {"ids": ids_mov}).mappings().all()
            liquidaciones = self.db.execute(
                liquidaciones_stmt, {"codigo_pago_grupo": codigo_pago_grupo}
            ).mappings().all()

            if not aplicaciones and not liquidaciones:
                obligaciones_ids = sorted(
                    {
                        row["id_obligacion_financiera"]
                        for row in self.db.execute(
                            text(
                                """
                                SELECT DISTINCT id_obligacion_financiera
                                FROM aplicacion_financiera
                                WHERE id_movimiento_financiero IN :ids
                                """
                            ).bindparams(bindparam("ids", expanding=True)),
                            {"ids": ids_mov},
                        ).mappings()
                    }
                )
                return {
                    "codigo_pago_grupo": codigo_pago_grupo,
                    "estado_reversion": "YA_ANULADO",
                    "movimientos_anulados": 0,
                    "aplicaciones_anuladas": 0,
                    "liquidaciones_punitorio_anuladas": 0,
                    "importe_punitorio_revertido": 0.0,
                    "obligaciones_afectadas": obligaciones_ids,
                    "estados_obligaciones": [],
                }

            obligaciones_ids = {
                a["id_obligacion_financiera"] for a in aplicaciones
            } | {l["id_obligacion_financiera"] for l in liquidaciones}

            for aplicacion in aplicaciones:
                self.db.execute(
                    update_app_stmt,
                    {
                        "id_aplicacion_financiera": aplicacion["id_aplicacion_financiera"],
                        "now": now,
                        "id_instalacion": id_instalacion,
                        "op_id": op_id,
                        "observaciones": self._json_observaciones_reversion(
                            aplicacion["observaciones"], motivo=motivo
                        ),
                    },
                )

            importe_punitorio_revertido = Decimal("0")
            for liquidacion in liquidaciones:
                importe = Decimal(str(liquidacion["importe_liquidado"]))
                self.db.execute(
                    anular_liq_stmt,
                    {
                        "id_liquidacion_punitorio": liquidacion[
                            "id_liquidacion_punitorio"
                        ],
                        "now": now,
                        "id_instalacion": id_instalacion,
                        "op_id": op_id,
                    },
                )
                self.db.execute(
                    reducir_comp_stmt,
                    {
                        "id_composicion_obligacion": liquidacion[
                            "id_composicion_obligacion"
                        ],
                        "importe_liquidado": importe,
                        "now": now,
                        "id_instalacion": id_instalacion,
                        "op_id": op_id,
                    },
                )
                importe_punitorio_revertido += importe

            for movimiento in movimientos:
                self.db.execute(
                    update_mov_stmt,
                    {
                        "id_movimiento_financiero": movimiento[
                            "id_movimiento_financiero"
                        ],
                        "now": now,
                        "id_instalacion": id_instalacion,
                        "op_id": op_id,
                        "observaciones": self._json_observaciones_reversion(
                            movimiento["observaciones"], motivo=motivo
                        ),
                    },
                )

            estados = []
            for id_obligacion in sorted(obligaciones_ids):
                estado = self.db.execute(
                    estado_stmt,
                    {
                        "id_obligacion_financiera": id_obligacion,
                        "now": now,
                        "id_instalacion": id_instalacion,
                        "op_id": op_id,
                    },
                ).mappings().one_or_none()
                if estado is not None:
                    estados.append(dict(estado))

            self.db.commit()
            return {
                "codigo_pago_grupo": codigo_pago_grupo,
                "estado_reversion": "ANULADO",
                "movimientos_anulados": len(movimientos),
                "aplicaciones_anuladas": len(aplicaciones),
                "liquidaciones_punitorio_anuladas": len(liquidaciones),
                "importe_punitorio_revertido": float(importe_punitorio_revertido),
                "obligaciones_afectadas": sorted(obligaciones_ids),
                "estados_obligaciones": estados,
            }
        except Exception:
            self.db.rollback()
            raise

    def get_recibo_pago_agrupado(
        self, *, codigo_pago_grupo: str
    ) -> dict[str, Any] | None:
        mov_stmt = text(
            """
            SELECT
                m.id_movimiento_financiero,
                m.uid_pago_grupo,
                m.codigo_pago_grupo,
                m.fecha_movimiento::date AS fecha_pago,
                m.importe,
                m.estado_movimiento,
                m.observaciones
            FROM movimiento_financiero m
            WHERE m.codigo_pago_grupo = :codigo_pago_grupo
              AND m.tipo_movimiento = 'PAGO'
              AND m.deleted_at IS NULL
            ORDER BY m.id_movimiento_financiero ASC
            """
        )
        movimientos = self.db.execute(
            mov_stmt, {"codigo_pago_grupo": codigo_pago_grupo}
        ).mappings().all()
        if not movimientos:
            return None

        ids_mov = [r["id_movimiento_financiero"] for r in movimientos]
        detalle_stmt = text(
            """
            SELECT
                a.id_movimiento_financiero,
                a.id_obligacion_financiera,
                o.periodo_desde,
                o.periodo_hasta,
                cf.codigo_concepto_financiero,
                a.importe_aplicado,
                CASE
                    WHEN m.estado_movimiento = 'ANULADO'
                      OR a.deleted_at IS NOT NULL THEN 'ANULADO'
                    ELSE o.estado_obligacion
                END AS estado_resultante,
                oo.id_persona,
                p.nombre,
                p.apellido,
                p.razon_social
            FROM aplicacion_financiera a
            JOIN movimiento_financiero m
              ON m.id_movimiento_financiero = a.id_movimiento_financiero
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = a.id_obligacion_financiera
             AND o.deleted_at IS NULL
            JOIN composicion_obligacion co
              ON co.id_composicion_obligacion = a.id_composicion_obligacion
             AND co.deleted_at IS NULL
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = co.id_concepto_financiero
             AND cf.deleted_at IS NULL
            LEFT JOIN obligacion_obligado oo
              ON oo.id_obligacion_financiera = a.id_obligacion_financiera
             AND oo.deleted_at IS NULL
            LEFT JOIN persona p
              ON p.id_persona = oo.id_persona
             AND p.deleted_at IS NULL
            WHERE a.id_movimiento_financiero IN :ids
            ORDER BY
                a.id_movimiento_financiero ASC,
                a.orden_aplicacion ASC,
                a.id_aplicacion_financiera ASC
            """
        ).bindparams(bindparam("ids", expanding=True))
        detalle_rows = self.db.execute(detalle_stmt, {"ids": ids_mov}).mappings().all()

        resumen = None
        for mov in movimientos:
            if not mov["observaciones"]:
                continue
            try:
                parsed = json.loads(mov["observaciones"])
            except (TypeError, ValueError):
                continue
            if parsed.get("tipo") == "pago_persona":
                resumen = parsed
                break

        id_persona = (
            int(resumen["id_persona"])
            if resumen is not None and "id_persona" in resumen
            else (detalle_rows[0]["id_persona"] if detalle_rows else None)
        )
        persona_row = next(
            (r for r in detalle_rows if id_persona is not None and r["id_persona"] == id_persona),
            detalle_rows[0] if detalle_rows else None,
        )
        descripcion_persona = None
        if persona_row is not None:
            razon_social = persona_row["razon_social"]
            nombre = persona_row["nombre"]
            apellido = persona_row["apellido"]
            descripcion_persona = (
                razon_social
                if razon_social
                else " ".join(p for p in [nombre, apellido] if p).strip() or None
            )

        detalle = [
            {
                "id_movimiento_financiero": row["id_movimiento_financiero"],
                "id_obligacion_financiera": row["id_obligacion_financiera"],
                "periodo_desde": row["periodo_desde"],
                "periodo_hasta": row["periodo_hasta"],
                "codigo_concepto_financiero": row["codigo_concepto_financiero"],
                "importe_aplicado": float(row["importe_aplicado"]),
                "estado_resultante": row["estado_resultante"],
            }
            for row in detalle_rows
        ]

        totales_dec: dict[str, Decimal] = defaultdict(Decimal)
        for row in detalle_rows:
            totales_dec[row["codigo_concepto_financiero"]] += Decimal(
                str(row["importe_aplicado"])
            )
        totales_por_concepto = [
            {
                "codigo_concepto_financiero": codigo,
                "importe_aplicado": float(importe),
            }
            for codigo, importe in sorted(totales_dec.items())
        ]

        monto_total = (
            Decimal(str(resumen["monto_ingresado"]))
            if resumen is not None and "monto_ingresado" in resumen
            else sum((Decimal(str(r["importe"])) for r in movimientos), Decimal("0"))
        )
        monto_aplicado = (
            Decimal(str(resumen["monto_aplicado"]))
            if resumen is not None and "monto_aplicado" in resumen
            else sum(
                (Decimal(str(r["importe_aplicado"])) for r in detalle_rows),
                Decimal("0"),
            )
        )
        remanente = (
            Decimal(str(resumen["remanente"]))
            if resumen is not None and "remanente" in resumen
            else max(monto_total - monto_aplicado, Decimal("0"))
        )

        estado_recibo = (
            "ANULADO"
            if all(m["estado_movimiento"] == "ANULADO" for m in movimientos)
            else "BORRADOR/CONSULTA"
        )

        return {
            "codigo_pago_grupo": movimientos[0]["codigo_pago_grupo"],
            "uid_pago_grupo": movimientos[0]["uid_pago_grupo"],
            "fecha_pago": (
                date.fromisoformat(resumen["fecha_pago"])
                if resumen is not None and "fecha_pago" in resumen
                else movimientos[0]["fecha_pago"]
            ),
            "id_persona": id_persona,
            "persona_nombre": descripcion_persona,
            "descripcion_persona": descripcion_persona,
            "monto_total": float(monto_total),
            "monto_aplicado": float(monto_aplicado),
            "remanente": float(remanente),
            "detalle": detalle,
            "totales_por_concepto": totales_por_concepto,
            "estado_recibo": estado_recibo,
            "leyenda": (
                "Vista de consulta sin valor fiscal. No genera comprobante "
                "persistido ni modifica saldos."
            ),
        }

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

    def registrar_liquidacion_punitorio(
        self,
        *,
        uid_global: str,
        now: Any,
        id_instalacion: Any,
        op_id: Any,
        id_obligacion_financiera: int,
        id_composicion_obligacion: int,
        uid_pago_grupo: str,
        codigo_pago_grupo: str,
        fecha_vencimiento: Any,
        fecha_inicio_calculo: Any,
        fecha_fin_calculo: Any,
        base_morable: Decimal,
        tasa_diaria: Decimal,
        dias_calculados: int,
        importe_liquidado: Decimal,
    ) -> dict[str, Any]:
        stmt = text(
            """
            INSERT INTO liquidacion_punitorio (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_obligacion_financiera, id_composicion_obligacion,
                uid_pago_grupo, codigo_pago_grupo,
                fecha_vencimiento, fecha_inicio_calculo, fecha_fin_calculo,
                base_morable, tasa_diaria, dias_calculados, importe_liquidado,
                estado_liquidacion
            )
            VALUES (
                :uid_global, 1, :created_at, :updated_at,
                :id_instalacion, :id_instalacion,
                :op_id, :op_id,
                :id_obligacion_financiera, :id_composicion_obligacion,
                :uid_pago_grupo, :codigo_pago_grupo,
                :fecha_vencimiento, :fecha_inicio_calculo, :fecha_fin_calculo,
                :base_morable, :tasa_diaria, :dias_calculados, :importe_liquidado,
                'ACTIVA'
            )
            RETURNING id_liquidacion_punitorio
            """
        )
        row = self.db.execute(
            stmt,
            {
                "uid_global": uid_global,
                "created_at": now,
                "updated_at": now,
                "id_instalacion": id_instalacion,
                "op_id": op_id,
                "id_obligacion_financiera": id_obligacion_financiera,
                "id_composicion_obligacion": id_composicion_obligacion,
                "uid_pago_grupo": uid_pago_grupo,
                "codigo_pago_grupo": codigo_pago_grupo,
                "fecha_vencimiento": fecha_vencimiento,
                "fecha_inicio_calculo": fecha_inicio_calculo,
                "fecha_fin_calculo": fecha_fin_calculo,
                "base_morable": base_morable,
                "tasa_diaria": tasa_diaria,
                "dias_calculados": dias_calculados,
                "importe_liquidado": importe_liquidado,
            },
        ).mappings().one()
        return dict(row)

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
                uid_pago_grupo, codigo_pago_grupo,
                fecha_movimiento, tipo_movimiento, importe, signo, estado_movimiento,
                observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :uid_pago_grupo, :codigo_pago_grupo,
                :fecha_movimiento, :tipo_movimiento, :importe, :signo, :estado_movimiento,
                :observaciones
            )
            RETURNING id_movimiento_financiero, uid_pago_grupo, codigo_pago_grupo
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
                        "uid_pago_grupo": pv["uid_pago_grupo"],
                        "codigo_pago_grupo": pv["codigo_pago_grupo"],
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
                        "uid_pago_grupo": mov_row["uid_pago_grupo"],
                        "codigo_pago_grupo": mov_row["codigo_pago_grupo"],
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
                o.id_relacion_generadora,
                o.fecha_vencimiento,
                o.saldo_pendiente,
                oo.porcentaje_responsabilidad,
                (
                    SELECT c.id_concepto_financiero
                    FROM composicion_obligacion c
                    JOIN concepto_financiero cf
                      ON cf.id_concepto_financiero = c.id_concepto_financiero
                    WHERE c.id_obligacion_financiera = o.id_obligacion_financiera
                      AND c.estado_composicion_obligacion = 'ACTIVA'
                      AND c.deleted_at IS NULL
                      AND c.saldo_componente > 0
                      AND cf.deleted_at IS NULL
                      AND cf.aplica_punitorio = true
                    ORDER BY c.orden_composicion ASC, c.id_composicion_obligacion ASC
                    LIMIT 1
                ) AS id_concepto_punitorio_base
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

    def resolve_parametro_punitorio(
        self,
        *,
        fecha_referencia: date,
        id_relacion_generadora: int | None = None,
        id_concepto_financiero: int | None = None,
    ) -> ResolucionMora:
        """
        Resuelve parametros persistidos de punitorio por prioridad V1:
        RELACION_GENERADORA > CONCEPTO > GLOBAL > defaults tecnicos.
        """
        table_exists = self.db.execute(
            text("SELECT to_regclass('public.parametro_punitorio')")
        ).scalar_one_or_none()
        if table_exists is None:
            return resolver_mora_params()

        params: dict[str, Any] = {"fecha_referencia": fecha_referencia}
        branches: list[str] = []

        if id_relacion_generadora is not None:
            branches.append(
                """
                SELECT tasa_diaria, dias_gracia, fecha_desde, 1 AS prioridad
                FROM parametro_punitorio
                WHERE alcance_tipo = 'RELACION_GENERADORA'
                  AND id_relacion_generadora = :id_relacion_generadora
                  AND deleted_at IS NULL
                  AND estado_parametro = 'ACTIVO'
                  AND fecha_desde <= :fecha_referencia
                  AND (fecha_hasta IS NULL OR fecha_hasta >= :fecha_referencia)
                """
            )
            params["id_relacion_generadora"] = id_relacion_generadora

        if id_concepto_financiero is not None:
            branches.append(
                """
                SELECT tasa_diaria, dias_gracia, fecha_desde, 2 AS prioridad
                FROM parametro_punitorio
                WHERE alcance_tipo = 'CONCEPTO'
                  AND id_concepto_financiero = :id_concepto_financiero
                  AND deleted_at IS NULL
                  AND estado_parametro = 'ACTIVO'
                  AND fecha_desde <= :fecha_referencia
                  AND (fecha_hasta IS NULL OR fecha_hasta >= :fecha_referencia)
                """
            )
            params["id_concepto_financiero"] = id_concepto_financiero

        branches.append(
            """
            SELECT tasa_diaria, dias_gracia, fecha_desde, 3 AS prioridad
            FROM parametro_punitorio
            WHERE alcance_tipo = 'GLOBAL'
              AND id_relacion_generadora IS NULL
              AND id_concepto_financiero IS NULL
              AND deleted_at IS NULL
              AND estado_parametro = 'ACTIVO'
              AND fecha_desde <= :fecha_referencia
              AND (fecha_hasta IS NULL OR fecha_hasta >= :fecha_referencia)
            """
        )

        stmt = text(
            f"""
            SELECT tasa_diaria, dias_gracia
            FROM (
                {" UNION ALL ".join(branches)}
            ) p
            ORDER BY prioridad ASC, fecha_desde DESC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, params).mappings().one_or_none()
        if row is None:
            return resolver_mora_params()

        return ResolucionMora(
            tasa_diaria=Decimal(str(row["tasa_diaria"])),
            dias_gracia=int(row["dias_gracia"]),
        )

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
        def _grupo_por_origen(tipo_origen: str, codigos: set[str]) -> str:
            tipo = tipo_origen.upper()
            if tipo == "CONTRATO_ALQUILER":
                return "LOCATIVO"
            if tipo in {"VENTA", "RESERVA_VENTA", "PLAN_VENTA"}:
                return "VENTA"
            if tipo in {
                "FACTURA_SERVICIO",
                "LIQUIDACION_RECUPERO",
                "LIQUIDACION_IMPUESTO_TRASLADADO",
            }:
                return "TRASLADADOS"
            if codigos.intersection(
                {
                    "SERVICIO_TRASLADADO",
                    "SERVICIO_RECUPERADO",
                    "EXPENSA_TRASLADADA",
                    "IMPUESTO_TRASLADADO",
                }
            ):
                return "TRASLADADOS"
            return "OTROS"

        filters = [
            "oo.id_persona = :id_persona",
            "oo.deleted_at IS NULL",
            "o.deleted_at IS NULL",
            "rg.deleted_at IS NULL",
        ]
        params: dict[str, Any] = {"id_persona": id_persona}

        if estado is not None:
            filters.append("o.estado_obligacion = :estado")
            params["estado"] = estado.strip().upper()
        else:
            filters.append("o.estado_obligacion NOT IN ('ANULADA', 'REEMPLAZADA')")
            filters.append(
                "NOT (o.estado_obligacion = 'CANCELADA' AND o.saldo_pendiente <= 0)"
            )
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
                rg.descripcion,
                o.fecha_emision,
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
        ids = [row["id_obligacion_financiera"] for row in rows]
        comps_by_ob: dict[int, list[dict[str, Any]]] = defaultdict(list)
        if ids:
            comp_stmt = text(
                """
                SELECT
                    c.id_composicion_obligacion,
                    c.id_obligacion_financiera,
                    cf.codigo_concepto_financiero,
                    c.importe_componente,
                    c.saldo_componente,
                    c.estado_composicion_obligacion
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
            for comp in comp_rows:
                comps_by_ob[comp["id_obligacion_financiera"]].append(
                    {
                        "id_composicion_obligacion": comp[
                            "id_composicion_obligacion"
                        ],
                        "codigo_concepto_financiero": comp[
                            "codigo_concepto_financiero"
                        ],
                        "importe_componente": float(comp["importe_componente"]),
                        "saldo_componente": float(comp["saldo_componente"]),
                        "estado_composicion_obligacion": comp[
                            "estado_composicion_obligacion"
                        ],
                    }
                )

        obligaciones = []
        saldo_total = Decimal("0")
        saldo_vencido = Decimal("0")
        saldo_futuro = Decimal("0")
        mora_total = Decimal("0")
        grupos_map: dict[str, dict[str, Any]] = {}
        grupo_saldos = {
            "LOCATIVO": Decimal("0"),
            "VENTA": Decimal("0"),
            "TRASLADADOS": Decimal("0"),
            "OTROS": Decimal("0"),
        }

        for row in rows:
            saldo = Decimal(str(row["saldo_pendiente"]))
            pct = Decimal(str(row["porcentaje_responsabilidad"]))
            composiciones = comps_by_ob[row["id_obligacion_financiera"]]
            codigos = {
                str(comp["codigo_concepto_financiero"]).upper()
                for comp in composiciones
            }
            grupo = _grupo_por_origen(str(row["tipo_origen"]), codigos)

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

            obligacion_item = {
                "id_obligacion_financiera": row["id_obligacion_financiera"],
                "id_relacion_generadora": row["id_relacion_generadora"],
                "tipo_origen": str(row["tipo_origen"]).upper(),
                "id_origen": row["id_origen"],
                "fecha_emision": row["fecha_emision"],
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
                "composiciones": composiciones,
            }
            obligaciones.append(obligacion_item)

            grupo_saldos[grupo] += saldo
            grupo_data = grupos_map.setdefault(
                grupo,
                {"grupo_origen_deuda": grupo, "saldo_total": Decimal("0"), "relaciones": {}},
            )
            grupo_data["saldo_total"] += saldo
            relaciones = grupo_data["relaciones"]
            relacion_data = relaciones.setdefault(
                row["id_relacion_generadora"],
                {
                    "id_relacion_generadora": row["id_relacion_generadora"],
                    "tipo_origen": str(row["tipo_origen"]).upper(),
                    "id_origen": row["id_origen"],
                    "descripcion_origen": row["descripcion"],
                    "saldo_total": Decimal("0"),
                    "obligaciones": [],
                },
            )
            relacion_data["saldo_total"] += saldo
            relacion_data["obligaciones"].append(
                {
                    "id_obligacion_financiera": row["id_obligacion_financiera"],
                    "estado_obligacion": row["estado_obligacion"],
                    "fecha_emision": row["fecha_emision"],
                    "fecha_vencimiento": fv,
                    "periodo_desde": row["periodo_desde"],
                    "periodo_hasta": row["periodo_hasta"],
                    "saldo_pendiente": float(saldo),
                    "composiciones": composiciones,
                }
            )

        total_con_mora_res = (saldo_total + mora_total).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        grupos_deuda = []
        for grupo in ("LOCATIVO", "VENTA", "TRASLADADOS", "OTROS"):
            if grupo not in grupos_map:
                continue
            grupo_data = grupos_map[grupo]
            relaciones = []
            for relacion in grupo_data["relaciones"].values():
                relaciones.append(
                    {
                        **relacion,
                        "saldo_total": float(relacion["saldo_total"]),
                        "cantidad_obligaciones": len(relacion["obligaciones"]),
                    }
                )
            grupos_deuda.append(
                {
                    "grupo_origen_deuda": grupo,
                    "saldo_total": float(grupo_data["saldo_total"]),
                    "relaciones": relaciones,
                }
            )

        return {
            "id_persona": id_persona,
            "fecha_corte": fecha_corte,
            "resumen": {
                "saldo_total": float(saldo_total),
                "saldo_pendiente_total": float(saldo_total),
                "saldo_vencido": float(saldo_vencido),
                "saldo_futuro": float(saldo_futuro),
                "mora_calculada": float(mora_total),
                "total_con_mora": float(total_con_mora_res),
                "saldo_locativo": float(grupo_saldos["LOCATIVO"]),
                "saldo_venta": float(grupo_saldos["VENTA"]),
                "saldo_trasladados": float(grupo_saldos["TRASLADADOS"]),
                "saldo_otros": float(grupo_saldos["OTROS"]),
            },
            "grupos_deuda": grupos_deuda,
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
