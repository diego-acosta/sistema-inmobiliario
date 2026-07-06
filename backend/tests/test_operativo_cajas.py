from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440253",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _apply_patch(db_session):
    sql = Path("backend/database/patch_caja_operativa_base_20260704.sql").read_text()
    db_session.execute(text(sql))


def _payload(**overrides):
    data = {
        "id_sucursal": 1,
        "id_instalacion": 1,
        "codigo_caja": f"CJ-{uuid4().hex[:8]}",
        "nombre_caja": "Caja operativa base",
        "tipo_caja": "GENERAL",
        "moneda_base": "ARS",
        "estado_caja": "ACTIVA",
        "permite_efectivo": True,
        "permite_transferencia": False,
        "permite_cheque": False,
        "descripcion": "Caja estructural sin movimientos",
        "observaciones": None,
    }
    data.update(overrides)
    return data


def test_crear_caja_operativa_ok_metadata_y_outbox(client, db_session):
    _apply_patch(db_session)
    payload = _payload(codigo_caja="CJ-OK-253")

    response = client.post("/api/v1/operativo/cajas", json=payload, headers=HEADERS)

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["version_registro"] == 1
    assert data["uid_global"]
    assert data["id_instalacion_origen"] == 1
    assert data["id_instalacion_ultima_modificacion"] == 1
    assert data["op_id_alta"] == HEADERS["X-Op-Id"]
    row = db_session.execute(
        text(
            "SELECT COUNT(*) FROM outbox_event WHERE event_type = 'caja_operativa_creada'"
        )
    ).scalar()
    assert row == 1


def test_replay_idempotente_compatible_no_duplica_caja_ni_outbox(client, db_session):
    _apply_patch(db_session)
    payload = _payload(codigo_caja="CJ-REPLAY-OK")
    headers = {**HEADERS, "X-Op-Id": str(uuid4())}

    first = client.post("/api/v1/operativo/cajas", json=payload, headers=headers)
    second = client.post("/api/v1/operativo/cajas", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["data"]["id_caja"] == second.json()["data"]["id_caja"]
    assert (
        db_session.execute(
            text("SELECT COUNT(*) FROM caja_operativa WHERE codigo_caja='CJ-REPLAY-OK'")
        ).scalar()
        == 1
    )
    assert (
        db_session.execute(
            text(
                "SELECT COUNT(*) FROM outbox_event WHERE event_type='caja_operativa_creada' AND aggregate_type='caja_operativa'"
            )
        ).scalar()
        == 1
    )


def test_replay_idempotente_incompatible_devuelve_409(client, db_session):
    _apply_patch(db_session)
    headers = {**HEADERS, "X-Op-Id": str(uuid4())}
    payload = _payload(codigo_caja="CJ-REPLAY-BAD")
    assert (
        client.post(
            "/api/v1/operativo/cajas", json=payload, headers=headers
        ).status_code
        == 201
    )

    response = client.post(
        "/api/v1/operativo/cajas",
        json={**payload, "nombre_caja": "Otra caja"},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENT_DUPLICATE"


def test_duplicado_activo_codigo_contexto_devuelve_409(client, db_session):
    _apply_patch(db_session)
    payload = _payload(codigo_caja="CJ-DUP")
    assert (
        client.post(
            "/api/v1/operativo/cajas",
            json=payload,
            headers={**HEADERS, "X-Op-Id": str(uuid4())},
        ).status_code
        == 201
    )

    response = client.post(
        "/api/v1/operativo/cajas",
        json=payload,
        headers={**HEADERS, "X-Op-Id": str(uuid4())},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "TECHNICAL_INCONSISTENCY"


def test_contexto_invalido_y_headers(client, db_session):
    _apply_patch(db_session)
    assert (
        client.post(
            "/api/v1/operativo/cajas",
            json=_payload(id_sucursal=999),
            headers={**HEADERS, "X-Op-Id": str(uuid4())},
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/v1/operativo/cajas",
            json=_payload(id_instalacion=999),
            headers={**HEADERS, "X-Op-Id": str(uuid4())},
        ).status_code
        == 404
    )
    assert (
        client.post("/api/v1/operativo/cajas", json=_payload(), headers={}).status_code
        == 400
    )


def test_validaciones_422(client, db_session):
    _apply_patch(db_session)
    for field, value in [
        ("codigo_caja", ""),
        ("tipo_caja", "INVALIDA"),
        ("estado_caja", "ABIERTA"),
        ("moneda_base", "EUR"),
    ]:
        response = client.post(
            "/api/v1/operativo/cajas",
            json=_payload(**{field: value}),
            headers={**HEADERS, "X-Op-Id": str(uuid4())},
        )
        assert response.status_code == 422


def test_listado_filtros_y_ficha(client, db_session):
    _apply_patch(db_session)
    empty = client.get("/api/v1/operativo/cajas")
    assert empty.status_code == 200
    assert empty.json()["data"] == []

    payload = _payload(codigo_caja="CJ-LIST", estado_caja="INACTIVA")
    created = client.post(
        "/api/v1/operativo/cajas",
        json=payload,
        headers={**HEADERS, "X-Op-Id": str(uuid4())},
    ).json()["data"]

    assert (
        len(
            client.get("/api/v1/operativo/cajas", params={"id_sucursal": 1}).json()[
                "data"
            ]
        )
        == 1
    )
    assert (
        len(
            client.get("/api/v1/operativo/cajas", params={"id_instalacion": 1}).json()[
                "data"
            ]
        )
        == 1
    )
    assert (
        len(
            client.get(
                "/api/v1/operativo/cajas", params={"estado_caja": "INACTIVA"}
            ).json()["data"]
        )
        == 1
    )
    detail = client.get(f"/api/v1/operativo/cajas/{created['id_caja']}")
    assert detail.status_code == 200
    assert detail.json()["data"]["codigo_caja"] == "CJ-LIST"
    assert client.get("/api/v1/operativo/cajas/999999").status_code == 404


def test_indices_caja_operativa_existen(db_session):
    _apply_patch(db_session)
    indexes = set(db_session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'caja_operativa'
    """)).scalars().all())
    assert "ux_caja_operativa_uid_global" in indexes
    assert "ux_caja_operativa_op_id_alta" in indexes
    assert "ux_caja_operativa_codigo_activa" in indexes
