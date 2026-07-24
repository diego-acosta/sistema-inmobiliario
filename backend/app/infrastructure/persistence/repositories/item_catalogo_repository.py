from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.infrastructure.persistence.repositories.catalogo_maestro_repository import (
    CatalogoMaestroRepository,
)
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)

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

    def by_op_alta(self, op_id: str) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(
                    f"SELECT {_COLUMNS} FROM item_catalogo WHERE op_id_alta=CAST(:op AS uuid)"
                ),
                {"op": op_id},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row else None

    @staticmethod
    def _payload_matches(row, payload):
        return all(
            row.get(k) == payload.get(k)
            for k in ("codigo_item_catalogo", "nombre_item_catalogo", "descripcion")
        )

    @staticmethod
    def _constraint_name(exc):
        return getattr(
            getattr(getattr(exc, "orig", None), "diag", None), "constraint_name", None
        )

    @staticmethod
    def _event(row, op_id):
        return {
            k: row[k]
            for k in (
                "id_item_catalogo",
                "id_catalogo_maestro",
                "uid_global",
                "codigo_item_catalogo",
                "nombre_item_catalogo",
                "descripcion",
                "estado_item_catalogo",
                "version_registro",
                "deleted_at",
                "id_instalacion_origen",
                "id_instalacion_ultima_modificacion",
            )
        } | {"op_id": op_id}

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

    def _raise_or_return_idempotent_replay(
        self, *, catalogo_id, op_id, payload, original_error
    ):
        existing = self.by_op_alta(op_id)
        if existing is None:
            raise original_error
        if existing["id_catalogo_maestro"] != catalogo_id or not self._payload_matches(
            existing, payload
        ):
            raise ItemCatalogoIdempotencyConflictError(
                "El X-Op-Id ya fue usado con un payload incompatible."
            )
        return existing

    def create(self, catalogo_id, payload, core):
        parent = self._parent(catalogo_id)
        if parent is None or parent["deleted_at"] is not None:
            return None
        op = str(core.x_op_id)
        existing = self.by_op_alta(op)
        if existing:
            if existing[
                "id_catalogo_maestro"
            ] != catalogo_id or not self._payload_matches(existing, payload):
                raise ItemCatalogoIdempotencyConflictError(
                    "El X-Op-Id ya fue usado con un payload incompatible."
                )
            return existing
        try:
            iid = self.db.execute(
                text(
                    """INSERT INTO item_catalogo (id_catalogo_maestro,codigo_item_catalogo,nombre_item_catalogo,descripcion,estado_item_catalogo,id_instalacion_origen,id_instalacion_ultima_modificacion,op_id_alta,op_id_ultima_modificacion) VALUES (:catalogo,:codigo_item_catalogo,:nombre_item_catalogo,:descripcion,'ACTIVO',:inst,:inst,CAST(:op AS uuid),CAST(:op AS uuid)) RETURNING id_item_catalogo"""
                ),
                {
                    **payload,
                    "catalogo": catalogo_id,
                    "inst": core.x_instalacion_id,
                    "op": op,
                },
            ).scalar_one()
            row = self.get(iid)
            OutboxRepository(self.db).add_event(
                event_type="item_catalogo_creado",
                aggregate_type="item_catalogo",
                aggregate_id=iid,
                payload=self._event(row, op),
                occurred_at=datetime.now(UTC),
            )
            self.db.commit()
            return row
        except IntegrityError as exc:
            self.db.rollback()
            if self._constraint_name(exc) == "ux_item_catalogo_op_id_alta":
                return self._raise_or_return_idempotent_replay(
                    catalogo_id=catalogo_id,
                    op_id=op,
                    payload=payload,
                    original_error=exc,
                )
            if self._constraint_name(exc) == "uq_item_catalogo":
                raise ItemCatalogoDuplicateCodeError(
                    "Ya existe un ítem con ese código en el catálogo."
                )
            raise
        except Exception:
            self.db.rollback()
            raise

    def change(self, catalogo_id, item_id, payload, core, version, action):
        if action == "baja":
            parent = self._parent(catalogo_id)
            row = self.get(item_id)
            if (
                parent is None
                or parent["deleted_at"] is not None
                or row is None
                or row["id_catalogo_maestro"] != catalogo_id
            ):
                row = None
        else:
            _, row = self._valid(catalogo_id, item_id)
        if row is None:
            return None
        op = str(core.x_op_id)
        if row["deleted_at"] is not None:
            if action == "baja" and str(row["op_id_ultima_modificacion"]) == op:
                return row
            return None
        if str(row["op_id_ultima_modificacion"]) == op:
            if action == "update" and self._payload_matches(row, payload):
                return row
            if (
                action == "estado"
                and row["estado_item_catalogo"] == payload["estado_item_catalogo"]
            ):
                return row
            raise ItemCatalogoIdempotencyConflictError(
                "El X-Op-Id ya fue usado con un payload incompatible."
            )
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
            "update": "codigo_item_catalogo=:codigo_item_catalogo,nombre_item_catalogo=:nombre_item_catalogo,descripcion=:descripcion",
            "estado": "estado_item_catalogo=:estado_item_catalogo",
            "baja": "deleted_at=CURRENT_TIMESTAMP",
        }[action]
        event = {
            "update": "item_catalogo_modificado",
            "estado": "item_catalogo_estado_cambiado",
            "baja": "item_catalogo_desactivado",
        }[action]
        try:
            result = self.db.execute(
                text(
                    f"UPDATE item_catalogo SET {sets}, id_instalacion_ultima_modificacion=:inst, op_id_ultima_modificacion=CAST(:op AS uuid) WHERE id_item_catalogo=:item AND id_catalogo_maestro=:catalogo AND deleted_at IS NULL AND version_registro=:version RETURNING id_item_catalogo"
                ),
                {
                    **payload,
                    "item": item_id,
                    "catalogo": catalogo_id,
                    "inst": core.x_instalacion_id,
                    "op": op,
                    "version": version,
                },
            ).scalar_one_or_none()
            if result is None:
                raise ItemCatalogoConcurrencyError("La versión del ítem no coincide.")
            row = self.get(item_id)
            OutboxRepository(self.db).add_event(
                event_type=event,
                aggregate_type="item_catalogo",
                aggregate_id=item_id,
                payload=self._event(row, op),
                occurred_at=datetime.now(UTC),
            )
            self.db.commit()
            return row
        except IntegrityError as exc:
            self.db.rollback()
            if self._constraint_name(exc) == "uq_item_catalogo":
                raise ItemCatalogoDuplicateCodeError(
                    "Ya existe un ítem con ese código en el catálogo."
                )
            raise
        except Exception:
            self.db.rollback()
            raise
