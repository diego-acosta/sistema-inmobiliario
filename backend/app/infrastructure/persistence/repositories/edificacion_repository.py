from dataclasses import asdict, is_dataclass
from typing import Any

from sqlalchemy import text

from app.infrastructure.persistence.base_repository import BaseRepository


class EdificacionRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    def get_edificaciones(self) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_edificacion,
                id_inmueble,
                id_unidad_funcional,
                descripcion,
                tipo_edificacion,
                superficie,
                observaciones
            FROM edificacion
            WHERE deleted_at IS NULL
            ORDER BY id_edificacion
            """
        )
        result = self.db.execute(statement)
        rows = result.mappings().all()
        return [
            {
                "id_edificacion": row["id_edificacion"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "descripcion": row["descripcion"],
                "tipo_edificacion": row["tipo_edificacion"],
                "superficie": row["superficie"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_edificaciones_by_inmueble(self, id_inmueble: int) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_edificacion,
                id_inmueble,
                id_unidad_funcional,
                descripcion,
                tipo_edificacion,
                superficie,
                observaciones
            FROM edificacion
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_edificacion
            """
        )
        result = self.db.execute(statement, {"id_inmueble": id_inmueble})
        rows = result.mappings().all()
        return [
            {
                "id_edificacion": row["id_edificacion"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "descripcion": row["descripcion"],
                "tipo_edificacion": row["tipo_edificacion"],
                "superficie": row["superficie"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_edificaciones_by_unidad_funcional(
        self, id_unidad_funcional: int
    ) -> list[dict[str, Any]]:
        statement = text(
            """
            SELECT
                id_edificacion,
                id_inmueble,
                id_unidad_funcional,
                descripcion,
                tipo_edificacion,
                superficie,
                observaciones
            FROM edificacion
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND deleted_at IS NULL
            ORDER BY id_edificacion
            """
        )
        result = self.db.execute(
            statement, {"id_unidad_funcional": id_unidad_funcional}
        )
        rows = result.mappings().all()
        return [
            {
                "id_edificacion": row["id_edificacion"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "descripcion": row["descripcion"],
                "tipo_edificacion": row["tipo_edificacion"],
                "superficie": row["superficie"],
                "observaciones": row["observaciones"],
            }
            for row in rows
        ]

    def get_edificacion(self, id_edificacion: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_edificacion,
                id_inmueble,
                id_unidad_funcional,
                descripcion,
                tipo_edificacion,
                superficie,
                observaciones
            FROM edificacion
            WHERE id_edificacion = :id_edificacion
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_edificacion": id_edificacion}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_edificacion": row["id_edificacion"],
            "id_inmueble": row["id_inmueble"],
            "id_unidad_funcional": row["id_unidad_funcional"],
            "descripcion": row["descripcion"],
            "tipo_edificacion": row["tipo_edificacion"],
            "superficie": row["superficie"],
            "observaciones": row["observaciones"],
        }

    def get_edificacion_for_update(self, id_edificacion: int) -> dict[str, Any] | None:
        statement = text(
            """
            SELECT
                id_edificacion,
                id_inmueble,
                id_unidad_funcional,
                descripcion,
                tipo_edificacion,
                superficie,
                observaciones,
                version_registro
            FROM edificacion
            WHERE id_edificacion = :id_edificacion
              AND deleted_at IS NULL
            """
        )
        row = self.db.execute(
            statement, {"id_edificacion": id_edificacion}
        ).mappings().one_or_none()
        if row is None:
            return None

        return {
            "id_edificacion": row["id_edificacion"],
            "id_inmueble": row["id_inmueble"],
            "id_unidad_funcional": row["id_unidad_funcional"],
            "descripcion": row["descripcion"],
            "tipo_edificacion": row["tipo_edificacion"],
            "superficie": row["superficie"],
            "observaciones": row["observaciones"],
            "version_registro": row["version_registro"],
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

    def create_edificacion(self, payload: Any) -> dict[str, Any]:
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
            "descripcion": values["descripcion"],
            "tipo_edificacion": values["tipo_edificacion"],
            "superficie": values["superficie"],
            "fecha_alta": values["created_at"],
            "observaciones": values["observaciones"],
        }

        statement = text(
            """
            INSERT INTO edificacion (
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
                descripcion,
                tipo_edificacion,
                superficie,
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
                :id_inmueble,
                :id_unidad_funcional,
                :descripcion,
                :tipo_edificacion,
                :superficie,
                :fecha_alta,
                :observaciones
            )
            RETURNING
                id_edificacion,
                uid_global,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                tipo_edificacion
            """
        )

        try:
            result = self.db.execute(statement, db_values)
            row = result.mappings().one()
            self.db.commit()
            return {
                "id_edificacion": row["id_edificacion"],
                "uid_global": row["uid_global"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "tipo_edificacion": row["tipo_edificacion"],
            }
        except Exception:
            self.db.rollback()
            raise

    def update_edificacion(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_edificacion": values["id_edificacion"],
            "descripcion": values["descripcion"],
            "tipo_edificacion": values["tipo_edificacion"],
            "superficie": values["superficie"],
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
            UPDATE edificacion
            SET
                descripcion = :descripcion,
                tipo_edificacion = :tipo_edificacion,
                superficie = :superficie,
                observaciones = :observaciones,
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_edificacion = :id_edificacion
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_edificacion,
                version_registro,
                id_inmueble,
                id_unidad_funcional,
                descripcion,
                tipo_edificacion,
                superficie,
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
                "id_edificacion": row["id_edificacion"],
                "version_registro": row["version_registro"],
                "id_inmueble": row["id_inmueble"],
                "id_unidad_funcional": row["id_unidad_funcional"],
                "descripcion": row["descripcion"],
                "tipo_edificacion": row["tipo_edificacion"],
                "superficie": row["superficie"],
                "observaciones": row["observaciones"],
            }
        except Exception:
            self.db.rollback()
            raise

    def delete_edificacion(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            values = payload
        elif is_dataclass(payload):
            values = asdict(payload)
        else:
            values = vars(payload)

        db_values = {
            "id_edificacion": values["id_edificacion"],
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
            UPDATE edificacion
            SET
                version_registro = :version_registro_nueva,
                updated_at = :updated_at,
                deleted_at = :deleted_at,
                id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion = :op_id_ultima_modificacion
            WHERE id_edificacion = :id_edificacion
              AND version_registro = :version_registro_actual
              AND deleted_at IS NULL
            RETURNING
                id_edificacion,
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
                "id_edificacion": row["id_edificacion"],
                "version_registro": row["version_registro"],
            }
        except Exception:
            self.db.rollback()
            raise
