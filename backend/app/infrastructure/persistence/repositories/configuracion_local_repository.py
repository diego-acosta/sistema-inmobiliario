from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.base_repository import BaseRepository
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)


class ConfiguracionLocalNotFoundError(ValueError):
    pass


class ConfiguracionLocalValidationError(ValueError):
    pass


class ConfiguracionLocalDuplicateActiveError(ValueError):
    pass


class ConfiguracionLocalIdempotencyConflictError(ValueError):
    pass


class ConfiguracionLocalConcurrencyError(ValueError):
    pass


_COLUMNS = """
    id_configuracion_local,
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
    clave_configuracion,
    valor_configuracion,
    tipo_valor,
    descripcion,
    estado_configuracion
"""

_PAYLOAD_FIELDS = (
    "id_sucursal",
    "id_instalacion",
    "clave_configuracion",
    "valor_configuracion",
    "tipo_valor",
    "descripcion",
    "estado_configuracion",
)


class ConfiguracionLocalRepository(BaseRepository[Any]):
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
            raise ConfiguracionLocalNotFoundError(
                "Sucursal no encontrada o dada de baja."
            )
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
            raise ConfiguracionLocalNotFoundError(
                "Instalación no encontrada o dada de baja."
            )
        if int(instalacion) != int(id_sucursal):
            raise ConfiguracionLocalValidationError(
                "La instalación no pertenece a la sucursal informada."
            )

    def list(self, *, id_sucursal: int, id_instalacion: int) -> list[dict[str, Any]]:
        self._validate_context(id_sucursal, id_instalacion)
        rows = (
            self.db.execute(
                text(f"""
                SELECT {_COLUMNS}
                FROM configuracion_local
                WHERE id_sucursal = :id_sucursal
                  AND id_instalacion = :id_instalacion
                  AND deleted_at IS NULL
                  AND estado_configuracion = 'ACTIVA'
                ORDER BY clave_configuracion
            """),
                {"id_sucursal": id_sucursal, "id_instalacion": id_instalacion},
            )
            .mappings()
            .all()
        )
        return [self._map(row) for row in rows]

    def get(self, id_configuracion_local: int) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(f"""
                SELECT {_COLUMNS}
                FROM configuracion_local
                WHERE id_configuracion_local = :id_configuracion_local
                  AND deleted_at IS NULL
            """),
                {"id_configuracion_local": id_configuracion_local},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(
                    f"SELECT {_COLUMNS} FROM configuracion_local WHERE op_id_alta = :op_id"
                ),
                {"op_id": op_id},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def get_active_by_key(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(f"""
                SELECT {_COLUMNS}
                FROM configuracion_local
                WHERE id_sucursal = :id_sucursal
                  AND id_instalacion = :id_instalacion
                  AND clave_configuracion = :clave_configuracion
                  AND deleted_at IS NULL
                  AND estado_configuracion = 'ACTIVA'
            """),
                payload,
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    @staticmethod
    def _outbox_payload(row: dict[str, Any], *, op_id: str) -> dict[str, Any]:
        return {**row, "op_id": op_id}

    def _add_outbox(
        self, *, row: dict[str, Any], event_type: str, op_id: str, evt: str
    ) -> None:
        OutboxRepository(self.db).add_event(
            event_type=event_type,
            aggregate_type="configuracion_local",
            aggregate_id=row["id_configuracion_local"],
            payload=self._outbox_payload(row, op_id=op_id),
            occurred_at=datetime.now(UTC),
            status="PENDING",
            processing_reason={"source": "SRV-OPE-007", "issue": "#252"},
            processing_metadata={"refs": ["#248"], "evt": evt},
        )

    def create(self, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any]:
        op_id = str(core.x_op_id)
        existing_op = self.get_by_op_id_alta(op_id)
        if existing_op is not None:
            if not self._payload_matches(existing_op, payload):
                raise ConfiguracionLocalIdempotencyConflictError(
                    "El X-Op-Id ya fue usado con un payload incompatible."
                )
            return existing_op
        self._validate_context(payload["id_sucursal"], payload["id_instalacion"])
        if self.get_active_by_key(payload) is not None:
            raise ConfiguracionLocalDuplicateActiveError(
                "Ya existe una configuración local activa para esa clave y contexto."
            )
        try:
            row = (
                self.db.execute(
                    text(f"""
                    INSERT INTO configuracion_local (
                        id_sucursal, id_instalacion, clave_configuracion,
                        valor_configuracion, tipo_valor, descripcion,
                        estado_configuracion, version_registro,
                        id_instalacion_origen, id_instalacion_ultima_modificacion,
                        op_id_alta, op_id_ultima_modificacion
                    ) VALUES (
                        :id_sucursal, :id_instalacion, :clave_configuracion,
                        :valor_configuracion, :tipo_valor, :descripcion,
                        :estado_configuracion, 1,
                        :id_instalacion_contexto, :id_instalacion_contexto,
                        :op_id, :op_id
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
            self._add_outbox(
                row=created,
                event_type="configuracion_local_creada",
                op_id=op_id,
                evt="EVT-OPE-012",
            )
            self.db.commit()
            return created
        except IntegrityError:
            self.db.rollback()
            raise ConfiguracionLocalDuplicateActiveError(
                "Ya existe una configuración local activa para esa clave y contexto."
            )

    def update(
        self,
        id_configuracion_local: int,
        payload: dict[str, Any],
        core: CoreEFHeaders,
        if_match_version: int,
    ) -> dict[str, Any]:
        current = self.get(id_configuracion_local)
        if current is None:
            raise ConfiguracionLocalNotFoundError("Configuración local no encontrada.")
        if current["version_registro"] != if_match_version:
            raise ConfiguracionLocalConcurrencyError(
                "If-Match-Version no coincide con version_registro."
            )
        self._validate_context(payload["id_sucursal"], payload["id_instalacion"])
        duplicate = self.get_active_by_key(payload)
        if (
            duplicate is not None
            and duplicate["id_configuracion_local"] != id_configuracion_local
        ):
            raise ConfiguracionLocalDuplicateActiveError(
                "Ya existe una configuración local activa para esa clave y contexto."
            )
        row = (
            self.db.execute(
                text(f"""
                UPDATE configuracion_local
                SET id_sucursal = :id_sucursal,
                    id_instalacion = :id_instalacion,
                    clave_configuracion = :clave_configuracion,
                    valor_configuracion = :valor_configuracion,
                    tipo_valor = :tipo_valor,
                    descripcion = :descripcion,
                    estado_configuracion = :estado_configuracion,
                    version_registro = version_registro + 1,
                    updated_at = CURRENT_TIMESTAMP,
                    id_instalacion_ultima_modificacion = :id_instalacion_contexto,
                    op_id_ultima_modificacion = :op_id
                WHERE id_configuracion_local = :id_configuracion_local
                  AND version_registro = :if_match_version
                  AND deleted_at IS NULL
                RETURNING {_COLUMNS}
            """),
                {
                    **payload,
                    "id_configuracion_local": id_configuracion_local,
                    "if_match_version": if_match_version,
                    "id_instalacion_contexto": core.x_instalacion_id,
                    "op_id": str(core.x_op_id),
                },
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            raise ConfiguracionLocalConcurrencyError(
                "If-Match-Version no coincide con version_registro."
            )
        updated = self._map(row)
        self._add_outbox(
            row=updated,
            event_type="configuracion_local_modificada",
            op_id=str(core.x_op_id),
            evt="EVT-OPE-013",
        )
        self.db.commit()
        return updated
