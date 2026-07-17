from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.infrastructure.persistence.base_repository import BaseRepository
from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository

_CATALOGO_COLUMNS = """
    id_catalogo_maestro,
    codigo_catalogo_maestro,
    nombre_catalogo_maestro,
    descripcion
"""

_CATALOGO_WRITE_COLUMNS = """
    id_catalogo_maestro,
    uid_global::text AS uid_global,
    version_registro,
    created_at,
    updated_at,
    deleted_at,
    id_instalacion_origen,
    id_instalacion_ultima_modificacion,
    op_id_alta::text AS op_id_alta,
    op_id_ultima_modificacion::text AS op_id_ultima_modificacion,
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


class CatalogoMaestroIdempotencyConflictError(ValueError):
    pass


class CatalogoMaestroConcurrencyError(ValueError):
    pass


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

    def get_write(self, id_catalogo_maestro: int) -> dict[str, Any] | None:
        row = self.db.execute(text(f"""
            SELECT {_CATALOGO_WRITE_COLUMNS}
            FROM catalogo_maestro
            WHERE id_catalogo_maestro = :id_catalogo_maestro
        """), {"id_catalogo_maestro": id_catalogo_maestro}).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        row = self.db.execute(text(f"""
            SELECT {_CATALOGO_WRITE_COLUMNS}
            FROM catalogo_maestro
            WHERE op_id_alta = CAST(:op_id AS uuid)
        """), {"op_id": op_id}).mappings().one_or_none()
        return self._map(row) if row is not None else None

    @staticmethod
    def _payload_matches(row: dict[str, Any], payload: dict[str, Any]) -> bool:
        return all(row.get(field) == payload.get(field) for field in (
            "codigo_catalogo_maestro", "nombre_catalogo_maestro", "descripcion"
        ))

    @staticmethod
    def _outbox_payload(row: dict[str, Any], *, op_id: str) -> dict[str, Any]:
        return {
            "id_catalogo_maestro": row["id_catalogo_maestro"],
            "uid_global": row["uid_global"],
            "codigo_catalogo_maestro": row["codigo_catalogo_maestro"],
            "nombre_catalogo_maestro": row["nombre_catalogo_maestro"],
            "descripcion": row["descripcion"],
            "version_registro": row["version_registro"],
            "deleted_at": row["deleted_at"],
            "id_instalacion_origen": row["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": row["id_instalacion_ultima_modificacion"],
            "op_id": op_id,
        }

    def create(self, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any]:
        op_id = str(core.x_op_id)
        existing = self.get_by_op_id_alta(op_id)
        if existing is not None:
            if not self._payload_matches(existing, payload):
                raise CatalogoMaestroIdempotencyConflictError(
                    "El X-Op-Id ya fue usado con un payload incompatible."
                )
            return existing
        try:
            catalogo_id = self.db.execute(text("""
                INSERT INTO catalogo_maestro (
                    codigo_catalogo_maestro, nombre_catalogo_maestro, descripcion,
                    id_instalacion_origen, id_instalacion_ultima_modificacion,
                    op_id_alta, op_id_ultima_modificacion
                ) VALUES (
                    :codigo_catalogo_maestro, :nombre_catalogo_maestro, :descripcion,
                    :id_instalacion, :id_instalacion, CAST(:op_id AS uuid), CAST(:op_id AS uuid)
                ) RETURNING id_catalogo_maestro
            """), {**payload, "id_instalacion": core.x_instalacion_id, "op_id": op_id}).scalar_one()
            created = self.get_write(catalogo_id)
            OutboxRepository(self.db).add_event(
                event_type="catalogo_maestro_creado", aggregate_type="catalogo_maestro",
                aggregate_id=catalogo_id, payload=self._outbox_payload(created, op_id=op_id),
                occurred_at=datetime.now(UTC),
            )
            self.db.commit()
            return created
        except Exception:
            self.db.rollback()
            raise

    def update(self, id_catalogo_maestro: int, payload: dict[str, Any], *, core: CoreEFHeaders, if_match_version: int) -> dict[str, Any] | None:
        actual = self.get_write(id_catalogo_maestro)
        if actual is None or actual["deleted_at"] is not None:
            return None
        op_id = str(core.x_op_id)
        if str(actual.get("op_id_ultima_modificacion")) == op_id:
            if self._payload_matches(actual, payload):
                return actual
            raise CatalogoMaestroIdempotencyConflictError(
                "El X-Op-Id ya fue usado con un payload incompatible."
            )
        if actual["version_registro"] != if_match_version:
            raise CatalogoMaestroConcurrencyError("La versión del catálogo maestro no coincide.")
        try:
            updated_id = self.db.execute(text("""
                UPDATE catalogo_maestro
                SET codigo_catalogo_maestro = :codigo_catalogo_maestro,
                    nombre_catalogo_maestro = :nombre_catalogo_maestro,
                    descripcion = :descripcion,
                    id_instalacion_ultima_modificacion = :id_instalacion,
                    op_id_ultima_modificacion = CAST(:op_id AS uuid)
                WHERE id_catalogo_maestro = :id_catalogo_maestro
                  AND deleted_at IS NULL
                  AND version_registro = :if_match_version
                RETURNING id_catalogo_maestro
            """), {**payload, "id_catalogo_maestro": id_catalogo_maestro,
                    "id_instalacion": core.x_instalacion_id, "op_id": op_id,
                    "if_match_version": if_match_version}).scalar_one_or_none()
            if updated_id is None:
                self.db.rollback()
                raise CatalogoMaestroConcurrencyError("La versión del catálogo maestro no coincide.")
            updated = self.get_write(updated_id)
            OutboxRepository(self.db).add_event(
                event_type="catalogo_maestro_modificado", aggregate_type="catalogo_maestro",
                aggregate_id=updated_id, payload=self._outbox_payload(updated, op_id=op_id),
                occurred_at=datetime.now(UTC),
            )
            self.db.commit()
            return updated
        except Exception:
            self.db.rollback()
            raise

    def baja_logica(self, id_catalogo_maestro: int, *, core: CoreEFHeaders, if_match_version: int) -> dict[str, Any] | None:
        actual = self.get_write(id_catalogo_maestro)
        if actual is None:
            return None
        op_id = str(core.x_op_id)
        if actual["deleted_at"] is not None:
            if str(actual.get("op_id_ultima_modificacion")) == op_id:
                return actual
            return None
        if actual["version_registro"] != if_match_version:
            raise CatalogoMaestroConcurrencyError("La versión del catálogo maestro no coincide.")
        try:
            updated_id = self.db.execute(text("""
                UPDATE catalogo_maestro
                SET deleted_at = CURRENT_TIMESTAMP,
                    id_instalacion_ultima_modificacion = :id_instalacion,
                    op_id_ultima_modificacion = CAST(:op_id AS uuid)
                WHERE id_catalogo_maestro = :id_catalogo_maestro
                  AND deleted_at IS NULL
                  AND version_registro = :if_match_version
                RETURNING id_catalogo_maestro
            """), {"id_catalogo_maestro": id_catalogo_maestro,
                    "id_instalacion": core.x_instalacion_id, "op_id": op_id,
                    "if_match_version": if_match_version}).scalar_one_or_none()
            if updated_id is None:
                self.db.rollback()
                raise CatalogoMaestroConcurrencyError("La versión del catálogo maestro no coincide.")
            updated = self.get_write(updated_id)
            OutboxRepository(self.db).add_event(
                event_type="catalogo_maestro_desactivado", aggregate_type="catalogo_maestro",
                aggregate_id=updated_id, payload=self._outbox_payload(updated, op_id=op_id),
                occurred_at=datetime.now(UTC),
            )
            self.db.commit()
            return updated
        except Exception:
            self.db.rollback()
            raise

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
