from typing import Any

from dataclasses import asdict, is_dataclass

from sqlalchemy import text

from app.infrastructure.persistence.base_repository import BaseRepository


class DesarrolloRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    def get_desarrollos(self) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_desarrollo,
                codigo_desarrollo,
                nombre_desarrollo,
                descripcion,
                estado_desarrollo,
                observaciones
            FROM desarrollo
            WHERE deleted_at IS NULL
            ORDER BY id_desarrollo
            """
        )
        result = self.db.execute(statement)
        rows = result.mappings().all()
        return [
            {
                "id_desarrollo": row["id_desarrollo"],
                "codigo_desarrollo": row["codigo_desarrollo"],
                "nombre_desarrollo": row["nombre_desarrollo"],
                "descripcion": row["descripcion"],
                "estado_desarrollo": row["estado_desarrollo"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_desarrollo(self, id_desarrollo: int) -> dict[str, Any] | None:
        statement = text(
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
        )
        row = self.db.execute(
            statement, {"id_desarrollo": id_desarrollo}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_desarrollo": row["id_desarrollo"],
            "codigo_desarrollo": row["codigo_desarrollo"],
            "nombre_desarrollo": row["nombre_desarrollo"],
            "descripcion": row["descripcion"],
            "estado_desarrollo": row["estado_desarrollo"],
            "observaciones": row["observaciones"],
        }

    def get_desarrollo_for_update(self, id_desarrollo: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_desarrollo,
                codigo_desarrollo,
                nombre_desarrollo,
                descripcion,
                estado_desarrollo,
                observaciones,
                version_registro
            FROM desarrollo
            WHERE id_desarrollo = :id_desarrollo
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_desarrollo": id_desarrollo}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_desarrollo": row["id_desarrollo"],
            "codigo_desarrollo": row["codigo_desarrollo"],
            "nombre_desarrollo": row["nombre_desarrollo"],
            "descripcion": row["descripcion"],
            "estado_desarrollo": row["estado_desarrollo"],
            "observaciones": row["observaciones"],
            "version_registro": row["version_registro"],
        }

    def create_desarrollo(self, payload: Any) -> dict[str, Any]:
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
            "codigo_desarrollo": values["codigo_desarrollo"],
            "nombre_desarrollo": values["nombre_desarrollo"],
            "descripcion": values["descripcion"],
            "estado_desarrollo": values["estado_desarrollo"],
            "fecha_alta": values["created_at"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO desarrollo (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_desarrollo,
                nombre_desarrollo,
                descripcion,
                estado_desarrollo,
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
                :codigo_desarrollo,
                :nombre_desarrollo,
                :descripcion,
                :estado_desarrollo,
                :fecha_alta,
                :observaciones
            )
            RETURNING
                id_desarrollo,
                uid_global,
                version_registro,
                estado_desarrollo
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_desarrollo": row["id_desarrollo"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "estado_desarrollo": row["estado_desarrollo"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_desarrollo(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_desarrollo": values["id_desarrollo"],
            "codigo_desarrollo": values["codigo_desarrollo"],
            "nombre_desarrollo": values["nombre_desarrollo"],
            "descripcion": values["descripcion"],
            "estado_desarrollo": values["estado_desarrollo"],
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
            UPDATE desarrollo
            SET
                codigo_desarrollo = :codigo_desarrollo,
                nombre_desarrollo = :nombre_desarrollo,
                descripcion = :descripcion,
                estado_desarrollo = :estado_desarrollo,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_desarrollo = :id_desarrollo
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_desarrollo,
                version_registro,
                codigo_desarrollo,
                nombre_desarrollo,
                descripcion,
                estado_desarrollo,
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
                "id_desarrollo": row["id_desarrollo"],
                "version_registro": row["version_registro"],
                "codigo_desarrollo": row["codigo_desarrollo"],
                "nombre_desarrollo": row["nombre_desarrollo"],
                "descripcion": row["descripcion"],
                "estado_desarrollo": row["estado_desarrollo"],
                "observaciones": row["observaciones"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_desarrollo(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_desarrollo": values["id_desarrollo"],
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
            UPDATE desarrollo
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_desarrollo = :id_desarrollo
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
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
                "id_desarrollo": row["id_desarrollo"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise
