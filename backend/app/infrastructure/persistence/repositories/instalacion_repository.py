from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.base_repository import BaseRepository
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)


class InstalacionIdempotencyConflictError(ValueError):
    pass


class InstalacionDuplicateActiveError(ValueError):
    pass


class InstalacionSucursalNotFoundError(ValueError):
    pass


_COLUMNS = """
    id_instalacion,
    uid_global::text AS uid_global,
    version_registro,
    created_at,
    updated_at,
    deleted_at,
    id_instalacion_origen,
    id_instalacion_ultima_modificacion,
    op_id_alta::text AS op_id_alta,
    op_id_ultima_modificacion::text AS op_id_ultima_modificacion,
    id_sucursal,
    codigo_instalacion,
    nombre_instalacion,
    descripcion_instalacion,
    estado_instalacion,
    es_principal,
    permite_sincronizacion,
    identificador_tecnico,
    direccion_local,
    fecha_alta,
    fecha_baja,
    observaciones
"""

_PAYLOAD_FIELDS = (
    "id_sucursal",
    "codigo_instalacion",
    "nombre_instalacion",
    "descripcion_instalacion",
    "estado_instalacion",
    "es_principal",
    "permite_sincronizacion",
    "identificador_tecnico",
    "direccion_local",
    "observaciones",
)


class InstalacionRepository(BaseRepository[Any]):
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
            "id_instalacion": row["id_instalacion"],
            "uid_global": row["uid_global"],
            "id_sucursal": row["id_sucursal"],
            "codigo_instalacion": row["codigo_instalacion"],
            "nombre_instalacion": row["nombre_instalacion"],
            "estado_instalacion": row["estado_instalacion"],
            "op_id": op_id,
            "id_instalacion_origen": row["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": row[
                "id_instalacion_ultima_modificacion"
            ],
            "version_registro": row["version_registro"],
        }

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(f"SELECT {_COLUMNS} FROM instalacion WHERE op_id_alta = :op_id"),
                {"op_id": op_id},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def get_active_by_codigo(self, codigo_instalacion: str) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(f"""
                SELECT {_COLUMNS}
                FROM instalacion
                WHERE codigo_instalacion = :codigo_instalacion
                  AND deleted_at IS NULL
                """),
                {"codigo_instalacion": codigo_instalacion},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def _sucursal_activa_exists(self, id_sucursal: int) -> bool:
        return bool(
            self.db.execute(
                text("""
                    SELECT 1
                    FROM sucursal
                    WHERE id_sucursal = :id_sucursal
                      AND deleted_at IS NULL
                    """),
                {"id_sucursal": id_sucursal},
            ).scalar()
        )

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
            raise InstalacionDuplicateActiveError(
                "Ya existe una instalación activa con ese código."
            )
        if not self._payload_matches(existing, payload):
            raise InstalacionIdempotencyConflictError(
                "El X-Op-Id ya fue usado con un payload incompatible."
            )
        return existing

    def create(self, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any]:
        op_id = str(core.x_op_id)
        existing = self.get_by_op_id_alta(op_id)
        if existing is not None:
            if not self._payload_matches(existing, payload):
                raise InstalacionIdempotencyConflictError(
                    "El X-Op-Id ya fue usado con un payload incompatible."
                )
            return existing

        if not self._sucursal_activa_exists(payload["id_sucursal"]):
            raise InstalacionSucursalNotFoundError(
                "Sucursal no encontrada o dada de baja."
            )

        if self.get_active_by_codigo(payload["codigo_instalacion"]) is not None:
            raise InstalacionDuplicateActiveError(
                "Ya existe una instalación activa con ese código."
            )

        statement = text(f"""
            INSERT INTO instalacion (
                id_sucursal,
                codigo_instalacion,
                nombre_instalacion,
                descripcion_instalacion,
                estado_instalacion,
                es_principal,
                permite_sincronizacion,
                identificador_tecnico,
                direccion_local,
                observaciones,
                version_registro,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion
            )
            VALUES (
                :id_sucursal,
                :codigo_instalacion,
                :nombre_instalacion,
                :descripcion_instalacion,
                :estado_instalacion,
                :es_principal,
                :permite_sincronizacion,
                :identificador_tecnico,
                :direccion_local,
                :observaciones,
                1,
                :id_instalacion_contexto,
                :id_instalacion_contexto,
                :op_id,
                :op_id
            )
            RETURNING {_COLUMNS}
            """)
        try:
            row = (
                self.db.execute(
                    statement,
                    {
                        **payload,
                        "id_instalacion_contexto": core.x_instalacion_id,
                        "op_id": op_id,
                    },
                )
                .mappings()
                .one()
            )
            created = self._map(row)
            OutboxRepository(self.db).add_event(
                event_type="instalacion_creada",
                aggregate_type="instalacion",
                aggregate_id=created["id_instalacion"],
                payload=self._outbox_payload(created, op_id=op_id),
                occurred_at=datetime.now(UTC),
                status="PENDING",
                processing_reason={"source": "SRV-OPE-002", "issue": "#251"},
                processing_metadata={"refs": ["#248"], "evt": "EVT-OPE-004"},
            )
            self.db.commit()
            return created
        except IntegrityError as exc:
            self.db.rollback()
            constraint_name = self._constraint_name(exc)
            if constraint_name in {
                "ux_instalacion_op_id_alta",
                "uq_instalacion_codigo",
            }:
                return self._raise_or_return_idempotent_replay(
                    op_id=op_id, payload=payload
                )
            raise
        except Exception:
            self.db.rollback()
            raise

    def list(
        self, *, id_sucursal: int | None = None, estado_instalacion: str | None = None
    ) -> list[dict[str, Any]]:
        where = ["deleted_at IS NULL"]
        params: dict[str, Any] = {}
        if id_sucursal is not None:
            where.append("id_sucursal = :id_sucursal")
            params["id_sucursal"] = id_sucursal
        if estado_instalacion:
            where.append("estado_instalacion = :estado_instalacion")
            params["estado_instalacion"] = estado_instalacion
        statement = text(f"""
            SELECT {_COLUMNS}
            FROM instalacion
            WHERE {' AND '.join(where)}
            ORDER BY id_instalacion
            """)
        return [
            self._map(row)
            for row in self.db.execute(statement, params).mappings().all()
        ]

    def get(self, id_instalacion: int) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(f"""
                SELECT {_COLUMNS}
                FROM instalacion
                WHERE id_instalacion = :id_instalacion
                  AND deleted_at IS NULL
                """),
                {"id_instalacion": id_instalacion},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None
