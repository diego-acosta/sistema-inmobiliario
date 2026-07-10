from datetime import UTC, datetime, time
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.base_repository import BaseRepository
from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository


class CajaAperturaNotFoundError(ValueError):
    pass


class CajaAperturaValidationError(ValueError):
    pass


class CajaAperturaDuplicateOpenError(ValueError):
    pass


class CajaAperturaIdempotencyConflictError(ValueError):
    pass


class CajaAperturaConcurrencyError(ValueError):
    pass


_COLUMNS = """
    a.id_apertura_caja,
    a.uid_global::text AS uid_global,
    a.version_registro,
    a.created_at,
    a.updated_at,
    a.deleted_at,
    a.id_instalacion_origen,
    a.id_instalacion_ultima_modificacion,
    a.op_id_alta::text AS op_id_alta,
    a.op_id_ultima_modificacion::text AS op_id_ultima_modificacion,
    a.id_caja,
    a.id_sucursal,
    a.id_instalacion,
    a.id_usuario_apertura,
    a.id_usuario_cierre,
    a.fecha_hora_apertura,
    a.fecha_hora_cierre,
    a.saldo_inicial,
    a.saldo_declarado_cierre,
    a.moneda,
    a.estado_apertura,
    a.observaciones_apertura,
    a.observaciones_cierre,
    c.codigo_caja,
    c.nombre_caja
"""

_PAYLOAD_FIELDS = (
    "id_caja",
    "id_sucursal",
    "id_instalacion",
    "fecha_hora_apertura",
    "saldo_inicial",
    "moneda",
    "observaciones_apertura",
)


def _naive_utc(value: datetime) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(UTC).replace(tzinfo=None)
    return value


def _now_naive_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CajaAperturaRepository(BaseRepository[Any]):
    def __init__(self, session) -> None:
        super().__init__(session)
        self.db = self.session

    @staticmethod
    def _map(row: Any) -> dict[str, Any]:
        data = dict(row)
        for key, value in list(data.items()):
            if isinstance(value, Decimal):
                data[key] = float(value)
        return data

    @staticmethod
    def _constraint_name(exc: IntegrityError) -> str | None:
        orig = getattr(exc, "orig", None)
        diag = getattr(orig, "diag", None)
        return getattr(diag, "constraint_name", None)

    def _validate_context(self, *, id_caja: int, id_sucursal: int, id_instalacion: int) -> None:
        sucursal = self.db.execute(text("""
            SELECT estado_sucursal FROM sucursal
            WHERE id_sucursal = :id_sucursal AND deleted_at IS NULL
        """), {"id_sucursal": id_sucursal}).scalar()
        if sucursal is None:
            raise CajaAperturaNotFoundError("Sucursal no encontrada.")
        if sucursal != "ACTIVA":
            raise CajaAperturaValidationError("Sucursal inactiva o dada de baja.")
        instalacion = self.db.execute(text("""
            SELECT id_sucursal, estado_instalacion FROM instalacion
            WHERE id_instalacion = :id_instalacion AND deleted_at IS NULL
        """), {"id_instalacion": id_instalacion}).mappings().one_or_none()
        if instalacion is None:
            raise CajaAperturaNotFoundError("Instalación no encontrada.")
        if instalacion["estado_instalacion"] != "ACTIVA":
            raise CajaAperturaValidationError("Instalación inactiva o dada de baja.")
        if int(instalacion["id_sucursal"]) != int(id_sucursal):
            raise CajaAperturaValidationError("La instalación no pertenece a la sucursal informada.")
        caja = self.db.execute(text("""
            SELECT id_sucursal, id_instalacion, estado_caja FROM caja_operativa
            WHERE id_caja = :id_caja AND deleted_at IS NULL
        """), {"id_caja": id_caja}).mappings().one_or_none()
        if caja is None:
            raise CajaAperturaNotFoundError("Caja operativa no encontrada.")
        if caja["estado_caja"] != "ACTIVA":
            raise CajaAperturaValidationError("Caja operativa inactiva o dada de baja.")
        if int(caja["id_sucursal"]) != int(id_sucursal) or int(caja["id_instalacion"]) != int(id_instalacion):
            raise CajaAperturaValidationError("La caja no pertenece a la sucursal/instalación informada.")

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        row = self.db.execute(text(f"""
            SELECT {_COLUMNS}
            FROM caja_operativa_apertura a
            JOIN caja_operativa c ON c.id_caja = a.id_caja
            WHERE a.op_id_alta = :op_id
        """), {"op_id": op_id}).mappings().one_or_none()
        return self._map(row) if row else None

    def _payload_matches(self, row: dict[str, Any], payload: dict[str, Any]) -> bool:
        return all(row.get(field) == payload.get(field) for field in _PAYLOAD_FIELDS)

    def _get_by_id(self, id_apertura_caja: int) -> dict[str, Any] | None:
        row = self.db.execute(text(f"""
            SELECT {_COLUMNS}
            FROM caja_operativa_apertura a
            JOIN caja_operativa c ON c.id_caja = a.id_caja
            WHERE a.id_apertura_caja = :id_apertura_caja
              AND a.deleted_at IS NULL
        """), {"id_apertura_caja": id_apertura_caja}).mappings().one_or_none()
        return self._map(row) if row else None

    def get_vigente_by_caja(self, id_caja: int) -> dict[str, Any] | None:
        row = self.db.execute(text(f"""
            SELECT {_COLUMNS}
            FROM caja_operativa_apertura a
            JOIN caja_operativa c ON c.id_caja = a.id_caja
            WHERE a.id_caja = :id_caja AND a.deleted_at IS NULL
              AND a.estado_apertura = 'ABIERTA' AND a.fecha_hora_cierre IS NULL
        """), {"id_caja": id_caja}).mappings().one_or_none()
        return self._map(row) if row else None

    def create(self, id_caja: int, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any]:
        op_id = str(core.x_op_id)
        normalized = {**payload, "id_caja": id_caja, "fecha_hora_apertura": _naive_utc(payload["fecha_hora_apertura"])}
        existing_op = self.get_by_op_id_alta(op_id)
        if existing_op:
            if not self._payload_matches(existing_op, normalized):
                raise CajaAperturaIdempotencyConflictError("El X-Op-Id ya fue usado con un payload incompatible.")
            return existing_op
        self._validate_context(id_caja=id_caja, id_sucursal=normalized["id_sucursal"], id_instalacion=normalized["id_instalacion"])
        if self.get_vigente_by_caja(id_caja):
            raise CajaAperturaDuplicateOpenError("Ya existe una apertura vigente para la caja operativa.")
        try:
            row = self.db.execute(text(f"""
                INSERT INTO caja_operativa_apertura (
                    id_caja, id_sucursal, id_instalacion, id_usuario_apertura,
                    fecha_hora_apertura, saldo_inicial, moneda, observaciones_apertura,
                    version_registro, id_instalacion_origen,
                    id_instalacion_ultima_modificacion, op_id_alta,
                    op_id_ultima_modificacion
                ) VALUES (
                    :id_caja, :id_sucursal, :id_instalacion, :id_usuario_apertura,
                    :fecha_hora_apertura, :saldo_inicial, :moneda, :observaciones_apertura,
                    1, :id_instalacion_contexto, :id_instalacion_contexto, :op_id, :op_id
                ) RETURNING *
            """), {**normalized, "id_usuario_apertura": core.x_usuario_id, "id_instalacion_contexto": core.x_instalacion_id, "op_id": op_id}).mappings().one()
            created = self.get_by_op_id_alta(str(row["op_id_alta"]))
            OutboxRepository(self.db).add_event(
                event_type="caja_operativa_abierta",
                aggregate_type="caja_operativa_apertura",
                aggregate_id=created["id_apertura_caja"],
                payload={**created, "op_id": op_id},
                occurred_at=datetime.now(UTC),
                status="PENDING",
                processing_reason={"source": "SRV-OPE-009", "issue": "#254"},
                processing_metadata={"refs": ["#248"], "evt": "EVT-OPE-015"},
            )
            self.db.commit()
            return created
        except IntegrityError as exc:
            self.db.rollback()
            name = self._constraint_name(exc)
            if name == "ux_caja_operativa_apertura_op_id_alta":
                existing = self.get_by_op_id_alta(op_id)
                if existing and self._payload_matches(existing, normalized):
                    return existing
                raise CajaAperturaIdempotencyConflictError("El X-Op-Id ya fue usado con un payload incompatible.")
            if name == "ux_caja_operativa_apertura_vigente_caja":
                raise CajaAperturaDuplicateOpenError("Ya existe una apertura vigente para la caja operativa.")
            raise
        except Exception:
            self.db.rollback()
            raise

    def cerrar(self, id_apertura_caja: int, payload: dict[str, Any], core: CoreEFHeaders, if_match_version: int) -> dict[str, Any]:
        cierre = (
            _naive_utc(payload["fecha_hora_cierre"])
            if payload.get("fecha_hora_cierre") is not None
            else _now_naive_utc()
        )
        actual = self._get_by_id(id_apertura_caja)
        if actual is None:
            raise CajaAperturaNotFoundError("Apertura de caja no encontrada.")
        if actual["estado_apertura"] != "ABIERTA" or actual["fecha_hora_cierre"] is not None:
            raise CajaAperturaDuplicateOpenError("La apertura de caja ya está cerrada o no está vigente.")
        if int(actual["version_registro"]) != int(if_match_version):
            raise CajaAperturaConcurrencyError("If-Match-Version no coincide con version_registro.")
        if cierre < actual["fecha_hora_apertura"]:
            raise CajaAperturaValidationError("fecha_hora_cierre no puede ser anterior a fecha_hora_apertura.")
        try:
            updated_row = self.db.execute(text(f"""
                WITH updated AS (
                    UPDATE caja_operativa_apertura
                    SET fecha_hora_cierre = :fecha_hora_cierre,
                        saldo_declarado_cierre = :saldo_declarado_cierre,
                        observaciones_cierre = :observaciones_cierre,
                        id_usuario_cierre = :id_usuario_cierre,
                        estado_apertura = 'CERRADA',
                        updated_at = CURRENT_TIMESTAMP,
                        version_registro = version_registro + 1,
                        id_instalacion_ultima_modificacion = :id_instalacion_ultima_modificacion,
                        op_id_ultima_modificacion = :op_id
                    WHERE id_apertura_caja = :id_apertura_caja
                      AND version_registro = :if_match_version
                      AND deleted_at IS NULL
                      AND estado_apertura = 'ABIERTA'
                      AND fecha_hora_cierre IS NULL
                    RETURNING *
                )
                SELECT
                    a.id_apertura_caja,
                    a.uid_global::text AS uid_global,
                    a.version_registro,
                    a.created_at,
                    a.updated_at,
                    a.deleted_at,
                    a.id_instalacion_origen,
                    a.id_instalacion_ultima_modificacion,
                    a.op_id_alta::text AS op_id_alta,
                    a.op_id_ultima_modificacion::text AS op_id_ultima_modificacion,
                    a.id_caja,
                    a.id_sucursal,
                    a.id_instalacion,
                    a.id_usuario_apertura,
                    a.id_usuario_cierre,
                    a.fecha_hora_apertura,
                    a.fecha_hora_cierre,
                    a.saldo_inicial,
                    a.saldo_declarado_cierre,
                    a.moneda,
                    a.estado_apertura,
                    a.observaciones_apertura,
                    a.observaciones_cierre,
                    c.codigo_caja,
                    c.nombre_caja
                FROM updated a
                JOIN caja_operativa c ON c.id_caja = a.id_caja
            """), {
                "id_apertura_caja": id_apertura_caja,
                "if_match_version": if_match_version,
                "fecha_hora_cierre": cierre,
                "saldo_declarado_cierre": payload["saldo_declarado_cierre"],
                "observaciones_cierre": payload.get("observaciones_cierre"),
                "id_usuario_cierre": core.x_usuario_id,
                "id_instalacion_ultima_modificacion": core.x_instalacion_id,
                "op_id": str(core.x_op_id),
            }).mappings().one_or_none()
            if updated_row is None:
                self.db.rollback()
                current = self._get_by_id(id_apertura_caja)
                if current is None:
                    raise CajaAperturaNotFoundError("Apertura de caja no encontrada.")
                if current["estado_apertura"] != "ABIERTA" or current["fecha_hora_cierre"] is not None:
                    raise CajaAperturaDuplicateOpenError("La apertura de caja ya está cerrada o no está vigente.")
                if int(current["version_registro"]) != int(if_match_version):
                    raise CajaAperturaConcurrencyError("If-Match-Version no coincide con version_registro.")
                raise CajaAperturaValidationError("No se pudo cerrar la apertura de caja por estado inconsistente.")
            updated = self._map(updated_row)
            OutboxRepository(self.db).add_event(
                event_type="caja_operativa_cerrada",
                aggregate_type="caja_operativa_apertura",
                aggregate_id=id_apertura_caja,
                payload={**updated, "op_id": str(core.x_op_id)},
                occurred_at=datetime.now(UTC),
                status="PENDING",
                processing_reason={"source": "SRV-OPE-009", "issue": "#254"},
                processing_metadata={"refs": ["#248"], "evt": "EVT-OPE-016"},
            )
            self.db.commit()
            return updated
        except Exception:
            self.db.rollback()
            raise

    def list_vigentes(self, *, id_sucursal: int | None = None, id_instalacion: int | None = None, abiertas_desde_antes_de: datetime | None = None, solo_abiertas_de_dias_anteriores: bool = False) -> list[dict[str, Any]]:
        where = ["a.deleted_at IS NULL", "a.estado_apertura = 'ABIERTA'", "a.fecha_hora_cierre IS NULL"]
        params: dict[str, Any] = {}
        if id_sucursal is not None:
            where.append("a.id_sucursal = :id_sucursal")
            params["id_sucursal"] = id_sucursal
        if id_instalacion is not None:
            where.append("a.id_instalacion = :id_instalacion")
            params["id_instalacion"] = id_instalacion
        if abiertas_desde_antes_de is not None:
            where.append("a.fecha_hora_apertura < :abiertas_desde_antes_de")
            params["abiertas_desde_antes_de"] = _naive_utc(abiertas_desde_antes_de)
        if solo_abiertas_de_dias_anteriores:
            where.append("a.fecha_hora_apertura < :inicio_hoy")
            params["inicio_hoy"] = datetime.combine(datetime.now(UTC).date(), time.min)
        rows = self.db.execute(text(f"""
            SELECT {_COLUMNS}
            FROM caja_operativa_apertura a JOIN caja_operativa c ON c.id_caja = a.id_caja
            WHERE {' AND '.join(where)}
            ORDER BY a.fecha_hora_apertura, a.id_apertura_caja
        """), params).mappings().all()
        return [self._map(row) for row in rows]
