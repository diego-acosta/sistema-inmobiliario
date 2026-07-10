from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.api.core_ef_headers import CoreEFHeaders
from app.infrastructure.persistence.base_repository import BaseRepository
from app.infrastructure.persistence.repositories.outbox_repository import OutboxRepository


class CajaMovimientoNotFoundError(ValueError):
    pass


class CajaMovimientoValidationError(ValueError):
    pass


class CajaMovimientoStateError(ValueError):
    pass


class CajaMovimientoIdempotencyConflictError(ValueError):
    pass


_COLUMNS = """
    m.id_movimiento_caja, m.uid_global::text AS uid_global, m.version_registro,
    m.created_at, m.updated_at, m.deleted_at, m.id_instalacion_origen,
    m.id_instalacion_ultima_modificacion, m.op_id_alta::text AS op_id_alta,
    m.op_id_ultima_modificacion::text AS op_id_ultima_modificacion,
    m.id_apertura_caja, m.id_caja, m.id_sucursal, m.id_instalacion,
    m.id_usuario_movimiento, m.fecha_hora_movimiento, m.tipo_movimiento,
    m.concepto_movimiento, m.descripcion, m.monto, m.moneda, m.sentido,
    m.estado_movimiento, m.observaciones
"""

_PAYLOAD_FIELDS = ("id_apertura_caja", "id_caja", "id_sucursal", "id_instalacion", "id_usuario_movimiento", "fecha_hora_movimiento", "tipo_movimiento", "concepto_movimiento", "descripcion", "monto", "moneda", "sentido", "observaciones")


def _naive_utc(value: datetime) -> datetime:
    return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value


class CajaMovimientoRepository(BaseRepository[Any]):
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
        diag = getattr(getattr(exc, "orig", None), "diag", None)
        return getattr(diag, "constraint_name", None)

    def get_by_op_id_alta(self, op_id: str) -> dict[str, Any] | None:
        row = self.db.execute(text(f"SELECT {_COLUMNS} FROM caja_operativa_movimiento m WHERE m.op_id_alta = :op_id"), {"op_id": op_id}).mappings().one_or_none()
        return self._map(row) if row else None

    def _payload_matches(self, row: dict[str, Any], payload: dict[str, Any]) -> bool:
        return all(row.get(k) == payload.get(k) for k in _PAYLOAD_FIELDS)

    def _comparable_payload_for_existing(
        self, existing: dict[str, Any], normalized: dict[str, Any], core: CoreEFHeaders
    ) -> dict[str, Any] | None:
        apertura_existing = self._get_apertura(existing["id_apertura_caja"])
        if apertura_existing is None:
            return None
        return {
            **normalized,
            "id_caja": apertura_existing["id_caja"],
            "id_sucursal": apertura_existing["id_sucursal"],
            "id_instalacion": apertura_existing["id_instalacion"],
            "id_usuario_movimiento": core.x_usuario_id,
        }

    def _raise_for_atomic_insert_no_row(self, payload: dict[str, Any], core: CoreEFHeaders) -> None:
        apertura = self._get_apertura(payload["id_apertura_caja"])
        if apertura is None or apertura["deleted_at"] is not None:
            raise CajaMovimientoNotFoundError("Apertura de caja no encontrada.")
        if apertura["estado_apertura"] != "ABIERTA" or apertura["fecha_hora_cierre"] is not None:
            raise CajaMovimientoStateError("La apertura de caja no está vigente.")
        if apertura["estado_caja"] != "ACTIVA":
            raise CajaMovimientoStateError("Caja operativa inactiva o dada de baja.")
        if int(apertura["id_sucursal"]) != core.x_sucursal_id or int(apertura["id_instalacion"]) != core.x_instalacion_id:
            raise CajaMovimientoValidationError("La apertura no pertenece al contexto sucursal/instalación informado.")
        if payload["moneda"] != apertura["moneda"]:
            raise CajaMovimientoValidationError("La moneda del movimiento debe coincidir con la moneda de la apertura.")
        if payload["fecha_hora_movimiento"] < apertura["fecha_hora_apertura"]:
            raise CajaMovimientoValidationError("fecha_hora_movimiento no puede ser anterior a fecha_hora_apertura.")
        raise CajaMovimientoValidationError("No se pudo registrar el movimiento por estado inconsistente de la apertura.")

    def _get_apertura(self, id_apertura_caja: int) -> dict[str, Any] | None:
        row = self.db.execute(text("""
            SELECT a.id_apertura_caja, a.id_caja, a.id_sucursal, a.id_instalacion,
                   a.fecha_hora_apertura, a.fecha_hora_cierre, a.estado_apertura,
                   a.deleted_at, a.moneda, c.estado_caja
            FROM caja_operativa_apertura a
            JOIN caja_operativa c ON c.id_caja = a.id_caja
            WHERE a.id_apertura_caja = :id_apertura_caja
        """), {"id_apertura_caja": id_apertura_caja}).mappings().one_or_none()
        return dict(row) if row else None

    def _validate(self, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any]:
        apertura = self._get_apertura(payload["id_apertura_caja"])
        if apertura is None or apertura["deleted_at"] is not None:
            raise CajaMovimientoNotFoundError("Apertura de caja no encontrada.")
        if apertura["estado_apertura"] != "ABIERTA" or apertura["fecha_hora_cierre"] is not None:
            raise CajaMovimientoStateError("La apertura de caja no está vigente.")
        if apertura["estado_caja"] != "ACTIVA":
            raise CajaMovimientoStateError("Caja operativa inactiva o dada de baja.")
        if int(apertura["id_sucursal"]) != core.x_sucursal_id or int(apertura["id_instalacion"]) != core.x_instalacion_id:
            raise CajaMovimientoValidationError("La apertura no pertenece al contexto sucursal/instalación informado.")
        if payload["moneda"] != apertura["moneda"]:
            raise CajaMovimientoValidationError("La moneda del movimiento debe coincidir con la moneda de la apertura.")
        if payload["fecha_hora_movimiento"] < apertura["fecha_hora_apertura"]:
            raise CajaMovimientoValidationError("fecha_hora_movimiento no puede ser anterior a fecha_hora_apertura.")
        if (payload["tipo_movimiento"] == "INGRESO" and payload["sentido"] != "ENTRADA") or (payload["tipo_movimiento"] == "EGRESO" and payload["sentido"] != "SALIDA"):
            raise CajaMovimientoValidationError("tipo_movimiento y sentido son incoherentes.")
        return apertura

    def create(self, id_apertura_caja: int, payload: dict[str, Any], core: CoreEFHeaders) -> dict[str, Any]:
        op_id = str(core.x_op_id)
        normalized = {**payload, "id_apertura_caja": id_apertura_caja, "fecha_hora_movimiento": _naive_utc(payload["fecha_hora_movimiento"])}
        existing = self.get_by_op_id_alta(op_id)
        if existing:
            compare = self._comparable_payload_for_existing(existing, normalized, core)
            if compare is None or not self._payload_matches(existing, compare):
                raise CajaMovimientoIdempotencyConflictError("El X-Op-Id ya fue usado con un payload incompatible.")
            return existing
        self._validate(normalized, core)
        values = {
            **normalized,
            "id_usuario_movimiento": core.x_usuario_id,
            "id_instalacion_contexto": core.x_instalacion_id,
            "x_sucursal_id": core.x_sucursal_id,
            "x_instalacion_id": core.x_instalacion_id,
            "op_id": op_id,
        }
        try:
            row = self.db.execute(text(f"""
                INSERT INTO caja_operativa_movimiento (
                    id_apertura_caja, id_caja, id_sucursal, id_instalacion,
                    id_usuario_movimiento, fecha_hora_movimiento, tipo_movimiento,
                    concepto_movimiento, descripcion, monto, moneda, sentido,
                    estado_movimiento, observaciones, version_registro,
                    id_instalacion_origen, id_instalacion_ultima_modificacion,
                    op_id_alta, op_id_ultima_modificacion
                )
                SELECT
                    a.id_apertura_caja, a.id_caja, a.id_sucursal, a.id_instalacion,
                    :id_usuario_movimiento, :fecha_hora_movimiento, :tipo_movimiento,
                    :concepto_movimiento, :descripcion, :monto, :moneda, :sentido,
                    'REGISTRADO', :observaciones, 1,
                    :id_instalacion_contexto, :id_instalacion_contexto, :op_id, :op_id
                FROM caja_operativa_apertura a
                JOIN caja_operativa c ON c.id_caja = a.id_caja
                WHERE a.id_apertura_caja = :id_apertura_caja
                  AND a.deleted_at IS NULL
                  AND a.estado_apertura = 'ABIERTA'
                  AND a.fecha_hora_cierre IS NULL
                  AND c.estado_caja = 'ACTIVA'
                  AND a.id_sucursal = :x_sucursal_id
                  AND a.id_instalacion = :x_instalacion_id
                  AND a.moneda = :moneda
                  AND :fecha_hora_movimiento >= a.fecha_hora_apertura
                RETURNING id_movimiento_caja
            """), values).mappings().one_or_none()
            if row is None:
                self.db.rollback()
                self._raise_for_atomic_insert_no_row(normalized, core)
            created = self.get(row["id_movimiento_caja"])
            OutboxRepository(self.db).add_event(event_type="caja_operativa_movimiento_registrado", aggregate_type="caja_operativa_movimiento", aggregate_id=created["id_movimiento_caja"], payload={**created, "op_id": op_id}, occurred_at=datetime.now(UTC), status="PENDING", processing_reason={"source": "SRV-OPE-010", "issue": "#255"}, processing_metadata={"refs": ["#248"], "evt": "EVT-OPE-017"})
            self.db.commit()
            return created
        except IntegrityError as exc:
            self.db.rollback()
            if self._constraint_name(exc) == "ux_caja_operativa_movimiento_op_id_alta":
                existing = self.get_by_op_id_alta(op_id)
                if existing:
                    compare = self._comparable_payload_for_existing(existing, normalized, core)
                    if compare is not None and self._payload_matches(existing, compare):
                        return existing
                raise CajaMovimientoIdempotencyConflictError("El X-Op-Id ya fue usado con un payload incompatible.")
            raise
        except Exception:
            self.db.rollback()
            raise

    def list_by_apertura(self, id_apertura_caja: int, **filters: Any) -> list[dict[str, Any]]:
        return self.list_general(id_apertura_caja=id_apertura_caja, **filters)

    def list_general(self, **filters: Any) -> list[dict[str, Any]]:
        where = ["m.deleted_at IS NULL"]
        params = {}
        for key in ("id_sucursal", "id_instalacion", "id_caja", "id_apertura_caja", "tipo_movimiento", "sentido", "estado_movimiento"):
            if filters.get(key) is not None:
                where.append(f"m.{key} = :{key}")
                params[key] = filters[key]
        if filters.get("fecha_desde") is not None:
            where.append("m.fecha_hora_movimiento >= :fecha_desde")
            params["fecha_desde"] = _naive_utc(filters["fecha_desde"])
        if filters.get("fecha_hasta") is not None:
            where.append("m.fecha_hora_movimiento <= :fecha_hasta")
            params["fecha_hasta"] = _naive_utc(filters["fecha_hasta"])
        rows = self.db.execute(text(f"SELECT {_COLUMNS} FROM caja_operativa_movimiento m WHERE {' AND '.join(where)} ORDER BY m.fecha_hora_movimiento, m.id_movimiento_caja"), params).mappings().all()
        return [self._map(r) for r in rows]

    def get(self, id_movimiento_caja: int) -> dict[str, Any] | None:
        row = self.db.execute(text(f"SELECT {_COLUMNS} FROM caja_operativa_movimiento m WHERE m.id_movimiento_caja = :id AND m.deleted_at IS NULL"), {"id": id_movimiento_caja}).mappings().one_or_none()
        return self._map(row) if row else None
