from copy import deepcopy
from datetime import UTC, datetime
from unittest.mock import patch
from urllib.parse import quote
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.api.authentication import get_authenticated_principal
from app.api.routers.administrativo_router import _validate_command_codigo
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
)
from app.application.common.idempotency import (
    IdempotencyRuntimeError,
    NonCanonicalizablePayload,
    OperationCompletion,
    UnexpectedOperationReceiptConflict,
    canonical_payload_hash,
    complete_operation,
)
from app.infrastructure.persistence.repositories.valor_parametro_global_command_repository import (
    ValorParametroGlobalCommandRepository,
)

CODE = "PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO"
ENDPOINT_TEMPLATE = "/api/v1/administrativo/configuracion/parametros/{}/valor-global"
ENDPOINT = ENDPOINT_TEMPLATE.format(CODE)


def _principal():
    return AuthenticatedPrincipal(
        id_usuario=1,
        codigo_usuario="USR-TEST",
        login="test",
        id_sesion=uuid4(),
        mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=datetime.now(UTC).replace(tzinfo=None),
        id_instalacion_origen_sesion=1,
        id_sucursal_operativa=None,
    )


def _headers(op_id=None, version=1, **overrides):
    headers = {
        "X-Op-Id": str(op_id or uuid4()),
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
        "If-Match-Version": str(version),
    }
    headers.update(overrides)
    return headers


def _grant(client):
    client.app.dependency_overrides[get_authenticated_principal] = _principal
    return patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService.authorize",
        return_value=AdministrativeAuthorizationDecision.GRANTED,
    )


def _row(db_session, code=CODE):
    return (
        db_session.execute(
            text("""
        SELECT v.id_valor_parametro, v.uid_global, v.valor_parametro,
               v.version_registro, v.updated_at, v.op_id_alta,
               v.op_id_ultima_modificacion, v.id_instalacion_origen,
               v.id_instalacion_ultima_modificacion
          FROM valor_parametro v JOIN parametro_sistema p USING(id_parametro_sistema)
         WHERE p.codigo_parametro=:code AND v.es_valor_vigente AND v.deleted_at IS NULL
    """),
            {"code": code},
        )
        .mappings()
        .one()
    )


def _effects(db_session, op_id=None):
    receipt = (
        0
        if op_id is None
        else db_session.execute(
            text("SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"),
            {"op": op_id},
        ).scalar_one()
    )
    return (
        db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one(),
        receipt,
    )


def _request(client, value, *, headers=None, endpoint=ENDPOINT):
    with _grant(client):
        return client.patch(
            endpoint, json={"valor_tipado": value}, headers=headers or {}
        )


def _seed_parameter(db_session, code, raw="15"):
    ids = db_session.execute(
        text("""
        SELECT
          (SELECT id_tipo_dato_parametro FROM tipo_dato_parametro WHERE codigo_tipo_dato='ENTERO'),
          (SELECT id_alcance_parametro FROM alcance_parametro WHERE codigo_alcance='GLOBAL')
    """)
    ).one()
    pid = db_session.execute(
        text("""
        INSERT INTO parametro_sistema(
          id_tipo_dato_parametro,id_alcance_parametro,codigo_parametro,nombre_parametro,
          exponible_api_administrativa,es_sensible,editable_administrativamente)
        VALUES (:type,:scope,:code,:code,true,false,true) RETURNING id_parametro_sistema
    """),
        {"type": ids[0], "scope": ids[1], "code": code},
    ).scalar_one()
    return (
        db_session.execute(
            text("""
        INSERT INTO valor_parametro(id_parametro_sistema,valor_parametro,es_valor_vigente)
        VALUES (:pid,:raw,true) RETURNING id_valor_parametro,uid_global,version_registro
    """),
            {"pid": pid, "raw": raw},
        )
        .mappings()
        .one()
    )


def _assert_header_error(response, header):
    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"]["header"] == header


@pytest.mark.parametrize(
    ("value", "missing"),
    [(None, True), ("not-a-uuid", False)],
    ids=["missing", "invalid"],
)
def test_x_op_id_failure_paths_before_claim(client, db_session, value, missing):
    headers = _headers()
    if missing:
        headers.pop("X-Op-Id")
    else:
        headers["X-Op-Id"] = value
    with patch(
        "app.application.administrativo.services.actualizar_valor_parametro_global_service.claim_operation"
    ) as claim:
        response = _request(client, 16, headers=headers)
    _assert_header_error(response, "X-Op-Id")
    claim.assert_not_called()
    assert _effects(db_session) == (0, 0)


@pytest.mark.parametrize(
    ("header", "value"),
    [
        ("X-Sucursal-Id", None),
        ("X-Sucursal-Id", "0"),
        ("X-Sucursal-Id", "-1"),
        ("X-Sucursal-Id", "abc"),
        ("X-Instalacion-Id", None),
        ("X-Instalacion-Id", "0"),
        ("X-Instalacion-Id", "-1"),
        ("X-Instalacion-Id", "abc"),
        ("If-Match-Version", None),
        ("If-Match-Version", "0"),
        ("If-Match-Version", "-1"),
        ("If-Match-Version", "abc"),
    ],
    ids=lambda item: str(item),
)
def test_each_required_technical_header_failure_is_identifiable(
    client, db_session, header, value
):
    headers = _headers()
    if value is None:
        headers.pop(header)
    else:
        headers[header] = value
    with patch(
        "app.application.administrativo.services.actualizar_valor_parametro_global_service.claim_operation"
    ) as claim:
        response = _request(client, 16, headers=headers)
    _assert_header_error(response, header)
    claim.assert_not_called()
    assert _effects(db_session) == (0, 0)


def test_body_strict_and_x_usuario_id_does_not_influence_identity(client):
    headers = _headers(**{"X-Usuario-Id": "999999"})
    assert _request(client, True, headers=headers).status_code == 422
    with _grant(client):
        extra = client.patch(
            ENDPOINT, json={"valor_tipado": 16, "extra": 1}, headers=headers
        )
    assert extra.status_code == 422


def test_version_mismatch_precedes_semantic_noop_and_preserves_everything(
    client, db_session
):
    before = dict(_row(db_session))
    op_id = uuid4()
    response = _request(
        client, 15, headers=_headers(op_id, before["version_registro"] + 1)
    )
    assert response.status_code == 412
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
    assert dict(_row(db_session)) == before
    assert _effects(db_session, op_id) == (0, 0)


@pytest.mark.parametrize(("raw", "requested"), [("015", 15), ("-0", 0), ("000", 0)])
def test_complete_semantic_noop_and_replay(client, db_session, raw, requested):
    db_session.execute(
        text(
            "UPDATE valor_parametro SET valor_parametro=:raw WHERE id_valor_parametro=:id"
        ),
        {"raw": raw, "id": _row(db_session)["id_valor_parametro"]},
    )
    before = dict(_row(db_session))
    op_id = uuid4()
    first = _request(
        client, requested, headers=_headers(op_id, before["version_registro"])
    )
    replay = _request(
        client, requested, headers=_headers(op_id, before["version_registro"])
    )
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert dict(_row(db_session)) == before
    assert _effects(db_session, op_id) == (0, 1)
    receipt = db_session.execute(
        text("SELECT result_code FROM operacion_idempotente WHERE op_id=:op"),
        {"op": op_id},
    ).scalar_one()
    assert receipt == "PARAMETRO_GLOBAL_SIN_CAMBIOS"


@pytest.mark.parametrize("raw", ["15.0", "+15", " 15 ", ""])
def test_invalid_persisted_integer_rolls_back_without_receipt(client, db_session, raw):
    target = _row(db_session)
    db_session.execute(
        text(
            "UPDATE valor_parametro SET valor_parametro=:raw WHERE id_valor_parametro=:id"
        ),
        {"raw": raw, "id": target["id_valor_parametro"]},
    )
    db_session.commit()
    before = dict(_row(db_session))
    op_id = uuid4()
    response = _request(client, 16, headers=_headers(op_id, before["version_registro"]))
    assert response.status_code == 500
    assert response.json()["error_code"] == "inconsistencia_parametro"
    assert dict(_row(db_session)) == before
    assert _effects(db_session, op_id) == (0, 0)


@pytest.mark.parametrize(
    "failure_target",
    [
        "app.application.administrativo.services.actualizar_valor_parametro_global_service.OutboxRepository.add_event",
        "app.application.administrativo.services.actualizar_valor_parametro_global_service.complete_operation",
    ],
)
def test_post_cas_failures_rollback_and_same_op_retry_executes(
    client, db_session, failure_target
):
    before = dict(_row(db_session))
    op_id = uuid4()
    headers = _headers(op_id, before["version_registro"])
    with patch(failure_target, side_effect=RuntimeError("SQL driver secret")):
        failed = _request(client, 16, headers=headers)
    assert failed.status_code == 500
    assert failed.json() == {
        "ok": False,
        "error_code": "TECHNICAL_INCONSISTENCY",
        "error_message": "No fue posible completar la operación.",
        "details": {},
    }
    assert dict(_row(db_session)) == before
    assert _effects(db_session, op_id) == (0, 0)
    retry = _request(client, 16, headers=headers)
    assert retry.status_code == 200
    assert _row(db_session)["valor_parametro"] == "16"
    assert _effects(db_session, op_id) == (1, 1)


@pytest.mark.parametrize(
    ("failure_target", "exception"),
    [
        ("canonical_payload_hash", NonCanonicalizablePayload("hash secret")),
        ("claim_operation", IdempotencyRuntimeError("claim secret")),
    ],
)
def test_idempotency_runtime_failures_are_sanitized(
    client, db_session, failure_target, exception
):
    module = "app.application.administrativo.services.actualizar_valor_parametro_global_service."
    op_id = uuid4()
    with patch(module + failure_target, side_effect=exception):
        response = _request(client, 16, headers=_headers(op_id))
    assert response.status_code == 500
    assert response.json()["error_code"] == "IDEMPOTENCY_TECHNICAL_ERROR"
    assert "secret" not in response.text
    assert _effects(db_session, op_id) == (0, 0)


def test_completion_idempotency_error_rolls_back_cas_and_outbox(client, db_session):
    before = dict(_row(db_session))
    op_id = uuid4()
    with patch(
        "app.application.administrativo.services.actualizar_valor_parametro_global_service.complete_operation",
        side_effect=UnexpectedOperationReceiptConflict("receipt secret"),
    ):
        response = _request(
            client, 16, headers=_headers(op_id, before["version_registro"])
        )
    assert response.status_code == 500
    assert response.json()["error_code"] == "IDEMPOTENCY_TECHNICAL_ERROR"
    assert "receipt" not in response.text
    assert dict(_row(db_session)) == before
    assert _effects(db_session, op_id) == (0, 0)


def test_command_target_and_payload_conflicts_precede_mutable_lookups(
    client, db_session
):
    version = _row(db_session)["version_registro"]
    command_op = uuid4()
    complete_operation(
        db_session,
        OperationCompletion(
            op_id=command_op,
            command_code="OTHER.COMMAND",
            target_type="VALOR_PARAMETRO",
            target_uid=None,
            target_key=CODE,
            payload_hash=canonical_payload_hash(
                {
                    "codigo_parametro": CODE,
                    "valor_tipado": "15",
                    "if_match_version": version,
                }
            ),
            canonicalization_version=1,
            result_code="OK",
            result_http_status=200,
            result_target_uid=None,
            result_version=None,
            response_snapshot={"ok": True},
            id_usuario=1,
            id_sucursal=1,
            id_instalacion=1,
        ),
    )
    db_session.commit()
    with patch.object(
        ValorParametroGlobalCommandRepository, "validate_context"
    ) as context:
        command = _request(client, 15, headers=_headers(command_op, version))
    assert command.json()["error_code"] == "IDEMPOTENCY_COMMAND_CONFLICT"
    context.assert_not_called()

    first_op = uuid4()
    assert _request(client, 15, headers=_headers(first_op, version)).status_code == 200
    other = "OTRO_PARAMETRO_412"
    _seed_parameter(db_session, other)
    target = _request(
        client,
        15,
        headers=_headers(first_op, version),
        endpoint=ENDPOINT_TEMPLATE.format(other),
    )
    assert target.json()["error_code"] == "IDEMPOTENCY_TARGET_CONFLICT"
    payload = _request(client, 99, headers=_headers(first_op, version))
    assert payload.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"


def test_replay_is_snapshot_only_after_mutable_state_and_context_change(
    client, db_session
):
    op_id = uuid4()
    version = _row(db_session)["version_registro"]
    original = _request(client, 15, headers=_headers(op_id, version))
    db_session.execute(
        text(
            "UPDATE parametro_sistema SET exponible_api_administrativa=false, editable_administrativamente=false WHERE codigo_parametro=:code"
        ),
        {"code": CODE},
    )
    db_session.execute(
        text(
            "UPDATE valor_parametro SET deleted_at=CURRENT_TIMESTAMP WHERE id_valor_parametro=:id"
        ),
        {"id": _row(db_session)["id_valor_parametro"]},
    )
    other_branch = db_session.execute(
        text(
            "INSERT INTO sucursal(codigo_sucursal,nombre_sucursal,estado_sucursal) "
            "VALUES ('REPLAY-412','Replay','ACTIVA') RETURNING id_sucursal"
        )
    ).scalar_one()
    db_session.execute(
        text("UPDATE instalacion SET id_sucursal=:branch WHERE id_instalacion=1"),
        {"branch": other_branch},
    )
    with (
        patch.object(
            ValorParametroGlobalCommandRepository, "validate_context"
        ) as context,
        patch.object(ValorParametroGlobalCommandRepository, "find_target") as lookup,
        patch.object(ValorParametroGlobalCommandRepository, "lock_target") as lock,
    ):
        replay = _request(client, 15, headers=_headers(op_id, version))
    assert replay.status_code == 200 and replay.json() == original.json()
    context.assert_not_called()
    lookup.assert_not_called()
    lock.assert_not_called()


@pytest.mark.parametrize(("sucursal", "instalacion"), [(999999, 1), (1, 999999)])
def test_invalid_technical_context_has_no_effects(
    client, db_session, sucursal, instalacion
):
    op_id = uuid4()
    before = dict(_row(db_session))
    response = _request(
        client,
        16,
        headers=_headers(
            op_id,
            **{"X-Sucursal-Id": str(sucursal), "X-Instalacion-Id": str(instalacion)},
        ),
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "inconsistencia_contexto_tecnico"
    assert dict(_row(db_session)) == before and _effects(db_session, op_id) == (0, 0)


def test_installation_from_other_branch_is_invalid_context(client, db_session):
    branch = db_session.execute(
        text(
            "INSERT INTO sucursal(codigo_sucursal,nombre_sucursal,estado_sucursal) VALUES ('OTRA-412','Otra','ACTIVA') RETURNING id_sucursal"
        )
    ).scalar_one()
    db_session.execute(
        text("UPDATE instalacion SET id_sucursal=:branch WHERE id_instalacion=1"),
        {"branch": branch},
    )
    op_id = uuid4()
    response = _request(client, 16, headers=_headers(op_id))
    assert (
        response.status_code == 400
        and response.json()["error_code"] == "inconsistencia_contexto_tecnico"
    )
    assert _effects(db_session, op_id) == (0, 0)


def test_material_outbox_provenance_hash_and_large_integer(client, db_session):
    target = _row(db_session)
    db_session.execute(
        text(
            "UPDATE valor_parametro SET valor_parametro='015' WHERE id_valor_parametro=:id"
        ),
        {"id": target["id_valor_parametro"]},
    )
    before = dict(_row(db_session))
    op_id = uuid4()
    large = 2**53 + 123
    first = _request(client, large, headers=_headers(op_id, before["version_registro"]))
    replay = _request(
        client, large, headers=_headers(op_id, before["version_registro"])
    )
    assert (
        first.status_code == replay.status_code == 200 and first.json() == replay.json()
    )
    after = _row(db_session)
    assert after["valor_parametro"] == str(large)
    assert after["op_id_ultima_modificacion"] == op_id
    assert after["id_instalacion_ultima_modificacion"] == 1
    assert (
        after["op_id_alta"] == before["op_id_alta"]
        and after["id_instalacion_origen"] == before["id_instalacion_origen"]
    )
    event = (
        db_session.execute(
            text(
                "SELECT * FROM outbox_event WHERE event_type='valor_parametro_modificado'"
            )
        )
        .mappings()
        .one()
    )
    assert (event["aggregate_type"], event["aggregate_id"], event["status"]) == (
        "valor_parametro",
        target["id_valor_parametro"],
        "PENDING",
    )
    data = event["payload"]["data"]
    metadata = event["payload"]["metadata"]
    assert data == {
        "uid_global": str(target["uid_global"]),
        "codigo_parametro": CODE,
        "valor_anterior": "15",
        "valor_nuevo": str(large),
        "version_anterior": before["version_registro"],
        "version_registro": after["version_registro"],
        "op_id": str(op_id),
    }
    expected = canonical_payload_hash(
        {
            "metadata": {"uid_instalacion_origen": metadata["uid_instalacion_origen"]},
            "data": data,
        }
    )
    assert metadata["payload_hash"] == expected
    assert len(expected) == 64 and expected == expected.lower()
    reordered = {
        "data": dict(reversed(list(data.items()))),
        "metadata": {"uid_instalacion_origen": metadata["uid_instalacion_origen"]},
    }
    assert canonical_payload_hash(reordered) == expected
    changed = deepcopy(data)
    changed["valor_nuevo"] = "1"
    assert (
        canonical_payload_hash(
            {
                "metadata": {
                    "uid_instalacion_origen": metadata["uid_instalacion_origen"]
                },
                "data": changed,
            }
        )
        != expected
    )


def test_cas_updates_only_exact_pk_when_versions_match(client, db_session):
    other = _seed_parameter(db_session, "FILA_B_412", "31")
    before_b = dict(_row(db_session, "FILA_B_412"))
    a = _row(db_session)
    op_id = uuid4()
    assert (
        _request(client, 16, headers=_headers(op_id, a["version_registro"])).status_code
        == 200
    )
    assert (
        _row(db_session)["valor_parametro"] == "16"
        and dict(_row(db_session, "FILA_B_412")) == before_b
    )
    event = db_session.execute(
        text("SELECT aggregate_id FROM outbox_event")
    ).scalar_one()
    receipt_uid = db_session.execute(
        text("SELECT result_target_uid FROM operacion_idempotente WHERE op_id=:op"),
        {"op": op_id},
    ).scalar_one()
    assert event == a["id_valor_parametro"] and receipt_uid == a["uid_global"]
    assert other["version_registro"] == a["version_registro"]


@pytest.mark.parametrize("logical", ["NO/EXISTE", "A/B/C", " CODE ", "X" * 100])
def test_path_routing_reaches_functional_logic(client, logical):
    endpoint = ENDPOINT_TEMPLATE.format(quote(logical, safe="/"))
    response = _request(client, 16, headers=_headers(), endpoint=endpoint)
    assert (
        response.status_code == 404
        and response.json()["error_code"] == "parametro_no_encontrado"
    )


@pytest.mark.parametrize("logical", ["X" * 101, "   ", "%09"])
def test_invalid_path_is_422_before_claim(client, logical):
    endpoint = ENDPOINT_TEMPLATE.format(
        logical if logical.startswith("%") else quote(logical)
    )
    with patch(
        "app.application.administrativo.services.actualizar_valor_parametro_global_service.claim_operation"
    ) as claim:
        response = _request(client, 16, headers=_headers(), endpoint=endpoint)
    assert response.status_code == 422
    claim.assert_not_called()


def test_crlf_is_rejected_by_ascii_ledger_validator():
    with pytest.raises(Exception) as error:
        _validate_command_codigo("\r\n")
    assert getattr(error.value, "status_code", None) == 422


def test_unicode_whitespace_is_not_ascii_ledger_whitespace(client):
    response = _request(
        client,
        16,
        headers=_headers(),
        endpoint=ENDPOINT_TEMPLATE.format(quote("\u00a0")),
    )
    assert (
        response.status_code == 404
        and response.json()["error_code"] == "parametro_no_encontrado"
    )


def test_occurred_at_uses_naive_utc_wall_clock_independent_of_session_timezone(
    db_session,
):
    from app.api.core_ef_headers import AuthenticatedCoreEFHeaders
    from app.application.administrativo.services.actualizar_valor_parametro_global_service import (
        ActualizarValorParametroGlobalService,
    )

    frozen = datetime(2026, 8, 14, 15, 30, 45, 123456, tzinfo=UTC)
    db_session.execute(text("SET LOCAL TIME ZONE 'America/Argentina/Buenos_Aires'"))
    before = _row(db_session)
    op_id = uuid4()
    result = ActualizarValorParametroGlobalService(
        db_session, clock=lambda: frozen
    ).execute(
        codigo_parametro=CODE,
        valor_tipado=int(before["valor_parametro"]) + 1,
        headers=AuthenticatedCoreEFHeaders(op_id, 1, 1, before["version_registro"]),
        id_usuario=1,
    )
    assert result["ok"] is True
    occurred_at = db_session.execute(
        text(
            "SELECT occurred_at FROM outbox_event WHERE payload->'data'->>'op_id'=:op"
        ),
        {"op": str(op_id)},
    ).scalar_one()
    assert occurred_at == frozen.replace(tzinfo=None)
    assert occurred_at.tzinfo is None


def test_decoded_path_is_preserved_in_target_key_and_fingerprint(client, db_session):
    logical = " A/B "
    seeded = _seed_parameter(db_session, logical, "15")
    op_id = uuid4()
    endpoint = ENDPOINT_TEMPLATE.format(quote(logical, safe="/"))
    response = _request(
        client,
        15,
        headers=_headers(op_id, seeded["version_registro"]),
        endpoint=endpoint,
    )
    assert response.status_code == 200
    receipt = db_session.execute(
        text(
            "SELECT target_key,payload_hash FROM operacion_idempotente WHERE op_id=:op"
        ),
        {"op": op_id},
    ).one()
    assert receipt.target_key == logical
    assert receipt.payload_hash == canonical_payload_hash(
        {
            "codigo_parametro": logical,
            "valor_tipado": "15",
            "if_match_version": seeded["version_registro"],
        }
    )
