from __future__ import annotations

import pytest

from app.application.common.synchronization_policy import (
    PROHIBITED_SYNC_AGGREGATES,
    SYNC_EVENT_POLICIES,
    InvalidSyncAggregate,
    SensitiveSyncPayload,
    SyncDispatchError,
    UnknownSyncEvent,
    sanitize_sync_error,
    validate_no_sensitive_sync_data,
    validate_sync_event,
)
from app.application.financiero.services.inbox_event_dispatcher import (
    InboxEventDispatcher,
)
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
    invalid = SensitiveSyncPayload("SYNC_PAYLOAD_INVALID")
    assert sanitize_sync_error(invalid) == "SYNC_SENSITIVE_PAYLOAD"
    assert sanitize_sync_error(
        invalid, preserve_invalid_payload=True
    ) == "SYNC_PAYLOAD_INVALID"


def test_sanitize_sync_error_normaliza_codigo_payload_legacy():
    assert sanitize_sync_error(
        SensitiveSyncPayload("SYNC_INVALID_PAYLOAD"),
        preserve_invalid_payload=True,
    ) == "SYNC_PAYLOAD_INVALID"


@pytest.mark.parametrize("payload", [None, {}, {"id_venta": 0}])
def test_payload_invalido_usa_unico_codigo_catalogado(payload):
    with pytest.raises(SensitiveSyncPayload) as captured:
        validate_sync_event("venta_confirmada", "venta", payload)
    assert captured.value.args == ("SYNC_PAYLOAD_INVALID",)


def test_valor_parametro_modificado_policy_contract() -> None:
    payload = {
        "metadata": {
            "uid_instalacion_origen": "00000000-0000-0000-0000-000000000001",
            "payload_hash": "a" * 64,
        },
        "data": {
            "uid_global": "00000000-0000-0000-0000-000000000002",
            "codigo_parametro": "P",
            "valor_anterior": "15",
            "valor_nuevo": "16",
            "version_anterior": 1,
            "version_registro": 2,
            "op_id": "00000000-0000-0000-0000-000000000003",
        },
    }
    policy = validate_sync_event(
        "valor_parametro_modificado", "valor_parametro", payload
    )
    assert policy.required_positive_int_fields == ()
    with pytest.raises(InvalidSyncAggregate):
        validate_sync_event("valor_parametro_modificado", "parametro_sistema", payload)
    with pytest.raises(UnknownSyncEvent):
        validate_sync_event(
            "valor_parametro_modificado_desconocido", "valor_parametro", payload
        )
    with pytest.raises(SensitiveSyncPayload):
        validate_sync_event(
            "valor_parametro_modificado",
            "valor_parametro",
            {**payload, "token": "secret"},
        )


def test_calendario_comercial_creado_policy_contract() -> None:
    payload = {
        "metadata": {
            "uid_instalacion_origen": "00000000-0000-0000-0000-000000000001",
            "payload_hash": "a" * 64,
        },
        "data": {
            "uid_global": "00000000-0000-0000-0000-000000000002",
            "version_agregada": 1,
        },
    }
    policy = validate_sync_event(
        "calendario_comercial_creado", "calendario_comercial", payload
    )
    assert policy.required_positive_int_fields == ()
    with pytest.raises(InvalidSyncAggregate):
        validate_sync_event(
            "calendario_comercial_creado", "valor_parametro", payload
        )
    with pytest.raises(SensitiveSyncPayload):
        validate_sync_event(
            "calendario_comercial_creado",
            "calendario_comercial",
            {**payload, "token": "secret"},
        )
    with pytest.raises(UnknownSyncEvent):
        validate_sync_event(
            "calendario_comercial_programado", "calendario_comercial", payload
        )
