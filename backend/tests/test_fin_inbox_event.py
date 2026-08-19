"""
Tests de integración para POST /api/v1/financiero/inbox.
Cubre: evento válido, evento desconocido e idempotencia.
"""
import pytest
from sqlalchemy import text

from app.application.financiero.services.inbox_event_dispatcher import InboxEventDispatcher
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
