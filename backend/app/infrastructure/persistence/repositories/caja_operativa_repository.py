from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.base_repository import BaseRepository
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)


class CajaOperativaNotFoundError(ValueError):
    pass


class CajaOperativaValidationError(ValueError):
    pass


class CajaOperativaDuplicateActiveError(ValueError):
    pass


class CajaOperativaIdempotencyConflictError(ValueError):
    pass


_COLUMNS = """
    id_caja,
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
    id_instalacion,
    codigo_caja,
    nombre_caja,
    tipo_caja,
    moneda_base,
    estado_caja,
    permite_efectivo,
    permite_transferencia,
    permite_cheque,
    descripcion,
    observaciones
"""

_PAYLOAD_FIELDS = (
    "id_sucursal",
    "id_instalacion",
    "codigo_caja",
    "nombre_caja",
    "tipo_caja",
    "moneda_base",
    "estado_caja",
    "permite_efectivo",
    "permite_transferencia",
    "permite_cheque",
    "descripcion",
    "observaciones",
)


class CajaOperativaRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    @staticmethod
    def _map(row: Any) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _payload_matches(row: dict[str, Any], payload: dict[str, Any]) -> bool:
        return all(row.get(field) == payload.get(field) for field in _PAYLOAD_FIELDS)

    def _validate_context(self, id_sucursal: int, id_instalacion: int) -> None:
        sucursal = self.db.execute(
            text("""
                SELECT id_sucursal FROM sucursal
                WHERE id_sucursal = :id_sucursal
                  AND deleted_at IS NULL
                  AND estado_sucursal <> 'DADA_DE_BAJA'
            """),
            {"id_sucursal": id_sucursal},
        ).scalar()
        if not sucursal:
            raise CajaOperativaNotFoundError("Sucursal no encontrada o dada de baja.")
        instalacion = self.db.execute(
            text("""
                SELECT id_sucursal FROM instalacion
                WHERE id_instalacion = :id_instalacion
                  AND deleted_at IS NULL
                  AND estado_instalacion <> 'DADA_DE_BAJA'
            """),
            {"id_instalacion": id_instalacion},
        ).scalar()
        if instalacion is None:
            raise CajaOperativaNotFoundError(
                "Instalación no encontrada o dada de baja."
            )
        if int(instalacion) != int(id_sucursal):
            raise CajaOperativaValidationError(
                "La instalación no pertenece a la sucursal informada."
            )

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(
                    f"SELECT {_COLUMNS} FROM caja_operativa WHERE op_id_alta = :op_id"
                ),
                {"op_id": op_id},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def get_active_by_codigo(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(f"""
                SELECT {_COLUMNS}
                FROM caja_operativa
                WHERE id_sucursal = :id_sucursal
                  AND id_instalacion = :id_instalacion
                  AND codigo_caja = :codigo_caja
                  AND deleted_at IS NULL
            """),
                payload,
            )
            .mappings()
            .one_or_none()
        )
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
            raise CajaOperativaDuplicateActiveError(
                "Ya existe una caja operativa activa con ese código para la sucursal e instalación."
            )
        if not self._payload_matches(existing, payload):
            raise CajaOperativaIdempotencyConflictError(
                "El X-Op-Id ya fue usado con un payload incompatible."
            )
        return existing

    @staticmethod
    def _outbox_payload(row: dict[str, Any], *, op_id: str) -> dict[str, Any]:
        return {**row, "op_id": op_id}

    def create(self, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any]:
        op_id = str(core.x_op_id)
        existing_op = self.get_by_op_id_alta(op_id)
        if existing_op is not None:
            if not self._payload_matches(existing_op, payload):
                raise CajaOperativaIdempotencyConflictError(
                    "El X-Op-Id ya fue usado con un payload incompatible."
                )
            return existing_op
        self._validate_context(payload["id_sucursal"], payload["id_instalacion"])
        if self.get_active_by_codigo(payload) is not None:
            raise CajaOperativaDuplicateActiveError(
                "Ya existe una caja operativa activa con ese código para la sucursal e instalación."
            )
        try:
            row = (
                self.db.execute(
                    text(f"""
                    INSERT INTO caja_operativa (
                        id_sucursal, id_instalacion, codigo_caja, nombre_caja,
                        tipo_caja, moneda_base, estado_caja, permite_efectivo,
                        permite_transferencia, permite_cheque, descripcion,
                        observaciones, version_registro, id_instalacion_origen,
                        id_instalacion_ultima_modificacion, op_id_alta,
                        op_id_ultima_modificacion
                    ) VALUES (
                        :id_sucursal, :id_instalacion, :codigo_caja, :nombre_caja,
                        :tipo_caja, :moneda_base, :estado_caja, :permite_efectivo,
                        :permite_transferencia, :permite_cheque, :descripcion,
                        :observaciones, 1, :id_instalacion_contexto,
                        :id_instalacion_contexto, :op_id, :op_id
                    ) RETURNING {_COLUMNS}
                """),
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
                event_type="caja_operativa_creada",
                aggregate_type="caja_operativa",
                aggregate_id=created["id_caja"],
                payload=self._outbox_payload(created, op_id=op_id),
                occurred_at=datetime.now(UTC),
                status="PENDING",
                processing_reason={"source": "SRV-OPE-008", "issue": "#253"},
                processing_metadata={"refs": ["#248"], "evt": "EVT-OPE-014"},
            )
            self.db.commit()
            return created
        except IntegrityError as exc:
            self.db.rollback()
            constraint_name = self._constraint_name(exc)
            if constraint_name == "ux_caja_operativa_op_id_alta":
                return self._raise_or_return_idempotent_replay(
                    op_id=op_id, payload=payload
                )
            if constraint_name == "ux_caja_operativa_codigo_activa":
                raise CajaOperativaDuplicateActiveError(
                    "Ya existe una caja operativa activa con ese código para la sucursal e instalación."
                )
            raise
        except Exception:
            self.db.rollback()
            raise

    def list(
        self,
        *,
        id_sucursal: int | None = None,
        id_instalacion: int | None = None,
        estado_caja: str | None = None,
        tipo_caja: str | None = None,
    ) -> list[dict[str, Any]]:
        where = ["deleted_at IS NULL"]
        params: dict[str, Any] = {}
        if id_sucursal is not None:
            where.append("id_sucursal = :id_sucursal")
            params["id_sucursal"] = id_sucursal
        if id_instalacion is not None:
            where.append("id_instalacion = :id_instalacion")
            params["id_instalacion"] = id_instalacion
        if estado_caja:
            where.append("estado_caja = :estado_caja")
            params["estado_caja"] = estado_caja
        if tipo_caja:
            where.append("tipo_caja = :tipo_caja")
            params["tipo_caja"] = tipo_caja
        rows = (
            self.db.execute(
                text(f"""
                SELECT {_COLUMNS}
                FROM caja_operativa
                WHERE {' AND '.join(where)}
                ORDER BY id_caja, codigo_caja
            """),
                params,
            )
            .mappings()
            .all()
        )
        return [self._map(row) for row in rows]

    def get(self, id_caja: int) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(f"""
                SELECT {_COLUMNS}
                FROM caja_operativa
                WHERE id_caja = :id_caja
                  AND deleted_at IS NULL
            """),
                {"id_caja": id_caja},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None
