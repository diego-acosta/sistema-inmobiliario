from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy import text

from app.infrastructure.persistence.base_repository import BaseRepository


INTEGRACION_COMERCIAL_EVENT_TYPES = (
    "venta_confirmada",
    "escrituracion_registrada",
)


class InmuebleRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    def inmueble_exists(self, id_inmueble: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM inmueble
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        )
        result = self.db.execute(
            statement, {"id_inmueble": id_inmueble}
        ).scalar_one_or_none()
        return result is not None

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM unidad_funcional
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND deleted_at IS NULL
            """
        )
        result = self.db.execute(
            statement, {"id_unidad_funcional": id_unidad_funcional}
        ).scalar_one_or_none()
        return result is not None

    def get_unidades_funcionales(self, id_inmueble: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_unidad_funcional,
                id_inmueble,
                codigo_unidad,
                nombre_unidad,
                superficie,
                estado_administrativo,
                estado_operativo,
                observaciones
            FROM unidad_funcional
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_unidad_funcional
            """
        )
        result = self.db.execute(statement, {"id_inmueble": id_inmueble})
        rows = result.mappings().all()
        return [
            {
                "id_unidad_funcional": row["id_unidad_funcional"],
                "id_inmueble": row["id_inmueble"],
                "codigo_unidad": row["codigo_unidad"],
                "nombre_unidad": row["nombre_unidad"],
                "superficie": row["superficie"],
                "estado_administrativo": row["estado_administrativo"],
                "estado_operativo": row["estado_operativo"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_inmueble_servicios(self, id_inmueble: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_inmueble_servicio,
                id_inmueble,
                id_servicio,
                estado,
                fecha_alta
            FROM inmueble_servicio
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_inmueble_servicio
            """
        )
        result = self.db.execute(statement, {"id_inmueble": id_inmueble})
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

    def get_inmueble_disponibilidades(self, id_inmueble: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_disponibilidad,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
                observaciones
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        )
        result = self.db.execute(statement, {"id_inmueble": id_inmueble})
        rows = result.mappings().all()
        return [
            {
                "id_disponibilidad": row["id_disponibilidad"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "estado_disponibilidad": row["estado_disponibilidad"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "motivo": row["motivo"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_unidad_funcional_disponibilidades(
        self, id_unidad_funcional: int
    ) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_disponibilidad,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
                observaciones
            FROM disponibilidad
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        )
        result = self.db.execute(
            statement, {"id_unidad_funcional": id_unidad_funcional}
        )
        rows = result.mappings().all()
        return [
            {
                "id_disponibilidad": row["id_disponibilidad"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "estado_disponibilidad": row["estado_disponibilidad"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "motivo": row["motivo"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_inmueble_ocupaciones(self, id_inmueble: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_ocupacion,
                id_inmueble,
                id_unidad_funcional,
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
                observaciones
            FROM ocupacion
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_ocupacion
            """
        )
        result = self.db.execute(statement, {"id_inmueble": id_inmueble})
        rows = result.mappings().all()
        return [
            {
                "id_ocupacion": row["id_ocupacion"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "tipo_ocupacion": row["tipo_ocupacion"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "descripcion": row["descripcion"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_unidad_funcional_ocupaciones(
        self, id_unidad_funcional: int
    ) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_ocupacion,
                id_inmueble,
                id_unidad_funcional,
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
                observaciones
            FROM ocupacion
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND deleted_at IS NULL
            ORDER BY id_ocupacion
            """
        )
        result = self.db.execute(
            statement, {"id_unidad_funcional": id_unidad_funcional}
        )
        rows = result.mappings().all()
        return [
            {
                "id_ocupacion": row["id_ocupacion"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "tipo_ocupacion": row["tipo_ocupacion"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "descripcion": row["descripcion"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_inmueble_integracion_trazabilidad(
        self, id_inmueble: int
    ) -> list[dict[str, Any]]:
        if not self.inmueble_exists(id_inmueble):
            return []
        return self._get_integracion_trazabilidad_activo(
            id_inmueble=id_inmueble,
            id_unidad_funcional=None,
        )

    def get_unidad_funcional_integracion_trazabilidad(
        self, id_unidad_funcional: int
    ) -> list[dict[str, Any]]:
        if not self.unidad_funcional_exists(id_unidad_funcional):
            return []
        return self._get_integracion_trazabilidad_activo(
            id_inmueble=None,
            id_unidad_funcional=id_unidad_funcional,
        )

    def get_disponibilidad_for_update(
        self, id_disponibilidad: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_disponibilidad,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
                observaciones,
                version_registro
            FROM disponibilidad
            WHERE id_disponibilidad = :id_disponibilidad
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_disponibilidad": id_disponibilidad}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_disponibilidad": row["id_disponibilidad"],
            "id_inmueble": row["id_inmueble"],
            "id_unidad_funcional": row["id_unidad_funcional"],
            "estado_disponibilidad": row["estado_disponibilidad"],
            "fecha_desde": row["fecha_desde"],
            "fecha_hasta": row["fecha_hasta"],
            "motivo": row["motivo"],
            "observaciones": row["observaciones"],
            "version_registro": row["version_registro"],
        }

    def _get_integracion_trazabilidad_activo(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
    ) -> list[dict[str, Any]]:
        if id_inmueble is not None:
            asset_filter = """
                voi.id_inmueble = :id_inmueble
                AND voi.id_unidad_funcional IS NULL
            """
            params = {"id_inmueble": id_inmueble}
        else:
            asset_filter = """
                voi.id_unidad_funcional = :id_unidad_funcional
                AND voi.id_inmueble IS NULL
            """
            params = {"id_unidad_funcional": id_unidad_funcional}

        ventas_rows = self.db.execute(
            text(
                f"""
                SELECT DISTINCT
                    v.id_venta,
                    v.id_reserva_venta,
                    v.codigo_venta,
                    v.fecha_venta,
                    v.estado_venta
                FROM venta v
                JOIN venta_objeto_inmobiliario voi
                  ON voi.id_venta = v.id_venta
                WHERE v.deleted_at IS NULL
                  AND voi.deleted_at IS NULL
                  AND {asset_filter}
                ORDER BY v.fecha_venta DESC, v.id_venta DESC
                """
            ),
            params,
        ).mappings().all()

        return [
            {
                "id_venta": row["id_venta"],
                "id_reserva_venta": row["id_reserva_venta"],
                "codigo_venta": row["codigo_venta"],
                "fecha_venta": row["fecha_venta"],
                "estado_venta": row["estado_venta"],
                "eventos": self._get_integracion_eventos_por_venta(row["id_venta"]),
            }
            for row in ventas_rows
        ]

    def _get_integracion_eventos_por_venta(self, id_venta: int) -> list[dict[str, Any]]:
        event_type_filters = ", ".join(
            f"'{event_type}'" for event_type in INTEGRACION_COMERCIAL_EVENT_TYPES
        )
        rows = self.db.execute(
            text(
                f"""
                SELECT
                    id,
                    event_type,
                    status,
                    occurred_at,
                    published_at
                FROM outbox_event
                WHERE aggregate_type = 'venta'
                  AND aggregate_id = :id_venta
                  AND event_type IN ({event_type_filters})
                ORDER BY occurred_at, id
                """
            ),
            {"id_venta": id_venta},
        ).mappings().all()

        return [
            {
                "id_evento_outbox": row["id"],
                "nombre_evento": row["event_type"],
                "estado": row["status"],
                "ocurrido_en": row["occurred_at"],
                "publicado_en": row["published_at"],
                "efecto_operativo_aplicado": self._get_efecto_operativo_aplicado(
                    event_type=row["event_type"],
                    event_status=row["status"],
                ),
            }
            for row in rows
        ]

    def _get_efecto_operativo_aplicado(
        self,
        *,
        event_type: str,
        event_status: str | None,
    ) -> dict[str, str | None]:
        normalized_type = (event_type or "").strip().lower()
        normalized_status = (event_status or "").strip().upper()

        if normalized_type == "venta_confirmada":
            return {
                "disponibilidad": "SIN_CAMBIO",
                "ocupacion": "SIN_CAMBIO",
            }

        if normalized_type == "escrituracion_registrada":
            disponibilidad = {
                "PENDING": "PENDIENTE",
                "PUBLISHED": "NO_DISPONIBLE",
                "REJECTED": "NO_APLICADO",
            }.get(normalized_status)
            return {
                "disponibilidad": disponibilidad,
                "ocupacion": "SIN_CAMBIO",
            }

        return {
            "disponibilidad": None,
            "ocupacion": None,
        }

    def get_ocupacion_for_update(self, id_ocupacion: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_ocupacion,
                id_inmueble,
                id_unidad_funcional,
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
                observaciones,
                version_registro
            FROM ocupacion
            WHERE id_ocupacion = :id_ocupacion
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_ocupacion": id_ocupacion}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_ocupacion": row["id_ocupacion"],
            "id_inmueble": row["id_inmueble"],
            "id_unidad_funcional": row["id_unidad_funcional"],
            "tipo_ocupacion": row["tipo_ocupacion"],
            "fecha_desde": row["fecha_desde"],
            "fecha_hasta": row["fecha_hasta"],
            "descripcion": row["descripcion"],
            "observaciones": row["observaciones"],
            "version_registro": row["version_registro"],
        }

    def get_unidad_funcional_servicios(
        self, id_unidad_funcional: int
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
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND deleted_at IS NULL
            ORDER BY id_unidad_funcional_servicio
            """
        )
        result = self.db.execute(
            statement, {"id_unidad_funcional": id_unidad_funcional}
        )
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

    def get_unidades_funcionales_global(self) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_unidad_funcional,
                id_inmueble,
                codigo_unidad,
                nombre_unidad,
                superficie,
                estado_administrativo,
                estado_operativo,
                observaciones
            FROM unidad_funcional
            WHERE deleted_at IS NULL
            ORDER BY id_unidad_funcional
            """
        )
        result = self.db.execute(statement)
        rows = result.mappings().all()
        return [
            {
                "id_unidad_funcional": row["id_unidad_funcional"],
                "id_inmueble": row["id_inmueble"],
                "codigo_unidad": row["codigo_unidad"],
                "nombre_unidad": row["nombre_unidad"],
                "superficie": row["superficie"],
                "estado_administrativo": row["estado_administrativo"],
                "estado_operativo": row["estado_operativo"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_unidad_funcional(self, id_unidad_funcional: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_unidad_funcional,
                id_inmueble,
                codigo_unidad,
                nombre_unidad,
                superficie,
                estado_administrativo,
                estado_operativo,
                observaciones
            FROM unidad_funcional
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_unidad_funcional": id_unidad_funcional}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_unidad_funcional": row["id_unidad_funcional"],
            "id_inmueble": row["id_inmueble"],
            "codigo_unidad": row["codigo_unidad"],
            "nombre_unidad": row["nombre_unidad"],
            "superficie": row["superficie"],
            "estado_administrativo": row["estado_administrativo"],
            "estado_operativo": row["estado_operativo"],
            "observaciones": row["observaciones"],
        }

    def get_unidad_funcional_for_update(
        self, id_unidad_funcional: int
    ) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_unidad_funcional,
                id_inmueble,
                codigo_unidad,
                nombre_unidad,
                superficie,
                estado_administrativo,
                estado_operativo,
                observaciones,
                version_registro
            FROM unidad_funcional
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_unidad_funcional": id_unidad_funcional}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_unidad_funcional": row["id_unidad_funcional"],
            "id_inmueble": row["id_inmueble"],
            "codigo_unidad": row["codigo_unidad"],
            "nombre_unidad": row["nombre_unidad"],
            "superficie": row["superficie"],
            "estado_administrativo": row["estado_administrativo"],
            "estado_operativo": row["estado_operativo"],
            "observaciones": row["observaciones"],
            "version_registro": row["version_registro"],
        }

    def get_inmuebles(self) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_inmueble,
                id_desarrollo,
                codigo_inmueble,
                nombre_inmueble,
                superficie,
                estado_administrativo,
                estado_juridico,
                observaciones
            FROM inmueble
            WHERE deleted_at IS NULL
            ORDER BY id_inmueble
            """
        )
        result = self.db.execute(statement)
        rows = result.mappings().all()
        return [
            {
                "id_inmueble": row["id_inmueble"],
                "id_desarrollo": row["id_desarrollo"],
                "codigo_inmueble": row["codigo_inmueble"],
                "nombre_inmueble": row["nombre_inmueble"],
                "superficie": row["superficie"],
                "estado_administrativo": row["estado_administrativo"],
                "estado_juridico": row["estado_juridico"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_inmueble(self, id_inmueble: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_inmueble,
                id_desarrollo,
                codigo_inmueble,
                nombre_inmueble,
                superficie,
                estado_administrativo,
                estado_juridico,
                observaciones
            FROM inmueble
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_inmueble": id_inmueble}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_inmueble": row["id_inmueble"],
            "id_desarrollo": row["id_desarrollo"],
            "codigo_inmueble": row["codigo_inmueble"],
            "nombre_inmueble": row["nombre_inmueble"],
            "superficie": row["superficie"],
            "estado_administrativo": row["estado_administrativo"],
            "estado_juridico": row["estado_juridico"],
            "observaciones": row["observaciones"],
        }

    def get_inmueble_for_update(self, id_inmueble: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_inmueble,
                id_desarrollo,
                codigo_inmueble,
                nombre_inmueble,
                superficie,
                estado_administrativo,
                estado_juridico,
                observaciones,
                version_registro
            FROM inmueble
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_inmueble": id_inmueble}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_inmueble": row["id_inmueble"],
            "id_desarrollo": row["id_desarrollo"],
            "codigo_inmueble": row["codigo_inmueble"],
            "nombre_inmueble": row["nombre_inmueble"],
            "superficie": row["superficie"],
            "estado_administrativo": row["estado_administrativo"],
            "estado_juridico": row["estado_juridico"],
            "observaciones": row["observaciones"],
            "version_registro": row["version_registro"],
        }

    def desarrollo_exists(self, id_desarrollo: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM desarrollo
            WHERE id_desarrollo = :id_desarrollo
              AND deleted_at IS NULL
            """
        )
        result = self.db.execute(
            statement, {"id_desarrollo": id_desarrollo}
        ).scalar_one_or_none()
        return result is not None

    def servicio_exists(self, id_servicio: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM servicio
            WHERE id_servicio = :id_servicio
              AND deleted_at IS NULL
            """
        )
        result = self.db.execute(
            statement, {"id_servicio": id_servicio}
        ).scalar_one_or_none()
        return result is not None

    def inmueble_servicio_exists(self, id_inmueble: int, id_servicio: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM inmueble_servicio
            WHERE id_inmueble = :id_inmueble
              AND id_servicio = :id_servicio
              AND deleted_at IS NULL
            """
        )
        result = self.db.execute(
            statement,
            {
                "id_inmueble": id_inmueble,
                "id_servicio": id_servicio,
            },
        ).scalar_one_or_none()
        return result is not None

    def unidad_funcional_servicio_exists(
        self, id_unidad_funcional: int, id_servicio: int
    ) -> bool:
        statement = text(
            """
            SELECT 1
            FROM unidad_funcional_servicio
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND id_servicio = :id_servicio
              AND deleted_at IS NULL
            """
        )
        result = self.db.execute(
            statement,
            {
                "id_unidad_funcional": id_unidad_funcional,
                "id_servicio": id_servicio,
            },
        ).scalar_one_or_none()
        return result is not None

    def create_inmueble(self, payload: Any) -> dict[str, Any]:
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
            "id_desarrollo": values["id_desarrollo"],
            "codigo_inmueble": values["codigo_inmueble"],
            "nombre_inmueble": values["nombre_inmueble"],
            "superficie": values["superficie"],
            "estado_administrativo": values["estado_administrativo"],
            "estado_juridico": values["estado_juridico"],
            "fecha_alta": values["created_at"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO inmueble (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_desarrollo,
                codigo_inmueble,
                nombre_inmueble,
                superficie,
                estado_administrativo,
                estado_juridico,
                fecha_alta,
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
                :id_desarrollo,
                :codigo_inmueble,
                :nombre_inmueble,
                :superficie,
                :estado_administrativo,
                :estado_juridico,
                :fecha_alta,
                :observaciones
            )
            RETURNING
                id_inmueble,
                uid_global,
                version_registro,
                codigo_inmueble,
                estado_administrativo,
                estado_juridico
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_inmueble": row["id_inmueble"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "codigo_inmueble": row["codigo_inmueble"],
                "estado_administrativo": row["estado_administrativo"],
                "estado_juridico": row["estado_juridico"],
            }
        except Exception:
            self.db.rollback()
            raise

    def create_inmueble_servicio(self, payload: Any) -> dict[str, Any]:
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
            "id_inmueble": values["id_inmueble"],
            "id_servicio": values["id_servicio"],
            "estado": values["estado"],
            "fecha_alta": values["created_at"],
        }

        statement = text(
            """
            INSERT INTO inmueble_servicio (
                id_inmueble_servicio,
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_inmueble,
                id_servicio,
                estado,
                fecha_alta
            )
            SELECT
                COALESCE(MAX(id_inmueble_servicio), 0) + 1,
                :uid_global,
                :version_registro,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_inmueble,
                :id_servicio,
                :estado,
                :fecha_alta
            FROM inmueble_servicio
            RETURNING
                id_inmueble_servicio,
                uid_global,
                version_registro,
                id_inmueble,
                id_servicio,
                estado
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_inmueble_servicio": row["id_inmueble_servicio"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "id_servicio": row["id_servicio"],
                "estado": row["estado"],
            }
        except Exception:
            self.db.rollback()
            raise

    def create_disponibilidad(self, payload: Any) -> dict[str, Any]:
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
            "id_inmueble": values["id_inmueble"],
            "id_unidad_funcional": values["id_unidad_funcional"],
            "estado_disponibilidad": values["estado_disponibilidad"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "motivo": values["motivo"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO disponibilidad (
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
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
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
                :estado_disponibilidad,
                :fecha_desde,
                :fecha_hasta,
                :motivo,
                :observaciones
            )
            RETURNING
                id_disponibilidad,
                uid_global,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
                observaciones
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_disponibilidad": row["id_disponibilidad"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "estado_disponibilidad": row["estado_disponibilidad"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "motivo": row["motivo"],
                "observaciones": row["observaciones"],
            }
        except Exception:
            self.db.rollback()
            raise

    def replace_disponibilidad_vigente(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        if values["id_inmueble"] is not None:
            parent_values = {"id_inmueble": values["id_inmueble"]}
            select_statement = text(
                """
                SELECT
                    id_disponibilidad,
                    id_inmueble,
                    id_unidad_funcional,
                    estado_disponibilidad,
                    fecha_desde,
                    fecha_hasta,
                    motivo,
                    observaciones,
                    version_registro
                FROM disponibilidad
                WHERE fecha_hasta IS NULL
                  AND deleted_at IS NULL
                  AND id_inmueble = :id_inmueble
                  AND id_unidad_funcional IS NULL
                ORDER BY id_disponibilidad
                FOR UPDATE
                """
            )
        else:
            parent_values = {"id_unidad_funcional": values["id_unidad_funcional"]}
            select_statement = text(
                """
                SELECT
                    id_disponibilidad,
                    id_inmueble,
                    id_unidad_funcional,
                    estado_disponibilidad,
                    fecha_desde,
                    fecha_hasta,
                    motivo,
                    observaciones,
                    version_registro
                FROM disponibilidad
                WHERE fecha_hasta IS NULL
                  AND deleted_at IS NULL
                  AND id_unidad_funcional = :id_unidad_funcional
                  AND id_inmueble IS NULL
                ORDER BY id_disponibilidad
                FOR UPDATE
                """
            )

        update_statement = text(
            """
            UPDATE disponibilidad
            SET
                fecha_hasta = :fecha_hasta,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_disponibilidad = :id_disponibilidad
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_disponibilidad
            """
        )

        insert_values = {
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
            "id_inmueble": values["id_inmueble"],
            "id_unidad_funcional": values["id_unidad_funcional"],
            "estado_disponibilidad": values["estado_disponibilidad"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": None,
            "motivo": values["motivo"],
            "observaciones": values["observaciones"],
        }

        insert_statement = text(
            """
            INSERT INTO disponibilidad (
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
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
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
                :estado_disponibilidad,
                :fecha_desde,
                :fecha_hasta,
                :motivo,
                :observaciones
            )
            RETURNING
                id_disponibilidad,
                uid_global,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
                observaciones
            """
        )

        try:
            open_rows = self.db.execute(
                select_statement, parent_values
            ).mappings().all()
            if len(open_rows) == 0:
                self.db.rollback()
                return {"status": "NO_OPEN"}
            if len(open_rows) > 1:
                self.db.rollback()
                return {"status": "MULTIPLE_OPEN"}

            current = open_rows[0]
            if values["fecha_desde"] < current["fecha_desde"]:
                self.db.rollback()
                return {"status": "INVALID_REPLACEMENT_DATE"}

            update_values = {
                "id_disponibilidad": current["id_disponibilidad"],
                "fecha_hasta": values["fecha_desde"],
                "version_registro_actual": current["version_registro"],
                "version_registro_nueva": current["version_registro"] + 1,
                "updated_at": values["updated_at"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            }

            updated = self.db.execute(
                update_statement, update_values
            ).mappings().one_or_none()
            if updated is None:
                self.db.rollback()
                return {"status": "NO_OPEN"}

            created = self.db.execute(
                insert_statement, insert_values
            ).mappings().one()
            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_disponibilidad": created["id_disponibilidad"],
                    "uid_global": str(created["uid_global"]),
                    "version_registro": created["version_registro"],
                    "id_inmueble": created["id_inmueble"],
                    "id_unidad_funcional": created["id_unidad_funcional"],
                    "estado_disponibilidad": created["estado_disponibilidad"],
                    "fecha_desde": created["fecha_desde"],
                    "fecha_hasta": created["fecha_hasta"],
                    "motivo": created["motivo"],
                    "observaciones": created["observaciones"],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def replace_disponibilidad_vigente_por_escrituracion(
        self,
        payload: Any,
        *,
        expected_current_state: str,
        already_applied_state: str,
    ) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        if values["id_inmueble"] is not None:
            parent_values = {"id_inmueble": values["id_inmueble"]}
            select_statement = text(
                """
                SELECT
                    id_disponibilidad,
                    id_inmueble,
                    id_unidad_funcional,
                    estado_disponibilidad,
                    fecha_desde,
                    fecha_hasta,
                    version_registro
                FROM disponibilidad
                WHERE fecha_hasta IS NULL
                  AND deleted_at IS NULL
                  AND id_inmueble = :id_inmueble
                  AND id_unidad_funcional IS NULL
                ORDER BY id_disponibilidad
                FOR UPDATE
                """
            )
        else:
            parent_values = {"id_unidad_funcional": values["id_unidad_funcional"]}
            select_statement = text(
                """
                SELECT
                    id_disponibilidad,
                    id_inmueble,
                    id_unidad_funcional,
                    estado_disponibilidad,
                    fecha_desde,
                    fecha_hasta,
                    version_registro
                FROM disponibilidad
                WHERE fecha_hasta IS NULL
                  AND deleted_at IS NULL
                  AND id_unidad_funcional = :id_unidad_funcional
                  AND id_inmueble IS NULL
                ORDER BY id_disponibilidad
                FOR UPDATE
                """
            )

        open_rows = self.db.execute(select_statement, parent_values).mappings().all()
        if len(open_rows) == 0:
            return {"status": "NO_OPEN_DISPONIBILIDAD"}
        if len(open_rows) > 1:
            return {"status": "MULTIPLE_OPEN_DISPONIBILIDAD"}

        current = open_rows[0]
        current_state = (current["estado_disponibilidad"] or "").strip().upper()
        if current_state == already_applied_state:
            return {"status": "ALREADY_APPLIED"}
        if current_state != expected_current_state:
            return {"status": "CURRENT_NOT_RESERVADA"}
        if values["fecha_desde"] < current["fecha_desde"]:
            return {"status": "INVALID_REPLACEMENT_DATE"}

        updated = self.db.execute(
            text(
                """
                UPDATE disponibilidad
                SET
                    fecha_hasta = :fecha_hasta,
                    version_registro = :version_registro_nueva,
                    updated_at = :updated_at,
                    id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                    op_id_ultima_modificacion = :op_id_ultima_modificacion
                WHERE id_disponibilidad = :id_disponibilidad
                  AND version_registro = :version_registro_actual
                  AND deleted_at IS NULL
                RETURNING id_disponibilidad
                """
            ),
            {
                "id_disponibilidad": current["id_disponibilidad"],
                "fecha_hasta": values["fecha_desde"],
                "version_registro_actual": current["version_registro"],
                "version_registro_nueva": current["version_registro"] + 1,
                "updated_at": values["updated_at"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            },
        ).mappings().one_or_none()
        if updated is None:
            return {"status": "NO_OPEN_DISPONIBILIDAD"}

        self.db.execute(
            text(
                """
                INSERT INTO disponibilidad (
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
                    estado_disponibilidad,
                    fecha_desde,
                    fecha_hasta,
                    motivo,
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
                    :estado_disponibilidad,
                    :fecha_desde,
                    NULL,
                    :motivo,
                    :observaciones
                )
                """
            ),
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
                "id_inmueble": values["id_inmueble"],
                "id_unidad_funcional": values["id_unidad_funcional"],
                "estado_disponibilidad": values["estado_disponibilidad"],
                "fecha_desde": values["fecha_desde"],
                "motivo": values["motivo"],
                "observaciones": values["observaciones"],
            },
        )
        return {"status": "OK"}

    def create_ocupacion(self, payload: Any) -> dict[str, Any]:
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
            "id_inmueble": values["id_inmueble"],
            "id_unidad_funcional": values["id_unidad_funcional"],
            "tipo_ocupacion": values["tipo_ocupacion"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "descripcion": values["descripcion"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO ocupacion (
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
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
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
                :tipo_ocupacion,
                :fecha_desde,
                :fecha_hasta,
                :descripcion,
                :observaciones
            )
            RETURNING
                id_ocupacion,
                uid_global,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
                observaciones
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_ocupacion": row["id_ocupacion"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "tipo_ocupacion": row["tipo_ocupacion"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "descripcion": row["descripcion"],
                "observaciones": row["observaciones"],
            }
        except Exception:
            self.db.rollback()
            raise

    def replace_ocupacion_vigente(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        if values["id_inmueble"] is not None:
            parent_values = {"id_inmueble": values["id_inmueble"]}
            select_statement = text(
                """
                SELECT
                    id_ocupacion,
                    id_inmueble,
                    id_unidad_funcional,
                    tipo_ocupacion,
                    fecha_desde,
                    fecha_hasta,
                    descripcion,
                    observaciones,
                    version_registro
                FROM ocupacion
                WHERE fecha_hasta IS NULL
                  AND deleted_at IS NULL
                  AND id_inmueble = :id_inmueble
                  AND id_unidad_funcional IS NULL
                ORDER BY id_ocupacion
                FOR UPDATE
                """
            )
        else:
            parent_values = {"id_unidad_funcional": values["id_unidad_funcional"]}
            select_statement = text(
                """
                SELECT
                    id_ocupacion,
                    id_inmueble,
                    id_unidad_funcional,
                    tipo_ocupacion,
                    fecha_desde,
                    fecha_hasta,
                    descripcion,
                    observaciones,
                    version_registro
                FROM ocupacion
                WHERE fecha_hasta IS NULL
                  AND deleted_at IS NULL
                  AND id_unidad_funcional = :id_unidad_funcional
                  AND id_inmueble IS NULL
                ORDER BY id_ocupacion
                FOR UPDATE
                """
            )

        update_statement = text(
            """
            UPDATE ocupacion
            SET
                fecha_hasta = :fecha_hasta,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_ocupacion = :id_ocupacion
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_ocupacion
            """
        )

        insert_values = {
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
            "id_inmueble": values["id_inmueble"],
            "id_unidad_funcional": values["id_unidad_funcional"],
            "tipo_ocupacion": values["tipo_ocupacion"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": None,
            "descripcion": values["descripcion"],
            "observaciones": values["observaciones"],
        }

        insert_statement = text(
            """
            INSERT INTO ocupacion (
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
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
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
                :tipo_ocupacion,
                :fecha_desde,
                :fecha_hasta,
                :descripcion,
                :observaciones
            )
            RETURNING
                id_ocupacion,
                uid_global,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
                observaciones
            """
        )

        try:
            open_rows = self.db.execute(
                select_statement, parent_values
            ).mappings().all()
            if len(open_rows) == 0:
                self.db.rollback()
                return {"status": "NO_OPEN"}
            if len(open_rows) > 1:
                self.db.rollback()
                return {"status": "MULTIPLE_OPEN"}

            current = open_rows[0]
            if values["fecha_desde"] < current["fecha_desde"]:
                self.db.rollback()
                return {"status": "INVALID_REPLACEMENT_DATE"}

            update_values = {
                "id_ocupacion": current["id_ocupacion"],
                "fecha_hasta": values["fecha_desde"],
                "version_registro_actual": current["version_registro"],
                "version_registro_nueva": current["version_registro"] + 1,
                "updated_at": values["updated_at"],
                "id_instalacion_ultima_modificacion": values[
                    "id_instalacion_ultima_modificacion"
                ],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            }

            updated = self.db.execute(
                update_statement, update_values
            ).mappings().one_or_none()
            if updated is None:
                self.db.rollback()
                return {"status": "NO_OPEN"}

            created = self.db.execute(
                insert_statement, insert_values
            ).mappings().one()
            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_ocupacion": created["id_ocupacion"],
                    "uid_global": str(created["uid_global"]),
                    "version_registro": created["version_registro"],
                    "id_inmueble": created["id_inmueble"],
                    "id_unidad_funcional": created["id_unidad_funcional"],
                    "tipo_ocupacion": created["tipo_ocupacion"],
                    "fecha_desde": created["fecha_desde"],
                    "fecha_hasta": created["fecha_hasta"],
                    "descripcion": created["descripcion"],
                    "observaciones": created["observaciones"],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def close_ocupacion(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_ocupacion": values["id_ocupacion"],
            "fecha_hasta": values["fecha_hasta"],
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
            UPDATE ocupacion
            SET
                fecha_hasta = :fecha_hasta,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_ocupacion = :id_ocupacion
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_ocupacion,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
                observaciones
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
                "id_ocupacion": row["id_ocupacion"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "tipo_ocupacion": row["tipo_ocupacion"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "descripcion": row["descripcion"],
                "observaciones": row["observaciones"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_ocupacion(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_ocupacion": values["id_ocupacion"],
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
            UPDATE ocupacion
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_ocupacion = :id_ocupacion
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_ocupacion,
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
                "id_ocupacion": row["id_ocupacion"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_ocupacion(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_ocupacion": values["id_ocupacion"],
            "id_inmueble": values["id_inmueble"],
            "id_unidad_funcional": values["id_unidad_funcional"],
            "tipo_ocupacion": values["tipo_ocupacion"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "descripcion": values["descripcion"],
            "observaciones": values["observaciones"],
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
            UPDATE ocupacion
            SET
                id_inmueble = :id_inmueble,
                id_unidad_funcional = :id_unidad_funcional,
                tipo_ocupacion = :tipo_ocupacion,
                fecha_desde = :fecha_desde,
                fecha_hasta = :fecha_hasta,
                descripcion = :descripcion,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_ocupacion = :id_ocupacion
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_ocupacion,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
                observaciones
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
                "id_ocupacion": row["id_ocupacion"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "tipo_ocupacion": row["tipo_ocupacion"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "descripcion": row["descripcion"],
                "observaciones": row["observaciones"],
            }
        except Exception:
            self.db.rollback()
            raise

    def close_disponibilidad(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_disponibilidad": values["id_disponibilidad"],
            "fecha_hasta": values["fecha_hasta"],
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
            UPDATE disponibilidad
            SET
                fecha_hasta = :fecha_hasta,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_disponibilidad = :id_disponibilidad
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_disponibilidad,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
                observaciones
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
                "id_disponibilidad": row["id_disponibilidad"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "estado_disponibilidad": row["estado_disponibilidad"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "motivo": row["motivo"],
                "observaciones": row["observaciones"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_disponibilidad(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_disponibilidad": values["id_disponibilidad"],
            "id_inmueble": values["id_inmueble"],
            "id_unidad_funcional": values["id_unidad_funcional"],
            "estado_disponibilidad": values["estado_disponibilidad"],
            "fecha_desde": values["fecha_desde"],
            "fecha_hasta": values["fecha_hasta"],
            "motivo": values["motivo"],
            "observaciones": values["observaciones"],
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
            UPDATE disponibilidad
            SET
                id_inmueble = :id_inmueble,
                id_unidad_funcional = :id_unidad_funcional,
                estado_disponibilidad = :estado_disponibilidad,
                fecha_desde = :fecha_desde,
                fecha_hasta = :fecha_hasta,
                motivo = :motivo,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_disponibilidad = :id_disponibilidad
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_disponibilidad,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
                observaciones
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
                "id_disponibilidad": row["id_disponibilidad"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "estado_disponibilidad": row["estado_disponibilidad"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "motivo": row["motivo"],
                "observaciones": row["observaciones"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_disponibilidad(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_disponibilidad": values["id_disponibilidad"],
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
            UPDATE disponibilidad
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_disponibilidad = :id_disponibilidad
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_disponibilidad,
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
                "id_disponibilidad": row["id_disponibilidad"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise

    def create_unidad_funcional(self, payload: Any) -> dict[str, Any]:
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
            "id_inmueble": values["id_inmueble"],
            "codigo_unidad": values["codigo_unidad"],
            "nombre_unidad": values["nombre_unidad"],
            "superficie": values["superficie"],
            "estado_administrativo": values["estado_administrativo"],
            "estado_operativo": values["estado_operativo"],
            "fecha_alta": values["created_at"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO unidad_funcional (
                id_unidad_funcional,
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_inmueble,
                codigo_unidad,
                nombre_unidad,
                superficie,
                estado_administrativo,
                estado_operativo,
                fecha_alta,
                observaciones
            )
            SELECT
                COALESCE(MAX(id_unidad_funcional), 0) + 1,
                :uid_global,
                :version_registro,
                :created_at,
                :updated_at,
                :id_instalacion_origen,
                :id_instalacion_ultima_modificacion,
                :op_id_alta,
                :op_id_ultima_modificacion,
                :id_inmueble,
                :codigo_unidad,
                :nombre_unidad,
                :superficie,
                :estado_administrativo,
                :estado_operativo,
                :fecha_alta,
                :observaciones
            FROM unidad_funcional
            RETURNING
                id_unidad_funcional,
                uid_global,
                version_registro,
                id_inmueble,
                codigo_unidad,
                estado_administrativo,
                estado_operativo
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_unidad_funcional": row["id_unidad_funcional"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "codigo_unidad": row["codigo_unidad"],
                "estado_administrativo": row["estado_administrativo"],
                "estado_operativo": row["estado_operativo"],
            }
        except Exception:
            self.db.rollback()
            raise

    def create_unidad_funcional_servicio(self, payload: Any) -> dict[str, Any]:
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
            "id_unidad_funcional": values["id_unidad_funcional"],
            "id_servicio": values["id_servicio"],
            "estado": values["estado"],
            "fecha_alta": values["created_at"],
        }

        statement = text(
            """
            INSERT INTO unidad_funcional_servicio (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_unidad_funcional,
                id_servicio,
                estado,
                fecha_alta
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
                :id_unidad_funcional,
                :id_servicio,
                :estado,
                :fecha_alta
            )
            RETURNING
                id_unidad_funcional_servicio,
                uid_global,
                version_registro,
                id_unidad_funcional,
                id_servicio,
                estado
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_unidad_funcional_servicio": row["id_unidad_funcional_servicio"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "id_servicio": row["id_servicio"],
                "estado": row["estado"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_unidad_funcional(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_unidad_funcional": values["id_unidad_funcional"],
            "codigo_unidad": values["codigo_unidad"],
            "nombre_unidad": values["nombre_unidad"],
            "superficie": values["superficie"],
            "estado_administrativo": values["estado_administrativo"],
            "estado_operativo": values["estado_operativo"],
            "observaciones": values["observaciones"],
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
            UPDATE unidad_funcional
            SET
                codigo_unidad = :codigo_unidad,
                nombre_unidad = :nombre_unidad,
                superficie = :superficie,
                estado_administrativo = :estado_administrativo,
                estado_operativo = :estado_operativo,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_unidad_funcional,
                version_registro,
                id_inmueble,
                codigo_unidad,
                nombre_unidad,
                superficie,
                estado_administrativo,
                estado_operativo,
                observaciones
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
                "id_unidad_funcional": row["id_unidad_funcional"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "codigo_unidad": row["codigo_unidad"],
                "nombre_unidad": row["nombre_unidad"],
                "superficie": row["superficie"],
                "estado_administrativo": row["estado_administrativo"],
                "estado_operativo": row["estado_operativo"],
                "observaciones": row["observaciones"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_unidad_funcional(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_unidad_funcional": values["id_unidad_funcional"],
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
            UPDATE unidad_funcional
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_unidad_funcional,
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
                "id_unidad_funcional": row["id_unidad_funcional"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_inmueble(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_inmueble": values["id_inmueble"],
            "id_desarrollo": values["id_desarrollo"],
            "codigo_inmueble": values["codigo_inmueble"],
            "nombre_inmueble": values["nombre_inmueble"],
            "superficie": values["superficie"],
            "estado_administrativo": values["estado_administrativo"],
            "estado_juridico": values["estado_juridico"],
            "observaciones": values["observaciones"],
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
            UPDATE inmueble
            SET
                id_desarrollo = :id_desarrollo,
                codigo_inmueble = :codigo_inmueble,
                nombre_inmueble = :nombre_inmueble,
                superficie = :superficie,
                estado_administrativo = :estado_administrativo,
                estado_juridico = :estado_juridico,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_inmueble = :id_inmueble
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_inmueble,
                version_registro,
                id_desarrollo,
                codigo_inmueble,
                nombre_inmueble,
                superficie,
                estado_administrativo,
                estado_juridico,
                observaciones
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
                "id_inmueble": row["id_inmueble"],
                "version_registro": row["version_registro"],
                "id_desarrollo": row["id_desarrollo"],
                "codigo_inmueble": row["codigo_inmueble"],
                "nombre_inmueble": row["nombre_inmueble"],
                "superficie": row["superficie"],
                "estado_administrativo": row["estado_administrativo"],
                "estado_juridico": row["estado_juridico"],
                "observaciones": row["observaciones"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_inmueble(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_inmueble": values["id_inmueble"],
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
            UPDATE inmueble
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_inmueble = :id_inmueble
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_inmueble,
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
                "id_inmueble": row["id_inmueble"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise

    def associate_inmueble_desarrollo(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_inmueble": values["id_inmueble"],
            "id_desarrollo": values["id_desarrollo"],
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
            UPDATE inmueble
            SET
                id_desarrollo = :id_desarrollo,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_inmueble = :id_inmueble
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_inmueble,
                id_desarrollo,
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
                "id_inmueble": row["id_inmueble"],
                "id_desarrollo": row["id_desarrollo"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise

    def disassociate_inmueble_desarrollo(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_inmueble": values["id_inmueble"],
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
            UPDATE inmueble
            SET
                id_desarrollo = NULL,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_inmueble = :id_inmueble
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_inmueble,
                id_desarrollo,
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
                "id_inmueble": row["id_inmueble"],
                "id_desarrollo": row["id_desarrollo"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise

    # ── consumer helpers (sin commit — el caller gestiona la transacción) ─────

    def create_entrega_restitucion_inmueble_sin_commit(
        self, payload: Any
    ) -> dict[str, Any]:
        from dataclasses import asdict, is_dataclass
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        stmt = text(
            """
            INSERT INTO entrega_restitucion_inmueble (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_contrato_alquiler, fecha_entrega, estado_inmueble, observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_contrato_alquiler, :fecha_entrega, :estado_inmueble, :observaciones
            )
            RETURNING id_entrega_restitucion
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
                "estado_inmueble": values["estado_inmueble"],
                "observaciones": values["observaciones"],
            },
        ).mappings().one()
        return {"id_entrega_restitucion": row["id_entrega_restitucion"]}

    def create_ocupacion_sin_commit(self, payload: Any) -> dict[str, Any]:
        from dataclasses import asdict, is_dataclass
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        stmt = text(
            """
            INSERT INTO ocupacion (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_inmueble, id_unidad_funcional,
                tipo_ocupacion, fecha_desde, fecha_hasta, descripcion, observaciones
            )
            VALUES (
                :uid_global, :version_registro, :created_at, :updated_at,
                :id_instalacion_origen, :id_instalacion_ultima_modificacion,
                :op_id_alta, :op_id_ultima_modificacion,
                :id_inmueble, :id_unidad_funcional,
                :tipo_ocupacion, :fecha_desde, :fecha_hasta, :descripcion, :observaciones
            )
            RETURNING id_ocupacion
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
                "id_inmueble": values["id_inmueble"],
                "id_unidad_funcional": values["id_unidad_funcional"],
                "tipo_ocupacion": values["tipo_ocupacion"],
                "fecha_desde": values["fecha_desde"],
                "fecha_hasta": values["fecha_hasta"],
                "descripcion": values["descripcion"],
                "observaciones": values["observaciones"],
            },
        ).mappings().one()
        return {"id_ocupacion": row["id_ocupacion"]}

    def get_open_ocupacion_alquiler_sin_commit(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
    ) -> dict[str, Any]:
        if id_inmueble is not None:
            filter_clause = "id_inmueble = :id_inmueble AND id_unidad_funcional IS NULL"
            params: dict[str, Any] = {"id_inmueble": id_inmueble}
        else:
            filter_clause = "id_unidad_funcional = :id_unidad_funcional AND id_inmueble IS NULL"
            params = {"id_unidad_funcional": id_unidad_funcional}

        stmt = text(
            f"""
            SELECT
                id_ocupacion, id_inmueble, id_unidad_funcional,
                tipo_ocupacion, fecha_desde, fecha_hasta, version_registro
            FROM ocupacion
            WHERE {filter_clause}
              AND UPPER(tipo_ocupacion) = 'ALQUILER'
              AND fecha_hasta IS NULL
              AND deleted_at IS NULL
            ORDER BY id_ocupacion
            FOR UPDATE
            """
        )
        rows = self.db.execute(stmt, params).mappings().all()
        if len(rows) == 0:
            return {"status": "NO_OPEN_OCUPACION_ALQUILER"}
        if len(rows) > 1:
            return {"status": "MULTIPLE_OPEN_OCUPACION_ALQUILER"}
        row = rows[0]
        return {
            "status": "OK",
            "data": {
                "id_ocupacion": row["id_ocupacion"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "tipo_ocupacion": row["tipo_ocupacion"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "version_registro": row["version_registro"],
            },
        }

    def close_ocupacion_sin_commit(self, payload: Any) -> dict[str, Any]:
        from dataclasses import asdict, is_dataclass
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        stmt = text(
            """
            UPDATE ocupacion
            SET
                fecha_hasta = :fecha_hasta,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_ocupacion = :id_ocupacion
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING id_ocupacion, version_registro, fecha_hasta
            """
        )
        row = self.db.execute(
            stmt,
            {
                "id_ocupacion": values["id_ocupacion"],
                "fecha_hasta": values["fecha_hasta"],
                "version_registro_actual": values["version_registro_actual"],
                "version_registro_nueva": values["version_registro_nueva"],
                "updated_at": values["updated_at"],
                "id_instalacion_ultima_modificacion": values["id_instalacion_ultima_modificacion"],
                "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
            },
        ).mappings().one_or_none()
        if row is None:
            return {"status": "CONCURRENCY_ERROR"}
        return {"status": "OK", "id_ocupacion": row["id_ocupacion"]}
