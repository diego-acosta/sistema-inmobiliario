from typing import Any

from sqlalchemy import text

from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.base_repository import BaseRepository


class UsuarioRolSeguridadIdempotencyConflictError(ValueError):
    pass


class UsuarioRolSeguridadConcurrencyError(ValueError):
    pass


_COLUMNS = """
    urs.id_usuario_rol_seguridad,
    urs.id_usuario,
    urs.id_rol_seguridad,
    urs.fecha_desde,
    urs.fecha_hasta,
    urs.version_registro,
    urs.updated_at,
    urs.deleted_at,
    urs.id_instalacion_origen,
    urs.id_instalacion_ultima_modificacion,
    urs.op_id_alta,
    urs.op_id_ultima_modificacion,
    r.codigo_rol,
    r.nombre_rol,
    r.descripcion,
    r.estado_rol
"""

_PAYLOAD_FIELDS = ("id_usuario", "id_rol_seguridad")


class UsuarioRolSeguridadRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    @staticmethod
    def _map(row: Any) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _payload_matches(row: dict[str, Any], payload: dict[str, Any]) -> bool:
        return all(row.get(field) == payload.get(field) for field in _PAYLOAD_FIELDS)

    def exists_usuario(self, id_usuario: int) -> bool:
        return bool(
            self.db.execute(
                text("SELECT 1 FROM usuario WHERE id_usuario = :id_usuario"),
                {"id_usuario": id_usuario},
            ).scalar()
        )

    def exists_rol_seguridad(self, id_rol_seguridad: int) -> bool:
        return bool(
            self.db.execute(
                text("SELECT 1 FROM rol_seguridad WHERE id_rol_seguridad = :id"),
                {"id": id_rol_seguridad},
            ).scalar()
        )

    def get(self, id_asignacion: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                f"""
                SELECT {_COLUMNS}
                FROM usuario_rol_seguridad urs
                JOIN rol_seguridad r ON r.id_rol_seguridad = urs.id_rol_seguridad
                WHERE urs.id_usuario_rol_seguridad = :id_asignacion
                """
            ),
            {"id_asignacion": id_asignacion},
        ).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                f"""
                SELECT {_COLUMNS}
                FROM usuario_rol_seguridad urs
                JOIN rol_seguridad r ON r.id_rol_seguridad = urs.id_rol_seguridad
                WHERE urs.op_id_alta = :op_id
                """
            ),
            {"op_id": op_id},
        ).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def list_by_usuario(
        self, id_usuario: int, *, incluir_bajas: bool = False
    ) -> list[dict[str, Any]] | None:
        if not self.exists_usuario(id_usuario):
            return None
        baja_filter = "" if incluir_bajas else "AND urs.deleted_at IS NULL AND urs.fecha_hasta IS NULL"
        rows = self.db.execute(
            text(
                f"""
                SELECT {_COLUMNS}
                FROM usuario_rol_seguridad urs
                JOIN rol_seguridad r ON r.id_rol_seguridad = urs.id_rol_seguridad
                WHERE urs.id_usuario = :id_usuario
                {baja_filter}
                ORDER BY urs.id_usuario_rol_seguridad
                """
            ),
            {"id_usuario": id_usuario},
        ).mappings().all()
        return [self._map(row) for row in rows]

    def list_by_rol_seguridad(
        self, id_rol_seguridad: int, *, incluir_bajas: bool = False
    ) -> list[dict[str, Any]] | None:
        if not self.exists_rol_seguridad(id_rol_seguridad):
            return None
        baja_filter = "" if incluir_bajas else "AND urs.deleted_at IS NULL AND urs.fecha_hasta IS NULL"
        rows = self.db.execute(
            text(
                f"""
                SELECT {_COLUMNS}
                FROM usuario_rol_seguridad urs
                JOIN rol_seguridad r ON r.id_rol_seguridad = urs.id_rol_seguridad
                WHERE urs.id_rol_seguridad = :id_rol_seguridad
                {baja_filter}
                ORDER BY urs.id_usuario_rol_seguridad
                """
            ),
            {"id_rol_seguridad": id_rol_seguridad},
        ).mappings().all()
        return [self._map(row) for row in rows]

    def create(
        self, id_usuario: int, payload: dict[str, Any], core: CoreEFHeaders
    ) -> dict[str, Any] | None:
        full_payload = {"id_usuario": id_usuario, **payload}
        op_id = str(core.x_op_id)
        existing = self.get_by_op_id_alta(op_id)
        if existing is not None:
            if not self._payload_matches(existing, full_payload):
                raise UsuarioRolSeguridadIdempotencyConflictError(
                    "El X-Op-Id ya fue usado con un payload incompatible."
                )
            return existing

        if not self.exists_usuario(id_usuario):
            return None
        if not self.exists_rol_seguridad(payload["id_rol_seguridad"]):
            return None

        try:
            row = self.db.execute(
                text(
                    f"""
                    INSERT INTO usuario_rol_seguridad (
                        id_usuario,
                        id_rol_seguridad,
                        fecha_desde,
                        version_registro,
                        updated_at,
                        id_instalacion_origen,
                        id_instalacion_ultima_modificacion,
                        op_id_alta,
                        op_id_ultima_modificacion
                    ) VALUES (
                        :id_usuario,
                        :id_rol_seguridad,
                        CURRENT_TIMESTAMP,
                        1,
                        CURRENT_TIMESTAMP,
                        :id_instalacion,
                        :id_instalacion,
                        :op_id,
                        :op_id
                    )
                    RETURNING id_usuario_rol_seguridad
                    """
                ),
                {
                    "id_usuario": id_usuario,
                    "id_rol_seguridad": payload["id_rol_seguridad"],
                    "id_instalacion": core.x_instalacion_id,
                    "op_id": op_id,
                },
            ).mappings().one()
            self.db.commit()
            return self.get(row["id_usuario_rol_seguridad"])
        except Exception:
            self.db.rollback()
            raise

    def baja_logica(
        self,
        id_usuario: int,
        id_asignacion: int,
        *,
        core: CoreEFHeaders,
        if_match_version: int,
    ) -> dict[str, Any] | None:
        actual = self.get(id_asignacion)
        if actual is None or actual["id_usuario"] != id_usuario:
            return None
        op_id = str(core.x_op_id)
        if str(actual.get("op_id_ultima_modificacion")) == op_id and actual.get("deleted_at") is not None:
            return actual
        if actual["version_registro"] != if_match_version:
            raise UsuarioRolSeguridadConcurrencyError("La versión de la asignación no coincide.")

        try:
            row = self.db.execute(
                text(
                    """
                    UPDATE usuario_rol_seguridad
                    SET fecha_hasta = COALESCE(fecha_hasta, CURRENT_TIMESTAMP),
                        deleted_at = COALESCE(deleted_at, CURRENT_TIMESTAMP),
                        updated_at = CURRENT_TIMESTAMP,
                        id_instalacion_ultima_modificacion = :id_instalacion,
                        op_id_ultima_modificacion = :op_id,
                        version_registro = version_registro + 1
                    WHERE id_usuario_rol_seguridad = :id_asignacion
                      AND id_usuario = :id_usuario
                      AND version_registro = :if_match_version
                    RETURNING id_usuario_rol_seguridad
                    """
                ),
                {
                    "id_asignacion": id_asignacion,
                    "id_usuario": id_usuario,
                    "if_match_version": if_match_version,
                    "id_instalacion": core.x_instalacion_id,
                    "op_id": op_id,
                },
            ).mappings().one_or_none()
            if row is None:
                self.db.rollback()
                raise UsuarioRolSeguridadConcurrencyError("La versión de la asignación no coincide.")
            self.db.commit()
            return self.get(row["id_usuario_rol_seguridad"])
        except Exception:
            self.db.rollback()
            raise
