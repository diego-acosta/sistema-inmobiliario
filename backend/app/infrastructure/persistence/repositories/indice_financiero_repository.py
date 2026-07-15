from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class IndiceFinancieroRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_valor_publicado_por_codigo_y_fecha(
        self,
        codigo_indice_financiero: str,
        fecha_objetivo: date,
    ) -> dict[str, Any] | None:
        codigo_normalizado = codigo_indice_financiero.strip().upper()
        if not codigo_normalizado:
            return None

        stmt = text(
            """
            SELECT
                i.id_indice_financiero,
                i.codigo_indice_financiero,
                i.nombre_indice_financiero,
                iv.id_indice_financiero_valor,
                iv.fecha_valor,
                iv.valor_indice,
                iv.fecha_publicacion,
                iv.fuente_valor
            FROM indice_financiero AS i
            JOIN indice_financiero_valor AS iv
                ON iv.id_indice_financiero = i.id_indice_financiero
            WHERE i.codigo_indice_financiero = :codigo_indice_financiero
              AND i.estado_indice_financiero = 'ACTIVO'
              AND i.deleted_at IS NULL
              AND iv.estado_valor_indice = 'PUBLICADO'
              AND iv.fecha_publicacion IS NOT NULL
              AND iv.deleted_at IS NULL
              AND iv.fecha_valor <= :fecha_objetivo
            ORDER BY iv.fecha_valor DESC
            LIMIT 1
            """
        )
        row = self.db.execute(
            stmt,
            {
                "codigo_indice_financiero": codigo_normalizado,
                "fecha_objetivo": fecha_objetivo,
            },
        ).mappings().one_or_none()

        if row is None:
            return None

        return self._row_to_valor_publicado(row)

    def get_valor_publicado_por_id_y_fecha(
        self,
        id_indice_financiero: int,
        fecha_objetivo: date,
    ) -> dict[str, Any] | None:
        if id_indice_financiero <= 0:
            return None

        stmt = text(
            """
            SELECT
                i.id_indice_financiero,
                i.codigo_indice_financiero,
                i.nombre_indice_financiero,
                iv.id_indice_financiero_valor,
                iv.fecha_valor,
                iv.valor_indice,
                iv.fecha_publicacion,
                iv.fuente_valor
            FROM indice_financiero AS i
            JOIN indice_financiero_valor AS iv
                ON iv.id_indice_financiero = i.id_indice_financiero
            WHERE i.id_indice_financiero = :id_indice_financiero
              AND i.estado_indice_financiero = 'ACTIVO'
              AND i.deleted_at IS NULL
              AND iv.estado_valor_indice = 'PUBLICADO'
              AND iv.fecha_publicacion IS NOT NULL
              AND iv.deleted_at IS NULL
              AND iv.fecha_valor <= :fecha_objetivo
            ORDER BY iv.fecha_valor DESC
            LIMIT 1
            """
        )
        row = self.db.execute(
            stmt,
            {
                "id_indice_financiero": id_indice_financiero,
                "fecha_objetivo": fecha_objetivo,
            },
        ).mappings().one_or_none()

        if row is None:
            return None

        return self._row_to_valor_publicado(row)


    def get_indice_financiero_activo(
        self, id_indice_financiero: int
    ) -> dict[str, Any] | None:
        if id_indice_financiero <= 0:
            return None
        stmt = text("""
            SELECT id_indice_financiero, codigo_indice_financiero, nombre_indice_financiero
            FROM indice_financiero
            WHERE id_indice_financiero = :id_indice_financiero
              AND estado_indice_financiero = 'ACTIVO'
              AND deleted_at IS NULL
            """)
        row = self.db.execute(
            stmt, {"id_indice_financiero": id_indice_financiero}
        ).mappings().one_or_none()
        return dict(row) if row else None

    def diagnosticar_valor_publicado_no_aplicable(
        self, id_indice_financiero: int, fecha_objetivo: date
    ) -> str:
        if self.get_indice_financiero_activo(id_indice_financiero) is None:
            return "INDICE_FINANCIERO_INACTIVO"

        stmt = text("""
            SELECT 1
            FROM indice_financiero_valor AS iv
            WHERE iv.id_indice_financiero = :id_indice_financiero
              AND iv.estado_valor_indice = 'PUBLICADO'
              AND iv.fecha_publicacion IS NULL
              AND iv.deleted_at IS NULL
              AND iv.fecha_valor <= :fecha_objetivo
            ORDER BY iv.fecha_valor DESC
            LIMIT 1
            """)
        row = self.db.execute(
            stmt,
            {
                "id_indice_financiero": id_indice_financiero,
                "fecha_objetivo": fecha_objetivo,
            },
        ).first()
        if row is not None:
            return "FECHA_PUBLICACION_INDICE_INCOMPLETA"
        return "VALOR_INDICE_PUBLICADO_INEXISTENTE"

    @staticmethod
    def _row_to_valor_publicado(row: Any) -> dict[str, Any]:
        return {
            "id_indice_financiero": row["id_indice_financiero"],
            "codigo_indice_financiero": row["codigo_indice_financiero"],
            "nombre_indice_financiero": row["nombre_indice_financiero"],
            "id_indice_financiero_valor": row["id_indice_financiero_valor"],
            "fecha_valor": row["fecha_valor"],
            "valor_indice": row["valor_indice"],
            "fecha_publicacion": row["fecha_publicacion"],
            "fuente_valor": row["fuente_valor"],
        }
