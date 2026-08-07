from __future__ import annotations

import pytest

from app.application.common.synchronization_policy import (
    InvalidSyncAggregate,
    PROHIBITED_SYNC_AGGREGATES,
    SYNC_EVENT_POLICIES,
    SensitiveSyncPayload,
    SyncDispatchError,
    UnknownSyncEvent,
    sanitize_sync_error,
    validate_sync_event,
    validate_no_sensitive_sync_data,
)
from app.application.financiero.services.inbox_event_dispatcher import InboxEventDispatcher
from app.application.integration.outbox_to_inbox_worker import _validate_payload


@pytest.mark.parametrize("policy", SYNC_EVENT_POLICIES.values())
def test_allowlist_acepta_contrato_y_rechaza_aggregate_y_secreto(policy) -> None:
    payload = {field: 1 for field in policy.required_positive_int_fields}
    assert validate_sync_event(policy.event_type, policy.aggregate_type, payload) == policy
    with pytest.raises(InvalidSyncAggregate):
        validate_sync_event(policy.event_type, "aggregate_incorrecto", payload)
    with pytest.raises(SensitiveSyncPayload):
        validate_sync_event(policy.event_type, policy.aggregate_type, {**payload, "password": "sentinel"})


def test_evento_desconocido_y_aggregates_locales_se_rechazan() -> None:
    with pytest.raises(UnknownSyncEvent):
        validate_sync_event("evento_no_registrado", "venta", {})
    assert PROHIBITED_SYNC_AGGREGATES == {"credencial_usuario", "sesion_usuario"}
    for aggregate in PROHIBITED_SYNC_AGGREGATES:
        with pytest.raises(InvalidSyncAggregate):
            validate_sync_event("venta_confirmada", aggregate, {"id_venta": 1})


@pytest.mark.parametrize("key", ["hash_credencial", "token_sesion", "password", "refresh_token", "hash_token"])
def test_payload_sensible_anidado_se_rechaza(key: str) -> None:
    with pytest.raises(SensitiveSyncPayload):
        validate_sync_event("venta_confirmada", "venta", {"id_venta": 1, "data": [{key.upper(): "sentinel"}]})


def test_algoritmo_hash_solo_se_rechaza_en_contexto_credencial() -> None:
    validate_sync_event("venta_confirmada", "venta", {"id_venta": 1, "algoritmo_hash": "legitimo"})
    with pytest.raises(SensitiveSyncPayload):
        validate_sync_event("venta_confirmada", "venta", {"id_venta": 1, "data": {"tipo_credencial": "PASSWORD", "algoritmo_hash": "argon2id:v1"}})


@pytest.mark.parametrize(
    "projection",
    [
        {"data": {"tipo_credencial": "PASSWORD", "identificador_credencial": "admin"}},
        {"estado_credencial": "ACTIVA"},
    ],
)
def test_proyecciones_parciales_de_credencial_se_rechazan(projection) -> None:
    with pytest.raises(SensitiveSyncPayload):
        validate_sync_event(
            "venta_confirmada", "venta", {"id_venta": 1, **projection}
        )


def test_validador_auxiliar_acepta_none_y_recorre_colecciones() -> None:
    validate_no_sensitive_sync_data(None)
    with pytest.raises(SensitiveSyncPayload):
        validate_no_sensitive_sync_data(({"nested": [{"TOKEN_SESION": "secret"}]},))


def test_worker_y_dispatcher_fallan_cerrado_para_desconocidos() -> None:
    with pytest.raises(UnknownSyncEvent):
        _validate_payload("evento_no_registrado", {})
    with pytest.raises(UnknownSyncEvent):
        InboxEventDispatcher(object()).dispatch("evento_no_registrado", {})


def test_dispatcher_detecta_evento_permitido_sin_handler() -> None:
    with pytest.raises(SyncDispatchError):
        InboxEventDispatcher(object()).dispatch("sucursal_creada", {})


def test_error_de_publicacion_se_sanitiza() -> None:
    raw = RuntimeError("postgresql://usuario:password@host/db SELECT sentinel")
    assert sanitize_sync_error(raw) == "SYNC_PUBLISH_FAILED"
    assert "password" not in sanitize_sync_error(raw)
