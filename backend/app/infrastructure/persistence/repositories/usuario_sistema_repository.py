from datetime import UTC, datetime
from typing import Any

from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.base_repository import BaseRepository
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)
from sqlalchemy import text


class UsuarioIdempotencyConflictError(ValueError):
    pass


class UsuarioConcurrencyError(ValueError):
    pass


_USUARIO_COLUMNS = """
    id_usuario,
    uid_global,
    codigo_usuario,
    login,
    email,
    estado_usuario,
    fecha_alta,
    fecha_baja,
    fecha_ultimo_acceso,
    usuario_sistema_interno,
    observaciones,
    version_registro,
    updated_at,
    deleted_at,
    id_instalacion_origen,
    id_instalacion_ultima_modificacion,
    op_id_alta,
    op_id_ultima_modificacion
"""

_PAYLOAD_FIELDS = (
    "codigo_usuario",
    "login",
    "email",
    "estado_usuario",
    "usuario_sistema_interno",
    "observaciones",
)


class UsuarioSistemaRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    @staticmethod
    def _map(row: Any) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _payload_matches(row: dict[str, Any], payload: dict[str, Any]) -> bool:
        for field in _PAYLOAD_FIELDS:
            if row.get(field) != payload.get(field):
                return False
        return True

    @staticmethod
    def _portable_datetime(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            if value.tzinfo is not None:
                value = value.astimezone(UTC).replace(tzinfo=None)
            return value.isoformat()
        return str(value)

    @classmethod
    def portable_snapshot(cls, row: dict[str, Any]) -> dict[str, Any]:
        """Proyección funcional portable de ``usuario``; excluye estado de auth local."""
        return {
            "codigo_usuario": row["codigo_usuario"],
            "login": row["login"],
            "email": row["email"],
            "estado_usuario": row["estado_usuario"],
            "usuario_sistema_interno": row["usuario_sistema_interno"],
            "observaciones": row["observaciones"],
            "fecha_alta": cls._portable_datetime(row["fecha_alta"]),
            "fecha_baja": cls._portable_datetime(row["fecha_baja"]),
            "deleted": row["deleted_at"] is not None,
        }

    def _installation_uid(self, id_instalacion: int | None) -> str:
        if id_instalacion is None:
            raise RuntimeError("SYNC_INSTALLATION_PROVENANCE_REQUIRED")
        uid = self.db.execute(
            text(
                "SELECT uid_global::text FROM instalacion "
                "WHERE id_instalacion = :id_instalacion"
            ),
            {"id_instalacion": id_instalacion},
        ).scalar_one_or_none()
        if uid is None:
            raise RuntimeError("SYNC_INSTALLATION_PROVENANCE_REQUIRED")
        return str(uid)

    def portable_outbox_payload(
        self, row: dict[str, Any], *, op_id: str
    ) -> dict[str, Any]:
        """Envelope emitible sin PK remota, credenciales, sesiones ni último acceso."""
        op_id_alta = row.get("op_id_alta")
        installation_uid = self._installation_uid(
            row.get("id_instalacion_ultima_modificacion")
        )
        return {
            "aggregate_uid": str(row["uid_global"]),
            "version_registro": row["version_registro"],
            "op_id": op_id,
            "provenance": {
                "installation_uid": installation_uid,
                "op_id_alta": str(op_id_alta) if op_id_alta is not None else None,
            },
            "snapshot": self.portable_snapshot(row),
        }

    def _emit_sync_event(
        self, *, event_type: str, row: dict[str, Any], op_id: str
    ) -> None:
        OutboxRepository(self.db).add_event(
            event_type=event_type,
            aggregate_type="usuario",
            aggregate_id=row["id_usuario"],
            payload=self.portable_outbox_payload(row, op_id=op_id),
            occurred_at=datetime.now(UTC),
        )

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        statement = text(
            f"""
            SELECT {_USUARIO_COLUMNS}
            FROM usuario
            WHERE op_id_alta = :op_id
            """
        )
        row = self.db.execute(statement, {"op_id": op_id}).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def get_by_codigo_exact(self, codigo_usuario: str) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(
                    f"SELECT {_USUARIO_COLUMNS} FROM usuario WHERE codigo_usuario = :codigo"
                ),
                {"codigo": codigo_usuario},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def get_by_login_exact(self, login: str) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(f"SELECT {_USUARIO_COLUMNS} FROM usuario WHERE login = :login"),
                {"login": login},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def get_by_uid_global(self, uid_global: str) -> dict[str, Any] | None:
        """Resuelve una identidad portable a la fila local, incluidas bajas lógicas."""
        row = (
            self.db.execute(
                text(f"SELECT {_USUARIO_COLUMNS} FROM usuario WHERE uid_global = :uid"),
                {"uid": uid_global},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def get_by_codigo_exact_for_update(
        self, codigo_usuario: str
    ) -> dict[str, Any] | None:
        row = (
            self.db.execute(
                text(
                    f"SELECT {_USUARIO_COLUMNS} FROM usuario "
                    "WHERE codigo_usuario = :codigo FOR UPDATE"
                ),
                {"codigo": codigo_usuario},
            )
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def create(self, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any]:
        op_id = str(core.x_op_id)
        existing = self.get_by_op_id_alta(op_id)
        if existing is not None:
            if not self._payload_matches(existing, payload):
                raise UsuarioIdempotencyConflictError(
                    "El X-Op-Id ya fue usado con un payload incompatible."
                )
            return existing

        statement = text(
            f"""
            INSERT INTO usuario (
                codigo_usuario,
                login,
                email,
                estado_usuario,
                usuario_sistema_interno,
                observaciones,
                version_registro,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion
            )
            VALUES (
                :codigo_usuario,
                :login,
                :email,
                :estado_usuario,
                :usuario_sistema_interno,
                :observaciones,
                1,
                :id_instalacion,
                :id_instalacion,
                :op_id,
                :op_id
            )
            RETURNING {_USUARIO_COLUMNS}
            """
        )
        values = {
            **payload,
            "id_instalacion": core.x_instalacion_id,
            "op_id": op_id,
        }
        try:
            row = self._map(self.db.execute(statement, values).mappings().one())
            self._emit_sync_event(event_type="usuario_creado", row=row, op_id=op_id)
            self.db.commit()
            return row
        except Exception:
            self.db.rollback()
            raise

    def list(self, *, incluir_bajas: bool = False) -> list[dict[str, Any]]:
        baja_filter = "" if incluir_bajas else "WHERE deleted_at IS NULL"
        statement = text(
            f"""
            SELECT {_USUARIO_COLUMNS}
            FROM usuario
            {baja_filter}
            ORDER BY id_usuario
            """
        )
        return [self._map(row) for row in self.db.execute(statement).mappings().all()]

    def get(self, id_usuario: int) -> dict[str, Any] | None:
        statement = text(
            f"""
            SELECT {_USUARIO_COLUMNS}
            FROM usuario
            WHERE id_usuario = :id_usuario
            """
        )
        row = (
            self.db.execute(statement, {"id_usuario": id_usuario})
            .mappings()
            .one_or_none()
        )
        return self._map(row) if row is not None else None

    def baja_logica(
        self,
        id_usuario: int,
        *,
        core: CoreEFHeaders,
        if_match_version: int,
    ) -> dict[str, Any] | None:
        op_id = str(core.x_op_id)
        actual = self.get(id_usuario)
        if actual is None:
            return None

        if (
            str(actual.get("op_id_ultima_modificacion")) == op_id
            and actual.get("deleted_at") is not None
        ):
            return actual

        used_op_ids = {
            str(value)
            for value in (
                actual.get("op_id_alta"),
                actual.get("op_id_ultima_modificacion"),
            )
            if value is not None
        }
        if op_id in used_op_ids:
            raise UsuarioIdempotencyConflictError(
                "El X-Op-Id ya fue usado por una operación incompatible."
            )

        if actual["version_registro"] != if_match_version:
            raise UsuarioConcurrencyError("La versión del usuario no coincide.")

        statement = text(
            f"""
            UPDATE usuario
            SET estado_usuario = 'INACTIVO',
                fecha_baja = COALESCE(fecha_baja, CURRENT_TIMESTAMP),
                deleted_at = COALESCE(deleted_at, CURRENT_TIMESTAMP),
                updated_at = CURRENT_TIMESTAMP,
                id_instalacion_ultima_modificacion = :id_instalacion,
                op_id_ultima_modificacion = :op_id,
                version_registro = version_registro + 1
            WHERE id_usuario = :id_usuario
              AND version_registro = :if_match_version
            RETURNING {_USUARIO_COLUMNS}
            """
        )
        try:
            result = self.db.execute(
                statement,
                {
                    "id_usuario": id_usuario,
                    "if_match_version": if_match_version,
                    "id_instalacion": core.x_instalacion_id,
                    "op_id": op_id,
                },
            ).mappings().one_or_none()
            if result is None:
                self.db.rollback()
                raise UsuarioConcurrencyError("La versión del usuario no coincide.")
            row = self._map(result)
            self._emit_sync_event(
                event_type="usuario_desactivado", row=row, op_id=op_id
            )
            self.db.commit()
            return row
        except Exception:
            self.db.rollback()
            raise

    def create_remote_snapshot(
        self,
        *,
        uid_global: str,
        version_registro: int,
        snapshot: dict[str, Any],
        op_id_alta: str | None,
        op_id_ultima_modificacion: str,
    ) -> dict[str, Any]:
        """Inserta snapshot remoto preservando UID/versión; no confirma transacción."""
        statement = text(
            f"""
            INSERT INTO usuario (
                uid_global,
                codigo_usuario,
                login,
                email,
                estado_usuario,
                fecha_alta,
                fecha_baja,
                usuario_sistema_interno,
                observaciones,
                version_registro,
                updated_at,
                deleted_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion
            ) VALUES (
                CAST(:uid_global AS uuid),
                :codigo_usuario,
                :login,
                :email,
                :estado_usuario,
                CAST(:fecha_alta AS timestamp),
                CAST(:fecha_baja AS timestamp),
                :usuario_sistema_interno,
                :observaciones,
                :version_registro,
                CURRENT_TIMESTAMP,
                CASE WHEN :deleted THEN CURRENT_TIMESTAMP ELSE NULL END,
                NULL,
                NULL,
                CAST(:op_id_alta AS uuid),
                CAST(:op_id_ultima_modificacion AS uuid)
            )
            RETURNING {_USUARIO_COLUMNS}
            """
        )
        row = self.db.execute(
            statement,
            {
                "uid_global": uid_global,
                "version_registro": version_registro,
                "op_id_alta": op_id_alta,
                "op_id_ultima_modificacion": op_id_ultima_modificacion,
                **snapshot,
            },
        ).mappings().one()
        return self._map(row)

    def apply_remote_snapshot_cas(
        self,
        *,
        uid_global: str,
        expected_version: int,
        incoming_version: int,
        snapshot: dict[str, Any],
        op_id: str,
    ) -> dict[str, Any] | None:
        """Aplica una versión remota mayor por CAS; no confirma ni revierte."""
        statement = text(
            f"""
            UPDATE usuario
            SET codigo_usuario = :codigo_usuario,
                login = :login,
                email = :email,
                estado_usuario = :estado_usuario,
                fecha_alta = CAST(:fecha_alta AS timestamp),
                fecha_baja = CAST(:fecha_baja AS timestamp),
                usuario_sistema_interno = :usuario_sistema_interno,
                observaciones = :observaciones,
                deleted_at = CASE
                    WHEN :deleted THEN COALESCE(deleted_at, CURRENT_TIMESTAMP)
                    ELSE NULL
                END,
                updated_at = CURRENT_TIMESTAMP,
                op_id_ultima_modificacion = CAST(:op_id AS uuid),
                version_registro = :incoming_version
            WHERE uid_global = CAST(:uid_global AS uuid)
              AND version_registro = :expected_version
            RETURNING {_USUARIO_COLUMNS}
            """
        )
        row = self.db.execute(
            statement,
            {
                "uid_global": uid_global,
                "expected_version": expected_version,
                "incoming_version": incoming_version,
                "op_id": op_id,
                **snapshot,
            },
        ).mappings().one_or_none()
        return self._map(row) if row is not None else None
