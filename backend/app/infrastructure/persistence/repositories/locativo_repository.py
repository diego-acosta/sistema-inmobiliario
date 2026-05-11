from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.application.common.outbox import OutboxEventPayload
from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository


class LocativoRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def inmueble_exists(self, id_inmueble: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM inmueble
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(statement, {"id_inmueble": id_inmueble}).scalar_one_or_none()
            is not None
        )

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM unidad_funcional
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(
                statement, {"id_unidad_funcional": id_unidad_funcional}
            ).scalar_one_or_none()
            is not None
        )

    def persona_exists(self, id_persona: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM persona
            WHERE id_persona = :id_persona
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(statement, {"id_persona": id_persona}).scalar_one_or_none()
            is not None
        )

    def rol_participacion_exists(self, id_rol_participacion: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM rol_participacion
            WHERE id_rol_participacion = :id_rol_participacion
              AND deleted_at IS NULL
              AND estado_rol = 'ACTIVO'
            """
        )
        return (
            self.db.execute(
                statement, {"id_rol_participacion": id_rol_participacion}
            ).scalar_one_or_none()
            is not None
        )

    def _get_objetos_for_contrato(self, id_contrato_alquiler: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT id_contrato_objeto, id_inmueble, id_unidad_funcional, observaciones
            FROM contrato_objeto_locativo
            WHERE id_contrato_alquiler = :id
              AND deleted_at IS NULL
            ORDER BY id_contrato_objeto
            """
        )
        rows = self.db.execute(statement, {"id": id_contrato_alquiler}).mappings().all()
        return [
            {
                "id_contrato_objeto": row["id_contrato_objeto"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def create_contrato_alquiler(
        self,
        payload: Any,
        objetos: list[Any],
    ) -> dict[str, Any]:
        contrato_values = self._values(payload)
        db_values = {
            "uid_global": contrato_values["uid_global"],
            "version_registro": contrato_values["version_registro"],
            "created_at": contrato_values["created_at"],
            "updated_at": contrato_values["updated_at"],
            "id_instalacion_origen": contrato_values["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": contrato_values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_alta": contrato_values["op_id_alta"],
            "op_id_ultima_modificacion": contrato_values["op_id_ultima_modificacion"],
            "id_reserva_locativa": contrato_values.get("id_reserva_locativa"),
            "id_cartera_locativa": contrato_values.get("id_cartera_locativa"),
            "id_contrato_anterior": contrato_values.get("id_contrato_anterior"),
            "codigo_contrato": contrato_values["codigo_contrato"],
            "fecha_inicio": contrato_values["fecha_inicio"],
            "fecha_fin": contrato_values["fecha_fin"],
            "estado_contrato": contrato_values["estado_contrato"],
            "observaciones": contrato_values["observaciones"],
            "dia_vencimiento_canon": contrato_values.get("dia_vencimiento_canon"),
        }

        contrato_statement = text(
            """
            INSERT INTO contrato_alquiler (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_reserva_locativa,
                id_cartera_locativa,
                id_contrato_anterior,
                codigo_contrato,
                fecha_inicio,
                fecha_fin,
                estado_contrato,
                observaciones,
                dia_vencimiento_canon
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
                :id_reserva_locativa,
                :id_cartera_locativa,
                :id_contrato_anterior,
                :codigo_contrato,
                :fecha_inicio,
                :fecha_fin,
                :estado_contrato,
                :observaciones,
                :dia_vencimiento_canon
            )
            RETURNING id_contrato_alquiler
            """
        )

        objeto_statement = text(
            """
            INSERT INTO contrato_objeto_locativo (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_contrato_alquiler,
                id_inmueble,
                id_unidad_funcional,
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
                :id_contrato_alquiler,
                :id_inmueble,
                :id_unidad_funcional,
                :observaciones
            )
            RETURNING id_contrato_objeto
            """
        )

        try:
            contrato_row = self.db.execute(contrato_statement, db_values).mappings().one()
            id_contrato_alquiler = contrato_row["id_contrato_alquiler"]
            created_objetos: list[dict[str, Any]] = []

            for objeto in objetos:
                values = self._values(objeto)
                objeto_row = self.db.execute(
                    objeto_statement,
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
                        "id_contrato_alquiler": id_contrato_alquiler,
                        "id_inmueble": values["id_inmueble"],
                        "id_unidad_funcional": values["id_unidad_funcional"],
                        "observaciones": values["observaciones"],
                    },
                ).mappings().one()
                created_objetos.append(
                    {
                        "id_contrato_objeto": objeto_row["id_contrato_objeto"],
                        "id_inmueble": values["id_inmueble"],
                        "id_unidad_funcional": values["id_unidad_funcional"],
                        "observaciones": values["observaciones"],
                    }
                )

            self.db.commit()
            return {
                "id_contrato_alquiler": id_contrato_alquiler,
                "objetos": created_objetos,
            }
        except Exception:
            self.db.rollback()
            raise

    def _get_condiciones_for_contrato(self, id_contrato_alquiler: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_condicion_economica,
                uid_global,
                version_registro,
                id_contrato_alquiler,
                monto_base,
                periodicidad,
                moneda,
                fecha_desde,
                fecha_hasta,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            FROM condicion_economica_alquiler
            WHERE id_contrato_alquiler = :id
              AND deleted_at IS NULL
            ORDER BY fecha_desde ASC, id_condicion_economica ASC
            """
        )
        rows = self.db.execute(statement, {"id": id_contrato_alquiler}).mappings().all()
        return [self._condicion_row_to_dict(row) for row in rows]

    def _condicion_row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "id_condicion_economica": row["id_condicion_economica"],
            "uid_global": str(row["uid_global"]),
            "version_registro": row["version_registro"],
            "id_contrato_alquiler": row["id_contrato_alquiler"],
            "monto_base": row["monto_base"],
            "periodicidad": row["periodicidad"],
            "moneda": row["moneda"],
            "fecha_desde": row["fecha_desde"],
            "fecha_hasta": row["fecha_hasta"],
            "observaciones": row["observaciones"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
            "deleted_at": row["deleted_at"],
        }

    def get_locatario_principal_contrato(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                rpr.id_persona,
                rpr.id_relacion_persona_rol,
                rp.codigo_rol
            FROM relacion_persona_rol rpr
            JOIN rol_participacion rp
              ON rp.id_rol_participacion = rpr.id_rol_participacion
            WHERE rpr.tipo_relacion = 'contrato_alquiler'
              AND rpr.id_relacion = :id_contrato_alquiler
              AND rpr.deleted_at IS NULL
              AND rp.deleted_at IS NULL
              AND rp.estado_rol = 'ACTIVO'
              AND UPPER(rp.codigo_rol) = 'LOCATARIO_PRINCIPAL'
            ORDER BY rpr.fecha_desde ASC, rpr.id_relacion_persona_rol ASC
            LIMIT 1
            """
        )
        row = (
            self.db.execute(
                statement,
                {"id_contrato_alquiler": id_contrato_alquiler},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    def get_contrato_alquiler(self, id_contrato_alquiler: int) -> dict[str, Any] | None:
        contrato_statement = text(
            """
            SELECT
                id_contrato_alquiler,
                uid_global,
                version_registro,
                codigo_contrato,
                fecha_inicio,
                fecha_fin,
                estado_contrato,
                observaciones,
                dia_vencimiento_canon,
                deleted_at
            FROM contrato_alquiler
            WHERE id_contrato_alquiler = :id
            """
        )

        contrato_row = (
            self.db.execute(contrato_statement, {"id": id_contrato_alquiler})
            .mappings()
            .one_or_none()
        )
        if contrato_row is None:
            return None

        objetos = self._get_objetos_for_contrato(id_contrato_alquiler)
        condiciones = self._get_condiciones_for_contrato(id_contrato_alquiler)

        return {
            "id_contrato_alquiler": contrato_row["id_contrato_alquiler"],
            "uid_global": str(contrato_row["uid_global"]),
            "version_registro": contrato_row["version_registro"],
            "codigo_contrato": contrato_row["codigo_contrato"],
            "fecha_inicio": contrato_row["fecha_inicio"],
            "fecha_fin": contrato_row["fecha_fin"],
            "estado_contrato": contrato_row["estado_contrato"],
            "observaciones": contrato_row["observaciones"],
            "dia_vencimiento_canon": contrato_row["dia_vencimiento_canon"],
            "deleted_at": contrato_row["deleted_at"],
            "objetos": objetos,
            "condiciones_economicas_alquiler": condiciones,
        }

    def get_contrato_alquiler_detalle_integral(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None:
        contrato = self.get_contrato_alquiler(id_contrato_alquiler)
        if contrato is None:
            return None

        partes = self._get_partes_for_contrato(id_contrato_alquiler)
        entrega = self._get_entrega_for_contrato(id_contrato_alquiler)
        restitucion = self._get_restitucion_for_contrato(id_contrato_alquiler)
        relacion = self._get_relacion_financiera_for_contrato(id_contrato_alquiler)

        obligaciones: list[dict[str, Any]] = []
        if relacion is not None:
            obligaciones = self._get_obligaciones_financieras_for_relacion(
                relacion["id_relacion_generadora"]
            )

        resumen = self._build_resumen_financiero(obligaciones)

        return {
            **contrato,
            "partes": partes,
            "entrega_locativa": entrega,
            "restitucion_locativa": restitucion,
            "relacion_financiera": relacion,
            "obligaciones_financieras": obligaciones,
            "resumen_financiero": resumen,
        }

    def _get_partes_for_contrato(
        self, id_contrato_alquiler: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT
                rpr.id_relacion_persona_rol,
                rpr.id_persona,
                p.tipo_persona,
                p.codigo_persona,
                p.nombre,
                p.apellido,
                p.razon_social,
                p.estado_persona,
                rpr.id_rol_participacion,
                rp.codigo_rol,
                rp.nombre_rol,
                rpr.fecha_desde,
                rpr.fecha_hasta,
                rpr.observaciones
            FROM relacion_persona_rol rpr
            JOIN rol_participacion rp
              ON rp.id_rol_participacion = rpr.id_rol_participacion
             AND rp.deleted_at IS NULL
            JOIN persona p
              ON p.id_persona = rpr.id_persona
             AND p.deleted_at IS NULL
            WHERE rpr.tipo_relacion = 'contrato_alquiler'
              AND rpr.id_relacion = :id
              AND rpr.deleted_at IS NULL
            ORDER BY rp.codigo_rol ASC, rpr.fecha_desde ASC, rpr.id_relacion_persona_rol ASC
            """
        )
        rows = self.db.execute(stmt, {"id": id_contrato_alquiler}).mappings().all()
        return [dict(row) for row in rows]

    def _get_entrega_for_contrato(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_entrega_locativa,
                uid_global,
                version_registro,
                id_contrato_alquiler,
                fecha_entrega,
                observaciones,
                deleted_at
            FROM entrega_locativa
            WHERE id_contrato_alquiler = :id
              AND deleted_at IS NULL
            ORDER BY id_entrega_locativa ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, {"id": id_contrato_alquiler}).mappings().one_or_none()
        if row is None:
            return None
        data = dict(row)
        data["uid_global"] = str(data["uid_global"])
        return data

    def _get_restitucion_for_contrato(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None:
        if not self._table_exists("restitucion_locativa"):
            return None

        stmt = text(
            """
            SELECT
                id_restitucion_locativa,
                uid_global,
                version_registro,
                id_contrato_alquiler,
                fecha_restitucion,
                estado_inmueble,
                observaciones,
                deleted_at
            FROM restitucion_locativa
            WHERE id_contrato_alquiler = :id
              AND deleted_at IS NULL
            ORDER BY id_restitucion_locativa ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, {"id": id_contrato_alquiler}).mappings().one_or_none()
        if row is None:
            return None
        data = dict(row)
        data["uid_global"] = str(data["uid_global"])
        return data

    def _table_exists(self, table_name: str) -> bool:
        row = self.db.execute(
            text("SELECT to_regclass(:table_name)"),
            {"table_name": f"public.{table_name}"},
        ).scalar_one_or_none()
        return row is not None

    def _get_relacion_financiera_for_contrato(
        self, id_contrato_alquiler: int
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
                fecha_alta
            FROM relacion_generadora
            WHERE LOWER(tipo_origen) = 'contrato_alquiler'
              AND id_origen = :id
              AND deleted_at IS NULL
            ORDER BY id_relacion_generadora ASC
            LIMIT 1
            """
        )
        row = self.db.execute(stmt, {"id": id_contrato_alquiler}).mappings().one_or_none()
        if row is None:
            return None
        data = dict(row)
        data["uid_global"] = str(data["uid_global"])
        return data

    def _get_obligaciones_financieras_for_relacion(
        self, id_relacion_generadora: int
    ) -> list[dict[str, Any]]:
        obligaciones_stmt = text(
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
                importe_cancelado_acumulado,
                importe_bonificado_acumulado,
                importe_anulado_acumulado,
                moneda,
                estado_obligacion
            FROM obligacion_financiera
            WHERE id_relacion_generadora = :id_relacion_generadora
              AND deleted_at IS NULL
            ORDER BY periodo_desde ASC NULLS LAST, id_obligacion_financiera ASC
            """
        )
        ob_rows = self.db.execute(
            obligaciones_stmt, {"id_relacion_generadora": id_relacion_generadora}
        ).mappings().all()
        if not ob_rows:
            return []

        ids = [row["id_obligacion_financiera"] for row in ob_rows]
        params = {"ids": tuple(ids)}

        comps_stmt = text(
            """
            SELECT
                co.id_obligacion_financiera,
                co.id_composicion_obligacion,
                co.id_concepto_financiero,
                cf.codigo_concepto_financiero,
                cf.nombre_concepto_financiero,
                cf.tipo_concepto_financiero,
                cf.naturaleza_concepto,
                co.orden_composicion,
                co.estado_composicion_obligacion,
                co.importe_componente,
                co.saldo_componente,
                co.moneda_componente,
                co.observaciones
            FROM composicion_obligacion co
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = co.id_concepto_financiero
             AND cf.deleted_at IS NULL
            WHERE co.id_obligacion_financiera IN :ids
              AND co.deleted_at IS NULL
            ORDER BY co.id_obligacion_financiera ASC, co.orden_composicion ASC,
                     co.id_composicion_obligacion ASC
            """
        ).bindparams(bindparam("ids", expanding=True))
        obligados_stmt = text(
            """
            SELECT
                id_obligacion_financiera,
                id_obligacion_obligado,
                id_persona,
                rol_obligado,
                porcentaje_responsabilidad
            FROM obligacion_obligado
            WHERE id_obligacion_financiera IN :ids
              AND deleted_at IS NULL
            ORDER BY id_obligacion_financiera ASC, id_obligacion_obligado ASC
            """
        ).bindparams(bindparam("ids", expanding=True))

        comps_by_ob: dict[int, list[dict[str, Any]]] = {id_: [] for id_ in ids}
        for row in self.db.execute(comps_stmt, params).mappings().all():
            item = dict(row)
            id_ob = item.pop("id_obligacion_financiera")
            comps_by_ob[id_ob].append(item)

        obligados_by_ob: dict[int, list[dict[str, Any]]] = {id_: [] for id_ in ids}
        for row in self.db.execute(obligados_stmt, params).mappings().all():
            item = dict(row)
            id_ob = item.pop("id_obligacion_financiera")
            obligados_by_ob[id_ob].append(item)

        obligaciones = []
        for row in ob_rows:
            item = dict(row)
            item["uid_global"] = str(item["uid_global"])
            item["composiciones"] = comps_by_ob[item["id_obligacion_financiera"]]
            item["obligados"] = obligados_by_ob[item["id_obligacion_financiera"]]
            obligaciones.append(item)
        return obligaciones

    def _build_resumen_financiero(
        self, obligaciones: list[dict[str, Any]]
    ) -> dict[str, Any]:
        saldo_total = sum(
            (Decimal(str(ob["importe_total"])) for ob in obligaciones), Decimal("0")
        )
        saldo_pendiente = sum(
            (Decimal(str(ob["saldo_pendiente"])) for ob in obligaciones), Decimal("0")
        )
        importe_cancelado = sum(
            (
                Decimal(str(ob["importe_cancelado_acumulado"]))
                for ob in obligaciones
            ),
            Decimal("0"),
        )
        return {
            "cantidad_obligaciones": len(obligaciones),
            "saldo_total": saldo_total,
            "saldo_pendiente": saldo_pendiente,
            "importe_cancelado": importe_cancelado,
            "cantidad_vencidas": sum(
                1 for ob in obligaciones if ob["estado_obligacion"] == "VENCIDA"
            ),
            "cantidad_canceladas": sum(
                1 for ob in obligaciones if ob["estado_obligacion"] == "CANCELADA"
            ),
            "cantidad_anuladas": sum(
                1 for ob in obligaciones if ob["estado_obligacion"] == "ANULADA"
            ),
        }

    def delete_contrato_alquiler(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)

        statement = text(
            """
            UPDATE contrato_alquiler
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_contrato_alquiler = :id_contrato_alquiler
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_contrato_alquiler,
                uid_global,
                version_registro,
                codigo_contrato,
                fecha_inicio,
                fecha_fin,
                estado_contrato,
                observaciones,
                dia_vencimiento_canon,
                deleted_at
            """
        )

        try:
            updated = (
                self.db.execute(
                    statement,
                    {
                        "id_contrato_alquiler": values["id_contrato_alquiler"],
                        "version_registro_actual": values["version_registro_actual"],
                        "version_registro_nueva": values["version_registro_nueva"],
                        "updated_at": values["updated_at"],
                        "deleted_at": values["deleted_at"],
                        "id_instalacion_ultima_modificacion": values[
                            "id_instalacion_ultima_modificacion"
                        ],
                        "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    },
                )
                .mappings()
                .one_or_none()
            )
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            id_contrato = updated["id_contrato_alquiler"]
            objetos = self._get_objetos_for_contrato(id_contrato)
            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_contrato_alquiler": id_contrato,
                    "uid_global": str(updated["uid_global"]),
                    "version_registro": updated["version_registro"],
                    "codigo_contrato": updated["codigo_contrato"],
                    "fecha_inicio": updated["fecha_inicio"],
                    "fecha_fin": updated["fecha_fin"],
                    "estado_contrato": updated["estado_contrato"],
                    "observaciones": updated["observaciones"],
                    "dia_vencimiento_canon": updated["dia_vencimiento_canon"],
                    "objetos": objetos,
                    "condiciones_economicas_alquiler": [],
                    "deleted_at": updated["deleted_at"],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def finalize_contrato_alquiler(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)

        statement = text(
            """
            UPDATE contrato_alquiler
            SET
                estado_contrato = :estado_contrato,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_contrato_alquiler = :id_contrato_alquiler
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_contrato_alquiler,
                uid_global,
                version_registro,
                codigo_contrato,
                fecha_inicio,
                fecha_fin,
                estado_contrato,
                observaciones,
                dia_vencimiento_canon
            """
        )

        try:
            updated = (
                self.db.execute(
                    statement,
                    {
                        "id_contrato_alquiler": values["id_contrato_alquiler"],
                        "estado_contrato": values["estado_contrato"],
                        "version_registro_actual": values["version_registro_actual"],
                        "version_registro_nueva": values["version_registro_nueva"],
                        "updated_at": values["updated_at"],
                        "id_instalacion_ultima_modificacion": values[
                            "id_instalacion_ultima_modificacion"
                        ],
                        "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    },
                )
                .mappings()
                .one_or_none()
            )
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            id_contrato = updated["id_contrato_alquiler"]
            objetos = self._get_objetos_for_contrato(id_contrato)
            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_contrato_alquiler": id_contrato,
                    "uid_global": str(updated["uid_global"]),
                    "version_registro": updated["version_registro"],
                    "codigo_contrato": updated["codigo_contrato"],
                    "fecha_inicio": updated["fecha_inicio"],
                    "fecha_fin": updated["fecha_fin"],
                    "estado_contrato": updated["estado_contrato"],
                    "observaciones": updated["observaciones"],
                    "dia_vencimiento_canon": updated["dia_vencimiento_canon"],
                    "objetos": objetos,
                    "condiciones_economicas_alquiler": [],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def has_condicion_economica_alquiler(self, id_contrato_alquiler: int) -> bool:
        stmt = text(
            """
            SELECT 1 FROM condicion_economica_alquiler
            WHERE id_contrato_alquiler = :id AND deleted_at IS NULL
            LIMIT 1
            """
        )
        return self.db.execute(stmt, {"id": id_contrato_alquiler}).scalar_one_or_none() is not None

    def activate_contrato_alquiler(self, payload: Any, outbox_event: Any) -> dict[str, Any]:
        values = self._values(payload)

        statement = text(
            """
            UPDATE contrato_alquiler
            SET
                estado_contrato = :estado_contrato,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_contrato_alquiler = :id_contrato_alquiler
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_contrato_alquiler,
                uid_global,
                version_registro,
                codigo_contrato,
                fecha_inicio,
                fecha_fin,
                estado_contrato,
                observaciones,
                dia_vencimiento_canon
            """
        )

        try:
            updated = (
                self.db.execute(
                    statement,
                    {
                        "id_contrato_alquiler": values["id_contrato_alquiler"],
                        "estado_contrato": values["estado_contrato"],
                        "version_registro_actual": values["version_registro_actual"],
                        "version_registro_nueva": values["version_registro_nueva"],
                        "updated_at": values["updated_at"],
                        "id_instalacion_ultima_modificacion": values[
                            "id_instalacion_ultima_modificacion"
                        ],
                        "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    },
                )
                .mappings()
                .one_or_none()
            )
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            id_contrato = updated["id_contrato_alquiler"]
            objetos = self._get_objetos_for_contrato(id_contrato)

            outbox_values = self._values(outbox_event)
            OutboxRepository(self.db).add_event(
                event_type=outbox_values["event_type"],
                aggregate_type=outbox_values["aggregate_type"],
                aggregate_id=outbox_values["aggregate_id"],
                payload=outbox_values["payload"],
                occurred_at=outbox_values["occurred_at"],
                status=outbox_values.get("status", "PENDING"),
            )

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_contrato_alquiler": id_contrato,
                    "uid_global": str(updated["uid_global"]),
                    "version_registro": updated["version_registro"],
                    "codigo_contrato": updated["codigo_contrato"],
                    "fecha_inicio": updated["fecha_inicio"],
                    "fecha_fin": updated["fecha_fin"],
                    "estado_contrato": updated["estado_contrato"],
                    "observaciones": updated["observaciones"],
                    "dia_vencimiento_canon": updated["dia_vencimiento_canon"],
                    "objetos": objetos,
                    "condiciones_economicas_alquiler": [],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def list_contratos_alquiler(
        self,
        *,
        q: str | None,
        codigo_contrato: str | None,
        estado_contrato: str | None,
        id_persona: int | None,
        rol_codigo: str | None,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        fecha_inicio_desde: date | None,
        fecha_inicio_hasta: date | None,
        fecha_fin_desde: date | None,
        fecha_fin_hasta: date | None,
        con_saldo: bool | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        filters = ["ca.deleted_at IS NULL"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if q is not None and q.strip():
            filters.append(
                """
                (
                    ca.codigo_contrato ILIKE :q
                    OR COALESCE(ca.observaciones, '') ILIKE :q
                    OR EXISTS (
                        SELECT 1
                        FROM relacion_persona_rol rpr
                        JOIN persona p ON p.id_persona = rpr.id_persona
                         AND p.deleted_at IS NULL
                        WHERE rpr.tipo_relacion = 'contrato_alquiler'
                          AND rpr.id_relacion = ca.id_contrato_alquiler
                          AND rpr.deleted_at IS NULL
                          AND (
                            COALESCE(p.nombre, '') ILIKE :q
                            OR COALESCE(p.apellido, '') ILIKE :q
                            OR COALESCE(p.razon_social, '') ILIKE :q
                            OR COALESCE(p.cuit_cuil, '') ILIKE :q
                            OR COALESCE(p.codigo_persona, '') ILIKE :q
                          )
                    )
                )
                """
            )
            params["q"] = f"%{q.strip()}%"

        if codigo_contrato is not None:
            filters.append("ca.codigo_contrato = :codigo_contrato")
            params["codigo_contrato"] = codigo_contrato

        if estado_contrato is not None:
            filters.append("LOWER(ca.estado_contrato) = :estado_contrato")
            params["estado_contrato"] = estado_contrato.strip().lower()

        if id_persona is not None:
            rol_filter = ""
            if rol_codigo is not None:
                rol_filter = "AND UPPER(rp.codigo_rol) = :rol_codigo"
                params["rol_codigo"] = rol_codigo.strip().upper()
            filters.append(
                f"""
                EXISTS (
                    SELECT 1
                    FROM relacion_persona_rol rpr
                    JOIN rol_participacion rp
                      ON rp.id_rol_participacion = rpr.id_rol_participacion
                     AND rp.deleted_at IS NULL
                    WHERE rpr.tipo_relacion = 'contrato_alquiler'
                      AND rpr.id_relacion = ca.id_contrato_alquiler
                      AND rpr.deleted_at IS NULL
                      AND rpr.id_persona = :id_persona
                      {rol_filter}
                )
                """
            )
            params["id_persona"] = id_persona
        elif rol_codigo is not None:
            filters.append(
                """
                EXISTS (
                    SELECT 1
                    FROM relacion_persona_rol rpr
                    JOIN rol_participacion rp
                      ON rp.id_rol_participacion = rpr.id_rol_participacion
                     AND rp.deleted_at IS NULL
                    WHERE rpr.tipo_relacion = 'contrato_alquiler'
                      AND rpr.id_relacion = ca.id_contrato_alquiler
                      AND rpr.deleted_at IS NULL
                      AND UPPER(rp.codigo_rol) = :rol_codigo
                )
                """
            )
            params["rol_codigo"] = rol_codigo.strip().upper()

        if fecha_inicio_desde is not None:
            filters.append("ca.fecha_inicio >= :fecha_inicio_desde")
            params["fecha_inicio_desde"] = fecha_inicio_desde

        if fecha_inicio_hasta is not None:
            filters.append("ca.fecha_inicio <= :fecha_inicio_hasta")
            params["fecha_inicio_hasta"] = fecha_inicio_hasta

        if fecha_fin_desde is not None:
            filters.append("ca.fecha_fin >= :fecha_fin_desde")
            params["fecha_fin_desde"] = fecha_fin_desde

        if fecha_fin_hasta is not None:
            filters.append("ca.fecha_fin <= :fecha_fin_hasta")
            params["fecha_fin_hasta"] = fecha_fin_hasta

        if id_inmueble is not None:
            filters.append(
                "EXISTS ("
                "SELECT 1 FROM contrato_objeto_locativo col"
                " WHERE col.id_contrato_alquiler = ca.id_contrato_alquiler"
                "   AND col.deleted_at IS NULL"
                "   AND col.id_inmueble = :id_inmueble"
                ")"
            )
            params["id_inmueble"] = id_inmueble

        if id_unidad_funcional is not None:
            filters.append(
                "EXISTS ("
                "SELECT 1 FROM contrato_objeto_locativo col"
                " WHERE col.id_contrato_alquiler = ca.id_contrato_alquiler"
                "   AND col.deleted_at IS NULL"
                "   AND col.id_unidad_funcional = :id_unidad_funcional"
                ")"
            )
            params["id_unidad_funcional"] = id_unidad_funcional

        if con_saldo is not None:
            saldo_clause = (
                """
                EXISTS (
                    SELECT 1
                    FROM relacion_generadora rg
                    JOIN obligacion_financiera ofi
                      ON ofi.id_relacion_generadora = rg.id_relacion_generadora
                     AND ofi.deleted_at IS NULL
                     AND ofi.saldo_pendiente > 0
                    WHERE LOWER(rg.tipo_origen) = 'contrato_alquiler'
                      AND rg.id_origen = ca.id_contrato_alquiler
                      AND rg.deleted_at IS NULL
                )
                """
            )
            filters.append(saldo_clause if con_saldo else f"NOT {saldo_clause}")

        where_clause = " AND ".join(filters)

        list_statement = text(
            f"""
            SELECT
                ca.id_contrato_alquiler,
                ca.uid_global,
                ca.version_registro,
                ca.codigo_contrato,
                ca.fecha_inicio,
                ca.fecha_fin,
                ca.estado_contrato,
                ca.observaciones
            FROM contrato_alquiler ca
            WHERE {where_clause}
            ORDER BY ca.fecha_inicio DESC, ca.id_contrato_alquiler DESC
            LIMIT :limit
            OFFSET :offset
            """
        )
        total_statement = text(
            f"""
            SELECT COUNT(*) AS total
            FROM contrato_alquiler ca
            WHERE {where_clause}
            """
        )

        rows = self.db.execute(list_statement, params).mappings().all()
        total = self.db.execute(total_statement, params).scalar_one()
        ids = [row["id_contrato_alquiler"] for row in rows]
        partes_by_id = self._get_partes_resumen_for_contratos(ids)
        objetos_by_id = self._get_objetos_resumen_for_contratos(ids)
        financiero_by_id = self._get_resumen_financiero_for_origenes(
            "contrato_alquiler", ids
        )

        return {
            "items": [
                {
                    "id_contrato_alquiler": row["id_contrato_alquiler"],
                    "uid_global": str(row["uid_global"]),
                    "version_registro": row["version_registro"],
                    "codigo_contrato": row["codigo_contrato"],
                    "fecha_inicio": row["fecha_inicio"],
                    "fecha_fin": row["fecha_fin"],
                    "estado_contrato": row["estado_contrato"],
                    "observaciones": row["observaciones"],
                    "partes_resumen": partes_by_id.get(
                        row["id_contrato_alquiler"], []
                    ),
                    "objetos_resumen": objetos_by_id.get(
                        row["id_contrato_alquiler"], []
                    ),
                    "relacion_financiera": financiero_by_id.get(
                        row["id_contrato_alquiler"]
                    ),
                    "acciones_ui": {"puede_abrir_detalle": True},
                }
                for row in rows
            ],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def _get_partes_resumen_for_contratos(
        self, ids: list[int]
    ) -> dict[int, list[dict[str, Any]]]:
        if not ids:
            return {}
        stmt = text(
            """
            SELECT
                rpr.id_relacion AS id_contrato_alquiler,
                rpr.id_relacion_persona_rol,
                rpr.id_persona,
                rp.codigo_rol,
                rp.nombre_rol,
                p.tipo_persona,
                p.codigo_persona,
                p.nombre,
                p.apellido,
                p.razon_social,
                p.cuit_cuil
            FROM relacion_persona_rol rpr
            JOIN rol_participacion rp
              ON rp.id_rol_participacion = rpr.id_rol_participacion
             AND rp.deleted_at IS NULL
            JOIN persona p
              ON p.id_persona = rpr.id_persona
             AND p.deleted_at IS NULL
            WHERE rpr.tipo_relacion = 'contrato_alquiler'
              AND rpr.id_relacion IN :ids
              AND rpr.deleted_at IS NULL
            ORDER BY rpr.id_relacion ASC, rp.codigo_rol ASC,
                     rpr.id_relacion_persona_rol ASC
            """
        ).bindparams(bindparam("ids", expanding=True))
        result: dict[int, list[dict[str, Any]]] = {id_: [] for id_ in ids}
        for row in self.db.execute(stmt, {"ids": tuple(ids)}).mappings().all():
            display_name = self._display_name(row)
            result[row["id_contrato_alquiler"]].append(
                {
                    "id_relacion_persona_rol": row["id_relacion_persona_rol"],
                    "id_persona": row["id_persona"],
                    "display_name": display_name,
                    "codigo_rol": row["codigo_rol"],
                    "nombre_rol": row["nombre_rol"],
                    "tipo_persona": row["tipo_persona"],
                    "cuit_cuil": row["cuit_cuil"],
                }
            )
        return result

    def _get_objetos_resumen_for_contratos(
        self, ids: list[int]
    ) -> dict[int, list[dict[str, Any]]]:
        if not ids:
            return {}
        stmt = text(
            """
            SELECT
                col.id_contrato_alquiler,
                col.id_contrato_objeto,
                col.id_inmueble,
                i.codigo_inmueble,
                i.nombre_inmueble,
                col.id_unidad_funcional,
                uf.codigo_unidad,
                uf.nombre_unidad,
                col.observaciones
            FROM contrato_objeto_locativo col
            LEFT JOIN inmueble i
              ON i.id_inmueble = col.id_inmueble
             AND i.deleted_at IS NULL
            LEFT JOIN unidad_funcional uf
              ON uf.id_unidad_funcional = col.id_unidad_funcional
             AND uf.deleted_at IS NULL
            WHERE col.id_contrato_alquiler IN :ids
              AND col.deleted_at IS NULL
            ORDER BY col.id_contrato_alquiler ASC, col.id_contrato_objeto ASC
            """
        ).bindparams(bindparam("ids", expanding=True))
        result: dict[int, list[dict[str, Any]]] = {id_: [] for id_ in ids}
        for row in self.db.execute(stmt, {"ids": tuple(ids)}).mappings().all():
            result[row["id_contrato_alquiler"]].append(dict(row))
        return result

    def _get_resumen_financiero_for_origenes(
        self, tipo_origen: str, ids: list[int]
    ) -> dict[int, dict[str, Any]]:
        if not ids:
            return {}
        stmt = text(
            """
            SELECT
                rg.id_origen,
                rg.id_relacion_generadora,
                COUNT(ofi.id_obligacion_financiera) AS cantidad_obligaciones,
                COALESCE(SUM(ofi.saldo_pendiente), 0) AS saldo_pendiente_total,
                COALESCE(
                    SUM(CASE WHEN ofi.estado_obligacion = 'VENCIDA' THEN 1 ELSE 0 END),
                    0
                ) AS cantidad_vencidas
            FROM relacion_generadora rg
            LEFT JOIN obligacion_financiera ofi
              ON ofi.id_relacion_generadora = rg.id_relacion_generadora
             AND ofi.deleted_at IS NULL
            WHERE LOWER(rg.tipo_origen) = :tipo_origen
              AND rg.id_origen IN :ids
              AND rg.deleted_at IS NULL
            GROUP BY rg.id_origen, rg.id_relacion_generadora
            ORDER BY rg.id_relacion_generadora ASC
            """
        ).bindparams(bindparam("ids", expanding=True))
        result: dict[int, dict[str, Any]] = {}
        for row in self.db.execute(
            stmt, {"tipo_origen": tipo_origen, "ids": tuple(ids)}
        ).mappings().all():
            result.setdefault(
                row["id_origen"],
                {
                    "id_relacion_generadora": row["id_relacion_generadora"],
                    "cantidad_obligaciones": row["cantidad_obligaciones"],
                    "saldo_pendiente_total": row["saldo_pendiente_total"],
                    "cantidad_vencidas": row["cantidad_vencidas"],
                },
            )
        return result

    def _display_name(self, row: Any) -> str:
        razon = row["razon_social"]
        if razon:
            return razon
        parts = [row["nombre"], row["apellido"]]
        display = " ".join(part for part in parts if part)
        return display or row["codigo_persona"] or f"Persona {row['id_persona']}"

    def has_vigencia_overlap_condicion(
        self,
        id_contrato_alquiler: int,
        moneda: str | None,
        fecha_desde: date,
        fecha_hasta: date | None,
        exclude_id: int | None = None,
    ) -> bool:
        params: dict[str, Any] = {
            "id_contrato_alquiler": id_contrato_alquiler,
            "moneda_norm": moneda or "",
            "fecha_desde": fecha_desde,
        }
        if fecha_hasta is not None:
            left_clause = "fecha_desde <= :fecha_hasta"
            params["fecha_hasta"] = fecha_hasta
        else:
            left_clause = "1=1"

        exclude_clause = ""
        if exclude_id is not None:
            exclude_clause = "AND id_condicion_economica <> :exclude_id"
            params["exclude_id"] = exclude_id

        statement = text(
            f"""
            SELECT 1
            FROM condicion_economica_alquiler
            WHERE id_contrato_alquiler = :id_contrato_alquiler
              AND deleted_at IS NULL
              AND COALESCE(moneda, '') = :moneda_norm
              AND {left_clause}
              AND (fecha_hasta IS NULL OR fecha_hasta >= :fecha_desde)
              {exclude_clause}
            LIMIT 1
            """
        )
        return self.db.execute(statement, params).scalar_one_or_none() is not None

    def create_condicion_economica_alquiler(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)

        statement = text(
            """
            INSERT INTO condicion_economica_alquiler (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_contrato_alquiler,
                monto_base,
                periodicidad,
                moneda,
                fecha_desde,
                fecha_hasta,
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
                :id_contrato_alquiler,
                :monto_base,
                :periodicidad,
                :moneda,
                :fecha_desde,
                :fecha_hasta,
                :observaciones
            )
            RETURNING
                id_condicion_economica,
                uid_global,
                version_registro,
                id_contrato_alquiler,
                monto_base,
                periodicidad,
                moneda,
                fecha_desde,
                fecha_hasta,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            """
        )

        try:
            row = self.db.execute(
                statement,
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
                    "id_contrato_alquiler": values["id_contrato_alquiler"],
                    "monto_base": values["monto_base"],
                    "periodicidad": values["periodicidad"],
                    "moneda": values["moneda"],
                    "fecha_desde": values["fecha_desde"],
                    "fecha_hasta": values["fecha_hasta"],
                    "observaciones": values["observaciones"],
                },
            ).mappings().one()
            self.db.commit()
            return self._condicion_row_to_dict(row)
        except Exception:
            self.db.rollback()
            raise

    def get_condicion_economica_alquiler(
        self, id_condicion_economica: int, id_contrato_alquiler: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_condicion_economica,
                uid_global,
                version_registro,
                id_contrato_alquiler,
                monto_base,
                periodicidad,
                moneda,
                fecha_desde,
                fecha_hasta,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            FROM condicion_economica_alquiler
            WHERE id_condicion_economica = :id_condicion_economica
              AND id_contrato_alquiler = :id_contrato_alquiler
            """
        )
        row = (
            self.db.execute(
                statement,
                {
                    "id_condicion_economica": id_condicion_economica,
                    "id_contrato_alquiler": id_contrato_alquiler,
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return None
        return self._condicion_row_to_dict(row)

    def list_condiciones_economicas_alquiler(
        self,
        *,
        id_contrato_alquiler: int,
        vigente: bool | None,
        fecha_desde: date | None,
        fecha_hasta: date | None,
        moneda: str | None,
        periodicidad: str | None,
    ) -> dict[str, Any]:
        filters = [
            "id_contrato_alquiler = :id_contrato_alquiler",
            "deleted_at IS NULL",
        ]
        params: dict[str, Any] = {"id_contrato_alquiler": id_contrato_alquiler}

        if vigente is True:
            filters.append(
                "(fecha_hasta IS NULL OR fecha_hasta >= CURRENT_DATE)"
            )
        elif vigente is False:
            filters.append("fecha_hasta < CURRENT_DATE")

        if fecha_desde is not None:
            filters.append("fecha_desde >= :fecha_desde")
            params["fecha_desde"] = fecha_desde

        if fecha_hasta is not None:
            filters.append(
                "(fecha_hasta IS NULL OR fecha_hasta <= :fecha_hasta)"
            )
            params["fecha_hasta"] = fecha_hasta

        if moneda is not None:
            filters.append("LOWER(COALESCE(moneda, '')) = :moneda")
            params["moneda"] = moneda.strip().lower()

        if periodicidad is not None:
            filters.append("LOWER(COALESCE(periodicidad, '')) = :periodicidad")
            params["periodicidad"] = periodicidad.strip().lower()

        where_clause = " AND ".join(filters)

        list_statement = text(
            f"""
            SELECT
                id_condicion_economica,
                uid_global,
                version_registro,
                id_contrato_alquiler,
                monto_base,
                periodicidad,
                moneda,
                fecha_desde,
                fecha_hasta,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            FROM condicion_economica_alquiler
            WHERE {where_clause}
            ORDER BY fecha_desde ASC, id_condicion_economica ASC
            """
        )
        total_statement = text(
            f"SELECT COUNT(*) FROM condicion_economica_alquiler WHERE {where_clause}"
        )

        rows = self.db.execute(list_statement, params).mappings().all()
        total = self.db.execute(total_statement, params).scalar_one()

        return {
            "items": [self._condicion_row_to_dict(row) for row in rows],
            "total": total,
        }

    def cerrar_vigencia_condicion_economica_alquiler(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)

        statement = text(
            """
            UPDATE condicion_economica_alquiler
            SET
                fecha_hasta = :fecha_hasta,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_condicion_economica = :id_condicion_economica
              AND id_contrato_alquiler = :id_contrato_alquiler
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_condicion_economica,
                uid_global,
                version_registro,
                id_contrato_alquiler,
                monto_base,
                periodicidad,
                moneda,
                fecha_desde,
                fecha_hasta,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            """
        )

        try:
            updated = (
                self.db.execute(
                    statement,
                    {
                        "id_condicion_economica": values["id_condicion_economica"],
                        "id_contrato_alquiler": values["id_contrato_alquiler"],
                        "fecha_hasta": values["fecha_hasta"],
                        "version_registro_actual": values["version_registro_actual"],
                        "version_registro_nueva": values["version_registro_nueva"],
                        "updated_at": values["updated_at"],
                        "id_instalacion_ultima_modificacion": values[
                            "id_instalacion_ultima_modificacion"
                        ],
                        "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    },
                )
                .mappings()
                .one_or_none()
            )
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            self.db.commit()
            return {"status": "OK", "data": self._condicion_row_to_dict(updated)}
        except Exception:
            self.db.rollback()
            raise

    def cancel_contrato_alquiler(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)

        statement = text(
            """
            UPDATE contrato_alquiler
            SET
                estado_contrato = :estado_contrato,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_contrato_alquiler = :id_contrato_alquiler
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_contrato_alquiler,
                uid_global,
                version_registro,
                codigo_contrato,
                fecha_inicio,
                fecha_fin,
                estado_contrato,
                observaciones,
                dia_vencimiento_canon
            """
        )

        try:
            updated = (
                self.db.execute(
                    statement,
                    {
                        "id_contrato_alquiler": values["id_contrato_alquiler"],
                        "estado_contrato": values["estado_contrato"],
                        "version_registro_actual": values["version_registro_actual"],
                        "version_registro_nueva": values["version_registro_nueva"],
                        "updated_at": values["updated_at"],
                        "id_instalacion_ultima_modificacion": values[
                            "id_instalacion_ultima_modificacion"
                        ],
                        "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    },
                )
                .mappings()
                .one_or_none()
            )
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            id_contrato = updated["id_contrato_alquiler"]
            objetos = self._get_objetos_for_contrato(id_contrato)
            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_contrato_alquiler": id_contrato,
                    "uid_global": str(updated["uid_global"]),
                    "version_registro": updated["version_registro"],
                    "codigo_contrato": updated["codigo_contrato"],
                    "fecha_inicio": updated["fecha_inicio"],
                    "fecha_fin": updated["fecha_fin"],
                    "estado_contrato": updated["estado_contrato"],
                    "observaciones": updated["observaciones"],
                    "dia_vencimiento_canon": updated["dia_vencimiento_canon"],
                    "objetos": objetos,
                    "condiciones_economicas_alquiler": [],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def update_contrato_alquiler(
        self,
        payload: Any,
        objetos: list[Any],
    ) -> dict[str, Any]:
        values = self._values(payload)

        update_statement = text(
            """
            UPDATE contrato_alquiler
            SET
                codigo_contrato = :codigo_contrato,
                fecha_inicio = :fecha_inicio,
                fecha_fin = :fecha_fin,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_contrato_alquiler = :id_contrato_alquiler
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_contrato_alquiler,
                uid_global,
                version_registro,
                codigo_contrato,
                fecha_inicio,
                fecha_fin,
                estado_contrato,
                observaciones
            """
        )

        delete_objetos_statement = text(
            """
            UPDATE contrato_objeto_locativo
            SET deleted_at = :deleted_at, updated_at = :updated_at
            WHERE id_contrato_alquiler = :id_contrato_alquiler
              AND deleted_at IS NULL
            """
        )

        insert_objeto_statement = text(
            """
            INSERT INTO contrato_objeto_locativo (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_contrato_alquiler,
                id_inmueble,
                id_unidad_funcional,
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
                :id_contrato_alquiler,
                :id_inmueble,
                :id_unidad_funcional,
                :observaciones
            )
            RETURNING id_contrato_objeto
            """
        )

        try:
            updated = (
                self.db.execute(
                    update_statement,
                    {
                        "id_contrato_alquiler": values["id_contrato_alquiler"],
                        "codigo_contrato": values["codigo_contrato"],
                        "fecha_inicio": values["fecha_inicio"],
                        "fecha_fin": values["fecha_fin"],
                        "observaciones": values["observaciones"],
                        "version_registro_actual": values["version_registro_actual"],
                        "version_registro_nueva": values["version_registro_nueva"],
                        "updated_at": values["updated_at"],
                        "id_instalacion_ultima_modificacion": values[
                            "id_instalacion_ultima_modificacion"
                        ],
                        "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    },
                )
                .mappings()
                .one_or_none()
            )
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            id_contrato = updated["id_contrato_alquiler"]

            self.db.execute(
                delete_objetos_statement,
                {
                    "deleted_at": values["updated_at"],
                    "updated_at": values["updated_at"],
                    "id_contrato_alquiler": id_contrato,
                },
            )

            new_objetos: list[dict[str, Any]] = []
            for objeto in objetos:
                obj_values = self._values(objeto)
                obj_row = self.db.execute(
                    insert_objeto_statement,
                    {
                        "uid_global": obj_values["uid_global"],
                        "version_registro": obj_values["version_registro"],
                        "created_at": obj_values["created_at"],
                        "updated_at": obj_values["updated_at"],
                        "id_instalacion_origen": obj_values["id_instalacion_origen"],
                        "id_instalacion_ultima_modificacion": obj_values[
                            "id_instalacion_ultima_modificacion"
                        ],
                        "op_id_alta": obj_values["op_id_alta"],
                        "op_id_ultima_modificacion": obj_values["op_id_ultima_modificacion"],
                        "id_contrato_alquiler": id_contrato,
                        "id_inmueble": obj_values["id_inmueble"],
                        "id_unidad_funcional": obj_values["id_unidad_funcional"],
                        "observaciones": obj_values["observaciones"],
                    },
                ).mappings().one()
                new_objetos.append(
                    {
                        "id_contrato_objeto": obj_row["id_contrato_objeto"],
                        "id_inmueble": obj_values["id_inmueble"],
                        "id_unidad_funcional": obj_values["id_unidad_funcional"],
                        "observaciones": obj_values["observaciones"],
                    }
                )

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_contrato_alquiler": id_contrato,
                    "uid_global": str(updated["uid_global"]),
                    "version_registro": updated["version_registro"],
                    "codigo_contrato": updated["codigo_contrato"],
                    "fecha_inicio": updated["fecha_inicio"],
                    "fecha_fin": updated["fecha_fin"],
                    "estado_contrato": updated["estado_contrato"],
                    "observaciones": updated["observaciones"],
                    "objetos": new_objetos,
                    "condiciones_economicas_alquiler": [],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    # ── disponibilidad helpers ────────────────────────────────────────────────

    def _disp_object_filter(
        self, *, id_inmueble: int | None, id_unidad_funcional: int | None
    ) -> str:
        if id_inmueble is not None:
            return "id_inmueble = :id_inmueble AND id_unidad_funcional IS NULL"
        return "id_unidad_funcional = :id_unidad_funcional AND id_inmueble IS NULL"

    def _disp_object_params(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> dict[str, Any]:
        return {
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
            "at_datetime": at_datetime,
        }

    def has_current_disponibilidad_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
        filters = self._disp_object_filter(
            id_inmueble=id_inmueble, id_unidad_funcional=id_unidad_funcional
        )
        stmt = text(
            f"""
            SELECT 1
            FROM disponibilidad
            WHERE deleted_at IS NULL
              AND {filters}
              AND fecha_desde <= :at_datetime
              AND (fecha_hasta IS NULL OR fecha_hasta >= :at_datetime)
              AND UPPER(estado_disponibilidad) = 'DISPONIBLE'
            """
        )
        return (
            self.db.execute(
                stmt,
                self._disp_object_params(
                    id_inmueble=id_inmueble,
                    id_unidad_funcional=id_unidad_funcional,
                    at_datetime=at_datetime,
                ),
            ).scalar_one_or_none()
            is not None
        )

    def has_current_disponibilidad_no_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
        filters = self._disp_object_filter(
            id_inmueble=id_inmueble, id_unidad_funcional=id_unidad_funcional
        )
        stmt = text(
            f"""
            SELECT 1
            FROM disponibilidad
            WHERE deleted_at IS NULL
              AND {filters}
              AND fecha_desde <= :at_datetime
              AND (fecha_hasta IS NULL OR fecha_hasta >= :at_datetime)
              AND UPPER(estado_disponibilidad) <> 'DISPONIBLE'
            """
        )
        return (
            self.db.execute(
                stmt,
                self._disp_object_params(
                    id_inmueble=id_inmueble,
                    id_unidad_funcional=id_unidad_funcional,
                    at_datetime=at_datetime,
                ),
            ).scalar_one_or_none()
            is not None
        )

    def has_conflicting_active_reserva_locativa(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
        exclude_id_reserva_locativa: int | None = None,
    ) -> bool:
        state_list = ", ".join(f"'{s}'" for s in sorted(conflict_states))
        if id_inmueble is not None:
            object_filter = "rlo.id_inmueble = :id_inmueble"
            params: dict[str, Any] = {"id_inmueble": id_inmueble}
        else:
            object_filter = "rlo.id_unidad_funcional = :id_unidad_funcional"
            params = {"id_unidad_funcional": id_unidad_funcional}

        exclude_clause = ""
        if exclude_id_reserva_locativa is not None:
            exclude_clause = "AND rl.id_reserva_locativa <> :exclude_id"
            params["exclude_id"] = exclude_id_reserva_locativa

        stmt = text(
            f"""
            SELECT 1
            FROM reserva_locativa_objeto rlo
            JOIN reserva_locativa rl ON rl.id_reserva_locativa = rlo.id_reserva_locativa
            WHERE rlo.deleted_at IS NULL
              AND rl.deleted_at IS NULL
              AND {object_filter}
              AND LOWER(rl.estado_reserva) IN ({state_list})
              {exclude_clause}
            LIMIT 1
            """
        )
        return self.db.execute(stmt, params).scalar_one_or_none() is not None

    # ── reserva_locativa CRUD ─────────────────────────────────────────────────

    def _reserva_locativa_obj_rows_to_list(self, rows: Any) -> list[dict[str, Any]]:
        return [
            {
                "id_reserva_locativa_objeto": row["id_reserva_locativa_objeto"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def _get_objetos_for_reserva_locativa(
        self, id_reserva_locativa: int
    ) -> list[dict[str, Any]]:
        stmt = text(
            """
            SELECT id_reserva_locativa_objeto, id_inmueble, id_unidad_funcional, observaciones
            FROM reserva_locativa_objeto
            WHERE id_reserva_locativa = :id AND deleted_at IS NULL
            ORDER BY id_reserva_locativa_objeto
            """
        )
        rows = self.db.execute(stmt, {"id": id_reserva_locativa}).mappings().all()
        return self._reserva_locativa_obj_rows_to_list(rows)

    def create_reserva_locativa_sin_commit(
        self, payload: Any, objetos: list[Any]
    ) -> dict[str, Any]:
        values = self._values(payload)

        insert_reserva = text(
            """
            INSERT INTO reserva_locativa (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                codigo_reserva, fecha_reserva, estado_reserva,
                fecha_vencimiento, observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :codigo_reserva, :fecha_reserva, :estado_reserva,
                :fecha_vencimiento, :observaciones
            )
            RETURNING id_reserva_locativa
            """
        )

        insert_objeto = text(
            """
            INSERT INTO reserva_locativa_objeto (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_reserva_locativa, id_inmueble, id_unidad_funcional, observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_reserva_locativa, :id_inmueble, :id_unidad_funcional, :observaciones
            )
            RETURNING id_reserva_locativa_objeto
            """
        )

        row = self.db.execute(
            insert_reserva,
            {
                "uid_global": values["uid_global"],
                "version_registro": values["version_registro"],
                "created_at": values["created_at"],
                "updated_at": values["updated_at"],
                "id_instalacion_origen": values["id_instalacion_origen"],
                "id_instalacion_ultima_modificacion": values["id_instalacion_ultima_modificacion"],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "codigo_reserva": values["codigo_reserva"],
                "fecha_reserva": values["fecha_reserva"],
                "estado_reserva": values["estado_reserva"],
                "fecha_vencimiento": values["fecha_vencimiento"],
                "observaciones": values["observaciones"],
            },
        ).mappings().one()
        id_reserva_locativa = row["id_reserva_locativa"]

        created_objetos: list[dict[str, Any]] = []
        for objeto in objetos:
            obj_values = self._values(objeto)
            obj_row = self.db.execute(
                insert_objeto,
                {
                    "uid_global": obj_values["uid_global"],
                    "version_registro": obj_values["version_registro"],
                    "created_at": obj_values["created_at"],
                    "updated_at": obj_values["updated_at"],
                    "id_instalacion_origen": obj_values["id_instalacion_origen"],
                    "id_instalacion_ultima_modificacion": obj_values["id_instalacion_ultima_modificacion"],
                    "op_id_alta": obj_values["op_id_alta"],
                    "op_id_ultima_modificacion": obj_values["op_id_ultima_modificacion"],
                    "id_reserva_locativa": id_reserva_locativa,
                    "id_inmueble": obj_values["id_inmueble"],
                    "id_unidad_funcional": obj_values["id_unidad_funcional"],
                    "observaciones": obj_values["observaciones"],
                },
            ).mappings().one()
            created_objetos.append(
                {
                    "id_reserva_locativa_objeto": obj_row["id_reserva_locativa_objeto"],
                    "id_inmueble": obj_values["id_inmueble"],
                    "id_unidad_funcional": obj_values["id_unidad_funcional"],
                    "observaciones": obj_values["observaciones"],
                }
            )

        return {
            "id_reserva_locativa": id_reserva_locativa,
            "uid_global": values["uid_global"],
            "version_registro": values["version_registro"],
            "codigo_reserva": values["codigo_reserva"],
            "fecha_reserva": values["fecha_reserva"],
            "estado_reserva": values["estado_reserva"],
            "fecha_vencimiento": values["fecha_vencimiento"],
            "observaciones": values["observaciones"],
            "objetos": created_objetos,
            "deleted_at": None,
        }

    def create_reserva_locativa(
        self, payload: Any, objetos: list[Any]
    ) -> dict[str, Any]:
        try:
            result = self.create_reserva_locativa_sin_commit(payload, objetos)
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def get_reserva_locativa(self, id_reserva_locativa: int) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_reserva_locativa, uid_global, version_registro,
                codigo_reserva, fecha_reserva, estado_reserva,
                fecha_vencimiento, observaciones, deleted_at
            FROM reserva_locativa
            WHERE id_reserva_locativa = :id
            """
        )
        row = self.db.execute(stmt, {"id": id_reserva_locativa}).mappings().one_or_none()
        if row is None:
            return None
        objetos = self._get_objetos_for_reserva_locativa(id_reserva_locativa)
        return {
            "id_reserva_locativa": row["id_reserva_locativa"],
            "uid_global": str(row["uid_global"]),
            "version_registro": row["version_registro"],
            "codigo_reserva": row["codigo_reserva"],
            "fecha_reserva": row["fecha_reserva"],
            "estado_reserva": row["estado_reserva"],
            "fecha_vencimiento": row["fecha_vencimiento"],
            "observaciones": row["observaciones"],
            "deleted_at": row["deleted_at"],
            "objetos": objetos,
        }

    def confirmar_reserva_locativa_sin_commit(
        self, payload: Any, outbox_event: OutboxEventPayload
    ) -> dict[str, Any]:
        values = self._values(payload)
        outbox_repo = OutboxRepository(self.db)

        stmt = text(
            """
            UPDATE reserva_locativa
            SET
                estado_reserva = :estado_reserva,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_reserva_locativa = :id_reserva_locativa
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_reserva_locativa, uid_global, version_registro,
                codigo_reserva, fecha_reserva, estado_reserva,
                fecha_vencimiento, observaciones
            """
        )

        updated = self.db.execute(
            stmt,
            {
                "id_reserva_locativa": values["id_reserva_locativa"],
                "estado_reserva": values["estado_reserva"],
                "version_registro_actual": values["version_registro_actual"],
                "version_registro_nueva": values["version_registro_nueva"],
                "updated_at": values["updated_at"],
                "id_instalacion_ultima_modificacion": values["id_instalacion_ultima_modificacion"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            },
        ).mappings().one_or_none()
        if updated is None:
            return {"status": "CONCURRENCY_ERROR"}

        id_reserva = updated["id_reserva_locativa"]
        objetos = self._get_objetos_for_reserva_locativa(id_reserva)

        outbox_values = self._values(outbox_event)
        outbox_repo.add_event(
            event_type=outbox_values["event_type"],
            aggregate_type=outbox_values["aggregate_type"],
            aggregate_id=outbox_values["aggregate_id"],
            payload=outbox_values["payload"],
            occurred_at=outbox_values["occurred_at"],
            status=outbox_values.get("status", "PENDING"),
        )

        return {
            "status": "OK",
            "data": {
                "id_reserva_locativa": id_reserva,
                "uid_global": str(updated["uid_global"]),
                "version_registro": updated["version_registro"],
                "codigo_reserva": updated["codigo_reserva"],
                "fecha_reserva": updated["fecha_reserva"],
                "estado_reserva": updated["estado_reserva"],
                "fecha_vencimiento": updated["fecha_vencimiento"],
                "observaciones": updated["observaciones"],
                "objetos": objetos,
                "deleted_at": None,
            },
        }

    def confirmar_reserva_locativa(
        self, payload: Any, outbox_event: OutboxEventPayload
    ) -> dict[str, Any]:
        try:
            result = self.confirmar_reserva_locativa_sin_commit(payload, outbox_event)
            if result.get("status") == "CONCURRENCY_ERROR":
                self.db.rollback()
                return result
            self.db.commit()
            return result
        except Exception:
            self.db.rollback()
            raise

    def cancel_reserva_locativa(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)

        stmt = text(
            """
            UPDATE reserva_locativa
            SET
                estado_reserva = :estado_reserva,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_reserva_locativa = :id_reserva_locativa
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_reserva_locativa, uid_global, version_registro,
                codigo_reserva, fecha_reserva, estado_reserva,
                fecha_vencimiento, observaciones
            """
        )

        try:
            updated = self.db.execute(
                stmt,
                {
                    "id_reserva_locativa": values["id_reserva_locativa"],
                    "estado_reserva": values["estado_reserva"],
                    "version_registro_actual": values["version_registro_actual"],
                    "version_registro_nueva": values["version_registro_nueva"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_ultima_modificacion": values["id_instalacion_ultima_modificacion"],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            id_reserva = updated["id_reserva_locativa"]
            objetos = self._get_objetos_for_reserva_locativa(id_reserva)
            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_reserva_locativa": id_reserva,
                    "uid_global": str(updated["uid_global"]),
                    "version_registro": updated["version_registro"],
                    "codigo_reserva": updated["codigo_reserva"],
                    "fecha_reserva": updated["fecha_reserva"],
                    "estado_reserva": updated["estado_reserva"],
                    "fecha_vencimiento": updated["fecha_vencimiento"],
                    "observaciones": updated["observaciones"],
                    "objetos": objetos,
                    "deleted_at": None,
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def has_entrega_for_contrato(self, id_contrato_alquiler: int) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM entrega_locativa
            WHERE id_contrato_alquiler = :id AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(stmt, {"id": id_contrato_alquiler}).scalar_one_or_none()
            is not None
        )

    def create_entrega_locativa_sin_commit(
        self, payload: Any, outbox_event: Any
    ) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text(
            """
            INSERT INTO entrega_locativa (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_contrato_alquiler, fecha_entrega, observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_contrato_alquiler, :fecha_entrega, :observaciones
            )
            RETURNING
                id_entrega_locativa, uid_global, version_registro,
                id_contrato_alquiler, fecha_entrega, observaciones, deleted_at
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
                "id_instalacion_ultima_modificacion": values["id_instalacion_ultima_modificacion"],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_contrato_alquiler": values["id_contrato_alquiler"],
                "fecha_entrega": values["fecha_entrega"],
                "observaciones": values["observaciones"],
            },
        ).mappings().one()

        outbox_values = self._values(outbox_event)
        OutboxRepository(self.db).add_event(
            event_type=outbox_values["event_type"],
            aggregate_type=outbox_values["aggregate_type"],
            aggregate_id=outbox_values["aggregate_id"],
            payload=outbox_values["payload"],
            occurred_at=outbox_values["occurred_at"],
            status=outbox_values.get("status", "PENDING"),
        )

        return {
            "id_entrega_locativa": row["id_entrega_locativa"],
            "uid_global": str(row["uid_global"]),
            "version_registro": row["version_registro"],
            "id_contrato_alquiler": row["id_contrato_alquiler"],
            "fecha_entrega": row["fecha_entrega"],
            "observaciones": row["observaciones"],
            "deleted_at": None,
        }

    def has_ocupacion_activa_for_contrato(self, id_contrato_alquiler: int) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM contrato_objeto_locativo col
            JOIN ocupacion o ON (
                (col.id_inmueble IS NOT NULL
                    AND o.id_inmueble = col.id_inmueble
                    AND o.id_unidad_funcional IS NULL)
                OR
                (col.id_unidad_funcional IS NOT NULL
                    AND o.id_unidad_funcional = col.id_unidad_funcional
                    AND o.id_inmueble IS NULL)
            )
            WHERE col.id_contrato_alquiler = :id
              AND col.deleted_at IS NULL
              AND o.deleted_at IS NULL
              AND UPPER(o.tipo_ocupacion) = 'ALQUILER'
              AND o.fecha_hasta IS NULL
            LIMIT 1
            """
        )
        return (
            self.db.execute(stmt, {"id": id_contrato_alquiler}).scalar_one_or_none()
            is not None
        )

    def has_restitucion_for_contrato(self, id_contrato_alquiler: int) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM restitucion_locativa
            WHERE id_contrato_alquiler = :id AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(stmt, {"id": id_contrato_alquiler}).scalar_one_or_none()
            is not None
        )

    def create_restitucion_locativa_sin_commit(
        self, payload: Any, outbox_event: Any
    ) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text(
            """
            INSERT INTO restitucion_locativa (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_contrato_alquiler, fecha_restitucion, estado_inmueble, observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_contrato_alquiler, :fecha_restitucion, :estado_inmueble, :observaciones
            )
            RETURNING
                id_restitucion_locativa, uid_global, version_registro,
                id_contrato_alquiler, fecha_restitucion, estado_inmueble, observaciones, deleted_at
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
                "id_instalacion_ultima_modificacion": values["id_instalacion_ultima_modificacion"],
                "op_id_alta": values["op_id_alta"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                "id_contrato_alquiler": values["id_contrato_alquiler"],
                "fecha_restitucion": values["fecha_restitucion"],
                "estado_inmueble": values["estado_inmueble"],
                "observaciones": values["observaciones"],
            },
        ).mappings().one()

        outbox_values = self._values(outbox_event)
        OutboxRepository(self.db).add_event(
            event_type=outbox_values["event_type"],
            aggregate_type=outbox_values["aggregate_type"],
            aggregate_id=outbox_values["aggregate_id"],
            payload=outbox_values["payload"],
            occurred_at=outbox_values["occurred_at"],
            status=outbox_values.get("status", "PENDING"),
        )

        return {
            "id_restitucion_locativa": row["id_restitucion_locativa"],
            "uid_global": str(row["uid_global"]),
            "version_registro": row["version_registro"],
            "id_contrato_alquiler": row["id_contrato_alquiler"],
            "fecha_restitucion": row["fecha_restitucion"],
            "estado_inmueble": row["estado_inmueble"],
            "observaciones": row["observaciones"],
            "deleted_at": None,
        }

    def has_contrato_for_reserva_locativa(self, id_reserva_locativa: int) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM contrato_alquiler
            WHERE id_reserva_locativa = :id AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(stmt, {"id": id_reserva_locativa}).scalar_one_or_none()
            is not None
        )

    def has_reserva_locativa_for_solicitud(self, id_solicitud_alquiler: int) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM reserva_locativa
            WHERE id_solicitud_alquiler = :id AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(stmt, {"id": id_solicitud_alquiler}).scalar_one_or_none()
            is not None
        )

    def vincular_solicitud_a_reserva_locativa(
        self, id_reserva_locativa: int, id_solicitud_alquiler: int
    ) -> None:
        stmt = text(
            """
            UPDATE reserva_locativa
            SET id_solicitud_alquiler = :id_solicitud_alquiler
            WHERE id_reserva_locativa = :id_reserva_locativa
            """
        )
        self.db.execute(
            stmt,
            {
                "id_reserva_locativa": id_reserva_locativa,
                "id_solicitud_alquiler": id_solicitud_alquiler,
            },
        )

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

    # ── solicitud_alquiler ────────────────────────────────────────────────────

    def _solicitud_row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "id_solicitud_alquiler": row["id_solicitud_alquiler"],
            "uid_global": str(row["uid_global"]),
            "version_registro": row["version_registro"],
            "codigo_solicitud": row["codigo_solicitud"],
            "fecha_solicitud": row["fecha_solicitud"],
            "estado_solicitud": row["estado_solicitud"],
            "observaciones": row["observaciones"],
            "deleted_at": row["deleted_at"],
        }

    def create_solicitud_alquiler(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text(
            """
            INSERT INTO solicitud_alquiler (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                codigo_solicitud, fecha_solicitud, estado_solicitud, observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :codigo_solicitud, :fecha_solicitud, :estado_solicitud, :observaciones
            )
            RETURNING
                id_solicitud_alquiler, uid_global, version_registro,
                codigo_solicitud, fecha_solicitud, estado_solicitud, observaciones, deleted_at
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
                    "id_instalacion_ultima_modificacion": values["id_instalacion_ultima_modificacion"],
                    "op_id_alta": values["op_id_alta"],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    "codigo_solicitud": values["codigo_solicitud"],
                    "fecha_solicitud": values["fecha_solicitud"],
                    "estado_solicitud": values["estado_solicitud"],
                    "observaciones": values["observaciones"],
                },
            ).mappings().one()
            self.db.commit()
            return self._solicitud_row_to_dict(row)
        except Exception:
            self.db.rollback()
            raise

    def get_solicitud_alquiler(self, id_solicitud_alquiler: int) -> dict[str, Any] | None:
        stmt = text(
            """
            SELECT
                id_solicitud_alquiler, uid_global, version_registro,
                codigo_solicitud, fecha_solicitud, estado_solicitud, observaciones, deleted_at
            FROM solicitud_alquiler
            WHERE id_solicitud_alquiler = :id
            """
        )
        row = self.db.execute(stmt, {"id": id_solicitud_alquiler}).mappings().one_or_none()
        if row is None:
            return None
        return self._solicitud_row_to_dict(row)

    def transicionar_solicitud_alquiler(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        stmt = text(
            """
            UPDATE solicitud_alquiler
            SET
                estado_solicitud = :estado_solicitud,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_solicitud_alquiler = :id_solicitud_alquiler
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_solicitud_alquiler, uid_global, version_registro,
                codigo_solicitud, fecha_solicitud, estado_solicitud, observaciones, deleted_at
            """
        )
        try:
            updated = self.db.execute(
                stmt,
                {
                    "id_solicitud_alquiler": values["id_solicitud_alquiler"],
                    "estado_solicitud": values["estado_solicitud"],
                    "version_registro_actual": values["version_registro_actual"],
                    "version_registro_nueva": values["version_registro_nueva"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_ultima_modificacion": values["id_instalacion_ultima_modificacion"],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}
            self.db.commit()
            return {"status": "OK", "data": self._solicitud_row_to_dict(updated)}
        except Exception:
            self.db.rollback()
            raise

    def _values(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        if is_dataclass(payload):
            return asdict(payload)
        return vars(payload)
