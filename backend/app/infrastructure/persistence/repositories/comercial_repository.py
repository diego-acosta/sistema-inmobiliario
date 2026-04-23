from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository


VENTA_INMOBILIARIO_EVENT_TYPES = (
    "venta_confirmada",
    "escrituracion_registrada",
)
VENTA_INMOBILIARIO_EFFECTS_BY_EVENT = {
    "venta_confirmada": {
        "disponibilidad": "SIN_CAMBIO",
        "ocupacion": "SIN_CAMBIO",
    },
    "escrituracion_registrada": {
        "disponibilidad": "RESERVADA->NO_DISPONIBLE",
        "ocupacion": "SIN_CAMBIO",
    },
}


class ComercialRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_reservas_venta(
        self,
        *,
        codigo_reserva: str | None,
        estado_reserva: str | None,
        fecha_desde: datetime | None,
        fecha_hasta: datetime | None,
        vigente: bool | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        filters = ["deleted_at IS NULL"]
        params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
        }

        if codigo_reserva is not None:
            filters.append("codigo_reserva = :codigo_reserva")
            params["codigo_reserva"] = codigo_reserva

        if estado_reserva is not None:
            filters.append("LOWER(estado_reserva) = :estado_reserva")
            params["estado_reserva"] = estado_reserva.strip().lower()

        if fecha_desde is not None:
            filters.append("fecha_reserva >= :fecha_desde")
            params["fecha_desde"] = fecha_desde

        if fecha_hasta is not None:
            filters.append("fecha_reserva <= :fecha_hasta")
            params["fecha_hasta"] = fecha_hasta

        if vigente is not None:
            if vigente:
                filters.append("LOWER(estado_reserva) IN ('activa', 'confirmada')")
            else:
                filters.append(
                    "LOWER(estado_reserva) NOT IN ('activa', 'confirmada')"
                )

        where_clause = " AND ".join(filters)

        reserva_statement = text(
            f"""
            SELECT
                id_reserva_venta,
                uid_global,
                version_registro,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                fecha_vencimiento,
                observaciones
            FROM reserva_venta
            WHERE {where_clause}
            ORDER BY fecha_reserva DESC, id_reserva_venta DESC
            LIMIT :limit
            OFFSET :offset
            """
        )
        total_statement = text(
            f"""
            SELECT COUNT(*) AS total
            FROM reserva_venta
            WHERE {where_clause}
            """
        )

        reserva_rows = self.db.execute(reserva_statement, params).mappings().all()
        total = self.db.execute(total_statement, params).scalar_one()

        reserva_ids = [row["id_reserva_venta"] for row in reserva_rows]
        objetos_by_reserva: dict[int, list[dict[str, Any]]] = {
            reserva_id: [] for reserva_id in reserva_ids
        }

        if reserva_ids:
            objetos_statement = text(
                """
                SELECT
                    id_reserva_venta,
                    id_reserva_venta_objeto,
                    id_inmueble,
                    id_unidad_funcional,
                    observaciones
                FROM reserva_venta_objeto_inmobiliario
                WHERE id_reserva_venta = ANY(:reserva_ids)
                  AND deleted_at IS NULL
                ORDER BY id_reserva_venta, id_reserva_venta_objeto
                """
            )
            objetos_rows = self.db.execute(
                objetos_statement, {"reserva_ids": reserva_ids}
            ).mappings().all()
            for row in objetos_rows:
                objetos_by_reserva[row["id_reserva_venta"]].append(
                    {
                        "id_reserva_venta_objeto": row["id_reserva_venta_objeto"],
                        "id_inmueble": row["id_inmueble"],
                        "id_unidad_funcional": row["id_unidad_funcional"],
                        "observaciones": row["observaciones"],
                    }
                )

        return {
            "items": [
                {
                    "id_reserva_venta": row["id_reserva_venta"],
                    "uid_global": str(row["uid_global"]),
                    "version_registro": row["version_registro"],
                    "codigo_reserva": row["codigo_reserva"],
                    "fecha_reserva": row["fecha_reserva"],
                    "estado_reserva": row["estado_reserva"],
                    "fecha_vencimiento": row["fecha_vencimiento"],
                    "observaciones": row["observaciones"],
                    "objetos": objetos_by_reserva.get(row["id_reserva_venta"], []),
                }
                for row in reserva_rows
            ],
            "total": total,
        }

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

    def get_reserva_venta(self, id_reserva_venta: int) -> dict[str, Any] | None:
        reserva_statement = text(
            """
            SELECT
                id_reserva_venta,
                uid_global,
                version_registro,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                fecha_vencimiento,
                observaciones,
                deleted_at
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        )
        objeto_statement = text(
            """
            SELECT
                id_reserva_venta_objeto,
                id_inmueble,
                id_unidad_funcional,
                observaciones
            FROM reserva_venta_objeto_inmobiliario
            WHERE id_reserva_venta = :id_reserva_venta
              AND deleted_at IS NULL
            ORDER BY id_reserva_venta_objeto
            """
        )
        participacion_statement = text(
            """
            SELECT
                id_relacion_persona_rol,
                id_persona,
                id_rol_participacion,
                fecha_desde,
                fecha_hasta,
                observaciones
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'reserva_venta'
              AND id_relacion = :id_reserva_venta
              AND deleted_at IS NULL
            ORDER BY id_relacion_persona_rol
            """
        )

        reserva_row = self.db.execute(
            reserva_statement, {"id_reserva_venta": id_reserva_venta}
        ).mappings().one_or_none()
        if reserva_row is None:
            return None

        objetos_rows = self.db.execute(
            objeto_statement, {"id_reserva_venta": id_reserva_venta}
        ).mappings().all()
        participaciones_rows = self.db.execute(
            participacion_statement, {"id_reserva_venta": id_reserva_venta}
        ).mappings().all()

        return {
            "id_reserva_venta": reserva_row["id_reserva_venta"],
            "uid_global": str(reserva_row["uid_global"]),
            "version_registro": reserva_row["version_registro"],
            "codigo_reserva": reserva_row["codigo_reserva"],
            "fecha_reserva": reserva_row["fecha_reserva"],
            "estado_reserva": reserva_row["estado_reserva"],
            "fecha_vencimiento": reserva_row["fecha_vencimiento"],
            "observaciones": reserva_row["observaciones"],
            "deleted_at": reserva_row["deleted_at"],
            "objetos": [
                {
                    "id_reserva_venta_objeto": row["id_reserva_venta_objeto"],
                    "id_inmueble": row["id_inmueble"],
                    "id_unidad_funcional": row["id_unidad_funcional"],
                    "observaciones": row["observaciones"],
                }
                for row in objetos_rows
            ],
            "participaciones": [
                {
                    "id_relacion_persona_rol": row["id_relacion_persona_rol"],
                    "id_persona": row["id_persona"],
                    "id_rol_participacion": row["id_rol_participacion"],
                    "fecha_desde": row["fecha_desde"],
                    "fecha_hasta": row["fecha_hasta"],
                    "observaciones": row["observaciones"],
                }
                for row in participaciones_rows
            ],
        }

    def reserva_codigo_exists(
        self,
        codigo_reserva: str,
        *,
        exclude_id_reserva_venta: int | None = None,
    ) -> bool:
        filters = ["codigo_reserva = :codigo_reserva"]
        params: dict[str, Any] = {"codigo_reserva": codigo_reserva}
        if exclude_id_reserva_venta is not None:
            filters.append("id_reserva_venta <> :exclude_id_reserva_venta")
            params["exclude_id_reserva_venta"] = exclude_id_reserva_venta

        where_clause = " AND ".join(filters)
        statement = text(
            f"""
            SELECT 1
            FROM reserva_venta
            WHERE {where_clause}
            """
        )
        return self.db.execute(statement, params).scalar_one_or_none() is not None

    def get_venta(self, id_venta: int) -> dict[str, Any] | None:
        venta_statement = text(
            """
            SELECT
                id_venta,
                uid_global,
                version_registro,
                id_reserva_venta,
                codigo_venta,
                fecha_venta,
                estado_venta,
                monto_total,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            FROM venta
            WHERE id_venta = :id_venta
            """
        )
        objeto_statement = text(
            """
            SELECT
                id_venta_objeto,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                precio_asignado,
                observaciones
            FROM venta_objeto_inmobiliario
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            ORDER BY id_venta_objeto
            """
        )

        venta_row = self.db.execute(
            venta_statement, {"id_venta": id_venta}
        ).mappings().one_or_none()
        if venta_row is None:
            return None

        objetos_rows = self.db.execute(
            objeto_statement, {"id_venta": id_venta}
        ).mappings().all()

        return {
            "id_venta": venta_row["id_venta"],
            "uid_global": str(venta_row["uid_global"]),
            "version_registro": venta_row["version_registro"],
            "id_reserva_venta": venta_row["id_reserva_venta"],
            "codigo_venta": venta_row["codigo_venta"],
            "fecha_venta": venta_row["fecha_venta"],
            "estado_venta": venta_row["estado_venta"],
            "monto_total": venta_row["monto_total"],
            "observaciones": venta_row["observaciones"],
            "created_at": venta_row["created_at"],
            "updated_at": venta_row["updated_at"],
            "deleted_at": venta_row["deleted_at"],
            "objetos": [
                {
                    "id_venta_objeto": row["id_venta_objeto"],
                    "version_registro": row["version_registro"],
                    "id_inmueble": row["id_inmueble"],
                    "id_unidad_funcional": row["id_unidad_funcional"],
                    "precio_asignado": row["precio_asignado"],
                    "observaciones": row["observaciones"],
                }
                for row in objetos_rows
            ],
        }

    def get_venta_detail(self, id_venta: int) -> dict[str, Any] | None:
        venta = self.get_venta(id_venta)
        if venta is None or venta["deleted_at"] is not None:
            return None

        current_timestamp = datetime.now(UTC)
        origen = {
            "venta_directa": venta["id_reserva_venta"] is None,
            "con_reserva": None,
        }
        if venta["id_reserva_venta"] is not None:
            origen["con_reserva"] = self._get_reserva_venta_origin(
                venta["id_reserva_venta"]
            )

        objetos = [
            {
                "id_venta_objeto_inmobiliario": objeto["id_venta_objeto"],
                "id_inmueble": objeto["id_inmueble"],
                "id_unidad_funcional": objeto["id_unidad_funcional"],
                "precio_asignado": objeto["precio_asignado"],
                "observaciones": objeto["observaciones"],
                "disponibilidad_actual": self._get_current_disponibilidad_state(
                    id_inmueble=objeto["id_inmueble"],
                    id_unidad_funcional=objeto["id_unidad_funcional"],
                    at_datetime=current_timestamp,
                ),
                "ocupacion_actual": self._get_current_ocupacion_type(
                    id_inmueble=objeto["id_inmueble"],
                    id_unidad_funcional=objeto["id_unidad_funcional"],
                    at_datetime=current_timestamp,
                ),
            }
            for objeto in venta["objetos"]
        ]
        instrumentos = self._get_instrumentos_compraventa_for_venta(id_venta)
        cesiones = self._get_cesiones_for_venta(id_venta)
        escrituraciones = self._get_escrituraciones_for_venta(id_venta)
        integracion_inmobiliaria = self._get_integracion_inmobiliaria_for_venta(id_venta)

        venta_cerrada_logica = (
            (venta["estado_venta"] or "").strip().lower() == "confirmada"
            and len(escrituraciones) > 0
        )
        estado_operativo_conocido_del_activo: str | None = None
        estados_operativos_conocidos = [
            objeto["disponibilidad_actual"] for objeto in objetos
        ]
        if objetos and all(
            estado is not None for estado in estados_operativos_conocidos
        ):
            estados_unicos = set(estados_operativos_conocidos)
            if len(estados_unicos) == 1:
                estado_operativo_conocido_del_activo = next(iter(estados_unicos))

        return {
            "id_venta": venta["id_venta"],
            "version_registro": venta["version_registro"],
            "codigo_venta": venta["codigo_venta"],
            "fecha_venta": venta["fecha_venta"],
            "estado_venta": venta["estado_venta"],
            "monto_total": venta["monto_total"],
            "deleted_at": venta["deleted_at"],
            "origen": origen,
            "objetos": objetos,
            "instrumentos_compraventa": instrumentos,
            "cesiones": cesiones,
            "escrituraciones": escrituraciones,
            "integracion_inmobiliaria": integracion_inmobiliaria,
            "resumen": {
                "venta_cerrada_logica": venta_cerrada_logica,
                "estado_operativo_conocido_del_activo": estado_operativo_conocido_del_activo,
            },
        }

    def list_instrumentos_compraventa_for_venta(
        self,
        id_venta: int,
        *,
        tipo_instrumento: str | None,
        estado_instrumento: str | None,
        fecha_desde: datetime | None,
        fecha_hasta: datetime | None,
    ) -> dict[str, Any]:
        instrumentos = self._get_instrumentos_compraventa_for_venta(
            id_venta,
            tipo_instrumento=tipo_instrumento,
            estado_instrumento=estado_instrumento,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        return {
            "items": instrumentos,
            "total": len(instrumentos),
        }

    def list_cesiones_for_venta(
        self,
        id_venta: int,
        *,
        tipo_cesion: str | None,
        fecha_desde: datetime | None,
        fecha_hasta: datetime | None,
    ) -> dict[str, Any]:
        cesiones = self._get_cesiones_for_venta(
            id_venta,
            tipo_cesion=tipo_cesion,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
        return {
            "items": cesiones,
            "total": len(cesiones),
        }

    def list_escrituraciones_for_venta(
        self,
        id_venta: int,
        *,
        fecha_desde: datetime | None,
        fecha_hasta: datetime | None,
        numero_escritura: str | None,
    ) -> dict[str, Any]:
        escrituraciones = self._get_escrituraciones_for_venta(
            id_venta,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero_escritura=numero_escritura,
        )
        return {
            "items": escrituraciones,
            "total": len(escrituraciones),
        }

    def _get_integracion_inmobiliaria_for_venta(self, id_venta: int) -> dict[str, Any]:
        event_type_filters = ", ".join(
            f"'{event_type}'" for event_type in VENTA_INMOBILIARIO_EVENT_TYPES
        )
        statement = text(
            f"""
            SELECT
                id,
                event_type,
                status,
                occurred_at,
                published_at,
                payload
            FROM outbox_event
            WHERE aggregate_type = 'venta'
              AND aggregate_id = :id_venta
              AND event_type IN ({event_type_filters})
            ORDER BY occurred_at, id
            """
        )
        rows = self.db.execute(statement, {"id_venta": id_venta}).mappings().all()
        return {
            "eventos": [
                {
                    "id_evento_outbox": row["id"],
                    "nombre_evento": row["event_type"],
                    "estado": row["status"],
                    "ocurrido_en": row["occurred_at"],
                    "publicado_en": row["published_at"],
                    "objetos": [
                        {
                            "id_inmueble": objeto["id_inmueble"],
                            "id_unidad_funcional": objeto["id_unidad_funcional"],
                            "efecto_inmobiliario": self._get_integration_effect_for_event(
                                row["event_type"]
                            ),
                        }
                        for objeto in self._get_event_objects_from_payload(row["payload"])
                    ],
                }
                for row in rows
            ]
        }

    def _get_event_objects_from_payload(self, payload: Any) -> list[dict[str, int | None]]:
        if not isinstance(payload, dict):
            return []

        objetos = payload.get("objetos")
        if not isinstance(objetos, list):
            return []

        seen_objects: set[tuple[str, int]] = set()
        parsed_objects: list[dict[str, int | None]] = []
        for objeto in objetos:
            if not isinstance(objeto, dict):
                continue

            id_inmueble = objeto.get("id_inmueble")
            id_unidad_funcional = objeto.get("id_unidad_funcional")
            if (id_inmueble is None) == (id_unidad_funcional is None):
                continue
            if id_inmueble is not None and not isinstance(id_inmueble, int):
                continue
            if id_unidad_funcional is not None and not isinstance(id_unidad_funcional, int):
                continue

            object_key = (
                ("inmueble", id_inmueble)
                if id_inmueble is not None
                else ("unidad_funcional", id_unidad_funcional)
            )
            if object_key in seen_objects:
                continue
            seen_objects.add(object_key)

            parsed_objects.append(
                {
                    "id_inmueble": id_inmueble,
                    "id_unidad_funcional": id_unidad_funcional,
                }
            )

        return parsed_objects

    def _get_integration_effect_for_event(self, event_type: str) -> dict[str, str | None]:
        effect = VENTA_INMOBILIARIO_EFFECTS_BY_EVENT.get(
            event_type,
            {
                "disponibilidad": None,
                "ocupacion": None,
            },
        )
        return {
            "disponibilidad": effect["disponibilidad"],
            "ocupacion": effect["ocupacion"],
        }

    def venta_exists_for_reserva(self, id_reserva_venta: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM venta
            WHERE id_reserva_venta = :id_reserva_venta
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(
                statement, {"id_reserva_venta": id_reserva_venta}
            ).scalar_one_or_none()
            is not None
        )

    def update_reserva_venta(self, payload: Any) -> dict[str, Any] | None:
        values = self._values(payload)

        statement = text(
            """
            UPDATE reserva_venta
            SET
                codigo_reserva = :codigo_reserva,
                fecha_reserva = :fecha_reserva,
                fecha_vencimiento = :fecha_vencimiento,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_reserva_venta = :id_reserva_venta
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_reserva_venta,
                uid_global,
                version_registro,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                fecha_vencimiento,
                observaciones
            """
        )

        try:
            updated = self.db.execute(
                statement,
                {
                    "id_reserva_venta": values["id_reserva_venta"],
                    "codigo_reserva": values["codigo_reserva"],
                    "fecha_reserva": values["fecha_reserva"],
                    "fecha_vencimiento": values["fecha_vencimiento"],
                    "observaciones": values["observaciones"],
                    "version_registro_actual": values["version_registro_actual"],
                    "version_registro_nueva": values["version_registro_nueva"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if updated is None:
                self.db.rollback()
                return None

            objetos = self.db.execute(
                text(
                    """
                    SELECT
                        id_reserva_venta_objeto,
                        id_inmueble,
                        id_unidad_funcional,
                        observaciones
                    FROM reserva_venta_objeto_inmobiliario
                    WHERE id_reserva_venta = :id_reserva_venta
                      AND deleted_at IS NULL
                    ORDER BY id_reserva_venta_objeto
                    """
                ),
                {"id_reserva_venta": values["id_reserva_venta"]},
            ).mappings().all()

            self.db.commit()
            return {
                "id_reserva_venta": updated["id_reserva_venta"],
                "uid_global": str(updated["uid_global"]),
                "version_registro": updated["version_registro"],
                "codigo_reserva": updated["codigo_reserva"],
                "fecha_reserva": updated["fecha_reserva"],
                "estado_reserva": updated["estado_reserva"],
                "fecha_vencimiento": updated["fecha_vencimiento"],
                "observaciones": updated["observaciones"],
                "objetos": [
                    {
                        "id_reserva_venta_objeto": objeto["id_reserva_venta_objeto"],
                        "id_inmueble": objeto["id_inmueble"],
                        "id_unidad_funcional": objeto["id_unidad_funcional"],
                        "observaciones": objeto["observaciones"],
                    }
                    for objeto in objetos
                ],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_reserva_venta(self, payload: Any) -> dict[str, Any] | None:
        values = self._values(payload)

        statement = text(
            """
            UPDATE reserva_venta
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_reserva_venta = :id_reserva_venta
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_reserva_venta,
                version_registro
            """
        )

        try:
            deleted = self.db.execute(
                statement,
                {
                    "id_reserva_venta": values["id_reserva_venta"],
                    "version_registro_actual": values["version_registro_actual"],
                    "version_registro_nueva": values["version_registro_nueva"],
                    "updated_at": values["updated_at"],
                    "deleted_at": values["deleted_at"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if deleted is None:
                self.db.rollback()
                return None

            self.db.commit()
            return {
                "id_reserva_venta": deleted["id_reserva_venta"],
                "version_registro": deleted["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise

    def has_active_venta_for_reserva(
        self,
        id_reserva_venta: int,
        *,
        conflict_states: set[str],
    ) -> bool:
        state_filters = ", ".join(f"'{state}'" for state in sorted(conflict_states))
        statement = text(
            f"""
            SELECT 1
            FROM venta
            WHERE id_reserva_venta = :id_reserva_venta
              AND deleted_at IS NULL
              AND LOWER(estado_venta) IN ({state_filters})
            """
        )
        return (
            self.db.execute(
                statement, {"id_reserva_venta": id_reserva_venta}
            ).scalar_one_or_none()
            is not None
        )

    def venta_codigo_exists(self, codigo_venta: str) -> bool:
        statement = text(
            """
            SELECT 1
            FROM venta
            WHERE codigo_venta = :codigo_venta
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(statement, {"codigo_venta": codigo_venta}).scalar_one_or_none()
            is not None
        )

    def get_current_disponibilidad_state(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> str | None:
        filters = self._object_filters(
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
        )
        statement = text(
            f"""
            SELECT UPPER(estado_disponibilidad) AS estado_disponibilidad
            FROM disponibilidad
            WHERE deleted_at IS NULL
              AND {filters}
              AND fecha_desde <= :at_datetime
              AND (fecha_hasta IS NULL OR fecha_hasta >= :at_datetime)
            ORDER BY id_disponibilidad
            """
        )
        rows = self.db.execute(
            statement,
            self._object_params(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                at_datetime=at_datetime,
            ),
        ).mappings().all()
        if len(rows) != 1:
            return None
        return rows[0]["estado_disponibilidad"]

    def has_current_disponibilidad_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
        filters = self._object_filters(id_inmueble=id_inmueble, id_unidad_funcional=id_unidad_funcional)
        statement = text(
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
                statement,
                self._object_params(
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
        filters = self._object_filters(id_inmueble=id_inmueble, id_unidad_funcional=id_unidad_funcional)
        statement = text(
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
                statement,
                self._object_params(
                    id_inmueble=id_inmueble,
                    id_unidad_funcional=id_unidad_funcional,
                    at_datetime=at_datetime,
                ),
            ).scalar_one_or_none()
            is not None
        )

    def has_current_ocupacion_conflict(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
        filters = self._object_filters(id_inmueble=id_inmueble, id_unidad_funcional=id_unidad_funcional)
        statement = text(
            f"""
            SELECT 1
            FROM ocupacion
            WHERE deleted_at IS NULL
              AND {filters}
              AND fecha_desde <= :at_datetime
              AND (fecha_hasta IS NULL OR fecha_hasta >= :at_datetime)
            """
        )
        return (
            self.db.execute(
                statement,
                self._object_params(
                    id_inmueble=id_inmueble,
                    id_unidad_funcional=id_unidad_funcional,
                    at_datetime=at_datetime,
                ),
            ).scalar_one_or_none()
            is not None
        )

    def has_conflicting_active_venta(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
        exclude_id_venta: int | None = None,
    ) -> bool:
        state_filters = ", ".join(f"'{state}'" for state in sorted(conflict_states))
        if id_inmueble is not None:
            object_filter = "vo.id_inmueble = :id_inmueble"
            params = {"id_inmueble": id_inmueble}
        else:
            object_filter = "vo.id_unidad_funcional = :id_unidad_funcional"
            params = {"id_unidad_funcional": id_unidad_funcional}

        exclude_filter = ""
        if exclude_id_venta is not None:
            exclude_filter = "AND v.id_venta <> :exclude_id_venta"
            params["exclude_id_venta"] = exclude_id_venta

        statement = text(
            f"""
            SELECT 1
            FROM venta_objeto_inmobiliario vo
            JOIN venta v ON v.id_venta = vo.id_venta
            WHERE vo.deleted_at IS NULL
              AND v.deleted_at IS NULL
              AND {object_filter}
              AND LOWER(v.estado_venta) IN ({state_filters})
              {exclude_filter}
            """
        )
        return self.db.execute(statement, params).scalar_one_or_none() is not None

    def has_conflicting_active_reserva(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
        exclude_id_reserva_venta: int | None = None,
    ) -> bool:
        state_filters = ", ".join(f"'{state}'" for state in sorted(conflict_states))
        if id_inmueble is not None:
            object_filter = "rvo.id_inmueble = :id_inmueble"
            params = {"id_inmueble": id_inmueble}
        else:
            object_filter = "rvo.id_unidad_funcional = :id_unidad_funcional"
            params = {"id_unidad_funcional": id_unidad_funcional}

        exclude_filter = ""
        if exclude_id_reserva_venta is not None:
            exclude_filter = "AND rv.id_reserva_venta <> :exclude_id_reserva_venta"
            params["exclude_id_reserva_venta"] = exclude_id_reserva_venta

        statement = text(
            f"""
            SELECT 1
            FROM reserva_venta_objeto_inmobiliario rvo
            JOIN reserva_venta rv ON rv.id_reserva_venta = rvo.id_reserva_venta
            WHERE rvo.deleted_at IS NULL
              AND rv.deleted_at IS NULL
              AND {object_filter}
              AND LOWER(rv.estado_reserva) IN ({state_filters})
              {exclude_filter}
            """
        )
        return self.db.execute(statement, params).scalar_one_or_none() is not None

    def confirm_reserva_venta(
        self,
        payload: Any,
        disponibilidades: list[Any],
    ) -> dict[str, Any]:
        values = self._values(payload)

        update_statement = text(
            """
            UPDATE reserva_venta
            SET
                estado_reserva = :estado_reserva,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_reserva_venta = :id_reserva_venta
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_reserva_venta,
                uid_global,
                version_registro,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                fecha_vencimiento,
                observaciones
            """
        )

        try:
            updated = self.db.execute(
                update_statement,
                {
                    "id_reserva_venta": values["id_reserva_venta"],
                    "estado_reserva": values["estado_reserva"],
                    "version_registro_actual": values["version_registro_actual"],
                    "version_registro_nueva": values["version_registro_nueva"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            for disponibilidad in disponibilidades:
                replace_result = self._replace_disponibilidad_vigente_in_transaction(
                    disponibilidad
                )
                if replace_result["status"] != "OK":
                    self.db.rollback()
                    return replace_result

            objetos = self.db.execute(
                text(
                    """
                    SELECT
                        id_reserva_venta_objeto,
                        id_inmueble,
                        id_unidad_funcional,
                        observaciones
                    FROM reserva_venta_objeto_inmobiliario
                    WHERE id_reserva_venta = :id_reserva_venta
                      AND deleted_at IS NULL
                    ORDER BY id_reserva_venta_objeto
                    """
                ),
                {"id_reserva_venta": values["id_reserva_venta"]},
            ).mappings().all()

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_reserva_venta": updated["id_reserva_venta"],
                    "uid_global": str(updated["uid_global"]),
                    "version_registro": updated["version_registro"],
                    "codigo_reserva": updated["codigo_reserva"],
                    "fecha_reserva": updated["fecha_reserva"],
                    "estado_reserva": updated["estado_reserva"],
                    "fecha_vencimiento": updated["fecha_vencimiento"],
                    "observaciones": updated["observaciones"],
                    "objetos": [
                        {
                            "id_reserva_venta_objeto": row["id_reserva_venta_objeto"],
                            "id_inmueble": row["id_inmueble"],
                            "id_unidad_funcional": row["id_unidad_funcional"],
                            "observaciones": row["observaciones"],
                        }
                        for row in objetos
                    ],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def cancel_reserva_venta(
        self,
        payload: Any,
        disponibilidades: list[Any],
    ) -> dict[str, Any]:
        values = self._values(payload)

        update_statement = text(
            """
            UPDATE reserva_venta
            SET
                estado_reserva = :estado_reserva,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_reserva_venta = :id_reserva_venta
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_reserva_venta,
                uid_global,
                version_registro,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                fecha_vencimiento,
                observaciones
            """
        )

        try:
            updated = self.db.execute(
                update_statement,
                {
                    "id_reserva_venta": values["id_reserva_venta"],
                    "estado_reserva": values["estado_reserva"],
                    "version_registro_actual": values["version_registro_actual"],
                    "version_registro_nueva": values["version_registro_nueva"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            for disponibilidad in disponibilidades:
                replace_result = self._replace_disponibilidad_vigente_in_transaction(
                    disponibilidad,
                    expected_current_state="RESERVADA",
                )
                if replace_result["status"] != "OK":
                    self.db.rollback()
                    return replace_result

            objetos = self.db.execute(
                text(
                    """
                    SELECT
                        id_reserva_venta_objeto,
                        id_inmueble,
                        id_unidad_funcional,
                        observaciones
                    FROM reserva_venta_objeto_inmobiliario
                    WHERE id_reserva_venta = :id_reserva_venta
                      AND deleted_at IS NULL
                    ORDER BY id_reserva_venta_objeto
                    """
                ),
                {"id_reserva_venta": values["id_reserva_venta"]},
            ).mappings().all()

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_reserva_venta": updated["id_reserva_venta"],
                    "uid_global": str(updated["uid_global"]),
                    "version_registro": updated["version_registro"],
                    "codigo_reserva": updated["codigo_reserva"],
                    "fecha_reserva": updated["fecha_reserva"],
                    "estado_reserva": updated["estado_reserva"],
                    "fecha_vencimiento": updated["fecha_vencimiento"],
                    "observaciones": updated["observaciones"],
                    "objetos": [
                        {
                            "id_reserva_venta_objeto": row["id_reserva_venta_objeto"],
                            "id_inmueble": row["id_inmueble"],
                            "id_unidad_funcional": row["id_unidad_funcional"],
                            "observaciones": row["observaciones"],
                        }
                        for row in objetos
                    ],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def expire_reserva_venta(
        self,
        payload: Any,
        disponibilidades: list[Any],
    ) -> dict[str, Any]:
        values = self._values(payload)

        update_statement = text(
            """
            UPDATE reserva_venta
            SET
                estado_reserva = :estado_reserva,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_reserva_venta = :id_reserva_venta
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_reserva_venta,
                uid_global,
                version_registro,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                fecha_vencimiento,
                observaciones
            """
        )

        try:
            updated = self.db.execute(
                update_statement,
                {
                    "id_reserva_venta": values["id_reserva_venta"],
                    "estado_reserva": values["estado_reserva"],
                    "version_registro_actual": values["version_registro_actual"],
                    "version_registro_nueva": values["version_registro_nueva"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            for disponibilidad in disponibilidades:
                replace_result = self._replace_disponibilidad_vigente_in_transaction(
                    disponibilidad,
                    expected_current_state="RESERVADA",
                )
                if replace_result["status"] != "OK":
                    self.db.rollback()
                    return replace_result

            objetos = self.db.execute(
                text(
                    """
                    SELECT
                        id_reserva_venta_objeto,
                        id_inmueble,
                        id_unidad_funcional,
                        observaciones
                    FROM reserva_venta_objeto_inmobiliario
                    WHERE id_reserva_venta = :id_reserva_venta
                      AND deleted_at IS NULL
                    ORDER BY id_reserva_venta_objeto
                    """
                ),
                {"id_reserva_venta": values["id_reserva_venta"]},
            ).mappings().all()

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_reserva_venta": updated["id_reserva_venta"],
                    "uid_global": str(updated["uid_global"]),
                    "version_registro": updated["version_registro"],
                    "codigo_reserva": updated["codigo_reserva"],
                    "fecha_reserva": updated["fecha_reserva"],
                    "estado_reserva": updated["estado_reserva"],
                    "fecha_vencimiento": updated["fecha_vencimiento"],
                    "observaciones": updated["observaciones"],
                    "objetos": [
                        {
                            "id_reserva_venta_objeto": row["id_reserva_venta_objeto"],
                            "id_inmueble": row["id_inmueble"],
                            "id_unidad_funcional": row["id_unidad_funcional"],
                            "observaciones": row["observaciones"],
                        }
                        for row in objetos
                    ],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def activate_reserva_venta(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)

        statement = text(
            """
            UPDATE reserva_venta
            SET
                estado_reserva = :estado_reserva,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_reserva_venta = :id_reserva_venta
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_reserva_venta,
                uid_global,
                version_registro,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                fecha_vencimiento,
                observaciones
            """
        )

        try:
            updated = self.db.execute(
                statement,
                {
                    "id_reserva_venta": values["id_reserva_venta"],
                    "estado_reserva": values["estado_reserva"],
                    "version_registro_actual": values["version_registro_actual"],
                    "version_registro_nueva": values["version_registro_nueva"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            objetos = self.db.execute(
                text(
                    """
                    SELECT
                        id_reserva_venta_objeto,
                        id_inmueble,
                        id_unidad_funcional,
                        observaciones
                    FROM reserva_venta_objeto_inmobiliario
                    WHERE id_reserva_venta = :id_reserva_venta
                      AND deleted_at IS NULL
                    ORDER BY id_reserva_venta_objeto
                    """
                ),
                {"id_reserva_venta": values["id_reserva_venta"]},
            ).mappings().all()

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_reserva_venta": updated["id_reserva_venta"],
                    "uid_global": str(updated["uid_global"]),
                    "version_registro": updated["version_registro"],
                    "codigo_reserva": updated["codigo_reserva"],
                    "fecha_reserva": updated["fecha_reserva"],
                    "estado_reserva": updated["estado_reserva"],
                    "fecha_vencimiento": updated["fecha_vencimiento"],
                    "observaciones": updated["observaciones"],
                    "objetos": [
                        {
                            "id_reserva_venta_objeto": row["id_reserva_venta_objeto"],
                            "id_inmueble": row["id_inmueble"],
                            "id_unidad_funcional": row["id_unidad_funcional"],
                            "observaciones": row["observaciones"],
                        }
                        for row in objetos
                    ],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def create_reserva_venta(
        self,
        payload: Any,
        objetos: list[Any],
        participaciones: list[Any],
    ) -> dict[str, Any]:
        reserva_values = self._values(payload)
        db_values = {
            "uid_global": reserva_values["uid_global"],
            "version_registro": reserva_values["version_registro"],
            "created_at": reserva_values["created_at"],
            "updated_at": reserva_values["updated_at"],
            "id_instalacion_origen": reserva_values["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": reserva_values[
                "id_instalacion_ultima_modificacion"
            ],
            "op_id_alta": reserva_values["op_id_alta"],
            "op_id_ultima_modificacion": reserva_values["op_id_ultima_modificacion"],
            "codigo_reserva": reserva_values["codigo_reserva"],
            "fecha_reserva": reserva_values["fecha_reserva"],
            "estado_reserva": reserva_values["estado_reserva"],
            "fecha_vencimiento": reserva_values["fecha_vencimiento"],
            "observaciones": reserva_values["observaciones"],
        }

        reserva_statement = text(
            """
            INSERT INTO reserva_venta (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                fecha_vencimiento,
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
                :codigo_reserva,
                :fecha_reserva,
                :estado_reserva,
                :fecha_vencimiento,
                :observaciones
            )
            RETURNING id_reserva_venta
            """
        )

        objeto_statement = text(
            """
            INSERT INTO reserva_venta_objeto_inmobiliario (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_reserva_venta,
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
                :id_reserva_venta,
                :id_inmueble,
                :id_unidad_funcional,
                :observaciones
            )
            RETURNING id_reserva_venta_objeto
            """
        )

        participacion_statement = text(
            """
            INSERT INTO relacion_persona_rol (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona,
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
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
                :id_persona,
                :id_rol_participacion,
                :tipo_relacion,
                :id_relacion,
                :fecha_desde,
                :fecha_hasta,
                :observaciones
            )
            """
        )

        try:
            reserva_row = self.db.execute(reserva_statement, db_values).mappings().one()
            id_reserva_venta = reserva_row["id_reserva_venta"]
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
                        "id_reserva_venta": id_reserva_venta,
                        "id_inmueble": values["id_inmueble"],
                        "id_unidad_funcional": values["id_unidad_funcional"],
                        "observaciones": values["observaciones"],
                    },
                ).mappings().one()
                created_objetos.append(
                    {
                        "id_reserva_venta_objeto": objeto_row["id_reserva_venta_objeto"],
                        "id_inmueble": values["id_inmueble"],
                        "id_unidad_funcional": values["id_unidad_funcional"],
                        "observaciones": values["observaciones"],
                    }
                )

            for participacion in participaciones:
                values = self._values(participacion)
                self.db.execute(
                    participacion_statement,
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
                        "id_persona": values["id_persona"],
                        "id_rol_participacion": values["id_rol_participacion"],
                        "tipo_relacion": values["tipo_relacion"],
                        "id_relacion": id_reserva_venta,
                        "fecha_desde": values["fecha_desde"],
                        "fecha_hasta": values["fecha_hasta"],
                        "observaciones": values["observaciones"],
                    },
                )

            self.db.commit()
            return {
                "id_reserva_venta": id_reserva_venta,
                "objetos": created_objetos,
            }
        except Exception:
            self.db.rollback()
            raise

    def generate_venta_from_reserva(
        self,
        payload: Any,
        objetos: list[Any],
        participaciones: list[Any],
        reserva_payload: Any,
    ) -> dict[str, Any]:
        venta_values = self._values(payload)
        reserva_values = self._values(reserva_payload)

        venta_statement = text(
            """
            INSERT INTO venta (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_reserva_venta,
                codigo_venta,
                fecha_venta,
                estado_venta,
                monto_total,
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
                :id_reserva_venta,
                :codigo_venta,
                :fecha_venta,
                :estado_venta,
                :monto_total,
                :observaciones
            )
            RETURNING id_venta
            """
        )

        objeto_statement = text(
            """
            INSERT INTO venta_objeto_inmobiliario (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_venta,
                id_inmueble,
                id_unidad_funcional,
                precio_asignado,
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
                :id_venta,
                :id_inmueble,
                :id_unidad_funcional,
                :precio_asignado,
                :observaciones
            )
            RETURNING id_venta_objeto
            """
        )

        participacion_statement = text(
            """
            INSERT INTO relacion_persona_rol (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_persona,
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
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
                :id_persona,
                :id_rol_participacion,
                :tipo_relacion,
                :id_relacion,
                :fecha_desde,
                :fecha_hasta,
                :observaciones
            )
            """
        )

        reserva_statement = text(
            """
            UPDATE reserva_venta
            SET
                estado_reserva = :estado_reserva,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_reserva_venta = :id_reserva_venta
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING id_reserva_venta
            """
        )

        try:
            venta_row = self.db.execute(venta_statement, venta_values).mappings().one()
            id_venta = venta_row["id_venta"]
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
                        "id_venta": id_venta,
                        "id_inmueble": values["id_inmueble"],
                        "id_unidad_funcional": values["id_unidad_funcional"],
                        "precio_asignado": values["precio_asignado"],
                        "observaciones": values["observaciones"],
                    },
                ).mappings().one()
                created_objetos.append(
                    {
                        "id_venta_objeto": objeto_row["id_venta_objeto"],
                        "id_inmueble": values["id_inmueble"],
                        "id_unidad_funcional": values["id_unidad_funcional"],
                        "precio_asignado": values["precio_asignado"],
                        "observaciones": values["observaciones"],
                    }
                )

            for participacion in participaciones:
                values = self._values(participacion)
                self.db.execute(
                    participacion_statement,
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
                        "id_persona": values["id_persona"],
                        "id_rol_participacion": values["id_rol_participacion"],
                        "tipo_relacion": values["tipo_relacion"],
                        "id_relacion": id_venta,
                        "fecha_desde": values["fecha_desde"],
                        "fecha_hasta": values["fecha_hasta"],
                        "observaciones": values["observaciones"],
                    },
                )

            updated = self.db.execute(
                reserva_statement,
                {
                    "id_reserva_venta": reserva_values["id_reserva_venta"],
                    "estado_reserva": reserva_values["estado_reserva"],
                    "version_registro_actual": reserva_values["version_registro_actual"],
                    "version_registro_nueva": reserva_values["version_registro_nueva"],
                    "updated_at": reserva_values["updated_at"],
                    "id_instalacion_ultima_modificacion": reserva_values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_ultima_modificacion": reserva_values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if updated is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_venta": id_venta,
                    "uid_global": venta_values["uid_global"],
                    "version_registro": venta_values["version_registro"],
                    "id_reserva_venta": venta_values["id_reserva_venta"],
                    "codigo_venta": venta_values["codigo_venta"],
                    "fecha_venta": venta_values["fecha_venta"],
                    "estado_venta": venta_values["estado_venta"],
                    "monto_total": venta_values["monto_total"],
                    "observaciones": venta_values["observaciones"],
                    "objetos": created_objetos,
                    "created_at": venta_values["created_at"],
                    "updated_at": venta_values["updated_at"],
                    "deleted_at": None,
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def define_condiciones_comerciales_venta(
        self,
        payload: Any,
        objetos: list[Any],
    ) -> dict[str, Any]:
        venta_values = self._values(payload)

        venta_statement = text(
            """
            UPDATE venta
            SET
                monto_total = :monto_total,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_venta = :id_venta
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_venta,
                uid_global,
                version_registro,
                id_reserva_venta,
                codigo_venta,
                fecha_venta,
                estado_venta,
                monto_total,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            """
        )

        objeto_statement = text(
            """
            UPDATE venta_objeto_inmobiliario
            SET
                precio_asignado = :precio_asignado,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_venta_objeto = :id_venta_objeto
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_venta_objeto,
                id_inmueble,
                id_unidad_funcional,
                precio_asignado,
                observaciones
            """
        )

        try:
            venta_row = self.db.execute(
                venta_statement,
                {
                    "id_venta": venta_values["id_venta"],
                    "monto_total": venta_values["monto_total"],
                    "version_registro_actual": venta_values["version_registro_actual"],
                    "version_registro_nueva": venta_values["version_registro_nueva"],
                    "updated_at": venta_values["updated_at"],
                    "id_instalacion_ultima_modificacion": venta_values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_ultima_modificacion": venta_values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if venta_row is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            updated_objetos: list[dict[str, Any]] = []
            for objeto in objetos:
                values = self._values(objeto)
                objeto_row = self.db.execute(
                    objeto_statement,
                    {
                        "id_venta_objeto": values["id_venta_objeto"],
                        "precio_asignado": values["precio_asignado"],
                        "version_registro_actual": values["version_registro_actual"],
                        "version_registro_nueva": values["version_registro_nueva"],
                        "updated_at": values["updated_at"],
                        "id_instalacion_ultima_modificacion": values[
                            "id_instalacion_ultima_modificacion"
                        ],
                        "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                    },
                ).mappings().one_or_none()
                if objeto_row is None:
                    self.db.rollback()
                    return {"status": "OBJECT_UPDATE_FAILED"}

                updated_objetos.append(
                    {
                        "id_venta_objeto": objeto_row["id_venta_objeto"],
                        "id_inmueble": objeto_row["id_inmueble"],
                        "id_unidad_funcional": objeto_row["id_unidad_funcional"],
                        "precio_asignado": objeto_row["precio_asignado"],
                        "observaciones": objeto_row["observaciones"],
                    }
                )

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_venta": venta_row["id_venta"],
                    "uid_global": str(venta_row["uid_global"]),
                    "version_registro": venta_row["version_registro"],
                    "id_reserva_venta": venta_row["id_reserva_venta"],
                    "codigo_venta": venta_row["codigo_venta"],
                    "fecha_venta": venta_row["fecha_venta"],
                    "estado_venta": venta_row["estado_venta"],
                    "monto_total": venta_row["monto_total"],
                    "observaciones": venta_row["observaciones"],
                    "objetos": updated_objetos,
                    "created_at": venta_row["created_at"],
                    "updated_at": venta_row["updated_at"],
                    "deleted_at": venta_row["deleted_at"],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def confirm_venta(self, payload: Any, *, outbox_event: Any | None = None) -> dict[str, Any]:
        values = self._values(payload)
        outbox_repository = OutboxRepository(self.db)

        venta_statement = text(
            """
            UPDATE venta
            SET
                estado_venta = :estado_venta,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_venta = :id_venta
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_venta,
                uid_global,
                version_registro,
                id_reserva_venta,
                codigo_venta,
                fecha_venta,
                estado_venta,
                monto_total,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            """
        )

        objeto_statement = text(
            """
            SELECT
                id_venta_objeto,
                id_inmueble,
                id_unidad_funcional,
                precio_asignado,
                observaciones
            FROM venta_objeto_inmobiliario
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            ORDER BY id_venta_objeto
            """
        )

        try:
            venta_row = self.db.execute(
                venta_statement,
                {
                    "id_venta": values["id_venta"],
                    "estado_venta": values["estado_venta"],
                    "observaciones": values["observaciones"],
                    "version_registro_actual": values["version_registro_actual"],
                    "version_registro_nueva": values["version_registro_nueva"],
                    "updated_at": values["updated_at"],
                    "id_instalacion_ultima_modificacion": values[
                        "id_instalacion_ultima_modificacion"
                    ],
                    "op_id_ultima_modificacion": values["op_id_ultima_modificacion"],
                },
            ).mappings().one_or_none()
            if venta_row is None:
                self.db.rollback()
                return {"status": "CONCURRENCY_ERROR"}

            objetos = self.db.execute(
                objeto_statement,
                {"id_venta": values["id_venta"]},
            ).mappings().all()

            if outbox_event is not None:
                outbox_values = self._values(outbox_event)
                outbox_repository.add_event(
                    event_type=outbox_values["event_type"],
                    aggregate_type=outbox_values["aggregate_type"],
                    aggregate_id=outbox_values["aggregate_id"],
                    payload=outbox_values["payload"],
                    occurred_at=outbox_values["occurred_at"],
                    published_at=outbox_values.get("published_at"),
                    status=outbox_values["status"],
                )

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_venta": venta_row["id_venta"],
                    "uid_global": str(venta_row["uid_global"]),
                    "version_registro": venta_row["version_registro"],
                    "id_reserva_venta": venta_row["id_reserva_venta"],
                    "codigo_venta": venta_row["codigo_venta"],
                    "fecha_venta": venta_row["fecha_venta"],
                    "estado_venta": venta_row["estado_venta"],
                    "monto_total": venta_row["monto_total"],
                    "observaciones": venta_row["observaciones"],
                    "objetos": [
                        {
                            "id_venta_objeto": row["id_venta_objeto"],
                            "id_inmueble": row["id_inmueble"],
                            "id_unidad_funcional": row["id_unidad_funcional"],
                            "precio_asignado": row["precio_asignado"],
                            "observaciones": row["observaciones"],
                        }
                        for row in objetos
                    ],
                    "created_at": venta_row["created_at"],
                    "updated_at": venta_row["updated_at"],
                    "deleted_at": venta_row["deleted_at"],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def create_instrumento_compraventa(
        self,
        payload: Any,
        objetos: list[Any],
    ) -> dict[str, Any]:
        values = self._values(payload)

        instrumento_statement = text(
            """
            INSERT INTO instrumento_compraventa (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_venta,
                tipo_instrumento,
                numero_instrumento,
                fecha_instrumento,
                estado_instrumento,
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
                :id_venta,
                :tipo_instrumento,
                :numero_instrumento,
                :fecha_instrumento,
                :estado_instrumento,
                :observaciones
            )
            RETURNING
                id_instrumento_compraventa,
                uid_global,
                version_registro,
                id_venta,
                tipo_instrumento,
                numero_instrumento,
                fecha_instrumento,
                estado_instrumento,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            """
        )

        objeto_statement = text(
            """
            INSERT INTO instrumento_objeto_inmobiliario (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_instrumento_compraventa,
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
                :id_instrumento_compraventa,
                :id_inmueble,
                :id_unidad_funcional,
                :observaciones
            )
            RETURNING
                id_instrumento_objeto,
                id_inmueble,
                id_unidad_funcional,
                observaciones
            """
        )

        try:
            instrumento_row = self.db.execute(instrumento_statement, values).mappings().one()
            id_instrumento = instrumento_row["id_instrumento_compraventa"]
            created_objetos: list[dict[str, Any]] = []

            for objeto in objetos:
                objeto_values = self._values(objeto)
                objeto_row = self.db.execute(
                    objeto_statement,
                    {
                        "uid_global": objeto_values["uid_global"],
                        "version_registro": objeto_values["version_registro"],
                        "created_at": objeto_values["created_at"],
                        "updated_at": objeto_values["updated_at"],
                        "id_instalacion_origen": objeto_values["id_instalacion_origen"],
                        "id_instalacion_ultima_modificacion": objeto_values[
                            "id_instalacion_ultima_modificacion"
                        ],
                        "op_id_alta": objeto_values["op_id_alta"],
                        "op_id_ultima_modificacion": objeto_values[
                            "op_id_ultima_modificacion"
                        ],
                        "id_instrumento_compraventa": id_instrumento,
                        "id_inmueble": objeto_values["id_inmueble"],
                        "id_unidad_funcional": objeto_values["id_unidad_funcional"],
                        "observaciones": objeto_values["observaciones"],
                    },
                ).mappings().one()
                created_objetos.append(
                    {
                        "id_instrumento_objeto": objeto_row["id_instrumento_objeto"],
                        "id_inmueble": objeto_row["id_inmueble"],
                        "id_unidad_funcional": objeto_row["id_unidad_funcional"],
                        "observaciones": objeto_row["observaciones"],
                    }
                )

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_instrumento_compraventa": instrumento_row[
                        "id_instrumento_compraventa"
                    ],
                    "uid_global": str(instrumento_row["uid_global"]),
                    "version_registro": instrumento_row["version_registro"],
                    "id_venta": instrumento_row["id_venta"],
                    "tipo_instrumento": instrumento_row["tipo_instrumento"],
                    "numero_instrumento": instrumento_row["numero_instrumento"],
                    "fecha_instrumento": instrumento_row["fecha_instrumento"],
                    "estado_instrumento": instrumento_row["estado_instrumento"],
                    "observaciones": instrumento_row["observaciones"],
                    "objetos": created_objetos,
                    "created_at": instrumento_row["created_at"],
                    "updated_at": instrumento_row["updated_at"],
                    "deleted_at": instrumento_row["deleted_at"],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def cesion_exists_for_venta(self, id_venta: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM cesion
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(statement, {"id_venta": id_venta}).scalar_one_or_none()
            is not None
        )

    def escrituracion_exists_for_venta(self, id_venta: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM escrituracion
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(statement, {"id_venta": id_venta}).scalar_one_or_none()
            is not None
        )

    def rescision_exists_for_venta(self, id_venta: int) -> bool:
        statement = text(
            """
            SELECT 1
            FROM rescision_venta
            WHERE id_venta = :id_venta
              AND deleted_at IS NULL
            """
        )
        return (
            self.db.execute(statement, {"id_venta": id_venta}).scalar_one_or_none()
            is not None
        )

    def create_cesion(self, payload: Any) -> dict[str, Any]:
        values = self._values(payload)
        statement = text(
            """
            INSERT INTO cesion (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_venta,
                fecha_cesion,
                tipo_cesion,
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
                :id_venta,
                :fecha_cesion,
                :tipo_cesion,
                :observaciones
            )
            RETURNING
                id_cesion,
                uid_global,
                version_registro,
                id_venta,
                fecha_cesion,
                tipo_cesion,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            """
        )

        try:
            cesion_row = self.db.execute(statement, values).mappings().one()
            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_cesion": cesion_row["id_cesion"],
                    "uid_global": str(cesion_row["uid_global"]),
                    "version_registro": cesion_row["version_registro"],
                    "id_venta": cesion_row["id_venta"],
                    "fecha_cesion": cesion_row["fecha_cesion"],
                    "tipo_cesion": cesion_row["tipo_cesion"],
                    "observaciones": cesion_row["observaciones"],
                    "created_at": cesion_row["created_at"],
                    "updated_at": cesion_row["updated_at"],
                    "deleted_at": cesion_row["deleted_at"],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def create_escrituracion(
        self,
        payload: Any,
        *,
        outbox_event: Any | None = None,
    ) -> dict[str, Any]:
        values = self._values(payload)
        outbox_repository = OutboxRepository(self.db)
        statement = text(
            """
            INSERT INTO escrituracion (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_venta,
                fecha_escrituracion,
                numero_escritura,
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
                :id_venta,
                :fecha_escrituracion,
                :numero_escritura,
                :observaciones
            )
            RETURNING
                id_escrituracion,
                uid_global,
                version_registro,
                id_venta,
                fecha_escrituracion,
                numero_escritura,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            """
        )

        try:
            escrituracion_row = self.db.execute(statement, values).mappings().one()

            if outbox_event is not None:
                outbox_values = self._values(outbox_event)
                payload_data = dict(outbox_values["payload"])
                payload_data["id_escrituracion"] = escrituracion_row["id_escrituracion"]
                outbox_repository.add_event(
                    event_type=outbox_values["event_type"],
                    aggregate_type=outbox_values["aggregate_type"],
                    aggregate_id=outbox_values["aggregate_id"],
                    payload=payload_data,
                    occurred_at=outbox_values["occurred_at"],
                    published_at=outbox_values.get("published_at"),
                    status=outbox_values["status"],
                )

            self.db.commit()
            return {
                "status": "OK",
                "data": {
                    "id_escrituracion": escrituracion_row["id_escrituracion"],
                    "uid_global": str(escrituracion_row["uid_global"]),
                    "version_registro": escrituracion_row["version_registro"],
                    "id_venta": escrituracion_row["id_venta"],
                    "fecha_escrituracion": escrituracion_row["fecha_escrituracion"],
                    "numero_escritura": escrituracion_row["numero_escritura"],
                    "observaciones": escrituracion_row["observaciones"],
                    "created_at": escrituracion_row["created_at"],
                    "updated_at": escrituracion_row["updated_at"],
                    "deleted_at": escrituracion_row["deleted_at"],
                },
            }
        except Exception:
            self.db.rollback()
            raise

    def _values(self, payload: Any) -> dict[str, Any]:
        if isinstance(payload, dict):
            return payload
        if is_dataclass(payload):
            return asdict(payload)
        return vars(payload)

    def _get_reserva_venta_origin(self, id_reserva_venta: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_reserva_venta,
                estado_reserva
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_reserva_venta": id_reserva_venta}
        ).mappings().one_or_none()
        if row is None:
            return None
        return {
            "id_reserva_venta": row["id_reserva_venta"],
            "estado_reserva_venta": row["estado_reserva"],
        }

    def _get_current_disponibilidad_state(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> str | None:
        filters = self._object_filters(
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
        )
        statement = text(
            f"""
            SELECT
                estado_disponibilidad
            FROM disponibilidad
            WHERE deleted_at IS NULL
              AND {filters}
              AND fecha_desde <= :at_datetime
              AND (fecha_hasta IS NULL OR fecha_hasta >= :at_datetime)
            ORDER BY id_disponibilidad
            """
        )
        rows = self.db.execute(
            statement,
            self._object_params(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                at_datetime=at_datetime,
            ),
        ).mappings().all()
        if len(rows) != 1:
            return None
        return rows[0]["estado_disponibilidad"]

    def _get_current_ocupacion_type(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> str | None:
        filters = self._object_filters(
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
        )
        statement = text(
            f"""
            SELECT
                tipo_ocupacion
            FROM ocupacion
            WHERE deleted_at IS NULL
              AND {filters}
              AND fecha_desde <= :at_datetime
              AND (fecha_hasta IS NULL OR fecha_hasta >= :at_datetime)
            ORDER BY id_ocupacion
            """
        )
        rows = self.db.execute(
            statement,
            self._object_params(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                at_datetime=at_datetime,
            ),
        ).mappings().all()
        if len(rows) != 1:
            return None
        return rows[0]["tipo_ocupacion"]

    def _get_instrumentos_compraventa_for_venta(
        self,
        id_venta: int,
        *,
        tipo_instrumento: str | None = None,
        estado_instrumento: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict[str, Any]]:
        filters = [
            "id_venta = :id_venta",
            "deleted_at IS NULL",
        ]
        params: dict[str, Any] = {"id_venta": id_venta}

        if tipo_instrumento is not None:
            filters.append("LOWER(tipo_instrumento) = :tipo_instrumento")
            params["tipo_instrumento"] = tipo_instrumento.strip().lower()

        if estado_instrumento is not None:
            filters.append("LOWER(estado_instrumento) = :estado_instrumento")
            params["estado_instrumento"] = estado_instrumento.strip().lower()

        if fecha_desde is not None:
            filters.append("fecha_instrumento >= :fecha_desde")
            params["fecha_desde"] = fecha_desde

        if fecha_hasta is not None:
            filters.append("fecha_instrumento <= :fecha_hasta")
            params["fecha_hasta"] = fecha_hasta

        where_clause = " AND ".join(filters)
        statement = text(
            f"""
            SELECT
                id_instrumento_compraventa,
                uid_global,
                version_registro,
                id_venta,
                tipo_instrumento,
                numero_instrumento,
                fecha_instrumento,
                estado_instrumento,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            FROM instrumento_compraventa
            WHERE {where_clause}
            ORDER BY id_instrumento_compraventa
            """
        )
        rows = self.db.execute(statement, params).mappings().all()
        instrumentos: list[dict[str, Any]] = []
        for row in rows:
            instrumentos.append(
                {
                    "id_instrumento_compraventa": row["id_instrumento_compraventa"],
                    "uid_global": str(row["uid_global"]),
                    "version_registro": row["version_registro"],
                    "id_venta": row["id_venta"],
                    "tipo_instrumento": row["tipo_instrumento"],
                    "numero_instrumento": row["numero_instrumento"],
                    "fecha_instrumento": row["fecha_instrumento"],
                    "estado_instrumento": row["estado_instrumento"],
                    "observaciones": row["observaciones"],
                    "objetos": self._get_instrumento_objetos(
                        row["id_instrumento_compraventa"]
                    ),
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "deleted_at": row["deleted_at"],
                }
            )
        return instrumentos

    def _get_instrumento_objetos(
        self, id_instrumento_compraventa: int
    ) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_instrumento_objeto,
                id_inmueble,
                id_unidad_funcional,
                observaciones
            FROM instrumento_objeto_inmobiliario
            WHERE id_instrumento_compraventa = :id_instrumento_compraventa
              AND deleted_at IS NULL
            ORDER BY id_instrumento_objeto
            """
        )
        rows = self.db.execute(
            statement,
            {"id_instrumento_compraventa": id_instrumento_compraventa},
        ).mappings().all()
        return [
            {
                "id_instrumento_objeto": row["id_instrumento_objeto"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def _get_cesiones_for_venta(
        self,
        id_venta: int,
        *,
        tipo_cesion: str | None = None,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
    ) -> list[dict[str, Any]]:
        filters = [
            "id_venta = :id_venta",
            "deleted_at IS NULL",
        ]
        params: dict[str, Any] = {"id_venta": id_venta}

        if tipo_cesion is not None:
            filters.append("LOWER(tipo_cesion) = :tipo_cesion")
            params["tipo_cesion"] = tipo_cesion.strip().lower()

        if fecha_desde is not None:
            filters.append("fecha_cesion >= :fecha_desde")
            params["fecha_desde"] = fecha_desde

        if fecha_hasta is not None:
            filters.append("fecha_cesion <= :fecha_hasta")
            params["fecha_hasta"] = fecha_hasta

        where_clause = " AND ".join(filters)
        statement = text(
            f"""
            SELECT
                id_cesion,
                uid_global,
                version_registro,
                id_venta,
                fecha_cesion,
                tipo_cesion,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            FROM cesion
            WHERE {where_clause}
            ORDER BY id_cesion
            """
        )
        rows = self.db.execute(statement, params).mappings().all()
        return [
            {
                "id_cesion": row["id_cesion"],
                "uid_global": str(row["uid_global"]),
                "version_registro": row["version_registro"],
                "id_venta": row["id_venta"],
                "fecha_cesion": row["fecha_cesion"],
                "tipo_cesion": row["tipo_cesion"],
                "observaciones": row["observaciones"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "deleted_at": row["deleted_at"],
            }
            for row in rows
        ]

    def _get_escrituraciones_for_venta(
        self,
        id_venta: int,
        *,
        fecha_desde: datetime | None = None,
        fecha_hasta: datetime | None = None,
        numero_escritura: str | None = None,
    ) -> list[dict[str, Any]]:
        filters = [
            "id_venta = :id_venta",
            "deleted_at IS NULL",
        ]
        params: dict[str, Any] = {"id_venta": id_venta}

        if fecha_desde is not None:
            filters.append("fecha_escrituracion >= :fecha_desde")
            params["fecha_desde"] = fecha_desde

        if fecha_hasta is not None:
            filters.append("fecha_escrituracion <= :fecha_hasta")
            params["fecha_hasta"] = fecha_hasta

        if numero_escritura is not None:
            filters.append("LOWER(numero_escritura) = :numero_escritura")
            params["numero_escritura"] = numero_escritura.strip().lower()

        where_clause = " AND ".join(filters)
        statement = text(
            f"""
            SELECT
                id_escrituracion,
                uid_global,
                version_registro,
                id_venta,
                fecha_escrituracion,
                numero_escritura,
                observaciones,
                created_at,
                updated_at,
                deleted_at
            FROM escrituracion
            WHERE {where_clause}
            ORDER BY id_escrituracion
            """
        )
        rows = self.db.execute(statement, params).mappings().all()
        return [
            {
                "id_escrituracion": row["id_escrituracion"],
                "uid_global": str(row["uid_global"]),
                "version_registro": row["version_registro"],
                "id_venta": row["id_venta"],
                "fecha_escrituracion": row["fecha_escrituracion"],
                "numero_escritura": row["numero_escritura"],
                "observaciones": row["observaciones"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "deleted_at": row["deleted_at"],
            }
            for row in rows
        ]

    def _replace_disponibilidad_vigente_in_transaction(
        self, payload: Any, *, expected_current_state: str = "DISPONIBLE"
    ) -> dict[str, Any]:
        values = self._values(payload)

        if values["id_inmueble"] is not None:
            parent_values = {"id_inmueble": values["id_inmueble"]}
            select_statement = text(
                """
                SELECT
                    id_disponibilidad,
                    estado_disponibilidad,
                    fecha_desde,
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
                    estado_disponibilidad,
                    fecha_desde,
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

        open_rows = self.db.execute(
            select_statement, parent_values
        ).mappings().all()
        if len(open_rows) == 0:
            return {"status": "NO_OPEN_DISPONIBILIDAD"}
        if len(open_rows) > 1:
            return {"status": "MULTIPLE_OPEN_DISPONIBILIDAD"}

        current = open_rows[0]
        if (current["estado_disponibilidad"] or "").strip().upper() != expected_current_state:
            if expected_current_state == "DISPONIBLE":
                return {"status": "CURRENT_NOT_DISPONIBLE"}
            return {"status": "CURRENT_NOT_EXPECTED_STATE"}

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
            RETURNING id_disponibilidad
            """
        )
        updated = self.db.execute(
            update_statement,
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

    def _object_filters(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
    ) -> str:
        if id_inmueble is not None:
            return "id_inmueble = :id_inmueble AND id_unidad_funcional IS NULL"
        return "id_unidad_funcional = :id_unidad_funcional AND id_inmueble IS NULL"

    def _object_params(
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
