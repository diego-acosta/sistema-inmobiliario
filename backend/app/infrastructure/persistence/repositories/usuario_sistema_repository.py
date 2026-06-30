from typing import Any

from sqlalchemy import text

from app.infrastructure.persistence.base_repository import BaseRepository


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
    observaciones
"""


class UsuarioSistemaRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    @staticmethod
    def _map(row: Any) -> dict[str, Any]:
        return dict(row)

    def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        statement = text(
            f"""
            INSERT INTO usuario (
                codigo_usuario,
                login,
                email,
                estado_usuario,
                usuario_sistema_interno,
                observaciones
            )
            VALUES (
                :codigo_usuario,
                :login,
                :email,
                :estado_usuario,
                :usuario_sistema_interno,
                :observaciones
            )
            RETURNING {_USUARIO_COLUMNS}
            """
        )
        try:
            row = self.db.execute(statement, payload).mappings().one()
            self.db.commit()
            return self._map(row)
        except Exception:
            self.db.rollback()
            raise

    def list(self, *, incluir_bajas: bool = False) -> list[dict[str, Any]]:
        baja_filter = "" if incluir_bajas else "WHERE fecha_baja IS NULL"
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

    def baja_logica(self, id_usuario: int) -> dict[str, Any] | None:
        statement = text(
            f"""
            UPDATE usuario
            SET estado_usuario = 'INACTIVO',
                fecha_baja = COALESCE(fecha_baja, CURRENT_TIMESTAMP)
            WHERE id_usuario = :id_usuario
            RETURNING {_USUARIO_COLUMNS}
            """
        )
        try:
            row = self.db.execute(statement, {"id_usuario": id_usuario}).mappings().one_or_none()
            self.db.commit()
            return self._map(row) if row is not None else None
        except Exception:
            self.db.rollback()
            raise
