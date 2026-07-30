from typing import Any

from app.infrastructure.persistence.base_repository import BaseRepository
from sqlalchemy import text


class ParametroSistemaRepository(BaseRepository[Any]):
    """Inventario read-only de definiciones de parámetros administrativos."""

    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    def list_definiciones(self) -> list[dict[str, Any]]:
        statement = text("""
            SELECT
                parametro.id_parametro_sistema,
                parametro.codigo_parametro,
                parametro.nombre_parametro,
                parametro.descripcion,
                tipo.id_tipo_dato_parametro,
                tipo.codigo_tipo_dato,
                tipo.nombre_tipo_dato,
                alcance.id_alcance_parametro,
                alcance.codigo_alcance,
                alcance.nombre_alcance
            FROM parametro_sistema AS parametro
            JOIN tipo_dato_parametro AS tipo
              ON tipo.id_tipo_dato_parametro = parametro.id_tipo_dato_parametro
            JOIN alcance_parametro AS alcance
              ON alcance.id_alcance_parametro = parametro.id_alcance_parametro
            ORDER BY parametro.codigo_parametro, parametro.id_parametro_sistema
        """)
        return [dict(row) for row in self.db.execute(statement).mappings().all()]
