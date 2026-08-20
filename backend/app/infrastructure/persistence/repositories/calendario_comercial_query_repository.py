from __future__ import annotations

from typing import Any

from app.infrastructure.persistence.base_repository import BaseRepository
from sqlalchemy import text


class CalendarioComercialQueryRepository(BaseRepository[Any]):
    """Snapshot read-only de la configuración administrativa de calendario."""

    def obtener_snapshot_fisico(self) -> list[dict[str, Any]]:
        # Una sola sentencia garantiza que definiciones, valores y raíz se lean
        # desde el mismo snapshot de PostgreSQL, sin locks ni efectos persistentes.
        statement = text("""
            WITH definiciones AS (
                SELECT p.id_parametro_sistema, p.codigo_parametro,
                       p.nombre_parametro, p.descripcion,
                       p.exponible_api_administrativa, p.es_sensible,
                       p.editable_administrativamente,
                       t.codigo_tipo_dato, a.codigo_alcance
                  FROM parametro_sistema p
                  LEFT JOIN tipo_dato_parametro t
                    ON t.id_tipo_dato_parametro = p.id_tipo_dato_parametro
                  LEFT JOIN alcance_parametro a
                    ON a.id_alcance_parametro = p.id_alcance_parametro
                 WHERE p.codigo_parametro IN (
                    'DIA_CIERRE_COMERCIAL',
                    'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS'
                 )
            ), filas AS (
                SELECT 'DEFINICION'::text AS clase,
                       d.codigo_parametro, d.id_parametro_sistema,
                       d.nombre_parametro, d.descripcion,
                       d.exponible_api_administrativa, d.es_sensible,
                       d.editable_administrativamente,
                       d.codigo_tipo_dato, d.codigo_alcance,
                       NULL::bigint AS id_valor_parametro,
                       NULL::text AS valor_parametro,
                       NULL::timestamp AS fecha_desde,
                       NULL::timestamp AS fecha_hasta,
                       NULL::bigint AS id_raiz,
                       NULL::bigint AS version_agregada,
                       NULL::timestamp AS deleted_at
                  FROM definiciones d
                UNION ALL
                SELECT 'VALOR', d.codigo_parametro, d.id_parametro_sistema,
                       NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                       v.id_valor_parametro, v.valor_parametro,
                       v.fecha_desde, v.fecha_hasta,
                       NULL, NULL, v.deleted_at
                  FROM definiciones d
                  JOIN valor_parametro v
                    ON v.id_parametro_sistema = d.id_parametro_sistema
                 WHERE v.id_sucursal IS NULL AND v.id_instalacion IS NULL
                UNION ALL
                SELECT 'RAIZ', NULL, NULL, NULL, NULL, NULL, NULL, NULL,
                       NULL, NULL, NULL, NULL, NULL, NULL,
                       c.id_configuracion_calendario_comercial,
                       c.version_registro, c.deleted_at
                  FROM configuracion_calendario_comercial c
            )
            SELECT * FROM filas
             ORDER BY clase, codigo_parametro NULLS LAST,
                      fecha_desde NULLS FIRST, id_valor_parametro NULLS FIRST,
                      id_raiz NULLS FIRST
        """)
        return [dict(row) for row in self.session.execute(statement).mappings().all()]
