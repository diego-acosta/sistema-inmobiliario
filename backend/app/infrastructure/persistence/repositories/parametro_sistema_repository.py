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

    def get_definicion_con_valor_global_marcado_vigente(
        self, codigo_parametro: str
    ) -> list[dict[str, Any]]:
        statement = text("""
            SELECT
                parametro.id_parametro_sistema,
                parametro.codigo_parametro,
                parametro.nombre_parametro,
                parametro.descripcion,
                parametro.exponible_api_administrativa,
                parametro.es_sensible,
                tipo.id_tipo_dato_parametro,
                tipo.codigo_tipo_dato,
                tipo.nombre_tipo_dato,
                tipo.descripcion_tipo_dato,
                alcance.id_alcance_parametro,
                alcance.codigo_alcance,
                alcance.nombre_alcance,
                alcance.descripcion_alcance,
                valor.id_valor_parametro,
                valor.uid_global,
                valor.valor_parametro AS valor_raw,
                valor.version_registro,
                valor.es_valor_vigente,
                valor.fecha_desde,
                valor.fecha_hasta,
                valor.created_at AS valor_created_at,
                valor.updated_at AS valor_updated_at
            FROM parametro_sistema AS parametro
            JOIN tipo_dato_parametro AS tipo
              ON tipo.id_tipo_dato_parametro = parametro.id_tipo_dato_parametro
            JOIN alcance_parametro AS alcance
              ON alcance.id_alcance_parametro = parametro.id_alcance_parametro
            LEFT JOIN valor_parametro AS valor
              ON valor.id_parametro_sistema = parametro.id_parametro_sistema
             AND valor.es_valor_vigente = true
             AND valor.deleted_at IS NULL
             AND valor.id_sucursal IS NULL
             AND valor.id_instalacion IS NULL
            WHERE parametro.codigo_parametro = :codigo_parametro
        """)
        return [
            dict(row)
            for row in self.db.execute(
                statement, {"codigo_parametro": codigo_parametro}
            ).mappings().all()
        ]
