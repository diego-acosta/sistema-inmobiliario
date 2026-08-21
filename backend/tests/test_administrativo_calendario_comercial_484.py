from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime
import threading
import time
from unittest.mock import patch
from uuid import uuid4, uuid5

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.authentication import get_authenticated_principal
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
)
from app.api.core_ef_headers import TechnicalCoreEFHeaders
from app.application.administrativo.services.bootstrap_calendario_comercial_service import (
    BootstrapCalendarioComercialError,
    BootstrapCalendarioComercialService,
    COMMAND_CODE,
    TARGET_KEY,
    TARGET_TYPE,
)
from app.application.common.idempotency import (
    OperationCompletion,
    canonical_payload_hash,
    complete_operation,
)
from app.config.database import engine

ENDPOINT = "/api/v1/administrativo/configuracion/calendario-comercial"
PAYLOAD = {"dia_cierre_comercial": 20,
           "dia_vencimiento_predeterminado_cuotas": 10,
           "vigente_desde": "2026-09-01"}


@pytest.fixture(autouse=True)
def _preserve_root_identity_sequence(db_session):
    sequence = db_session.execute(text(
        "SELECT pg_get_serial_sequence('configuracion_calendario_comercial', "
        "'id_configuracion_calendario_comercial')"
    )).scalar_one()
    state = db_session.execute(text(
        "SELECT last_value, is_called FROM " + sequence
    )).one()
    yield
    db_session.execute(
        text("SELECT setval(:sequence, :value, :called)"),
        {"sequence": sequence, "value": state.last_value,
         "called": state.is_called},
    )


def _principal():
    return AuthenticatedPrincipal(
        id_usuario=1, codigo_usuario="ROL-ALTERNATIVO", login="bootstrap",
        id_sesion=uuid4(), mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=datetime.now(UTC).replace(tzinfo=None),
        id_instalacion_origen_sesion=1, id_sucursal_operativa=None)


def _headers(op_id=None):
    return {"X-Op-Id": str(op_id or uuid4()), "X-Sucursal-Id": "1",
            "X-Instalacion-Id": "1", "X-Usuario-Id": "no-participa"}


def _post(client, payload=PAYLOAD, headers=None):
    client.app.dependency_overrides[get_authenticated_principal] = _principal
    with patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService.authorize",
        return_value=AdministrativeAuthorizationDecision.GRANTED,
    ):
        return client.post(ENDPOINT, json=payload, headers=headers or {})


def _counts(db_session):
    return db_session.execute(text("""
        SELECT (SELECT count(*) FROM configuracion_calendario_comercial),
               (SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p
                 USING(id_parametro_sistema) WHERE p.codigo_parametro IN
                 ('DIA_CIERRE_COMERCIAL',
                  'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS'))
    """)).one()


def _outbox_count(db_session):
    return db_session.execute(text("""
        SELECT count(*) FROM outbox_event
         WHERE event_type='calendario_comercial_creado'
           AND aggregate_type='calendario_comercial'
    """)).scalar_one()


def _payload_hash(payload=PAYLOAD):
    return canonical_payload_hash({
        "dia_cierre_comercial": payload["dia_cierre_comercial"],
        "dia_vencimiento_predeterminado_cuotas": payload[
            "dia_vencimiento_predeterminado_cuotas"
        ],
        "vigente_desde": payload["vigente_desde"],
    })


def _receipt(db_session, op_id, *, command=COMMAND_CODE,
             target_type=TARGET_TYPE, target_key=TARGET_KEY,
             payload_hash=None):
    complete_operation(db_session, OperationCompletion(
        op_id=op_id, command_code=command, target_type=target_type,
        target_uid=None, target_key=target_key,
        payload_hash=payload_hash or _payload_hash(), canonicalization_version=1,
        result_code="TEST", result_http_status=201, result_target_uid=None,
        result_version=1, response_snapshot={"ok": True, "data": {}},
        id_usuario=1, id_sucursal=1, id_instalacion=1))
    db_session.commit()


def _insert_value(db_session, code, value="20"):
    db_session.execute(text("""
        INSERT INTO valor_parametro(id_parametro_sistema, valor_parametro,
          es_valor_vigente, fecha_desde)
        SELECT id_parametro_sistema, :value, true, DATE '2026-09-01'
          FROM parametro_sistema WHERE codigo_parametro=:code
    """), {"code": code, "value": value})


def _assert_not_fecha_efectiva(response):
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "fecha_efectiva" not in body["error_message"]
    assert "fecha_efectiva" not in str(body["details"])
    assert "input" not in body["details"]


def _assert_header_error(response, header, reason):
    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"] == {"header": header, "reason": reason}


def test_bootstrap_y_replay_durable_sin_efectos_adicionales(client, db_session):
    op_id = uuid4()
    first = _post(client, headers=_headers(op_id))
    assert first.status_code == 201
    assert first.json()["data"]["estado"] == "COMPLETA"
    assert _counts(db_session) == (1, 2)
    assert _outbox_count(db_session) == 1
    child_ops = dict(db_session.execute(text("""
        SELECT p.codigo_parametro, v.op_id_alta
          FROM valor_parametro v JOIN parametro_sistema p
            USING(id_parametro_sistema)
         WHERE p.codigo_parametro IN
          ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
    """)).all())
    assert child_ops == {code: uuid5(op_id, code) for code in child_ops}
    assert len(set(child_ops.values())) == 2
    replay = _post(client, headers={**_headers(op_id), "X-Sucursal-Id": "999999"})
    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert _counts(db_session) == (1, 2)
    assert _outbox_count(db_session) == 1


def test_outbox_agregado_portable_y_hash_determinista(client, db_session):
    op_id = uuid4()
    assert _post(client, headers=_headers(op_id)).status_code == 201
    event = db_session.execute(text("""
        SELECT event_type, aggregate_type, aggregate_id, status, payload
          FROM outbox_event WHERE event_type='calendario_comercial_creado'
    """)).mappings().one()
    assert (event["event_type"], event["aggregate_type"], event["status"]) == (
        "calendario_comercial_creado", "calendario_comercial", "PENDING")
    payload = event["payload"]
    data = payload["data"]
    metadata = payload["metadata"]
    assert data["op_id"] == str(op_id)
    assert data["version_agregada"] == 1
    assert data["vigente_desde"] == "2026-09-01"
    assert data["fecha_hasta"] is None
    assert data["dia_cierre_comercial"] == 20
    assert data["dia_vencimiento_predeterminado_cuotas"] == 10
    assert data["valor_dia_cierre_comercial"]["version_registro"] == 1
    assert data["valor_dia_vencimiento_predeterminado_cuotas"][
        "version_registro"
    ] == 1
    assert "id_configuracion_calendario_comercial" not in str(payload)
    assert "id_valor_parametro" not in str(payload)
    expected = canonical_payload_hash({
        "metadata": {"uid_instalacion_origen": metadata["uid_instalacion_origen"]},
        "data": data,
    })
    assert metadata["payload_hash"] == expected
    assert len(expected) == 64 and expected == expected.lower()


def test_bootstrap_payload_conflict(client, db_session):
    op_id = uuid4()
    assert _post(client, headers=_headers(op_id)).status_code == 201
    changed = {**PAYLOAD, "dia_cierre_comercial": 21}
    response = _post(client, changed, _headers(op_id))
    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert _counts(db_session) == (1, 2)
    assert _outbox_count(db_session) == 1


@pytest.mark.parametrize(
    ("stored", "expected"),
    [
        ({"command": "OTHER", "target_type": "OTHER", "target_key": "OTHER",
          "payload_hash": "b" * 64}, "IDEMPOTENCY_COMMAND_CONFLICT"),
        ({"target_type": "OTHER", "target_key": "OTHER",
          "payload_hash": "b" * 64}, "IDEMPOTENCY_TARGET_CONFLICT"),
    ],
)
def test_precedencia_conflicto_command_target_payload(client, db_session,
                                                       stored, expected):
    op_id = uuid4()
    _receipt(db_session, op_id, **stored)
    response = _post(client, headers=_headers(op_id))
    assert response.status_code == 409
    assert response.json()["error_code"] == expected
    assert _counts(db_session) == (0, 0)
    assert _outbox_count(db_session) == 0


def test_estado_parcial_no_se_repara(client, db_session):
    db_session.execute(text("INSERT INTO configuracion_calendario_comercial DEFAULT VALUES"))
    db_session.commit()
    response = _post(client, headers=_headers())
    assert response.status_code == 409
    assert response.json()["error_code"] == "CONFIGURACION_CALENDARIO_COMERCIAL_CONFLICTO"
    assert _counts(db_session) == (1, 0)
    assert _outbox_count(db_session) == 0


@pytest.mark.parametrize("state", [
    "UN_VALOR", "DOS_VALORES", "RAIZ_UN_VALOR", "COMPLETO", "RAIZ_HISTORICA",
])
def test_estados_previos_no_se_reparan(client, db_session, state):
    if state in {"RAIZ_UN_VALOR", "COMPLETO", "RAIZ_HISTORICA"}:
        db_session.execute(text(
            "INSERT INTO configuracion_calendario_comercial DEFAULT VALUES"))
    if state == "RAIZ_HISTORICA":
        db_session.execute(text(
            "UPDATE configuracion_calendario_comercial SET deleted_at=CURRENT_TIMESTAMP"))
    if state in {"UN_VALOR", "DOS_VALORES", "RAIZ_UN_VALOR", "COMPLETO"}:
        _insert_value(db_session, "DIA_CIERRE_COMERCIAL")
    if state in {"DOS_VALORES", "COMPLETO"}:
        _insert_value(db_session, "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS", "10")
    db_session.commit()
    before = _counts(db_session)
    response = _post(client, headers=_headers())
    assert response.status_code == 409
    assert _counts(db_session) == before
    assert _outbox_count(db_session) == 0


def test_headers_y_openapi(client):
    response = _post(client)
    _assert_header_error(response, "X-Op-Id", "requerido faltante")
    operation = client.get("/openapi.json").json()["paths"][ENDPOINT]["post"]
    parameters = operation["parameters"]
    pairs = [(parameter["name"], parameter["in"]) for parameter in parameters]
    assert len(pairs) == len(set(pairs))
    calendar_headers = [item for item in parameters if item["in"] == "header"]
    assert len(calendar_headers) == 3
    expected = {
        ("X-Op-Id", "header"),
        ("X-Sucursal-Id", "header"),
        ("X-Instalacion-Id", "header"),
    }
    assert {(item["name"], item["in"]) for item in calendar_headers} == expected
    assert all(item["required"] is True for item in calendar_headers)
    assert all(pairs.count(pair) == 1 for pair in expected)
    assert ("X-Usuario-Id", "header") not in pairs
    assert ("If-Match-Version", "header") not in pairs
    request_schema = client.get("/openapi.json").json()["components"]["schemas"][
        "BootstrapCalendarioComercialRequest"
    ]
    assert "vigente_desde" in request_schema["required"]
    assert request_schema["properties"]["vigente_desde"] == {
        "type": "string",
        "format": "date",
        "title": "Vigente Desde",
    }


@pytest.mark.parametrize("missing", ["X-Op-Id", "X-Sucursal-Id", "X-Instalacion-Id"])
def test_post_header_faltante_sanitizado(client, missing):
    headers = _headers()
    headers.pop(missing)
    _assert_header_error(
        _post(client, headers=headers), missing, "requerido faltante"
    )


@pytest.mark.parametrize(
    ("header", "value"),
    [
        ("X-Op-Id", "no-es-uuid"),
        ("X-Sucursal-Id", "abc"),
        ("X-Sucursal-Id", "0"),
        ("X-Instalacion-Id", "abc"),
        ("X-Instalacion-Id", "0"),
    ],
)
def test_post_header_invalido_pasa_por_parser_core_ef(client, header, value):
    headers = _headers()
    headers[header] = value
    _assert_header_error(_post(client, headers=headers), header, "inválido")


def test_dias_son_enteros_estrictos_y_fecha_explicita(client):
    for invalid in (0, 32, 1.5, "20", True, None):
        response = _post(client, {**PAYLOAD, "dia_cierre_comercial": invalid}, _headers())
        assert response.status_code == 422
        _assert_not_fecha_efectiva(response)
    for payload in (
        {k: v for k, v in PAYLOAD.items() if k != "vigente_desde"},
        {**PAYLOAD, "vigente_desde": "fecha-invalida"},
    ):
        _assert_not_fecha_efectiva(_post(client, payload, _headers()))


@pytest.mark.parametrize(
    "invalid",
    [
        0,
        1,
        0.0,
        True,
        False,
        None,
        [],
        {},
        "20260901",
        "2026-9-1",
        "2026-09-1",
        "2026-9-01",
        "2026/09/01",
        "01-09-2026",
        "2026-09-01T00:00:00",
        "2026-09-01T12:30:00",
        "2026-09-01Z",
        "2026-W36-2",
        "2026-244",
        "2026-02-30",
    ],
)
def test_vigente_desde_rechaza_coerciones_sin_efectos(
    client, db_session, invalid
):
    op_id = uuid4()
    response = _post(
        client, {**PAYLOAD, "vigente_desde": invalid}, _headers(op_id)
    )
    assert response.status_code == 422
    _assert_not_fecha_efectiva(response)
    assert _counts(db_session) == (0, 0)
    assert _outbox_count(db_session) == 0
    assert db_session.execute(
        text("SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"),
        {"op": op_id},
    ).scalar_one() == 0


def test_get_sin_fecha_preserva_error_contractual_483(client):
    client.app.dependency_overrides[get_authenticated_principal] = _principal
    with patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService.authorize",
        return_value=AdministrativeAuthorizationDecision.GRANTED,
    ):
        response = client.get(ENDPOINT)
    assert response.status_code == 422
    assert response.json()["error_message"].startswith("fecha_efectiva")


def test_rollback_integral_y_retry_mismo_op_id(client, db_session):
    op_id = uuid4()
    with patch(
        "app.application.administrativo.services.bootstrap_calendario_comercial_service.complete_operation",
        side_effect=RuntimeError("fallo inyectado"),
    ):
        failed = _post(client, headers=_headers(op_id))
    assert failed.status_code == 500
    assert _counts(db_session) == (0, 0)
    assert _outbox_count(db_session) == 0
    assert db_session.execute(text(
        "SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"),
        {"op": op_id}).scalar_one() == 0
    assert _post(client, headers=_headers(op_id)).status_code == 201
    assert _counts(db_session) == (1, 2)
    assert _outbox_count(db_session) == 1


def _cleanup_concurrent(op_ids):
    with engine.begin() as connection:
        connection.execute(text(
            "DELETE FROM outbox_event WHERE event_type='calendario_comercial_creado'"
        ))
        connection.execute(text("""
            DELETE FROM valor_parametro v USING parametro_sistema p
             WHERE v.id_parametro_sistema=p.id_parametro_sistema
               AND p.codigo_parametro IN
                 ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
        """))
        connection.execute(text("DELETE FROM configuracion_calendario_comercial"))
        for trigger in ("trg_bud_operacion_idempotente_inmutable",
                        "trg_bt_operacion_idempotente_inmutable"):
            connection.execute(text(
                f"ALTER TABLE operacion_idempotente DISABLE TRIGGER {trigger}"))
        try:
            connection.execute(text(
                "DELETE FROM operacion_idempotente WHERE op_id=ANY(:ops)"),
                {"ops": op_ids})
        finally:
            for trigger in ("trg_bud_operacion_idempotente_inmutable",
                            "trg_bt_operacion_idempotente_inmutable"):
                connection.execute(text(
                    f"ALTER TABLE operacion_idempotente ENABLE ALWAYS TRIGGER {trigger}"))


def _concurrent_bootstrap(*, same_op):
    op_ids = [uuid4(), uuid4()]
    if same_op:
        op_ids[1] = op_ids[0]
    barrier = threading.Barrier(2)
    outcomes = []

    def run(index):
        with Session(engine) as session:
            barrier.wait()
            try:
                result = BootstrapCalendarioComercialService(session).execute(
                    dia_cierre_comercial=20,
                    dia_vencimiento_predeterminado_cuotas=10,
                    vigente_desde=date(2026, 9, 1),
                    headers=TechnicalCoreEFHeaders(op_ids[index], 1, 1),
                    id_usuario=1)
                session.commit()
                outcomes.append(("OK", result))
            except BootstrapCalendarioComercialError as exc:
                session.rollback()
                outcomes.append((exc.code, None))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run, index) for index in range(2)]
            time.sleep(0.1)
            for future in futures:
                future.result(10)
        with Session(engine) as session:
            counts = session.execute(text("""
                SELECT (SELECT count(*) FROM configuracion_calendario_comercial),
                       (SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p
                        USING(id_parametro_sistema) WHERE p.codigo_parametro IN
                        ('DIA_CIERRE_COMERCIAL','DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')),
                       (SELECT count(*) FROM operacion_idempotente WHERE op_id=ANY(:ops)),
                       (SELECT count(*) FROM outbox_event
                         WHERE event_type='calendario_comercial_creado')
            """), {"ops": list(set(op_ids))}).one()
        return outcomes, counts, op_ids
    finally:
        _cleanup_concurrent(list(set(op_ids)))


def test_concurrencia_postgres_distintos_op_id_materializa_una_vez():
    outcomes, counts, _ = _concurrent_bootstrap(same_op=False)
    assert sorted(outcome[0] for outcome in outcomes) == [
        "CONFIGURACION_CALENDARIO_COMERCIAL_CONFLICTO", "OK"]
    assert counts == (1, 2, 1, 1)


def test_concurrencia_postgres_mismo_op_id_replay_snapshot():
    outcomes, counts, _ = _concurrent_bootstrap(same_op=True)
    assert [outcome[0] for outcome in outcomes] == ["OK", "OK"]
    assert outcomes[0][1] == outcomes[1][1]
    assert counts == (1, 2, 1, 1)
