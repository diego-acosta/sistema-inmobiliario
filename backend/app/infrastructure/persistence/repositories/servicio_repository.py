from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy import text

from app.infrastructure.persistence.base_repository import BaseRepository


class ServicioRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    def get_servicio_for_update(self, id_servicio: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_servicio,
                codigo_servicio,
                nombre_servicio,
                descripcion,
                estado_servicio,
                version_registro
            FROM servicio
            WHERE id_servicio = :id_servicio
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_servicio": id_servicio}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_servicio": row["id_servicio"],
            "codigo_servicio": row["codigo_servicio"],
            "nombre_servicio": row["nombre_servicio"],
            "descripcion": row["descripcion"],
            "estado_servicio": row["estado_servicio"],
            "version_registro": row["version_registro"],
        }

    def get_servicios(self) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_servicio,
                codigo_servicio,
                nombre_servicio,
                descripcion,
                estado_servicio
            FROM servicio
            WHERE deleted_at IS NULL
            ORDER BY id_servicio
            """
        )
        result = self.db.execute(statement)
        rows = result.mappings().all()
        return [
            {
                "id_servicio": row["id_servicio"],
                "codigo_servicio": row["codigo_servicio"],
                "nombre_servicio": row["nombre_servicio"],
                "descripcion": row["descripcion"],
                "estado_servicio": row["estado_servicio"],
            }
            for row in rows
        ]

    def get_servicio_inmuebles(self, id_servicio: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_inmueble_servicio,
                id_inmueble,
                id_servicio,
                estado,
                fecha_alta
            FROM inmueble_servicio
            WHERE id_servicio = :id_servicio
              AND deleted_at IS NULL
            ORDER BY id_inmueble_servicio
            """
        )
        result = self.db.execute(statement, {"id_servicio": id_servicio})
        rows = result.mappings().all()
        return [
            {
                "id_inmueble_servicio": row["id_inmueble_servicio"],
                "id_inmueble": row["id_inmueble"],
                "id_servicio": row["id_servicio"],
                "estado": row["estado"],
                "fecha_alta": (
                    row["fecha_alta"].isoformat() if row["fecha_alta"] is not None else None
                ),
            }
            for row in rows
        ]

    def get_servicio_unidades_funcionales(
        self, id_servicio: int
    ) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_unidad_funcional_servicio,
                id_unidad_funcional,
                id_servicio,
                estado,
                fecha_alta
            FROM unidad_funcional_servicio
            WHERE id_servicio = :id_servicio
              AND deleted_at IS NULL
            ORDER BY id_unidad_funcional_servicio
            """
        )
        result = self.db.execute(statement, {"id_servicio": id_servicio})
        rows = result.mappings().all()
        return [
            {
                "id_unidad_funcional_servicio": row["id_unidad_funcional_servicio"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "id_servicio": row["id_servicio"],
                "estado": row["estado"],
                "fecha_alta": (
                    row["fecha_alta"].isoformat() if row["fecha_alta"] is not None else None
                ),
            }
            for row in rows
        ]

    def get_servicio(self, id_servicio: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_servicio,
                codigo_servicio,
                nombre_servicio,
                descripcion,
                estado_servicio
            FROM servicio
            WHERE id_servicio = :id_servicio
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_servicio": id_servicio}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_servicio": row["id_servicio"],
            "codigo_servicio": row["codigo_servicio"],
            "nombre_servicio": row["nombre_servicio"],
            "descripcion": row["descripcion"],
            "estado_servicio": row["estado_servicio"],
        }

    def servicio_activo_exists(self, id_servicio: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM servicio
            WHERE id_servicio = :id_servicio
              AND estado_servicio = 'ACTIVO'
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(statement, {"id_servicio": id_servicio}).scalar_one_or_none()
            is not None
        )

    def servicio_asociado_a_inmueble(
        self, id_servicio: int, id_inmueble: int
    ) -> bool:
        statement = text(
            """
            SELECT 1
            FROM inmueble_servicio
            WHERE id_servicio = :id_servicio
              AND id_inmueble = :id_inmueble
              AND estado = 'ACTIVO'
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(
                statement,
                {"id_servicio": id_servicio, "id_inmueble": id_inmueble},
            ).scalar_one_or_none()
            is not None
        )

    def servicio_asociado_a_unidad_funcional(
        self, id_servicio: int, id_unidad_funcional: int
    ) -> bool:
        statement = text(
            """
            SELECT 1
            FROM unidad_funcional_servicio
            WHERE id_servicio = :id_servicio
              AND id_unidad_funcional = :id_unidad_funcional
              AND estado = 'ACTIVO'
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(
                statement,
                {
                    "id_servicio": id_servicio,
                    "id_unidad_funcional": id_unidad_funcional,
                },
            ).scalar_one_or_none()
            is not None
        )

    def factura_servicio_activa_exists(
        self, proveedor: str, numero_factura: str
    ) -> bool:
        statement = text(
            """
            SELECT 1
            FROM factura_servicio
            WHERE proveedor = :proveedor
              AND numero_factura = :numero_factura
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(
                statement,
                {"proveedor": proveedor, "numero_factura": numero_factura},
            ).scalar_one_or_none()
            is not None
        )

    def _factura_servicio_row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "id_factura_servicio": row["id_factura_servicio"],
            "uid_global": str(row["uid_global"]),
            "version_registro": row["version_registro"],
            "id_servicio": row["id_servicio"],
            "id_inmueble": row["id_inmueble"],
            "id_unidad_funcional": row["id_unidad_funcional"],
            "proveedor": row["proveedor"],
            "numero_factura": row["numero_factura"],
            "fecha_emision": row["fecha_emision"].isoformat(),
            "fecha_vencimiento": (
                row["fecha_vencimiento"].isoformat()
                if row["fecha_vencimiento"] is not None
                else None
            ),
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
            "importe_total": float(row["importe_total"]),
            "estado_factura_servicio": row["estado_factura_servicio"],
            "observaciones": row["observaciones"],
        }

    def get_factura_servicio(
        self, id_factura_servicio: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_factura_servicio,
                uid_global,
                version_registro,
                id_servicio,
                id_inmueble,
                id_unidad_funcional,
                proveedor,
                numero_factura,
                fecha_emision,
                fecha_vencimiento,
                periodo_desde,
                periodo_hasta,
                importe_total,
                estado_factura_servicio,
                observaciones
            FROM factura_servicio
            WHERE id_factura_servicio = :id_factura_servicio
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement,
            {"id_factura_servicio": id_factura_servicio},
        ).mappings().one_or_none()
        if row is None:
            return None
        return self._factura_servicio_row_to_dict(row)

    def get_facturas_servicio(self) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_factura_servicio,
                uid_global,
                version_registro,
                id_servicio,
                id_inmueble,
                id_unidad_funcional,
                proveedor,
                numero_factura,
                fecha_emision,
                fecha_vencimiento,
                periodo_desde,
                periodo_hasta,
                importe_total,
                estado_factura_servicio,
                observaciones
            FROM factura_servicio
            WHERE deleted_at IS NULL
            ORDER BY id_factura_servicio
            """
        )
        rows = self.db.execute(statement).mappings().all()
        return [self._factura_servicio_row_to_dict(row) for row in rows]

    def create_factura_servicio(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        statement = text(
            """
            INSERT INTO factura_servicio (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_servicio,
                id_inmueble,
                id_unidad_funcional,
                proveedor,
                numero_factura,
                fecha_emision,
                fecha_vencimiento,
                periodo_desde,
                periodo_hasta,
                importe_total,
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
                :id_servicio,
                :id_inmueble,
                :id_unidad_funcional,
                :proveedor,
                :numero_factura,
                :fecha_emision,
                :fecha_vencimiento,
                :periodo_desde,
                :periodo_hasta,
                :importe_total,
                :observaciones
            )
            RETURNING
                id_factura_servicio,
                uid_global,
                version_registro,
                id_servicio,
                id_inmueble,
                id_unidad_funcional,
                proveedor,
                numero_factura,
                fecha_emision,
                fecha_vencimiento,
                periodo_desde,
                periodo_hasta,
                importe_total,
                estado_factura_servicio,
                observaciones
            """
        )

        try:
            row = self.db.execute(statement, values).mappings().one()
            self.db.commit()
            return self._factura_servicio_row_to_dict(row)
        except Exception:
            self.db.rollback()
            raise

    def create_servicio(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
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
            "codigo_servicio": values["codigo_servicio"],
            "nombre_servicio": values["nombre_servicio"],
            "descripcion": values["descripcion"],
            "estado_servicio": values["estado_servicio"],
        }

        statement = text(
            """
            INSERT INTO servicio (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_servicio,
                nombre_servicio,
                descripcion,
                estado_servicio
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
                :codigo_servicio,
                :nombre_servicio,
                :descripcion,
                :estado_servicio
            )
            RETURNING
                id_servicio,
                uid_global,
                version_registro,
                codigo_servicio,
                nombre_servicio,
                estado_servicio
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_servicio": row["id_servicio"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "codigo_servicio": row["codigo_servicio"],
                "nombre_servicio": row["nombre_servicio"],
                "estado_servicio": row["estado_servicio"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_servicio(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_servicio": values["id_servicio"],
            "codigo_servicio": values["codigo_servicio"],
            "nombre_servicio": values["nombre_servicio"],
            "descripcion": values["descripcion"],
            "estado_servicio": values["estado_servicio"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE servicio
            SET
                codigo_servicio = :codigo_servicio,
                nombre_servicio = :nombre_servicio,
                descripcion = :descripcion,
                estado_servicio = :estado_servicio,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_servicio = :id_servicio
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_servicio,
                version_registro,
                codigo_servicio,
                nombre_servicio,
                descripcion,
                estado_servicio
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_servicio": row["id_servicio"],
                "version_registro": row["version_registro"],
                "codigo_servicio": row["codigo_servicio"],
                "nombre_servicio": row["nombre_servicio"],
                "descripcion": row["descripcion"],
                "estado_servicio": row["estado_servicio"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_servicio(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_servicio": values["id_servicio"],
            "version_registro_actual": values["version_registro_actual"],
            "version_registro_nueva": values["version_registro_nueva"],
            "updated_at": values["updated_at"],
            "deleted_at": values["deleted_at"],
            "id_instalacion_ultima_modificacion": values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
        }

        statement = text(
            """
            UPDATE servicio
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_servicio = :id_servicio
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_servicio,
                version_registro
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return {
                "id_servicio": row["id_servicio"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise
