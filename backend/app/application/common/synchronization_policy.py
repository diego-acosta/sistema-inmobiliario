"""Política única, default-deny, para eventos de sincronización."""
from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping


class SynchronizationPolicyError(RuntimeError):
    code = "SYNC_POLICY_REJECTED"


class UnknownSyncEvent(SynchronizationPolicyError):
    code = "SYNC_EVENT_NOT_ALLOWED"


class InvalidSyncAggregate(SynchronizationPolicyError):
    code = "SYNC_AGGREGATE_NOT_ALLOWED"


class SensitiveSyncPayload(SynchronizationPolicyError):
    code = "SYNC_SENSITIVE_PAYLOAD"


class SyncDispatchError(RuntimeError):
    code = "SYNC_DISPATCH_FAILED"


@dataclass(frozen=True, slots=True)
class SyncEventPolicy:
    event_type: str
    aggregate_type: str
    required_positive_int_fields: tuple[str, ...] = ()


def _p(event: str, aggregate: str, *required: str) -> SyncEventPolicy:
    return SyncEventPolicy(event, aggregate, required)


# Inventario de contratos emitidos por callers runtime de OutboxRepository.add_event.
SYNC_EVENT_POLICIES: Mapping[str, SyncEventPolicy] = MappingProxyType({p.event_type: p for p in (
    _p("catalogo_maestro_creado", "catalogo_maestro"), _p("catalogo_maestro_modificado", "catalogo_maestro"),
    _p("catalogo_maestro_desactivado", "catalogo_maestro"), _p("item_catalogo_creado", "item_catalogo"),
    _p("item_catalogo_modificado", "item_catalogo"), _p("item_catalogo_estado_cambiado", "item_catalogo"),
    _p("item_catalogo_desactivado", "item_catalogo"), _p("sucursal_creada", "sucursal"),
    _p("instalacion_creada", "instalacion"), _p("configuracion_local_creada", "configuracion_local"),
    _p("configuracion_local_modificada", "configuracion_local"), _p("rol_asignado_a_usuario", "usuario_rol_seguridad"),
    _p("rol_revocado_de_usuario", "usuario_rol_seguridad"), _p("usuario_asociado_a_sucursal", "usuario_sucursal"),
    _p("caja_operativa_creada", "caja_operativa"), _p("caja_operativa_abierta", "caja_operativa_apertura"),
    _p("caja_operativa_cerrada", "caja_operativa_apertura"),
    _p("caja_operativa_movimiento_registrado", "caja_operativa_movimiento"),
    _p("venta_confirmada", "venta", "id_venta"), _p("escrituracion_registrada", "venta", "id_venta"),
    _p("contrato_alquiler_activado", "contrato_alquiler", "id_contrato_alquiler"),
    _p("entrega_locativa_registrada", "contrato_alquiler"),
    _p("restitucion_locativa_registrada", "contrato_alquiler"),
    _p("reserva_locativa_confirmada", "reserva_locativa"),
)})

PROHIBITED_SYNC_AGGREGATES = frozenset({"credencial_usuario", "sesion_usuario"})
SENSITIVE_PAYLOAD_KEYS = frozenset({
    "password", "password_hash", "hash_credencial", "token", "token_sesion",
    "refresh_token", "hash_token", "authorization", "cookie", "cookies",
    "credencial_usuario", "sesion_usuario",
})


def _validate_sensitive_keys(value: Any, *, credential_context: bool = False) -> None:
    if isinstance(value, dict):
        keys = {str(key).strip().casefold() for key in value}
        credential_markers = {"tipo_credencial", "identificador_credencial"}
        if keys & SENSITIVE_PAYLOAD_KEYS or (
            "algoritmo_hash" in keys
            and (credential_context or bool(keys & credential_markers))
        ):
            raise SensitiveSyncPayload(SensitiveSyncPayload.code)
        nested_context = credential_context or bool(keys & credential_markers)
        for child in value.values():
            _validate_sensitive_keys(child, credential_context=nested_context)
    elif isinstance(value, (list, tuple)):
        for child in value:
            _validate_sensitive_keys(child, credential_context=credential_context)


def validate_sync_event(event_type: str, aggregate_type: str, payload: Any) -> SyncEventPolicy:
    policy = SYNC_EVENT_POLICIES.get(event_type)
    if policy is None:
        raise UnknownSyncEvent(UnknownSyncEvent.code)
    if aggregate_type in PROHIBITED_SYNC_AGGREGATES or aggregate_type != policy.aggregate_type:
        raise InvalidSyncAggregate(InvalidSyncAggregate.code)
    if not isinstance(payload, dict):
        raise SensitiveSyncPayload("SYNC_INVALID_PAYLOAD")
    _validate_sensitive_keys(payload)
    for field in policy.required_positive_int_fields:
        value = payload.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise SensitiveSyncPayload("SYNC_INVALID_PAYLOAD")
    return policy


def sanitize_sync_error(exc: BaseException) -> str:
    if isinstance(exc, SynchronizationPolicyError):
        return exc.code
    if isinstance(exc, SyncDispatchError):
        return exc.code
    return "SYNC_PUBLISH_FAILED"
