from typing import Any

from app.infrastructure.persistence.repositories.catalogo_maestro_repository import (
    CatalogoMaestroRepository,
)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

_COLUMNS = """
 id_item_catalogo, id_catalogo_maestro, uid_global::text AS uid_global,
 version_registro, created_at, updated_at, deleted_at, id_instalacion_origen,
 id_instalacion_ultima_modificacion, op_id_alta::text AS op_id_alta,
 op_id_ultima_modificacion::text AS op_id_ultima_modificacion,
 codigo_item_catalogo, nombre_item_catalogo, descripcion, estado_item_catalogo
"""


class ItemCatalogoIdempotencyConflictError(ValueError):
    pass


class ItemCatalogoConcurrencyError(ValueError):
    pass


class ItemCatalogoDuplicateCodeError(ValueError):
    pass


class ItemCatalogoInvalidStateTransitionError(ValueError):
    pass


class ItemCatalogoRepository:
    def __init__(self, session) -> None:
        self.db = session

    def get(self, item_id: int) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(
                    f"SELECT {_COLUMNS} FROM item_catalogo WHERE id_item_catalogo=:id"
                ),
                {"id": item_id},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    @staticmethod
    def _constraint_name(exc):
        return getattr(
            getattr(getattr(exc, "orig", None), "diag", None), "constraint_name", None
        )

    def _parent(self, catalogo_id):
        return CatalogoMaestroRepository(self.db).get_write(catalogo_id)

    def _valid(self, catalogo_id, item_id):
        parent = self._parent(catalogo_id)
        item = self.get(item_id)
        if parent is None or parent["deleted_at"] is not None:
            return None, None
        if (
            item is None
            or item["id_catalogo_maestro"] != catalogo_id
            or item["deleted_at"] is not None
        ):
            return parent, None
        return parent, item

    def lock_parent(self, catalogo_id):
        row = self.db.execute(text(
            "SELECT * FROM catalogo_maestro WHERE id_catalogo_maestro=:id FOR UPDATE"
        ), {"id": catalogo_id}).mappings().one_or_none()
        return dict(row) if row else None

    def lock_item(self, item_id):
        row = self.db.execute(text(
            f"SELECT {_COLUMNS} FROM item_catalogo WHERE id_item_catalogo=:id FOR UPDATE"
        ), {"id": item_id}).mappings().one_or_none()
        return dict(row) if row else None

    def create(self, catalogo_id, payload, *, op_id):
        parent = self.lock_parent(catalogo_id)
        if parent is None or parent["deleted_at"] is not None:
            return None
        try:
            iid = self.db.execute(
                text(
                    """
                    INSERT INTO item_catalogo (
                        id_catalogo_maestro, codigo_item_catalogo,
                        nombre_item_catalogo, descripcion, estado_item_catalogo,
                        id_instalacion_origen, id_instalacion_ultima_modificacion,
                        op_id_alta, op_id_ultima_modificacion
                    ) VALUES (
                        :catalogo, :codigo_item_catalogo, :nombre_item_catalogo,
                        :descripcion, 'ACTIVO', NULL, NULL,
                        CAST(:op AS uuid), CAST(:op AS uuid)
                    ) RETURNING id_item_catalogo
                    """
                ),
                {
                    **payload,
                    "catalogo": catalogo_id,
                    "op": op_id,
                },
            ).scalar_one()
            return self.get(iid)
        except IntegrityError as exc:
            if self._constraint_name(exc) == "uq_item_catalogo":
                raise ItemCatalogoDuplicateCodeError(
                    "Ya existe un ítem con ese código en el catálogo."
                ) from exc
            raise

    def change(self, catalogo_id, item_id, payload, *, op_id, version, action):
        parent = self.lock_parent(catalogo_id)
        row = self.lock_item(item_id)
        if (parent is None or parent["deleted_at"] is not None or row is None
                or row["id_catalogo_maestro"] != catalogo_id):
            row = None
        if row is None:
            return None
        if row["deleted_at"] is not None:
            return None
        if row["version_registro"] != version:
            raise ItemCatalogoConcurrencyError("La versión del ítem no coincide.")
        if (
            action == "estado"
            and row["estado_item_catalogo"] == payload["estado_item_catalogo"]
        ):
            raise ItemCatalogoInvalidStateTransitionError(
                "El estado destino ya es el estado actual del ítem."
            )
        sets = {
            "update": """
                codigo_item_catalogo = :codigo_item_catalogo,
                nombre_item_catalogo = :nombre_item_catalogo,
                descripcion = :descripcion
            """,
            "estado": "estado_item_catalogo=:estado_item_catalogo",
            "baja": "deleted_at=CURRENT_TIMESTAMP",
        }[action]
        try:
            result = self.db.execute(
                text(
                    f"""
                    UPDATE item_catalogo
                    SET {sets},
                        id_instalacion_ultima_modificacion = NULL,
                        op_id_ultima_modificacion = CAST(:op AS uuid)
                    WHERE id_item_catalogo = :item
                      AND id_catalogo_maestro = :catalogo
                      AND deleted_at IS NULL
                      AND version_registro = :version
                    RETURNING id_item_catalogo
                    """
                ),
                {
                    **payload,
                    "item": item_id,
                    "catalogo": catalogo_id,
                    "op": op_id,
                    "version": version,
                },
            ).scalar_one_or_none()
            if result is None:
                raise ItemCatalogoConcurrencyError("La versión del ítem no coincide.")
            return self.get(item_id)
        except IntegrityError as exc:
            if self._constraint_name(exc) == "uq_item_catalogo":
                raise ItemCatalogoDuplicateCodeError(
                    "Ya existe un ítem con ese código en el catálogo."
                ) from exc
            raise
