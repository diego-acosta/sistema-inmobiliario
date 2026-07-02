from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.base_repository import BaseRepository
from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository


class SucursalIdempotencyConflictError(ValueError):
    pass


class SucursalDuplicateActiveError(ValueError):
    pass


_COLUMNS = """
    id_sucursal,
    uid_global::text AS uid_global,
    version_registro,
    created_at,
    updated_at,
    deleted_at,
    id_instalacion_origen,
    id_instalacion_ultima_modificacion,
    op_id_alta::text AS op_id_alta,
    op_id_ultima_modificacion::text AS op_id_ultima_modificacion,
    codigo_sucursal,
    nombre_sucursal,
    descripcion_sucursal,
    estado_sucursal,
    es_casa_central,
    permite_operacion,
    fecha_alta,
    fecha_baja,
    observaciones
"""

_PAYLOAD_FIELDS = (
    "codigo_sucursal",
    "nombre_sucursal",
    "descripcion_sucursal",
    "estado_sucursal",
    "es_casa_central",
    "permite_operacion",
    "observaciones",
)


class SucursalRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    @staticmethod
    def _map(row: Any) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _payload_matches(row: dict[str, Any], payload: dict[str, Any]) -> bool:
        return all(row.get(field) == payload.get(field) for field in _PAYLOAD_FIELDS)

    @staticmethod
    def _outbox_payload(row: dict[str, Any], *, op_id: str) -> dict[str, Any]:
        return {
            "id_sucursal": row["id_sucursal"],
            "uid_global": row["uid_global"],
            "codigo_sucursal": row["codigo_sucursal"],
            "nombre_sucursal": row["nombre_sucursal"],
            "estado_sucursal": row["estado_sucursal"],
            "op_id": op_id,
            "id_instalacion_origen": row["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": row[
                "id_instalacion_ultima_modificacion"
            ],
            "version_registro": row["version_registro"],
        }

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        row = self.db.execute(
            text(f"SELECT {_COLUMNS} FROM sucursal WHERE op_id_alta = :op_id"),
            {"op_id": op_id},
        ).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def get_active_by_codigo(self, codigo_sucursal: str) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                f"""
                SELECT {_COLUMNS}
                FROM sucursal
                WHERE codigo_sucursal = :codigo_sucursal
                  AND deleted_at IS NULL
                """
            ),
            {"codigo_sucursal": codigo_sucursal},
        ).mappings().one_or_none()
        return self._map(row) if row is not None else None

    @staticmethod
    def _constraint_name(exc: IntegrityError) -> str | None:
        orig = getattr(exc, "orig", None)
        diag = getattr(orig, "diag", None)
        return getattr(diag, "constraint_name", None)

    def _raise_or_return_idempotent_replay(
        self, *, op_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        existing = self.get_by_op_id_alta(op_id)
        if existing is None:
            raise SucursalDuplicateActiveError("Ya existe una sucursal activa con ese código.")
        if not self._payload_matches(existing, payload):
            raise SucursalIdempotencyConflictError(
                "El X-Op-Id ya fue usado con un payload incompatible."
            )
        return existing

    def create(self, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any]:
        op_id = str(core.x_op_id)
        existing = self.get_by_op_id_alta(op_id)
        if existing is not None:
            if not self._payload_matches(existing, payload):
                raise SucursalIdempotencyConflictError(
                    "El X-Op-Id ya fue usado con un payload incompatible."
                )
            return existing

        if self.get_active_by_codigo(payload["codigo_sucursal"]) is not None:
            raise SucursalDuplicateActiveError("Ya existe una sucursal activa con ese código.")

        statement = text(
            f"""
            INSERT INTO sucursal (
                codigo_sucursal,
                nombre_sucursal,
                descripcion_sucursal,
                estado_sucursal,
                es_casa_central,
                permite_operacion,
                observaciones,
                version_registro,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion
            )
            VALUES (
                :codigo_sucursal,
                :nombre_sucursal,
                :descripcion_sucursal,
                :estado_sucursal,
                :es_casa_central,
                :permite_operacion,
                :observaciones,
                1,
                :id_instalacion,
                :id_instalacion,
                :op_id,
                :op_id
            )
            RETURNING {_COLUMNS}
            """
        )
        try:
            row = self.db.execute(
                statement,
                {**payload, "id_instalacion": core.x_instalacion_id, "op_id": op_id},
            ).mappings().one()
            created = self._map(row)
            OutboxRepository(self.db).add_event(
                event_type="sucursal_creada",
                aggregate_type="sucursal",
                aggregate_id=created["id_sucursal"],
                payload=self._outbox_payload(created, op_id=op_id),
                occurred_at=datetime.now(UTC),
                status="PENDING",
                processing_reason={"source": "SRV-OPE-001", "issue": "#250"},
                processing_metadata={"refs": ["#248"]},
            )
            self.db.commit()
            return created
        except IntegrityError as exc:
            self.db.rollback()
            constraint_name = self._constraint_name(exc)
            if constraint_name in {"ux_sucursal_op_id_alta", "uq_sucursal_codigo"}:
                return self._raise_or_return_idempotent_replay(
                    op_id=op_id, payload=payload
                )
            raise
        except Exception:
            self.db.rollback()
            raise

    def list(self, *, estado_sucursal: str | None = None) -> list[dict[str, Any]]:
        where = ["deleted_at IS NULL"]
        params: dict[str, Any] = {}
        if estado_sucursal:
            where.append("estado_sucursal = :estado_sucursal")
            params["estado_sucursal"] = estado_sucursal
        statement = text(
            f"""
            SELECT {_COLUMNS}
            FROM sucursal
            WHERE {' AND '.join(where)}
            ORDER BY id_sucursal
            """
        )
        return [self._map(row) for row in self.db.execute(statement, params).mappings().all()]

    def get(self, id_sucursal: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                f"""
                SELECT {_COLUMNS}
                FROM sucursal
                WHERE id_sucursal = :id_sucursal
                  AND deleted_at IS NULL
                """
            ),
            {"id_sucursal": id_sucursal},
        ).mappings().one_or_none()
        return self._map(row) if row is not None else None
