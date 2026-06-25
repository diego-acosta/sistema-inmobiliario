from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy import text

from app.infrastructure.persistence.base_repository import BaseRepository


INTEGRACION_COMERCIAL_EVENT_TYPES = (
    "venta_confirmada",
    "escrituracion_registrada",
)


def _format_inmueble_direccion(calle: object, altura: object) -> str | None:
    parts = [str(value).strip() for value in (calle, altura) if str(value or "").strip()]
    return " ".join(parts) if parts else None


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


    _DCR_COLUMNS = """
                id_dato_catastral_registral,
                id_inmueble,
                uid_global::text AS uid_global,
                version_registro,
                created_at,
                updated_at,
                nomenclatura_catastral,
                partida_inmobiliaria,
                matricula,
                folio_real,
                circunscripcion,
                seccion,
                chacra,
                quinta,
                fraccion,
                manzana,
                lote,
                parcela,
                subparcela,
                superficie_titulo,
                superficie_mensura,
                medidas,
                situacion_posesoria,
                situacion_dominial,
                organismo_origen,
                fecha_desde,
                fecha_hasta,
                estado_dato,
                observaciones
    """

    @staticmethod
    def _map_dcr_row(row: Any) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _dcr_payload_values(payload: Any) -> dict[str, Any]:
        return {
            **payload.values,
            "id_inmueble": payload.id_inmueble,
            "version_registro": payload.version_registro_nueva,
            "now": payload.now,
            "id_instalacion": payload.id_instalacion,
            "op_id": payload.op_id,
        }

    def list_datos_catastrales_registrales(
        self, id_inmueble: int
    ) -> list[dict[str, Any]]:
        statement = text(
            f"""
            SELECT {self._DCR_COLUMNS}
            FROM inmueble_dato_catastral_registral
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_dato_catastral_registral
            """
        )
        rows = self.db.execute(
            statement,
            {"id_inmueble": id_inmueble},
        ).mappings().all()
        return [self._map_dcr_row(row) for row in rows]

    def get_dato_catastral_registral(
        self, id_inmueble: int, id_dato: int
    ) -> dict[str, Any] | None:
        statement = text(
            f"""
            SELECT {self._DCR_COLUMNS}
            FROM inmueble_dato_catastral_registral
            WHERE id_inmueble = :id_inmueble
              AND id_dato_catastral_registral = :id_dato
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement,
            {"id_inmueble": id_inmueble, "id_dato": id_dato},
        ).mappings().one_or_none()
        return self._map_dcr_row(row) if row is not None else None

    def create_dato_catastral_registral(self, payload: Any) -> dict[str, Any]:
        values = self._dcr_payload_values(payload)
        columns = [
            "id_inmueble",
            *payload.values.keys(),
            "version_registro",
            "created_at",
            "updated_at",
            "id_instalacion_origen",
            "id_instalacion_ultima_modificacion",
            "op_id_alta",
            "op_id_ultima_modificacion",
        ]
        value_placeholders = [
            ":id_inmueble",
            *[f":{field}" for field in payload.values.keys()],
            ":version_registro",
            ":now",
            ":now",
            ":id_instalacion",
            ":id_instalacion",
            ":op_id",
            ":op_id",
        ]
        cols = ", ".join(columns)
        vals = ", ".join(value_placeholders)
        statement = text(
            f"""
            INSERT INTO inmueble_dato_catastral_registral ({cols})
            VALUES ({vals})
            RETURNING {self._DCR_COLUMNS}
            """
        )
        try:
            row = self.db.execute(statement, values).mappings().one()
            self.db.commit()
            return self._map_dcr_row(row)
        except Exception:
            self.db.rollback()
            raise

    def update_dato_catastral_registral(
        self, payload: Any
    ) -> dict[str, Any] | None:
        set_fields = ",\n                ".join(
            f"{field} = :{field}" for field in payload.values.keys()
        )
        values = {
            **payload.values,
            "id_inmueble": payload.id_inmueble,
            "id_dato": payload.id_dato_catastral_registral,
            "version_actual": payload.version_registro_actual,
            "version_nueva": payload.version_registro_nueva,
            "now": payload.now,
            "id_instalacion": payload.id_instalacion,
            "op_id": payload.op_id,
        }
        statement = text(
            f"""
            UPDATE inmueble_dato_catastral_registral
            SET {set_fields},
                version_registro = :version_nueva,
                updated_at = :now,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id
            WHERE id_inmueble = :id_inmueble
              AND id_dato_catastral_registral = :id_dato
              AND version_registro = :version_actual
              AND deleted_at IS NULL
            RETURNING {self._DCR_COLUMNS}
            """
        )
        try:
            row = self.db.execute(statement, values).mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return self._map_dcr_row(row)
        except Exception:
            self.db.rollback()
            raise

    def baja_dato_catastral_registral(
        self, payload: Any
    ) -> dict[str, Any] | None:
        statement = text(
            """
            UPDATE inmueble_dato_catastral_registral
            SET deleted_at = :now,
                version_registro = :version_nueva,
                updated_at = :now,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id
            WHERE id_inmueble = :id_inmueble
              AND id_dato_catastral_registral = :id_dato
              AND version_registro = :version_actual
              AND deleted_at IS NULL
            RETURNING id_dato_catastral_registral, id_inmueble, version_registro
            """
        )
        values = {
            "id_inmueble": payload.id_inmueble,
            "id_dato": payload.id_dato_catastral_registral,
            "version_actual": payload.version_registro_actual,
            "version_nueva": payload.version_registro_nueva,
            "now": payload.now,
            "id_instalacion": payload.id_instalacion,
            "op_id": payload.op_id,
        }
        try:
            row = self.db.execute(statement, values).mappings().one_or_none()
            if row is None:
                self.db.rollback()
                return None
            self.db.commit()
            return self._map_dcr_row(row)
        except Exception:
            self.db.rollback()
            raise

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

    def get_inmueble_detalle_integral(
        self, id_inmueble: int
    ) -> dict[str, Any] | None:
        inmueble = self.get_inmueble(id_inmueble)
        if inmueble is None:
            return None

        disponibilidades = self._get_disponibilidades_activo(
            id_inmueble=id_inmueble,
            id_unidad_funcional=None,
        )
        ocupaciones = self._get_ocupaciones_activo(
            id_inmueble=id_inmueble,
            id_unidad_funcional=None,
        )
        disponibilidad_actual, disponibilidad_ambigua = self._get_actual(
            disponibilidades
        )
        ocupacion_actual, ocupacion_ambigua = self._get_actual(ocupaciones)
        unidades = self.get_unidades_funcionales(id_inmueble)
        servicios = self.get_inmueble_servicios(id_inmueble)
        responsables = self._get_responsables_servicio_activo(
            id_inmueble=id_inmueble,
            id_unidad_funcional=None,
        )

        return {
            "inmueble": inmueble,
            "desarrollo": self._get_desarrollo(inmueble["id_desarrollo"]),
            "unidades_funcionales": unidades,
            "servicios": servicios,
            "responsables_servicio": responsables,
            "disponibilidad_actual": disponibilidad_actual,
            "disponibilidad_ambigua": disponibilidad_ambigua,
            "ocupacion_actual": ocupacion_actual,
            "ocupacion_ambigua": ocupacion_ambigua,
            "disponibilidades": disponibilidades,
            "ocupaciones": ocupaciones,
            "reservas_venta": self._get_reservas_venta_activo(
                id_inmueble=id_inmueble,
                id_unidad_funcional=None,
            ),
            "ventas": self._get_ventas_activo(
                id_inmueble=id_inmueble,
                id_unidad_funcional=None,
            ),
            "reservas_locativas": self._get_reservas_locativas_activo(
                id_inmueble=id_inmueble,
                id_unidad_funcional=None,
            ),
            "contratos_alquiler": self._get_contratos_alquiler_activo(
                id_inmueble=id_inmueble,
                id_unidad_funcional=None,
            ),
            "trazabilidad_integracion": self._get_integracion_trazabilidad_activo(
                id_inmueble=id_inmueble,
                id_unidad_funcional=None,
            ),
            "resumen_operativo": {
                "cantidad_unidades": len(unidades),
                "cantidad_servicios": len(servicios),
                "tiene_ocupacion_actual": ocupacion_actual is not None,
                "tiene_disponibilidad_actual": disponibilidad_actual is not None,
                "disponibilidad_ambigua": disponibilidad_ambigua,
                "ocupacion_ambigua": ocupacion_ambigua,
            },
        }

    def get_unidad_funcional_detalle_integral(
        self, id_unidad_funcional: int
    ) -> dict[str, Any] | None:
        unidad = self.get_unidad_funcional(id_unidad_funcional)
        if unidad is None:
            return None

        inmueble = self.get_inmueble(unidad["id_inmueble"])
        if inmueble is None:
            return None

        disponibilidades = self._get_disponibilidades_activo(
            id_inmueble=None,
            id_unidad_funcional=id_unidad_funcional,
        )
        ocupaciones = self._get_ocupaciones_activo(
            id_inmueble=None,
            id_unidad_funcional=id_unidad_funcional,
        )
        disponibilidad_actual, disponibilidad_ambigua = self._get_actual(
            disponibilidades
        )
        ocupacion_actual, ocupacion_ambigua = self._get_actual(ocupaciones)
        servicios = self.get_unidad_funcional_servicios(id_unidad_funcional)
        responsables = self._get_responsables_servicio_activo(
            id_inmueble=None,
            id_unidad_funcional=id_unidad_funcional,
        )

        return {
            "unidad_funcional": unidad,
            "inmueble": inmueble,
            "servicios": servicios,
            "responsables_servicio": responsables,
            "disponibilidad_actual": disponibilidad_actual,
            "disponibilidad_ambigua": disponibilidad_ambigua,
            "ocupacion_actual": ocupacion_actual,
            "ocupacion_ambigua": ocupacion_ambigua,
            "disponibilidades": disponibilidades,
            "ocupaciones": ocupaciones,
            "reservas_venta": self._get_reservas_venta_activo(
                id_inmueble=None,
                id_unidad_funcional=id_unidad_funcional,
            ),
            "ventas": self._get_ventas_activo(
                id_inmueble=None,
                id_unidad_funcional=id_unidad_funcional,
            ),
            "reservas_locativas": self._get_reservas_locativas_activo(
                id_inmueble=None,
                id_unidad_funcional=id_unidad_funcional,
            ),
            "contratos_alquiler": self._get_contratos_alquiler_activo(
                id_inmueble=None,
                id_unidad_funcional=id_unidad_funcional,
            ),
            "trazabilidad_integracion": self._get_integracion_trazabilidad_activo(
                id_inmueble=None,
                id_unidad_funcional=id_unidad_funcional,
            ),
            "resumen_operativo": {
                "cantidad_servicios": len(servicios),
                "tiene_ocupacion_actual": ocupacion_actual is not None,
                "tiene_disponibilidad_actual": disponibilidad_actual is not None,
                "disponibilidad_ambigua": disponibilidad_ambigua,
                "ocupacion_ambigua": ocupacion_ambigua,
            },
        }

    def _get_actual(
        self, vigencias: list[dict[str, Any]]
    ) -> tuple[dict[str, Any] | None, bool]:
        abiertas = [item for item in vigencias if item["fecha_hasta"] is None]
        if len(abiertas) == 1:
            return abiertas[0], False
        if len(abiertas) > 1:
            return None, True
        return None, False

    def _asset_where(
        self, *, alias: str = "", id_inmueble: int | None, id_unidad_funcional: int | None
    ) -> tuple[str, dict[str, int]]:
        prefix = f"{alias}." if alias else ""
        if id_inmueble is not None:
            return (
                f"{prefix}id_inmueble = :id_inmueble AND {prefix}id_unidad_funcional IS NULL",
                {"id_inmueble": id_inmueble},
            )
        return (
            f"{prefix}id_unidad_funcional = :id_unidad_funcional AND {prefix}id_inmueble IS NULL",
            {"id_unidad_funcional": id_unidad_funcional or 0},
        )

    def _get_desarrollo(self, id_desarrollo: int | None) -> dict[str, Any] | None:
        if id_desarrollo is None:
            return None
        row = self.db.execute(
            text(
                """
                SELECT
                    id_desarrollo,
                    codigo_desarrollo,
                    nombre_desarrollo,
                    descripcion,
                    estado_desarrollo,
                    observaciones
                FROM desarrollo
                WHERE id_desarrollo = :id_desarrollo
                  AND deleted_at IS NULL
                """
            ),
            {"id_desarrollo": id_desarrollo},
        ).mappings().one_or_none()
        return dict(row) if row is not None else None

    def _get_disponibilidades_activo(
        self, *, id_inmueble: int | None, id_unidad_funcional: int | None
    ) -> list[dict[str, Any]]:
        where, params = self._asset_where(
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
        )
        rows = self.db.execute(
            text(
                f"""
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
                WHERE {where}
                  AND deleted_at IS NULL
                ORDER BY fecha_desde DESC, id_disponibilidad DESC
                """
            ),
            params,
        ).mappings().all()
        return [dict(row) for row in rows]

    def _get_ocupaciones_activo(
        self, *, id_inmueble: int | None, id_unidad_funcional: int | None
    ) -> list[dict[str, Any]]:
        where, params = self._asset_where(
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
        )
        rows = self.db.execute(
            text(
                f"""
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
                WHERE {where}
                  AND deleted_at IS NULL
                ORDER BY fecha_desde DESC, id_ocupacion DESC
                """
            ),
            params,
        ).mappings().all()
        return [dict(row) for row in rows]

    def _get_responsables_servicio_activo(
        self, *, id_inmueble: int | None, id_unidad_funcional: int | None
    ) -> list[dict[str, Any]]:
        where, params = self._asset_where(
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
        )
        rows = self.db.execute(
            text(
                f"""
                SELECT
                    id_asignacion_servicio_responsable,
                    id_servicio,
                    id_inmueble,
                    id_unidad_funcional,
                    id_persona,
                    porcentaje_responsabilidad,
                    fecha_desde,
                    fecha_hasta,
                    estado_asignacion,
                    observaciones
                FROM asignacion_servicio_responsable
                WHERE {where}
                  AND deleted_at IS NULL
                ORDER BY id_asignacion_servicio_responsable
                """
            ),
            params,
        ).mappings().all()
        return [
            {
                **dict(row),
                "porcentaje_responsabilidad": (
                    float(row["porcentaje_responsabilidad"])
                    if row["porcentaje_responsabilidad"] is not None
                    else None
                ),
                "fecha_desde": (
                    row["fecha_desde"].isoformat()
                    if row["fecha_desde"] is not None
                    else None
                ),
                "fecha_hasta": (
                    row["fecha_hasta"].isoformat()
                    if row["fecha_hasta"] is not None
                    else None
                ),
            }
            for row in rows
        ]

    def _get_reservas_venta_activo(
        self, *, id_inmueble: int | None, id_unidad_funcional: int | None
    ) -> list[dict[str, Any]]:
        where, params = self._asset_where(
            alias="rvo",
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
        )
        rows = self.db.execute(
            text(
                f"""
                SELECT DISTINCT
                    rv.id_reserva_venta,
                    rv.codigo_reserva,
                    rv.fecha_reserva,
                    rv.fecha_vencimiento,
                    rv.estado_reserva,
                    rv.observaciones
                FROM reserva_venta rv
                JOIN reserva_venta_objeto_inmobiliario rvo
                  ON rvo.id_reserva_venta = rv.id_reserva_venta
                WHERE rv.deleted_at IS NULL
                  AND rvo.deleted_at IS NULL
                  AND {where}
                ORDER BY rv.fecha_reserva DESC, rv.id_reserva_venta DESC
                """
            ),
            params,
        ).mappings().all()
        return [dict(row) for row in rows]

    def _get_ventas_activo(
        self, *, id_inmueble: int | None, id_unidad_funcional: int | None
    ) -> list[dict[str, Any]]:
        where, params = self._asset_where(
            alias="voi",
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
        )
        rows = self.db.execute(
            text(
                f"""
                SELECT DISTINCT
                    v.id_venta,
                    v.id_reserva_venta,
                    v.codigo_venta,
                    v.fecha_venta,
                    v.estado_venta,
                    v.monto_total,
                    v.moneda,
                    v.observaciones
                FROM venta v
                JOIN venta_objeto_inmobiliario voi
                  ON voi.id_venta = v.id_venta
                WHERE v.deleted_at IS NULL
                  AND voi.deleted_at IS NULL
                  AND {where}
                ORDER BY v.fecha_venta DESC, v.id_venta DESC
                """
            ),
            params,
        ).mappings().all()
        return [
            {
                **dict(row),
                "monto_total": (
                    float(row["monto_total"]) if row["monto_total"] is not None else None
                ),
            }
            for row in rows
        ]

    def _get_reservas_locativas_activo(
        self, *, id_inmueble: int | None, id_unidad_funcional: int | None
    ) -> list[dict[str, Any]]:
        where, params = self._asset_where(
            alias="rlo",
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
        )
        rows = self.db.execute(
            text(
                f"""
                SELECT DISTINCT
                    rl.id_reserva_locativa,
                    rl.id_solicitud_alquiler,
                    rl.codigo_reserva,
                    rl.fecha_reserva,
                    rl.fecha_vencimiento,
                    rl.estado_reserva,
                    rl.observaciones
                FROM reserva_locativa rl
                JOIN reserva_locativa_objeto rlo
                  ON rlo.id_reserva_locativa = rl.id_reserva_locativa
                WHERE rl.deleted_at IS NULL
                  AND rlo.deleted_at IS NULL
                  AND {where}
                ORDER BY rl.fecha_reserva DESC, rl.id_reserva_locativa DESC
                """
            ),
            params,
        ).mappings().all()
        return [dict(row) for row in rows]

    def _get_contratos_alquiler_activo(
        self, *, id_inmueble: int | None, id_unidad_funcional: int | None
    ) -> list[dict[str, Any]]:
        where, params = self._asset_where(
            alias="col",
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
        )
        rows = self.db.execute(
            text(
                f"""
                SELECT DISTINCT
                    ca.id_contrato_alquiler,
                    ca.id_reserva_locativa,
                    ca.codigo_contrato,
                    ca.fecha_inicio,
                    ca.fecha_fin,
                    ca.estado_contrato,
                    ca.observaciones
                FROM contrato_alquiler ca
                JOIN contrato_objeto_locativo col
                  ON col.id_contrato_alquiler = ca.id_contrato_alquiler
                WHERE ca.deleted_at IS NULL
                  AND col.deleted_at IS NULL
                  AND {where}
                ORDER BY ca.fecha_inicio DESC, ca.id_contrato_alquiler DESC
                """
            ),
            params,
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_unidades_funcionales_global(
        self,
        *,
        q: str | None = None,
        id_inmueble: int | None = None,
        estado_administrativo: str | None = None,
        estado_operativo: str | None = None,
        disponibilidad_actual: str | None = None,
        ocupacion_actual: str | None = None,
        id_servicio: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        where_clauses = ["uf.deleted_at IS NULL", "i.deleted_at IS NULL"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if q:
            where_clauses.append(
                """
                (
                    LOWER(uf.codigo_unidad) LIKE :q
                    OR LOWER(COALESCE(uf.nombre_unidad, '')) LIKE :q
                    OR LOWER(COALESCE(uf.observaciones, '')) LIKE :q
                    OR LOWER(i.codigo_inmueble) LIKE :q
                    OR LOWER(COALESCE(i.nombre_inmueble, '')) LIKE :q
                )
                """
            )
            params["q"] = f"%{q.lower()}%"
        if id_inmueble is not None:
            where_clauses.append("uf.id_inmueble = :id_inmueble")
            params["id_inmueble"] = id_inmueble
        if estado_administrativo:
            where_clauses.append("uf.estado_administrativo = :estado_administrativo")
            params["estado_administrativo"] = estado_administrativo
        if estado_operativo:
            where_clauses.append("uf.estado_operativo = :estado_operativo")
            params["estado_operativo"] = estado_operativo
        if disponibilidad_actual:
            where_clauses.append(
                "disp.abiertos = 1 AND disp.estado_actual = :disponibilidad_actual"
            )
            params["disponibilidad_actual"] = disponibilidad_actual
        if ocupacion_actual:
            where_clauses.append(
                "ocup.abiertos = 1 AND ocup.tipo_actual = :ocupacion_actual"
            )
            params["ocupacion_actual"] = ocupacion_actual
        if id_servicio is not None:
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM unidad_funcional_servicio ufs
                    WHERE ufs.id_unidad_funcional = uf.id_unidad_funcional
                      AND ufs.id_servicio = :id_servicio
                      AND ufs.deleted_at IS NULL
                )
                """
            )
            params["id_servicio"] = id_servicio

        where_sql = "\n              AND ".join(where_clauses)
        ctes = """
            WITH disp AS (
                SELECT
                    id_unidad_funcional,
                    COUNT(*) AS abiertos,
                    MIN(id_disponibilidad) AS id_disponibilidad,
                    MIN(estado_disponibilidad) AS estado_actual,
                    MIN(fecha_desde) AS fecha_desde,
                    MIN(fecha_hasta) AS fecha_hasta,
                    MIN(motivo) AS motivo,
                    MIN(observaciones) AS observaciones
                FROM disponibilidad
                WHERE id_unidad_funcional IS NOT NULL
                  AND id_inmueble IS NULL
                  AND fecha_hasta IS NULL
                  AND deleted_at IS NULL
                GROUP BY id_unidad_funcional
            ),
            ocup AS (
                SELECT
                    id_unidad_funcional,
                    COUNT(*) AS abiertos,
                    MIN(id_ocupacion) AS id_ocupacion,
                    MIN(tipo_ocupacion) AS tipo_actual,
                    MIN(fecha_desde) AS fecha_desde,
                    MIN(fecha_hasta) AS fecha_hasta,
                    MIN(descripcion) AS descripcion,
                    MIN(observaciones) AS observaciones
                FROM ocupacion
                WHERE id_unidad_funcional IS NOT NULL
                  AND id_inmueble IS NULL
                  AND fecha_hasta IS NULL
                  AND deleted_at IS NULL
                GROUP BY id_unidad_funcional
            )
        """
        count_statement = text(
            f"""
            {ctes}
            SELECT COUNT(*)
            FROM unidad_funcional uf
            JOIN inmueble i
              ON i.id_inmueble = uf.id_inmueble
            LEFT JOIN disp
              ON disp.id_unidad_funcional = uf.id_unidad_funcional
            LEFT JOIN ocup
              ON ocup.id_unidad_funcional = uf.id_unidad_funcional
            WHERE {where_sql}
            """
        )
        total = self.db.execute(count_statement, params).scalar_one()

        statement = text(
            f"""
            {ctes}
            SELECT
                uf.id_unidad_funcional,
                uf.id_inmueble,
                uf.codigo_unidad,
                uf.nombre_unidad,
                uf.superficie,
                uf.estado_administrativo,
                uf.estado_operativo,
                uf.observaciones,
                i.codigo_inmueble,
                i.nombre_inmueble,
                CASE
                    WHEN COALESCE(disp.abiertos, 0) = 1 THEN json_build_object(
                        'id_disponibilidad', disp.id_disponibilidad,
                        'id_inmueble', NULL,
                        'id_unidad_funcional', uf.id_unidad_funcional,
                        'estado_disponibilidad', disp.estado_actual,
                        'fecha_desde', disp.fecha_desde,
                        'fecha_hasta', disp.fecha_hasta,
                        'motivo', disp.motivo,
                        'observaciones', disp.observaciones
                    )
                    ELSE NULL
                END AS disponibilidad_actual,
                COALESCE(disp.abiertos, 0) > 1 AS disponibilidad_ambigua,
                CASE
                    WHEN COALESCE(ocup.abiertos, 0) = 1 THEN json_build_object(
                        'id_ocupacion', ocup.id_ocupacion,
                        'id_inmueble', NULL,
                        'id_unidad_funcional', uf.id_unidad_funcional,
                        'tipo_ocupacion', ocup.tipo_actual,
                        'fecha_desde', ocup.fecha_desde,
                        'fecha_hasta', ocup.fecha_hasta,
                        'descripcion', ocup.descripcion,
                        'observaciones', ocup.observaciones
                    )
                    ELSE NULL
                END AS ocupacion_actual,
                COALESCE(ocup.abiertos, 0) > 1 AS ocupacion_ambigua
            FROM unidad_funcional uf
            JOIN inmueble i
              ON i.id_inmueble = uf.id_inmueble
            LEFT JOIN disp
              ON disp.id_unidad_funcional = uf.id_unidad_funcional
            LEFT JOIN ocup
              ON ocup.id_unidad_funcional = uf.id_unidad_funcional
            WHERE {where_sql}
            ORDER BY uf.id_unidad_funcional
            LIMIT :limit OFFSET :offset
            """
        )
        rows = self.db.execute(statement, params).mappings().all()
        items = [
            {
                "id_unidad_funcional": row["id_unidad_funcional"],
                "id_inmueble": row["id_inmueble"],
                "codigo_unidad": row["codigo_unidad"],
                "codigo_unidad_funcional": row["codigo_unidad"],
                "nombre_unidad": row["nombre_unidad"],
                "nombre": row["nombre_unidad"],
                "descripcion": row["observaciones"],
                "tipo_unidad": None,
                "superficie": row["superficie"],
                "estado_administrativo": row["estado_administrativo"],
                "estado_operativo": row["estado_operativo"],
                "observaciones": row["observaciones"],
                "disponibilidad_actual": row["disponibilidad_actual"],
                "disponibilidad_ambigua": row["disponibilidad_ambigua"],
                "ocupacion_actual": row["ocupacion_actual"],
                "ocupacion_ambigua": row["ocupacion_ambigua"],
                "inmueble": {
                    "id_inmueble": row["id_inmueble"],
                    "codigo_inmueble": row["codigo_inmueble"],
                    "nombre_inmueble": row["nombre_inmueble"],
                    "direccion": None,
                    "ubicacion": None,
                },
            }
            for row in rows
        ]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

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

    def get_inmuebles(
        self,
        *,
        q: str | None = None,
        estado_administrativo: str | None = None,
        estado_juridico: str | None = None,
        id_desarrollo: int | None = None,
        disponibilidad_actual: str | None = None,
        ocupacion_actual: str | None = None,
        id_servicio: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        where_clauses = ["i.deleted_at IS NULL"]
        params: dict[str, Any] = {"limit": limit, "offset": offset}

        if q:
            where_clauses.append(
                """
                (
                    LOWER(i.codigo_inmueble) LIKE :q
                    OR LOWER(COALESCE(i.nombre_inmueble, '')) LIKE :q
                    OR LOWER(COALESCE(i.calle, '')) LIKE :q
                    OR LOWER(COALESCE(i.altura, '')) LIKE :q
                    OR LOWER(COALESCE(i.observaciones, '')) LIKE :q
                )
                """
            )
            params["q"] = f"%{q.lower()}%"
        if estado_administrativo:
            where_clauses.append("i.estado_administrativo = :estado_administrativo")
            params["estado_administrativo"] = estado_administrativo
        if estado_juridico:
            where_clauses.append("i.estado_juridico = :estado_juridico")
            params["estado_juridico"] = estado_juridico
        if id_desarrollo is not None:
            where_clauses.append("i.id_desarrollo = :id_desarrollo")
            params["id_desarrollo"] = id_desarrollo
        if disponibilidad_actual:
            where_clauses.append(
                "disp.abiertos = 1 AND disp.estado_actual = :disponibilidad_actual"
            )
            params["disponibilidad_actual"] = disponibilidad_actual
        if ocupacion_actual:
            where_clauses.append(
                "ocup.abiertos = 1 AND ocup.tipo_actual = :ocupacion_actual"
            )
            params["ocupacion_actual"] = ocupacion_actual
        if id_servicio is not None:
            where_clauses.append(
                """
                EXISTS (
                    SELECT 1
                    FROM inmueble_servicio ins
                    WHERE ins.id_inmueble = i.id_inmueble
                      AND ins.id_servicio = :id_servicio
                      AND ins.deleted_at IS NULL
                )
                """
            )
            params["id_servicio"] = id_servicio

        where_sql = "\n              AND ".join(where_clauses)
        ctes = """
            WITH disp AS (
                SELECT
                    id_inmueble,
                    COUNT(*) AS abiertos,
                    MIN(id_disponibilidad) AS id_disponibilidad,
                    MIN(estado_disponibilidad) AS estado_actual,
                    MIN(fecha_desde) AS fecha_desde,
                    MIN(fecha_hasta) AS fecha_hasta,
                    MIN(motivo) AS motivo,
                    MIN(observaciones) AS observaciones
                FROM disponibilidad
                WHERE id_inmueble IS NOT NULL
                  AND id_unidad_funcional IS NULL
                  AND fecha_hasta IS NULL
                  AND deleted_at IS NULL
                GROUP BY id_inmueble
            ),
            ocup AS (
                SELECT
                    id_inmueble,
                    COUNT(*) AS abiertos,
                    MIN(id_ocupacion) AS id_ocupacion,
                    MIN(tipo_ocupacion) AS tipo_actual,
                    MIN(fecha_desde) AS fecha_desde,
                    MIN(fecha_hasta) AS fecha_hasta,
                    MIN(descripcion) AS descripcion,
                    MIN(observaciones) AS observaciones
                FROM ocupacion
                WHERE id_inmueble IS NOT NULL
                  AND id_unidad_funcional IS NULL
                  AND fecha_hasta IS NULL
                  AND deleted_at IS NULL
                GROUP BY id_inmueble
            ),
            uf_count AS (
                SELECT id_inmueble, COUNT(*) AS cantidad
                FROM unidad_funcional
                WHERE deleted_at IS NULL
                GROUP BY id_inmueble
            )
        """
        count_statement = text(
            f"""
            {ctes}
            SELECT COUNT(*)
            FROM inmueble i
            LEFT JOIN disp
              ON disp.id_inmueble = i.id_inmueble
            LEFT JOIN ocup
              ON ocup.id_inmueble = i.id_inmueble
            LEFT JOIN uf_count
              ON uf_count.id_inmueble = i.id_inmueble
            WHERE {where_sql}
            """
        )
        total = self.db.execute(count_statement, params).scalar_one()

        statement = text(
            f"""
            {ctes}
            SELECT
                i.id_inmueble,
                i.id_desarrollo,
                i.codigo_inmueble,
                i.nombre_inmueble,
                i.calle,
                i.altura,
                i.superficie,
                i.estado_administrativo,
                i.estado_juridico,
                i.observaciones,
                CASE
                    WHEN COALESCE(disp.abiertos, 0) = 1 THEN json_build_object(
                        'id_disponibilidad', disp.id_disponibilidad,
                        'id_inmueble', i.id_inmueble,
                        'id_unidad_funcional', NULL,
                        'estado_disponibilidad', disp.estado_actual,
                        'fecha_desde', disp.fecha_desde,
                        'fecha_hasta', disp.fecha_hasta,
                        'motivo', disp.motivo,
                        'observaciones', disp.observaciones
                    )
                    ELSE NULL
                END AS disponibilidad_actual,
                COALESCE(disp.abiertos, 0) > 1 AS disponibilidad_ambigua,
                CASE
                    WHEN COALESCE(ocup.abiertos, 0) = 1 THEN json_build_object(
                        'id_ocupacion', ocup.id_ocupacion,
                        'id_inmueble', i.id_inmueble,
                        'id_unidad_funcional', NULL,
                        'tipo_ocupacion', ocup.tipo_actual,
                        'fecha_desde', ocup.fecha_desde,
                        'fecha_hasta', ocup.fecha_hasta,
                        'descripcion', ocup.descripcion,
                        'observaciones', ocup.observaciones
                    )
                    ELSE NULL
                END AS ocupacion_actual,
                COALESCE(ocup.abiertos, 0) > 1 AS ocupacion_ambigua,
                COALESCE(uf_count.cantidad, 0) AS cantidad_unidades_funcionales
            FROM inmueble i
            LEFT JOIN disp
              ON disp.id_inmueble = i.id_inmueble
            LEFT JOIN ocup
              ON ocup.id_inmueble = i.id_inmueble
            LEFT JOIN uf_count
              ON uf_count.id_inmueble = i.id_inmueble
            WHERE {where_sql}
            ORDER BY i.id_inmueble
            LIMIT :limit OFFSET :offset
            """
        )
        rows = self.db.execute(statement, params).mappings().all()
        items = [
            {
                "id_inmueble": row["id_inmueble"],
                "id_desarrollo": row["id_desarrollo"],
                "codigo_inmueble": row["codigo_inmueble"],
                "nombre_inmueble": row["nombre_inmueble"],
                "nombre": row["nombre_inmueble"],
                "descripcion": row["observaciones"],
                "tipo_inmueble": None,
                "calle": row["calle"],
                "altura": row["altura"],
                "direccion": _format_inmueble_direccion(row["calle"], row["altura"]),
                "ubicacion": None,
                "superficie": row["superficie"],
                "estado_administrativo": row["estado_administrativo"],
                "estado_juridico": row["estado_juridico"],
                "observaciones": row["observaciones"],
                "disponibilidad_actual": row["disponibilidad_actual"],
                "disponibilidad_ambigua": row["disponibilidad_ambigua"],
                "ocupacion_actual": row["ocupacion_actual"],
                "ocupacion_ambigua": row["ocupacion_ambigua"],
                "cantidad_unidades_funcionales": row["cantidad_unidades_funcionales"],
            }
            for row in rows
        ]
        return {"items": items, "total": total, "limit": limit, "offset": offset}

    def get_inmueble(self, id_inmueble: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_inmueble,
                id_desarrollo,
                uid_global::text AS uid_global,
                version_registro,
                codigo_inmueble,
                nombre_inmueble,
                calle,
                altura,
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
            "uid_global": row["uid_global"],
            "version_registro": row["version_registro"],
            "codigo_inmueble": row["codigo_inmueble"],
            "nombre_inmueble": row["nombre_inmueble"],
            "calle": row["calle"],
            "altura": row["altura"],
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
                calle,
                altura,
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
            "calle": row["calle"],
            "altura": row["altura"],
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
            "calle": values["calle"],
            "altura": values["altura"],
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
                calle,
                altura,
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
                :calle,
                :altura,
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
            "calle": values["calle"],
            "altura": values["altura"],
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
                calle = :calle,
                altura = :altura,
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
                calle,
                altura,
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
                "calle": row["calle"],
                "altura": row["altura"],
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

    def has_entrega_restitucion_inmueble_for_contrato_fecha_sin_commit(
        self, *, id_contrato_alquiler: int, fecha_entrega
    ) -> bool:
        stmt = text(
            """
            SELECT 1
            FROM entrega_restitucion_inmueble
            WHERE id_contrato_alquiler = :id_contrato_alquiler
              AND fecha_entrega = :fecha_entrega
              AND deleted_at IS NULL
            LIMIT 1
            """
        )
        return (
            self.db.execute(
                stmt,
                {
                    "id_contrato_alquiler": id_contrato_alquiler,
                    "fecha_entrega": fecha_entrega,
                },
            ).scalar_one_or_none()
            is not None
        )

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
