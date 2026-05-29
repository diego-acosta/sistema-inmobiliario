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
            return {field: getattr(payload, field) for field in payload.__dataclass_fields__}
        if isinstance(payload, dict):
            return payload
        return vars(payload)

    def get_venta_minima(self, id_venta: int) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_venta,
                estado_venta,
                monto_total,
                moneda,
                deleted_at
            FROM venta
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(stmt, {"id_venta": id_venta}).mappings().one_or_none()
        return dict(row) if row else None

    def get_plan_pago_venta_vivo(self, id_venta: int) -> dict[str, Any] | None:
        stmt = text(
            """
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
            """
        )
        row = self.db.execute(stmt, {"id_venta": id_venta}).mappings().one_or_none()
        return dict(row) if row else None

    def upsert_plan_pago_venta_borrador(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        existing = self.get_plan_pago_venta_vivo(values["id_venta"])
        if existing is not None:
            stmt = text(
                """
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
                """
            )
            row = self.db.execute(
                stmt, {**values, "id_plan_pago_venta": existing["id_plan_pago_venta"]}
            ).mappings().one()
            return dict(row)

        stmt = text(
            """
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
            """
        )
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
        stmt = text(
            """
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
            """
        )
        row = self.db.execute(
            stmt,
            {
                "id_plan_pago_venta": id_plan_pago_venta,
                "updated_at": updated_at,
                "id_instalacion_ultima_modificacion": id_instalacion_ultima_modificacion,
                "op_id_ultima_modificacion": op_id_ultima_modificacion,
            },
        ).mappings().one()
        return dict(row)

    def get_or_create_relacion_generadora(self, payload: Any) -> dict[str, Any]:
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
            """
        )
        row = self.db.execute(stmt, values).mappings().one()
        return dict(row)

    def get_or_create_generacion_cronograma(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text(
            """
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
            """
        )
        row = self.db.execute(stmt, values).mappings().one()
        return dict(row)

    def get_or_create_plan_pago_venta_bloque(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text(
            """
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
            """
        )
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
        if self._normalize_upper_or_none(bloque.get("metodo_liquidacion")) != self._normalize_upper_or_none(
            expected.get("metodo_liquidacion")
        ):
            incompatible.append("metodo_liquidacion")
        if self._normalize_tasa_or_none(
            bloque.get("tasa_interes_directo_periodica")
        ) != self._normalize_tasa_or_none(expected.get("tasa_interes_directo_periodica")):
            incompatible.append("tasa_interes_directo_periodica")
        if self._normalize_int_or_none(bloque.get("cantidad_periodos")) != self._normalize_int_or_none(
            expected.get("cantidad_periodos")
        ):
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
        stmt = text(
            """
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
            """
        )
        row = self.db.execute(stmt, values).mappings().one()
        indexacion = dict(row)
        self._ensure_plan_pago_venta_bloque_indexacion_compatible(indexacion, values)
        return indexacion

    def get_plan_pago_venta_bloque_indexacion(
        self, id_plan_pago_venta_bloque: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
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
            """
        )
        row = self.db.execute(
            stmt, {"id_plan_pago_venta_bloque": id_plan_pago_venta_bloque}
        ).mappings().one_or_none()
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

    def get_plan_pago_venta_bloques(
        self, id_plan_pago_venta: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
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
            """
        )
        rows = self.db.execute(
            stmt, {"id_plan_pago_venta": id_plan_pago_venta}
        ).mappings().all()
        return [dict(row) for row in rows]

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

    def get_compradores_financieros_venta(
        self, id_venta: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                rpr.id_relacion_persona_rol,
                rpr.id_persona,
                rp.codigo_rol
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
            """
        )
        rows = self.db.execute(stmt, {"id_venta": id_venta}).mappings().all()
        return [dict(row) for row in rows]

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
                return self._set_obligacion_plan_pago_venta_bloque(
                    id_obligacion_financiera=existing["id_obligacion_financiera"],
                    id_plan_pago_venta_bloque=expected_bloque,
                    updated_at=values["updated_at"],
                    id_instalacion_ultima_modificacion=values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    op_id_ultima_modificacion=values["op_id_ultima_modificacion"],
                )
            if (
                existing_bloque is not None
                and expected_bloque is not None
                and existing_bloque != expected_bloque
            ):
                raise ValueError(
                    "OBLIGACION_PLAN_PAGO_VENTA_BLOQUE_INCOMPATIBLE:"
                    f"{values['clave_funcional_origen']}"
                )
            return existing

        ob_stmt = text(
            """
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
            """
        )
        ob_row = self.db.execute(ob_stmt, values).mappings().one_or_none()
        if ob_row is None:
            return self._get_obligacion_by_clave(
                id_relacion_generadora=values["id_relacion_generadora"],
                clave_funcional_origen=values["clave_funcional_origen"],
            )

        obligacion = dict(ob_row)
        self._create_composicion(values, obligacion["id_obligacion_financiera"])
        self._create_obligado(values, obligacion["id_obligacion_financiera"])
        return obligacion

    def get_obligaciones_cronograma_by_claves(
        self,
        *,
        id_relacion_generadora: int,
        claves_funcionales: list[str],
    ) -> list[dict[str, Any]]:
        if not claves_funcionales:
            return []
        stmt = text(
            """
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
            """
        )
        rows = self.db.execute(
            stmt,
            {
                "id_relacion_generadora": id_relacion_generadora,
                "claves_funcionales": claves_funcionales,
            },
        ).mappings().all()
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
        stmt = text(
            """
            UPDATE obligacion_financiera
            SET
                id_plan_pago_venta_bloque = :id_plan_pago_venta_bloque,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_obligacion_financiera = :id_obligacion_financiera
              AND deleted_at IS NULL
              AND id_plan_pago_venta_bloque IS NULL
            """
        )
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
        stmt = text(
            """
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
            """
        )
        row = self.db.execute(
            stmt, {"id_obligacion_financiera": id_obligacion_financiera}
        ).mappings().one()
        return dict(row)

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
        stmt = text(
            """
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
            """
        )
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

    def _create_obligado(
        self, values: dict[str, Any], id_obligacion_financiera: int
    ) -> None:
        stmt = text(
            """
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
                :id_persona_obligado,
                :rol_obligado,
                100.00
            )
            """
        )
        self.db.execute(
            stmt,
            {
                **values,
                "id_obligacion_financiera": id_obligacion_financiera,
            },
        )
