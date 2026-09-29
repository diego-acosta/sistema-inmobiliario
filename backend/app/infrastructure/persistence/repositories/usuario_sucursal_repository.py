from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.base_repository import BaseRepository
from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository


class UsuarioSucursalIdempotencyConflictError(ValueError):
    pass


class UsuarioSucursalDuplicateActiveError(ValueError):
    pass


class UsuarioSucursalIneligibleTargetError(ValueError):
    pass


class UsuarioSucursalTechnicalError(RuntimeError):
    pass


_COLUMNS = """
    us.id_usuario_sucursal,
    us.uid_global::text AS uid_global,
    us.id_usuario,
    us.id_sucursal,
    us.tipo_habilitacion_sucursal,
    us.es_sucursal_predeterminada,
    us.puede_operar,
    us.puede_consultar,
    us.puede_administrar,
    us.fecha_desde,
    us.fecha_hasta,
    us.estado_vinculo,
    us.observaciones,
    us.version_registro,
    us.created_at,
    us.updated_at,
    us.deleted_at,
    us.id_instalacion_origen,
    us.id_instalacion_ultima_modificacion,
    us.op_id_alta::text AS op_id_alta,
    us.op_id_ultima_modificacion::text AS op_id_ultima_modificacion,
    s.codigo_sucursal,
    s.nombre_sucursal,
    s.estado_sucursal
"""

_PAYLOAD_FIELDS = (
    "id_usuario",
    "id_sucursal",
    "tipo_habilitacion_sucursal",
    "es_sucursal_predeterminada",
    "puede_operar",
    "puede_consultar",
    "puede_administrar",
    "fecha_desde",
    "fecha_hasta",
    "observaciones",
)


class UsuarioSucursalRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    @staticmethod
    def _map(row: Any) -> dict[str, Any]:
        return dict(row)

    @staticmethod
    def _payload_matches(row: dict[str, Any], payload: dict[str, Any]) -> bool:
        return all(row.get(field) == payload.get(field) for field in _PAYLOAD_FIELDS)

    def exists_usuario(self, id_usuario: int) -> bool:
        return bool(self.db.execute(text("""
            SELECT 1 FROM usuario
            WHERE id_usuario = :id_usuario
              AND deleted_at IS NULL
              AND fecha_baja IS NULL
        """), {"id_usuario": id_usuario}).scalar())

    def exists_sucursal(self, id_sucursal: int) -> bool:
        return bool(self.db.execute(text("""
            SELECT 1 FROM sucursal
            WHERE id_sucursal = :id_sucursal
              AND deleted_at IS NULL
              AND fecha_baja IS NULL
        """), {"id_sucursal": id_sucursal}).scalar())

    def get(self, id_usuario_sucursal: int) -> dict[str, Any] | None:
        row = self.db.execute(text(f"""
            SELECT {_COLUMNS}
            FROM usuario_sucursal us
            JOIN sucursal s ON s.id_sucursal = us.id_sucursal
            WHERE us.id_usuario_sucursal = :id_usuario_sucursal
        """), {"id_usuario_sucursal": id_usuario_sucursal}).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        row = self.db.execute(text(f"""
            SELECT {_COLUMNS}
            FROM usuario_sucursal us
            JOIN sucursal s ON s.id_sucursal = us.id_sucursal
            WHERE us.op_id_alta = :op_id
        """), {"op_id": op_id}).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def get_active_by_usuario_sucursal(self, id_usuario: int, id_sucursal: int) -> dict[str, Any] | None:
        row = self.db.execute(text(f"""
            SELECT {_COLUMNS}
            FROM usuario_sucursal us
            JOIN sucursal s ON s.id_sucursal = us.id_sucursal
            WHERE us.id_usuario = :id_usuario
              AND us.id_sucursal = :id_sucursal
              AND us.deleted_at IS NULL
              AND us.estado_vinculo = 'ACTIVO'
              AND us.fecha_hasta IS NULL
        """), {"id_usuario": id_usuario, "id_sucursal": id_sucursal}).mappings().one_or_none()
        return self._map(row) if row is not None else None


    def get_active_default_by_usuario(self, id_usuario: int) -> dict[str, Any] | None:
        row = self.db.execute(text(f"""
            SELECT {_COLUMNS}
            FROM usuario_sucursal us
            JOIN sucursal s ON s.id_sucursal = us.id_sucursal
            WHERE us.id_usuario = :id_usuario
              AND us.es_sucursal_predeterminada = true
              AND us.deleted_at IS NULL
              AND us.estado_vinculo = 'ACTIVO'
              AND us.fecha_hasta IS NULL
        """), {"id_usuario": id_usuario}).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def get_current_effective_by_usuario_sucursal(
        self,
        id_usuario: int,
        id_sucursal: int,
        *,
        fecha_desde: datetime,
        fecha_hasta: datetime | None,
    ) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                f"""
                WITH current_clock AS (
                    SELECT clock_timestamp() AT TIME ZONE 'UTC' AS now_utc
                )
                SELECT {_COLUMNS}
                FROM usuario_sucursal us
                JOIN sucursal s ON s.id_sucursal = us.id_sucursal
                CROSS JOIN current_clock ct
                WHERE us.id_usuario = :id_usuario
                  AND us.id_sucursal = :id_sucursal
                  AND us.deleted_at IS NULL
                  AND us.estado_vinculo = 'ACTIVO'
                  AND us.fecha_desde <= ct.now_utc
                  AND (
                    us.fecha_hasta IS NULL
                    OR us.fecha_hasta > ct.now_utc
                  )
                  AND :fecha_desde <= ct.now_utc
                  AND (
                    CAST(:fecha_hasta AS timestamp without time zone) IS NULL
                    OR CAST(:fecha_hasta AS timestamp without time zone) > ct.now_utc
                  )
                """
            ),
            {
                "id_usuario": id_usuario,
                "id_sucursal": id_sucursal,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
            },
        ).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def get_current_effective_default_by_usuario(
        self,
        id_usuario: int,
        *,
        fecha_desde: datetime,
        fecha_hasta: datetime | None,
    ) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                f"""
                WITH current_clock AS (
                    SELECT clock_timestamp() AT TIME ZONE 'UTC' AS now_utc
                )
                SELECT {_COLUMNS}
                FROM usuario_sucursal us
                JOIN sucursal s ON s.id_sucursal = us.id_sucursal
                CROSS JOIN current_clock ct
                WHERE us.id_usuario = :id_usuario
                  AND us.es_sucursal_predeterminada = true
                  AND us.deleted_at IS NULL
                  AND us.estado_vinculo = 'ACTIVO'
                  AND us.fecha_desde <= ct.now_utc
                  AND (
                    us.fecha_hasta IS NULL
                    OR us.fecha_hasta > ct.now_utc
                  )
                  AND :fecha_desde <= ct.now_utc
                  AND (
                    CAST(:fecha_hasta AS timestamp without time zone) IS NULL
                    OR CAST(:fecha_hasta AS timestamp without time zone) > ct.now_utc
                  )
                """
            ),
            {
                "id_usuario": id_usuario,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta,
            },
        ).mappings().one_or_none()
        return self._map(row) if row is not None else None

    def has_unknown_link_state(self, id_usuario: int) -> bool:
        return bool(
            self.db.execute(
                text(
                    """
                    SELECT 1
                    FROM usuario_sucursal
                    WHERE id_usuario = :id_usuario
                      AND estado_vinculo NOT IN ('ACTIVO', 'INACTIVO')
                    LIMIT 1
                    """
                ),
                {"id_usuario": id_usuario},
            ).scalar()
        )

    def lock_usuario(self, id_usuario: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                SELECT id_usuario, estado_usuario, fecha_baja, deleted_at
                FROM usuario
                WHERE id_usuario = :id_usuario
                FOR UPDATE
                """
            ),
            {"id_usuario": id_usuario},
        ).mappings().one_or_none()
        return dict(row) if row is not None else None

    def lock_sucursal(self, id_sucursal: int) -> dict[str, Any] | None:
        row = self.db.execute(
            text(
                """
                SELECT id_sucursal, estado_sucursal, fecha_baja, deleted_at
                FROM sucursal
                WHERE id_sucursal = :id_sucursal
                FOR KEY SHARE
                """
            ),
            {"id_sucursal": id_sucursal},
        ).mappings().one_or_none()
        return dict(row) if row is not None else None

    def list_by_usuario(self, id_usuario: int, *, incluir_bajas: bool = False) -> list[dict[str, Any]] | None:
        if not self.exists_usuario(id_usuario):
            return None
        filtros = ""
        if not incluir_bajas:
            filtros = """
              AND us.deleted_at IS NULL
              AND us.estado_vinculo = 'ACTIVO'
              AND us.fecha_hasta IS NULL
              AND s.deleted_at IS NULL
              AND s.fecha_baja IS NULL
            """
        rows = self.db.execute(text(f"""
            SELECT {_COLUMNS}
            FROM usuario_sucursal us
            JOIN sucursal s ON s.id_sucursal = us.id_sucursal
            WHERE us.id_usuario = :id_usuario
            {filtros}
            ORDER BY us.es_sucursal_predeterminada DESC, us.id_usuario_sucursal
        """), {"id_usuario": id_usuario}).mappings().all()
        return [self._map(row) for row in rows]

    @staticmethod
    def _outbox_payload(row: dict[str, Any], *, op_id: str) -> dict[str, Any]:
        return {
            "id_usuario_sucursal": row["id_usuario_sucursal"],
            "uid_global": row["uid_global"],
            "id_usuario": row["id_usuario"],
            "id_sucursal": row["id_sucursal"],
            "op_id": op_id,
            "version_registro": row["version_registro"],
            "id_instalacion_origen": row["id_instalacion_origen"],
            "id_instalacion_ultima_modificacion": row["id_instalacion_ultima_modificacion"],
        }

    def _raise_or_return_idempotent_replay(self, *, op_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_by_op_id_alta(op_id)
        if existing is None:
            raise UsuarioSucursalDuplicateActiveError(
                "Ya existe un vínculo activo para el usuario y la sucursal."
            )
        if not self._payload_matches(existing, payload):
            raise UsuarioSucursalIdempotencyConflictError(
                "El X-Op-Id ya fue usado con un payload incompatible."
            )
        return existing

    def create(self, id_usuario: int, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any] | None:
        full_payload = {"id_usuario": id_usuario, **payload}
        op_id = str(core.x_op_id)
        existing = self.get_by_op_id_alta(op_id)
        if existing is not None:
            if not self._payload_matches(existing, full_payload):
                raise UsuarioSucursalIdempotencyConflictError(
                    "El X-Op-Id ya fue usado con un payload incompatible."
                )
            return existing
        if not self.exists_usuario(id_usuario) or not self.exists_sucursal(payload["id_sucursal"]):
            return None
        if self.get_active_by_usuario_sucursal(id_usuario, payload["id_sucursal"]) is not None:
            raise UsuarioSucursalDuplicateActiveError(
                "Ya existe un vínculo activo para el usuario y la sucursal."
            )
        if payload.get("es_sucursal_predeterminada") and self.get_active_default_by_usuario(id_usuario) is not None:
            raise UsuarioSucursalDuplicateActiveError(
                "Ya existe una sucursal predeterminada activa para el usuario."
            )
        try:
            row = self.db.execute(text(f"""
                INSERT INTO usuario_sucursal (
                    id_usuario, id_sucursal, tipo_habilitacion_sucursal,
                    es_sucursal_predeterminada, puede_operar, puede_consultar,
                    puede_administrar, fecha_desde, fecha_hasta, estado_vinculo,
                    observaciones, version_registro, id_instalacion_origen,
                    id_instalacion_ultima_modificacion, op_id_alta,
                    op_id_ultima_modificacion
                ) VALUES (
                    :id_usuario, :id_sucursal, :tipo_habilitacion_sucursal,
                    :es_sucursal_predeterminada, :puede_operar, :puede_consultar,
                    :puede_administrar, :fecha_desde, :fecha_hasta, 'ACTIVO',
                    :observaciones, 1, :id_instalacion, :id_instalacion,
                    :op_id, :op_id
                ) RETURNING id_usuario_sucursal
            """), {**full_payload, "id_instalacion": core.x_instalacion_id, "op_id": op_id}).mappings().one()
            created = self.get(row["id_usuario_sucursal"])
            OutboxRepository(self.db).add_event(
                event_type="usuario_asociado_a_sucursal",
                aggregate_type="usuario_sucursal",
                aggregate_id=created["id_usuario_sucursal"],
                payload=self._outbox_payload(created, op_id=op_id),
                occurred_at=datetime.now(UTC),
                status="PENDING",
                processing_reason={"source": "EVT-ADM-008", "issue": "#262"},
                processing_metadata={"refs": ["#249", "#248"]},
            )
            self.db.commit()
            return created
        except IntegrityError as exc:
            self.db.rollback()
            constraint = getattr(getattr(getattr(exc, "orig", None), "diag", None), "constraint_name", None)
            if constraint in {"ux_usuario_sucursal_op_id_alta", "ux_usuario_sucursal_activa"}:
                return self._raise_or_return_idempotent_replay(op_id=op_id, payload=full_payload)
            if constraint == "ux_usuario_sucursal_predeterminada_activa":
                raise UsuarioSucursalDuplicateActiveError(
                    "Ya existe una sucursal predeterminada activa para el usuario."
                ) from exc
            raise
        except Exception:
            self.db.rollback()
            raise

    def create_central(
        self,
        id_usuario: int,
        payload: dict[str, Any],
        *,
        op_id: str,
    ) -> dict[str, Any]:
        usuario = self.lock_usuario(id_usuario)
        if usuario is None:
            raise LookupError("usuario")
        if usuario["estado_usuario"] not in {"ACTIVO", "INACTIVO"}:
            raise UsuarioSucursalTechnicalError("estado_usuario desconocido")
        if (
            usuario["estado_usuario"] != "ACTIVO"
            or usuario["deleted_at"] is not None
            or usuario["fecha_baja"] is not None
        ):
            raise UsuarioSucursalIneligibleTargetError("usuario")

        id_sucursal = payload["id_sucursal"]
        sucursal = self.lock_sucursal(id_sucursal)
        if sucursal is None:
            raise LookupError("sucursal")
        if sucursal["estado_sucursal"] not in {
            "ACTIVA",
            "INACTIVA",
            "DADA_DE_BAJA",
        }:
            raise UsuarioSucursalTechnicalError("estado_sucursal desconocido")
        if (
            sucursal["estado_sucursal"] != "ACTIVA"
            or sucursal["deleted_at"] is not None
            or sucursal["fecha_baja"] is not None
        ):
            raise UsuarioSucursalIneligibleTargetError("sucursal")

        if self.has_unknown_link_state(id_usuario):
            raise UsuarioSucursalTechnicalError("estado_vinculo desconocido")

        if (
            self.get_active_by_usuario_sucursal(id_usuario, id_sucursal) is not None
            or self.get_current_effective_by_usuario_sucursal(
                id_usuario,
                id_sucursal,
                fecha_desde=payload["fecha_desde"],
                fecha_hasta=payload["fecha_hasta"],
            )
            is not None
        ):
            raise UsuarioSucursalDuplicateActiveError
        if (
            payload["es_sucursal_predeterminada"]
            and (
                self.get_active_default_by_usuario(id_usuario) is not None
                or self.get_current_effective_default_by_usuario(
                    id_usuario,
                    fecha_desde=payload["fecha_desde"],
                    fecha_hasta=payload["fecha_hasta"],
                )
                is not None
            )
        ):
            raise UsuarioSucursalDuplicateActiveError

        row = self.db.execute(
            text(
                """
                INSERT INTO usuario_sucursal (
                    id_usuario, id_sucursal, tipo_habilitacion_sucursal,
                    es_sucursal_predeterminada, puede_operar, puede_consultar,
                    puede_administrar, fecha_desde, fecha_hasta, estado_vinculo,
                    observaciones, version_registro, id_instalacion_origen,
                    id_instalacion_ultima_modificacion, op_id_alta,
                    op_id_ultima_modificacion
                ) VALUES (
                    :id_usuario, :id_sucursal, :tipo_habilitacion_sucursal,
                    :es_sucursal_predeterminada, :puede_operar,
                    :puede_consultar, :puede_administrar, :fecha_desde,
                    :fecha_hasta, 'ACTIVO', :observaciones, 1,
                    NULL, NULL, :op_id, :op_id
                )
                RETURNING id_usuario_sucursal
                """
            ),
            {"id_usuario": id_usuario, "op_id": op_id, **payload},
        ).mappings().one()
        created = self.get(row["id_usuario_sucursal"])
        if created is None:
            raise UsuarioSucursalTechnicalError("vínculo no recuperable")
        return created
