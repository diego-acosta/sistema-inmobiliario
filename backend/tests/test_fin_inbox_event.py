"""
Tests de integración para POST /api/v1/financiero/inbox.
Cubre: evento válido, evento desconocido e idempotencia.
"""
import pytest
from sqlalchemy import text

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
    response2 = client.post(URL, headers=INBOX_HEADERS, json=body)

    assert response1.status_code == 204
    assert response2.status_code == 204

    assert _count_relaciones_venta(db_session, id_venta=id_venta) == 1

    relacion = _get_relacion_venta(db_session, id_venta=id_venta)
    assert (
        _count_obligaciones_relacion(
            db_session,
            id_relacion_generadora=relacion["id_relacion_generadora"],
        )
        == 1
    )
