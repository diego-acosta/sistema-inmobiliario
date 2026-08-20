"""
Tests de integración para POST /api/v1/financiero/inbox.
Cubre: evento válido, evento desconocido e idempotencia.
"""
from uuid import uuid4

import pytest
from sqlalchemy import text

import app.application.financiero.services.inbox_event_dispatcher as inbox_dispatcher_module
from app.application.administrativo.services.actualizar_valor_parametro_global_service import (
    COMMAND_CODE as ADMIN_VALOR_GLOBAL_COMMAND_CODE,
    TARGET_TYPE as ADMIN_VALOR_GLOBAL_TARGET_TYPE,
)
from app.application.common.idempotency import (
    CANONICALIZATION_VERSION,
    ClaimDecision,
    OperationClaim,
    OperationCompletion,
    canonical_payload_hash,
    claim_operation,
    complete_operation,
)
from app.application.financiero.services.inbox_event_dispatcher import InboxEventDispatcher
from tests.test_fin_event_contrato_alquiler import (
    _crear_condicion,
    _crear_contrato_borrador,
    _crear_locatario_principal,
)
from tests.test_escrituraciones_create import _confirmar_venta_publica


URL = "/api/v1/financiero/inbox"
INBOX_HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_inbox_openapi_declara_error_response_400(client) -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"][URL]["post"]
    response_400 = operation["responses"]["400"]
    assert "409" in operation["responses"]
    error_schema_ref = response_400["content"]["application/json"]["schema"]["$ref"]
    error_schema_name = error_schema_ref.rsplit("/", 1)[-1]

    assert error_schema_name.endswith("__ErrorResponse")
    assert {"error_code", "error_message"} <= set(
        schema["components"]["schemas"][error_schema_name]["properties"]
    )
    header_parameters = {
        parameter["name"]: parameter
        for parameter in operation["parameters"]
        if parameter["in"] == "header"
    }
    assert set(header_parameters) == {
        "X-Op-Id",
        "X-Sucursal-Id",
        "X-Instalacion-Id",
    }
    assert all(parameter["required"] for parameter in header_parameters.values())


@pytest.mark.parametrize("missing_header", INBOX_HEADERS)
def test_inbox_rechaza_header_tecnico_faltante_antes_del_evento(
    client, missing_header
) -> None:
    headers = {key: value for key, value in INBOX_HEADERS.items() if key != missing_header}

    response = client.post(
        URL,
        headers=headers,
        json={"event_type": "evento_inexistente_xyz", "payload": {}},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert response.json()["details"] == {"header": missing_header}


@pytest.mark.parametrize(
    ("header", "invalid_value"),
    (
        ("X-Op-Id", "no-es-uuid"),
        ("X-Sucursal-Id", "0"),
        ("X-Sucursal-Id", "-1"),
        ("X-Sucursal-Id", "no-es-entero"),
        ("X-Instalacion-Id", "0"),
        ("X-Instalacion-Id", "-1"),
        ("X-Instalacion-Id", "no-es-entero"),
    ),
)
def test_inbox_rechaza_header_tecnico_invalido_antes_del_evento(
    client, header, invalid_value
) -> None:
    response = client.post(
        URL,
        headers={**INBOX_HEADERS, header: invalid_value},
        json={"event_type": "evento_inexistente_xyz", "payload": {}},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "VALIDATION_ERROR"
    assert response.json()["details"] == {"header": header}


# ─── helpers ─────────────────────────────────────────────────────────────────


def _count_relaciones_venta(db_session, *, id_venta: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM relacion_generadora
            WHERE tipo_origen = 'venta'
              AND id_origen = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()["total"]


def _count_obligaciones_relacion(db_session, *, id_relacion_generadora: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM obligacion_financiera
            WHERE id_relacion_generadora = :id
              AND deleted_at IS NULL
            """
        ),
        {"id": id_relacion_generadora},
    ).mappings().one()["total"]


def _get_relacion_venta(db_session, *, id_venta: int) -> dict:
    return db_session.execute(
        text(
            """
            SELECT id_relacion_generadora, tipo_origen, id_origen,
                   estado_relacion_generadora, op_id_alta
            FROM relacion_generadora
            WHERE tipo_origen = 'venta'
              AND id_origen = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()


def _get_metadata_grafo_venta(db_session, *, id_venta: int) -> list[dict]:
    return list(
        db_session.execute(
            text(
                """
                SELECT
                    rg.id_instalacion_origen AS rg_origen,
                    rg.id_instalacion_ultima_modificacion AS rg_ultima,
                    rg.op_id_alta AS rg_op_alta,
                    rg.op_id_ultima_modificacion AS rg_op_ultima,
                    ofi.id_instalacion_origen AS of_origen,
                    ofi.id_instalacion_ultima_modificacion AS of_ultima,
                    ofi.op_id_alta AS of_op_alta,
                    ofi.op_id_ultima_modificacion AS of_op_ultima,
                    co.id_instalacion_origen AS co_origen,
                    co.id_instalacion_ultima_modificacion AS co_ultima,
                    co.op_id_alta AS co_op_alta,
                    co.op_id_ultima_modificacion AS co_op_ultima,
                    oo.id_instalacion_origen AS oo_origen,
                    oo.id_instalacion_ultima_modificacion AS oo_ultima,
                    oo.op_id_alta AS oo_op_alta,
                    oo.op_id_ultima_modificacion AS oo_op_ultima
                FROM relacion_generadora rg
                JOIN obligacion_financiera ofi
                  ON ofi.id_relacion_generadora = rg.id_relacion_generadora
                JOIN composicion_obligacion co
                  ON co.id_obligacion_financiera = ofi.id_obligacion_financiera
                JOIN obligacion_obligado oo
                  ON oo.id_obligacion_financiera = ofi.id_obligacion_financiera
                WHERE rg.tipo_origen = 'venta' AND rg.id_origen = :id_venta
                """
            ),
            {"id_venta": id_venta},
        ).mappings()
    )


def _count_receipts(db_session, op_id: str) -> int:
    return db_session.execute(
        text("SELECT count(*) FROM operacion_idempotente WHERE op_id = CAST(:op_id AS uuid)"),
        {"op_id": op_id},
    ).scalar_one()


def _assert_context_validation_without_effects(response, db_session, op_id: str) -> None:
    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error_code": "VALIDATION_ERROR",
        "error_message": "El contexto técnico sucursal/instalación es inválido.",
        "details": {"headers": ["X-Sucursal-Id", "X-Instalacion-Id"]},
    }
    assert _count_receipts(db_session, op_id) == 0
    assert db_session.execute(text("SELECT count(*) FROM relacion_generadora")).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM obligacion_financiera")).scalar_one() == 0


def test_inbox_rechaza_instalacion_inexistente_antes_de_sync_y_claim(
    client, db_session
) -> None:
    headers = {
        **INBOX_HEADERS,
        "X-Op-Id": "750e8400-e29b-41d4-a716-446655440002",
        "X-Instalacion-Id": "999999999",
    }

    response = client.post(
        URL,
        headers=headers,
        json={"event_type": "evento_inexistente_xyz", "payload": {}},
    )

    _assert_context_validation_without_effects(response, db_session, headers["X-Op-Id"])


def test_inbox_rechaza_instalacion_de_otra_sucursal_sin_receipt_ni_writes(
    client, db_session
) -> None:
    other_branch = db_session.execute(
        text(
            """
            INSERT INTO sucursal (codigo_sucursal, nombre_sucursal, estado_sucursal)
            VALUES (:code, 'Sucursal ajena inbox', 'ACTIVA')
            RETURNING id_sucursal
            """
        ),
        {"code": f"SUC_INBOX_{uuid4().hex[:10]}"},
    ).scalar_one()
    other_installation = db_session.execute(
        text(
            """
            INSERT INTO instalacion (
                uid_global, id_sucursal, codigo_instalacion, nombre_instalacion,
                estado_instalacion, es_principal, permite_sincronizacion
            ) VALUES (
                :uid_global, :id_sucursal, :code, 'Instalación ajena inbox',
                'ACTIVA', false, true
            ) RETURNING id_instalacion
            """
        ),
        {
            "uid_global": uuid4(),
            "id_sucursal": other_branch,
            "code": f"INST_INBOX_{uuid4().hex[:10]}",
        },
    ).scalar_one()
    headers = {
        **INBOX_HEADERS,
        "X-Op-Id": "850e8400-e29b-41d4-a716-446655440003",
        "X-Instalacion-Id": str(other_installation),
    }

    response = client.post(
        URL,
        headers=headers,
        json={"event_type": "venta_confirmada", "payload": {"id_venta": 999999999}},
    )

    _assert_context_validation_without_effects(response, db_session, headers["X-Op-Id"])


@pytest.mark.parametrize(
    ("metadata", "op_id"),
    (
        (1.5, "a50e8400-e29b-41d4-a716-446655440005"),
        ([1, 2.5], "b50e8400-e29b-41d4-a716-446655440006"),
    ),
)
def test_inbox_rechaza_payload_no_canonicalizable_antes_de_claim_y_handler(
    client, db_session, monkeypatch, metadata, op_id
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    headers = {**INBOX_HEADERS, "X-Op-Id": op_id}

    def unexpected_handler(*args, **kwargs):
        raise AssertionError("el handler no debe ejecutarse")

    monkeypatch.setattr(
        inbox_dispatcher_module.HandleVentaConfirmadaEventService,
        "execute",
        unexpected_handler,
    )

    response = client.post(
        URL,
        headers=headers,
        json={
            "event_type": "venta_confirmada",
            "payload": {"id_venta": venta["id_venta"], "metadata": metadata},
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error_code": "IDEMPOTENCY_PAYLOAD_INVALID",
        "error_message": "IDEMPOTENCY_PAYLOAD_INVALID",
        "details": None,
    }
    assert _count_receipts(db_session, op_id) == 0
    assert _count_relaciones_venta(db_session, id_venta=venta["id_venta"]) == 0
    assert db_session.execute(
        text("SELECT count(*) FROM obligacion_financiera")
    ).scalar_one() == 0


def test_inbox_acepta_extras_canonicalizables(client, db_session) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    op_id = "c50e8400-e29b-41d4-a716-446655440007"

    response = client.post(
        URL,
        headers={**INBOX_HEADERS, "X-Op-Id": op_id},
        json={
            "event_type": "venta_confirmada",
            "payload": {
                "id_venta": venta["id_venta"],
                "metadata": {
                    "source": "sync",
                    "attempt": 2,
                    "flags": [True, False, None],
                },
            },
        },
    )

    assert response.status_code == 204
    assert _count_receipts(db_session, op_id) == 1
    assert _count_relaciones_venta(db_session, id_venta=venta["id_venta"]) == 1


def test_inbox_evento_desconocido_precede_payload_no_canonicalizable(
    client, db_session
) -> None:
    op_id = "d50e8400-e29b-41d4-a716-446655440008"
    response = client.post(
        URL,
        headers={**INBOX_HEADERS, "X-Op-Id": op_id},
        json={"event_type": "evento_inexistente_xyz", "payload": {"value": 1.5}},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "SYNC_EVENT_NOT_ALLOWED"
    assert _count_receipts(db_session, op_id) == 0


def test_inbox_contexto_invalido_precede_payload_no_canonicalizable(
    client, db_session
) -> None:
    headers = {
        **INBOX_HEADERS,
        "X-Op-Id": "e50e8400-e29b-41d4-a716-446655440009",
        "X-Instalacion-Id": "999999999",
    }
    response = client.post(
        URL,
        headers=headers,
        json={"event_type": "venta_confirmada", "payload": {"id_venta": 1, "value": 1.5}},
    )

    _assert_context_validation_without_effects(response, db_session, headers["X-Op-Id"])


@pytest.mark.parametrize(
    ("payload", "op_id"),
    (
        ({}, "f50e8400-e29b-41d4-a716-446655440010"),
        ({"id_venta": 0}, "150e8400-e29b-41d4-a716-446655440011"),
    ),
)
def test_inbox_rechaza_identificador_sync_invalido_sin_claim_ni_handler(
    client, db_session, monkeypatch, payload, op_id
) -> None:
    def unexpected_handler(*args, **kwargs):
        raise AssertionError("el handler no debe ejecutarse")

    monkeypatch.setattr(
        inbox_dispatcher_module.HandleVentaConfirmadaEventService,
        "execute",
        unexpected_handler,
    )
    response = client.post(
        URL,
        headers={**INBOX_HEADERS, "X-Op-Id": op_id},
        json={"event_type": "venta_confirmada", "payload": payload},
    )

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error_code": "SYNC_SENSITIVE_PAYLOAD",
        "error_message": "SYNC_SENSITIVE_PAYLOAD",
        "details": None,
    }
    assert _count_receipts(db_session, op_id) == 0
    assert db_session.execute(
        text("SELECT count(*) FROM relacion_generadora")
    ).scalar_one() == 0
    assert db_session.execute(
        text("SELECT count(*) FROM obligacion_financiera")
    ).scalar_one() == 0


def test_inbox_rechaza_clave_sensible_sin_filtrar_contenido(
    client, db_session, monkeypatch
) -> None:
    op_id = "250e8400-e29b-41d4-a716-446655440012"
    sensitive_value = "NO_ASSERT_VALUE"

    def unexpected_handler(*args, **kwargs):
        raise AssertionError("el handler no debe ejecutarse")

    monkeypatch.setattr(
        inbox_dispatcher_module.HandleVentaConfirmadaEventService,
        "execute",
        unexpected_handler,
    )
    response = client.post(
        URL,
        headers={**INBOX_HEADERS, "X-Op-Id": op_id},
        json={
            "event_type": "venta_confirmada",
            "payload": {
                "id_venta": 1,
                "metadata": {"token": sensitive_value},
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "SYNC_SENSITIVE_PAYLOAD"
    assert "token" not in response.text.casefold()
    assert sensitive_value not in response.text
    assert _count_receipts(db_session, op_id) == 0
    assert db_session.execute(
        text("SELECT count(*) FROM relacion_generadora")
    ).scalar_one() == 0
    assert db_session.execute(
        text("SELECT count(*) FROM obligacion_financiera")
    ).scalar_one() == 0


# ─── caso 1: evento válido ────────────────────────────────────────────────────


def test_inbox_venta_confirmada_crea_relacion_generadora_y_obligacion(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    id_venta = venta["id_venta"]

    response = client.post(
        URL,
        headers=INBOX_HEADERS,
        json={
            "event_type": "venta_confirmada",
            "payload": {"id_venta": id_venta},
        },
    )

    assert response.status_code == 204
    assert response.content == b""

    assert _count_relaciones_venta(db_session, id_venta=id_venta) == 1

    relacion = _get_relacion_venta(db_session, id_venta=id_venta)
    assert relacion["tipo_origen"] == "venta"
    assert relacion["id_origen"] == id_venta
    assert str(relacion["op_id_alta"]) == INBOX_HEADERS["X-Op-Id"]
    metadata_rows = _get_metadata_grafo_venta(db_session, id_venta=id_venta)
    assert metadata_rows
    for row in metadata_rows:
        assert all(
            row[key] == 1
            for key in row
            if "_op_" not in key and key.endswith(("origen", "ultima"))
        )
        assert all(
            str(row[key]) == INBOX_HEADERS["X-Op-Id"]
            for key in row
            if "_op_" in key
        )
    assert _count_receipts(db_session, INBOX_HEADERS["X-Op-Id"]) == 1

    assert (
        _count_obligaciones_relacion(
            db_session,
            id_relacion_generadora=relacion["id_relacion_generadora"],
        )
        == 1
    )


# ─── caso 2: evento desconocido ──────────────────────────────────────────────


def test_inbox_evento_desconocido_no_rompe_y_no_crea_datos(
    client, db_session
) -> None:
    response = client.post(
        URL,
        headers=INBOX_HEADERS,
        json={
            "event_type": "evento_inexistente_xyz",
            "payload": {"foo": "bar"},
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error_code": "SYNC_EVENT_NOT_ALLOWED",
        "error_message": "SYNC_EVENT_NOT_ALLOWED",
        "details": None,
    }

    total_relaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM relacion_generadora WHERE deleted_at IS NULL")
    ).mappings().one()["total"]
    assert total_relaciones == 0

    total_obligaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM obligacion_financiera WHERE deleted_at IS NULL")
    ).mappings().one()["total"]
    assert total_obligaciones == 0


def test_inbox_evento_allowlisted_sin_handler_devuelve_error_controlado(
    client,
) -> None:
    response = client.post(
        URL,
        headers=INBOX_HEADERS,
        json={"event_type": "sucursal_creada", "payload": {}},
    )

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error_code": "SYNC_DISPATCH_FAILED",
        "error_message": "SYNC_DISPATCH_FAILED",
        "details": None,
    }


# ─── caso 3: idempotencia ─────────────────────────────────────────────────────


def test_inbox_venta_confirmada_idempotente_no_duplica(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    id_venta = venta["id_venta"]
    body = {
        "event_type": "venta_confirmada",
        "payload": {"id_venta": id_venta},
    }

    response1 = client.post(URL, headers=INBOX_HEADERS, json=body)
    materialized_after_first = tuple(
        db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        for table in (
            "relacion_generadora",
            "obligacion_financiera",
            "composicion_obligacion",
            "obligacion_obligado",
        )
    )
    response2 = client.post(URL, headers=INBOX_HEADERS, json=body)
    materialized_after_replay = tuple(
        db_session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()
        for table in (
            "relacion_generadora",
            "obligacion_financiera",
            "composicion_obligacion",
            "obligacion_obligado",
        )
    )

    assert response1.status_code == 204
    assert response2.status_code == 204
    assert materialized_after_replay == materialized_after_first
    assert _count_receipts(db_session, INBOX_HEADERS["X-Op-Id"]) == 1

    assert _count_relaciones_venta(db_session, id_venta=id_venta) == 1

    relacion = _get_relacion_venta(db_session, id_venta=id_venta)
    assert (
        _count_obligaciones_relacion(
            db_session,
            id_relacion_generadora=relacion["id_relacion_generadora"],
        )
        == 1
    )


def test_inbox_mismo_op_id_payload_distinto_devuelve_conflicto_sin_writes(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    id_venta = venta["id_venta"]
    first = client.post(
        URL,
        headers=INBOX_HEADERS,
        json={"event_type": "venta_confirmada", "payload": {"id_venta": id_venta}},
    )
    before = db_session.execute(
        text("SELECT count(*) FROM relacion_generadora")
    ).scalar_one()

    second = client.post(
        URL,
        headers=INBOX_HEADERS,
        json={
            "event_type": "venta_confirmada",
            "payload": {"id_venta": id_venta + 999_999},
        },
    )

    assert first.status_code == 204
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert db_session.execute(text("SELECT count(*) FROM relacion_generadora")).scalar_one() == before
    assert _count_receipts(db_session, INBOX_HEADERS["X-Op-Id"]) == 1


def test_inbox_mismo_op_id_event_type_distinto_devuelve_conflicto(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    first = client.post(
        URL,
        headers=INBOX_HEADERS,
        json={
            "event_type": "venta_confirmada",
            "payload": {"id_venta": venta["id_venta"]},
        },
    )
    second = client.post(
        URL,
        headers=INBOX_HEADERS,
        json={
            "event_type": "contrato_alquiler_activado",
            "payload": {"id_contrato_alquiler": 999_999},
        },
    )

    assert first.status_code == 204
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENCY_TARGET_CONFLICT"
    assert _count_receipts(db_session, INBOX_HEADERS["X-Op-Id"]) == 1


def test_inbox_op_id_global_usado_por_otro_command_devuelve_command_conflict(
    client, db_session, monkeypatch
) -> None:
    op_id = uuid4()
    payload_hash = canonical_payload_hash(
        {
            "codigo_parametro": "PARAMETRO_TEST",
            "valor_tipado": "1",
            "if_match_version": 1,
        }
    )
    claim = OperationClaim(
        op_id=op_id,
        command_code=ADMIN_VALOR_GLOBAL_COMMAND_CODE,
        target_type=ADMIN_VALOR_GLOBAL_TARGET_TYPE,
        target_uid=None,
        target_key="PARAMETRO_TEST",
        payload_hash=payload_hash,
        canonicalization_version=CANONICALIZATION_VERSION,
    )
    assert claim_operation(db_session, claim).decision is ClaimDecision.EXECUTE
    complete_operation(
        db_session,
        OperationCompletion(
            op_id=claim.op_id,
            command_code=claim.command_code,
            target_type=claim.target_type,
            target_uid=claim.target_uid,
            target_key=claim.target_key,
            payload_hash=claim.payload_hash,
            canonicalization_version=claim.canonicalization_version,
            result_code="PARAMETRO_GLOBAL_MODIFICADO",
            result_http_status=200,
            result_target_uid=None,
            result_version=1,
            response_snapshot={"ok": True},
            id_usuario=None,
            id_sucursal=1,
            id_instalacion=1,
        ),
    )
    db_session.commit()

    def unexpected_handler(*args, **kwargs):
        raise AssertionError("el handler financiero no debe ejecutarse")

    monkeypatch.setattr(
        inbox_dispatcher_module.HandleVentaConfirmadaEventService,
        "execute",
        unexpected_handler,
    )
    response = client.post(
        URL,
        headers={**INBOX_HEADERS, "X-Op-Id": str(op_id)},
        json={"event_type": "venta_confirmada", "payload": {"id_venta": 999999}},
    )

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error_code": "IDEMPOTENCY_COMMAND_CONFLICT",
        "error_message": "IDEMPOTENCY_COMMAND_CONFLICT",
        "details": None,
    }
    receipt = db_session.execute(
        text(
            """
            SELECT command_code, count(*) OVER () AS total
            FROM operacion_idempotente
            WHERE op_id = :op_id
            """
        ),
        {"op_id": op_id},
    ).mappings().one()
    assert receipt == {
        "command_code": ADMIN_VALOR_GLOBAL_COMMAND_CODE,
        "total": 1,
    }
    assert db_session.execute(
        text("SELECT count(*) FROM relacion_generadora")
    ).scalar_one() == 0
    assert db_session.execute(
        text("SELECT count(*) FROM obligacion_financiera")
    ).scalar_one() == 0


def test_inbox_op_id_distinto_preserva_convergencia_funcional(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    body = {
        "event_type": "venta_confirmada",
        "payload": {"id_venta": venta["id_venta"]},
    }
    other_headers = {
        **INBOX_HEADERS,
        "X-Op-Id": "650e8400-e29b-41d4-a716-446655440001",
    }

    assert client.post(URL, headers=INBOX_HEADERS, json=body).status_code == 204
    assert client.post(URL, headers=other_headers, json=body).status_code == 204
    assert _count_receipts(db_session, INBOX_HEADERS["X-Op-Id"]) == 1
    assert _count_receipts(db_session, other_headers["X-Op-Id"]) == 1
    assert _count_relaciones_venta(db_session, id_venta=venta["id_venta"]) == 1


def test_inbox_error_post_claim_hace_rollback_y_permite_retry(
    client, db_session, monkeypatch
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    body = {
        "event_type": "venta_confirmada",
        "payload": {"id_venta": venta["id_venta"]},
    }
    original = InboxEventDispatcher._dispatch_validated

    def fail_after_claim(*args, **kwargs):
        raise RuntimeError("fallo controlado post-claim")

    monkeypatch.setattr(InboxEventDispatcher, "_dispatch_validated", fail_after_claim)
    with pytest.raises(RuntimeError, match="fallo controlado post-claim"):
        client.post(URL, headers=INBOX_HEADERS, json=body)
    assert _count_receipts(db_session, INBOX_HEADERS["X-Op-Id"]) == 0
    assert _count_relaciones_venta(db_session, id_venta=venta["id_venta"]) == 0

    monkeypatch.setattr(InboxEventDispatcher, "_dispatch_validated", original)
    retry = client.post(URL, headers=INBOX_HEADERS, json=body)
    assert retry.status_code == 204
    assert _count_receipts(db_session, INBOX_HEADERS["X-Op-Id"]) == 1


def test_inbox_locativo_completion_fallida_revierte_cronograma_y_permite_retry(
    client, db_session, monkeypatch
) -> None:
    contrato = _crear_contrato_borrador(
        client,
        codigo="INBOX-LOC-ROLLBACK-001",
        fecha_inicio="2026-05-01",
        fecha_fin="2026-07-31",
    )
    _crear_condicion(
        client,
        contrato["id_contrato_alquiler"],
        50000.0,
        "2026-05-01",
    )
    _crear_locatario_principal(
        client,
        db_session,
        contrato["id_contrato_alquiler"],
    )
    db_session.commit()
    headers = {
        **INBOX_HEADERS,
        "X-Op-Id": "950e8400-e29b-41d4-a716-446655440004",
    }
    body = {
        "event_type": "contrato_alquiler_activado",
        "payload": {"id_contrato_alquiler": contrato["id_contrato_alquiler"]},
    }
    original_complete = inbox_dispatcher_module.complete_operation

    def fail_completion(*args, **kwargs):
        raise RuntimeError("fallo controlado de completion locativa")

    monkeypatch.setattr(inbox_dispatcher_module, "complete_operation", fail_completion)
    with pytest.raises(RuntimeError, match="fallo controlado de completion locativa"):
        client.post(URL, headers=headers, json=body)

    assert _count_receipts(db_session, headers["X-Op-Id"]) == 0
    assert db_session.execute(
        text(
            """
            SELECT count(*)
            FROM relacion_generadora
            WHERE tipo_origen = 'contrato_alquiler'
              AND id_origen = :id_contrato
            """
        ),
        {"id_contrato": contrato["id_contrato_alquiler"]},
    ).scalar_one() == 0
    assert db_session.execute(
        text(
            """
            SELECT count(*)
            FROM obligacion_financiera ofi
            JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = ofi.id_relacion_generadora
            WHERE rg.tipo_origen = 'contrato_alquiler'
              AND rg.id_origen = :id_contrato
            """
        ),
        {"id_contrato": contrato["id_contrato_alquiler"]},
    ).scalar_one() == 0

    monkeypatch.setattr(
        inbox_dispatcher_module,
        "complete_operation",
        original_complete,
    )
    retry = client.post(URL, headers=headers, json=body)
    assert retry.status_code == 204
    assert _count_receipts(db_session, headers["X-Op-Id"]) == 1
    id_relacion = db_session.execute(
        text(
            """
            SELECT id_relacion_generadora
            FROM relacion_generadora
            WHERE tipo_origen = 'contrato_alquiler'
              AND id_origen = :id_contrato
            """
        ),
        {"id_contrato": contrato["id_contrato_alquiler"]},
    ).scalar_one()
    assert _count_obligaciones_relacion(
        db_session,
        id_relacion_generadora=id_relacion,
    ) == 3
