from typing import Any

from sqlalchemy import text

from app.infrastructure.persistence.base_repository import BaseRepository

_CATALOGO_COLUMNS = """
    id_catalogo_maestro,
    codigo_catalogo_maestro,
    nombre_catalogo_maestro,
    descripcion
"""

_ITEM_COLUMNS = """
    id_item_catalogo,
    id_catalogo_maestro,
    codigo_item_catalogo,
    nombre_item_catalogo,
    descripcion,
    estado_item_catalogo
"""


class CatalogoMaestroRepository(BaseRepository[Any]):
    """Consultas read-only de catálogos administrativos.

    CORE-EF: QUERY_READLIKE. No exige headers write, no persiste cambios,
    no genera outbox, no incrementa versiones y no realiza commits de negocio.
    """

    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    @staticmethod
    def _map(row: Any) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _pagination(page: int, page_size: int) -> dict[str, int]:
        return {"limit": page_size, "offset": (page - 1) * page_size}

    def list_catalogos(
        self, q: str | None, page: int, page_size: int
    ) -> dict[str, Any]:
        where_clauses: list[str] = ["deleted_at IS NULL"]
        params: dict[str, Any] = self._pagination(page, page_size)
        if q:
            where_clauses.append(
                "(codigo_catalogo_maestro ILIKE :q OR nombre_catalogo_maestro ILIKE :q)"
            )
            params["q"] = f"%{q}%"

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        total_statement = text(f"""
            SELECT COUNT(*)
            FROM catalogo_maestro
            {where_sql}
            """)
        data_statement = text(f"""
            SELECT {_CATALOGO_COLUMNS}
            FROM catalogo_maestro
            {where_sql}
            ORDER BY codigo_catalogo_maestro, id_catalogo_maestro
            LIMIT :limit OFFSET :offset
            """)
        total = self.db.execute(total_statement, params).scalar_one()
        items = [
            self._map(row) for row in self.db.execute(data_statement, params).mappings().all()
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}

    def get_catalogo(self, id_catalogo_maestro: int) -> dict[str, Any] | None:
        statement = text(f"""
            SELECT {_CATALOGO_COLUMNS}
            FROM catalogo_maestro
            WHERE id_catalogo_maestro = :id_catalogo_maestro
              AND deleted_at IS NULL
            """)
        row = (
            self.db.execute(statement, {"id_catalogo_maestro": id_catalogo_maestro})
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def list_items(
        self,
        id_catalogo_maestro: int,
        q: str | None,
        estado_item_catalogo: str | None,
        page: int,
        page_size: int,
    ) -> dict[str, Any] | None:
        if self.get_catalogo(id_catalogo_maestro) is None:
            return None

        where_clauses = ["id_catalogo_maestro = :id_catalogo_maestro", "deleted_at IS NULL"]
        params: dict[str, Any] = {
            "id_catalogo_maestro": id_catalogo_maestro,
            **self._pagination(page, page_size),
        }
        if q:
            where_clauses.append(
                "(codigo_item_catalogo ILIKE :q OR nombre_item_catalogo ILIKE :q)"
            )
            params["q"] = f"%{q}%"
        if estado_item_catalogo is not None:
            where_clauses.append("estado_item_catalogo = :estado_item_catalogo")
            params["estado_item_catalogo"] = estado_item_catalogo

        where_sql = f"WHERE {' AND '.join(where_clauses)}"
        total_statement = text(f"""
            SELECT COUNT(*)
            FROM item_catalogo
            {where_sql}
            """)
        data_statement = text(f"""
            SELECT {_ITEM_COLUMNS}
            FROM item_catalogo
            {where_sql}
            ORDER BY codigo_item_catalogo, id_item_catalogo
            LIMIT :limit OFFSET :offset
            """)
        total = self.db.execute(total_statement, params).scalar_one()
        items = [
            self._map(row) for row in self.db.execute(data_statement, params).mappings().all()
        ]
        return {"items": items, "total": total, "page": page, "page_size": page_size}
