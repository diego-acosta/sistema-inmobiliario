from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


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

    def create_contrato_alquiler(
        self,
        payload: Any,
        objetos: list[Any],
        participaciones: list[Any],
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
                :id_reserva_locativa,
                :id_cartera_locativa,
                :id_contrato_anterior,
                :codigo_contrato,
                :fecha_inicio,
                :fecha_fin,
                :estado_contrato,
                :observaciones
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
                        "tipo_relacion": values.get("tipo_relacion", "CONTRATO_ALQUILER"),
                        "id_relacion": id_contrato_alquiler,
                        "fecha_desde": values["fecha_desde"],
                        "fecha_hasta": values["fecha_hasta"],
                        "observaciones": values["observaciones"],
                    },
                )

            self.db.commit()
            return {
                "id_contrato_alquiler": id_contrato_alquiler,
                "objetos": created_objetos,
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
