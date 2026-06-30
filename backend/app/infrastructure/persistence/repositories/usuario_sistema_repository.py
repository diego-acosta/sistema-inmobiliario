from typing import Any

from sqlalchemy import text

from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.base_repository import BaseRepository


class UsuarioIdempotencyConflictError(ValueError):
    pass


class UsuarioConcurrencyError(ValueError):
    pass


_USUARIO_COLUMNS = """
    id_usuario,
    codigo_usuario,
    login,
    email,
    estado_usuario,
    fecha_alta,
    fecha_baja,
    fecha_ultimo_acceso,
    usuario_sistema_interno,
    observaciones,
    version_registro,
    updated_at,
    deleted_at,
    id_instalacion_origen,
    id_instalacion_ultima_modificacion,
    op_id_alta,
    op_id_ultima_modificacion
"""

_PAYLOAD_FIELDS = (
    "codigo_usuario",
    "login",
    "email",
    "estado_usuario",
    "usuario_sistema_interno",
    "observaciones",
)


class UsuarioSistemaRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    @staticmethod
    def _map(row: Any) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _payload_matches(row: dict[str, Any], payload: dict[str, Any]) -> bool:
        for field in _PAYLOAD_FIELDS:
            if row.get(field) != payload.get(field):
                return False
        return True

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        statement = text(
            f"""
            SELECT {_USUARIO_COLUMNS}
            FROM usuario
            WHERE op_id_alta = :op_id
            """
        )
        row = self.db.execute(statement, {"op_id": op_id}).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def create(self, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any]:
        op_id = str(core.x_op_id)
        existing = self.get_by_op_id_alta(op_id)
        if existing is not None:
            if not self._payload_matches(existing, payload):
                raise UsuarioIdempotencyConflictError(
                    "El X-Op-Id ya fue usado con un payload incompatible."
                )
            return existing

        statement = text(
            f"""
            INSERT INTO usuario (
                codigo_usuario,
                login,
                email,
                estado_usuario,
                usuario_sistema_interno,
                observaciones,
                version_registro,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion
            )
            VALUES (
                :codigo_usuario,
                :login,
                :email,
                :estado_usuario,
                :usuario_sistema_interno,
                :observaciones,
                1,
                :id_instalacion,
                :id_instalacion,
                :op_id,
                :op_id
            )
            RETURNING {_USUARIO_COLUMNS}
            """
        )
        values = {
            **payload,
            "id_instalacion": core.x_instalacion_id,
            "op_id": op_id,
        }
        try:
            row = self.db.execute(statement, values).mappings().one()
            self.db.commit()
            return self._map(row)
        except Exception:
            self.db.rollback()
            raise

    def list(self, *, incluir_bajas: bool = False) -> list[dict[str, Any]]:
        baja_filter = "" if incluir_bajas else "WHERE deleted_at IS NULL"
        statement = text(
            f"""
            SELECT {_USUARIO_COLUMNS}
            FROM usuario
            {baja_filter}
            ORDER BY id_usuario
            """
        )
        return [self._map(row) for row in self.db.execute(statement).mappings().all()]

    def get(self, id_usuario: int) -> dict[str, Any] | None:
        statement = text(
            f"""
            SELECT {_USUARIO_COLUMNS}
            FROM usuario
            WHERE id_usuario = :id_usuario
            """
        )
        row = self.db.execute(statement, {"id_usuario": id_usuario}).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def baja_logica(
        self,
        id_usuario: int,
        *,
        core: CoreEFHeaders,
        if_match_version: int,
    ) -> dict[str, Any] | None:
        op_id = str(core.x_op_id)
        actual = self.get(id_usuario)
        if actual is None:
            return None

        if str(actual.get("op_id_ultima_modificacion")) == op_id and actual.get("deleted_at") is not None:
            return actual

        if actual["version_registro"] != if_match_version:
            raise UsuarioConcurrencyError("La versión del usuario no coincide.")

        statement = text(
            f"""
            UPDATE usuario
            SET estado_usuario = 'INACTIVO',
                fecha_baja = COALESCE(fecha_baja, CURRENT_TIMESTAMP),
                deleted_at = COALESCE(deleted_at, CURRENT_TIMESTAMP),
                updated_at = CURRENT_TIMESTAMP,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id,
                version_registro = version_registro + 1
            WHERE id_usuario = :id_usuario
              AND version_registro = :if_match_version
            RETURNING {_USUARIO_COLUMNS}
            """
        )
        try:
            row = self.db.execute(
                statement,
                {
                    "id_usuario": id_usuario,
                    "if_match_version": if_match_version,
                    "id_instalacion": core.x_instalacion_id,
                    "op_id": op_id,
                },
            ).mappings().one_or_none()
            if row is None:
                self.db.rollback()
                raise UsuarioConcurrencyError("La versión del usuario no coincide.")
            self.db.commit()
            return self._map(row)
        except Exception:
            self.db.rollback()
            raise
