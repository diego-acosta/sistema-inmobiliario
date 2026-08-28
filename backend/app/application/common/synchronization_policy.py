"""Política única, default-deny, para eventos de sincronización."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


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
    _p("valor_parametro_modificado", "valor_parametro"),
    _p("calendario_comercial_creado", "calendario_comercial"),
    _p("calendario_comercial_programado", "calendario_comercial"),
    _p(
        "financiero.indexacion_cuotas_v2.corrida_aplicada",
        "corrida_indexacion_financiera",
        "id_corrida_indexacion_financiera",
    ),
)})

PROHIBITED_SYNC_AGGREGATES = frozenset({"credencial_usuario", "sesion_usuario"})
SENSITIVE_PAYLOAD_KEYS = frozenset({
    "password", "password_hash", "hash_credencial", "token", "token_sesion",
    "refresh_token", "hash_token", "authorization", "cookie", "cookies",
    "credencial_usuario", "sesion_usuario",
})
CREDENTIAL_SPECIFIC_KEYS = frozenset({
    "tipo_credencial", "identificador_credencial", "hash_credencial",
    "estado_credencial", "es_credencial_principal", "fecha_activacion",
    "fecha_vencimiento", "fecha_revocacion", "motivo_revocacion",
    "obliga_rotacion", "ultimo_cambio_credencial",
    "intentos_fallidos_acumulados", "ultimo_intento_fallido", "bloqueo_hasta",
    "requiere_reset",
})


def validate_no_sensitive_sync_data(
    value: Any, *, credential_context: bool = False
) -> None:
    """Rechaza material sensible anidado sin incluir sus valores en errores."""
    if value is None:
        return
    if isinstance(value, dict):
        keys = {str(key).strip().casefold() for key in value}
        credential_markers = keys & CREDENTIAL_SPECIFIC_KEYS
        if keys & (SENSITIVE_PAYLOAD_KEYS | CREDENTIAL_SPECIFIC_KEYS) or (
            "algoritmo_hash" in keys
            and (credential_context or bool(credential_markers))
        ):
            raise SensitiveSyncPayload(SensitiveSyncPayload.code)
        nested_context = credential_context or bool(keys & credential_markers)
        for child in value.values():
            validate_no_sensitive_sync_data(child, credential_context=nested_context)
    elif isinstance(value, (list, tuple)):
        for child in value:
            validate_no_sensitive_sync_data(child, credential_context=credential_context)


def validate_sync_event(event_type: str, aggregate_type: str, payload: Any) -> SyncEventPolicy:
    policy = SYNC_EVENT_POLICIES.get(event_type)
    if policy is None:
        raise UnknownSyncEvent(UnknownSyncEvent.code)
    if aggregate_type in PROHIBITED_SYNC_AGGREGATES or aggregate_type != policy.aggregate_type:
        raise InvalidSyncAggregate(InvalidSyncAggregate.code)
    if not isinstance(payload, dict):
        raise SensitiveSyncPayload("SYNC_PAYLOAD_INVALID")
    validate_no_sensitive_sync_data(payload)
    for field in policy.required_positive_int_fields:
        value = payload.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise SensitiveSyncPayload("SYNC_PAYLOAD_INVALID")
    return policy


def validate_retained_sync_envelope(
    *, event_type: str, aggregate_type: str, payload: Any,
    provenance: Any, op_id: Any = None, aggregate_uid: Any = None,
    version_registro: Any = None,
) -> bool:
    """Valida todo envelope retenido; preserva el claim legacy payload-less."""
    retained = any(value is not None for value in (
        op_id, payload, provenance, aggregate_uid, version_registro,
    ))
    if retained:
        validate_sync_event(event_type, aggregate_type, payload)
        validate_no_sensitive_sync_data(provenance)
    return retained


def sanitize_sync_error(
    exc: BaseException | str, *, preserve_invalid_payload: bool = False
) -> str:
    if preserve_invalid_payload and (
        exc in {"SYNC_INVALID_PAYLOAD", "SYNC_PAYLOAD_INVALID"}
        or (
            isinstance(exc, SensitiveSyncPayload)
            and exc.args in {
                ("SYNC_INVALID_PAYLOAD",),
                ("SYNC_PAYLOAD_INVALID",),
            }
        )
    ):
        return "SYNC_PAYLOAD_INVALID"
    if isinstance(exc, str) and exc in {
        "SYNC_POLICY_REJECTED", "SYNC_EVENT_NOT_ALLOWED",
        "SYNC_AGGREGATE_NOT_ALLOWED", "SYNC_SENSITIVE_PAYLOAD",
        "SYNC_DISPATCH_FAILED", "SYNC_PUBLISH_FAILED",
    }:
        return exc
    if isinstance(exc, SynchronizationPolicyError):
        return exc.code
    if isinstance(exc, SyncDispatchError):
        return exc.code
    return "SYNC_PUBLISH_FAILED"
