from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text

HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440254",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _apply_patch(db_session):
    db_session.execute(text(Path("backend/database/patch_caja_operativa_base_20260704.sql").read_text()))
    db_session.execute(text(Path("backend/database/patch_apertura_cierre_caja_operativa_20260706.sql").read_text()))


def _crear_caja(client, codigo="CJ-APE"):
    response = client.post(
        "/api/v1/operativo/cajas",
        json={
            "id_sucursal": 1,
            "id_instalacion": 1,
            "codigo_caja": f"{codigo}-{uuid4().hex[:8]}",
            "nombre_caja": "Caja Mostrador 1",
            "tipo_caja": "GENERAL",
            "moneda_base": "ARS",
            "estado_caja": "ACTIVA",
            "permite_efectivo": True,
            "permite_transferencia": False,
            "permite_cheque": False,
        },
        headers={**HEADERS, "X-Op-Id": str(uuid4())},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _apertura_payload(**overrides):
    data = {
        "id_sucursal": 1,
        "id_instalacion": 1,
        "fecha_hora_apertura": "2026-07-06T09:12:00",
        "saldo_inicial": 1000,
        "moneda": "ARS",
        "observaciones_apertura": "Inicio de jornada",
    }
    data.update(overrides)
    return data


def test_abrir_caja_ok_metadata_y_outbox(client, db_session):
    _apply_patch(db_session)
    caja = _crear_caja(client)

    response = client.post(
        f"/api/v1/operativo/cajas/{caja['id_caja']}/aperturas",
        json=_apertura_payload(),
        headers=HEADERS,
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["version_registro"] == 1
    assert data["id_usuario_apertura"] == 1
    assert data["id_instalacion_origen"] == 1
    assert data["op_id_alta"] == HEADERS["X-Op-Id"]
    assert data["estado_apertura"] == "ABIERTA"
    assert db_session.execute(text("SELECT COUNT(*) FROM outbox_event WHERE event_type='caja_operativa_abierta'")).scalar() == 1


def test_replay_idempotente_compatible_no_duplica_apertura_ni_outbox(client, db_session):
    _apply_patch(db_session)
    caja = _crear_caja(client)
    headers = {**HEADERS, "X-Op-Id": str(uuid4())}
    payload = _apertura_payload()

    first = client.post(f"/api/v1/operativo/cajas/{caja['id_caja']}/aperturas", json=payload, headers=headers)
    second = client.post(f"/api/v1/operativo/cajas/{caja['id_caja']}/aperturas", json=payload, headers=headers)

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["data"]["id_apertura_caja"] == second.json()["data"]["id_apertura_caja"]
    assert db_session.execute(text("SELECT COUNT(*) FROM caja_operativa_apertura")).scalar() == 1
    assert db_session.execute(text("SELECT COUNT(*) FROM outbox_event WHERE event_type='caja_operativa_abierta'")).scalar() == 1


def test_replay_idempotente_incompatible_y_doble_vigente(client, db_session):
    _apply_patch(db_session)
    caja = _crear_caja(client)
    headers = {**HEADERS, "X-Op-Id": str(uuid4())}
    assert client.post(f"/api/v1/operativo/cajas/{caja['id_caja']}/aperturas", json=_apertura_payload(), headers=headers).status_code == 201

    incompatible = client.post(
        f"/api/v1/operativo/cajas/{caja['id_caja']}/aperturas",
        json=_apertura_payload(saldo_inicial=2000),
        headers=headers,
    )
    duplicate = client.post(
        f"/api/v1/operativo/cajas/{caja['id_caja']}/aperturas",
        json=_apertura_payload(),
        headers={**HEADERS, "X-Op-Id": str(uuid4())},
    )

    assert incompatible.status_code == 409
    assert incompatible.json()["error_code"] == "IDEMPOTENT_DUPLICATE"
    assert duplicate.status_code == 409
    assert duplicate.json()["error_code"] == "TECHNICAL_INCONSISTENCY"


def test_get_apertura_vigente_y_listado_advertencias(client, db_session):
    _apply_patch(db_session)
    caja = _crear_caja(client)
    assert client.get(f"/api/v1/operativo/cajas/{caja['id_caja']}/apertura-vigente").json()["data"] is None
    ayer = (datetime.now(UTC) - timedelta(days=1)).replace(hour=9, minute=12, second=0, microsecond=0).isoformat()
    created = client.post(
        f"/api/v1/operativo/cajas/{caja['id_caja']}/aperturas",
        json=_apertura_payload(fecha_hora_apertura=ayer),
        headers={**HEADERS, "X-Op-Id": str(uuid4())},
    )
    assert created.status_code == 201

    vigente = client.get(f"/api/v1/operativo/cajas/{caja['id_caja']}/apertura-vigente")
    listado = client.get("/api/v1/operativo/cajas/aperturas-vigentes", params={"id_sucursal": 1, "id_instalacion": 1, "solo_abiertas_de_dias_anteriores": True})

    assert vigente.status_code == 200
    assert vigente.json()["data"]["codigo_caja"] == caja["codigo_caja"]
    assert listado.status_code == 200
    assert len(listado.json()["data"]) == 1
    assert listado.json()["data"][0]["nombre_caja"] == "Caja Mostrador 1"


def test_cerrar_caja_ok_version_estado_outbox(client, db_session):
    _apply_patch(db_session)
    caja = _crear_caja(client)
    apertura = client.post(
        f"/api/v1/operativo/cajas/{caja['id_caja']}/aperturas",
        json=_apertura_payload(),
        headers={**HEADERS, "X-Op-Id": str(uuid4())},
    ).json()["data"]

    response = client.patch(
        f"/api/v1/operativo/cajas/aperturas/{apertura['id_apertura_caja']}/cerrar",
        json={"fecha_hora_cierre": "2026-07-07T10:00:00", "saldo_declarado_cierre": 1200, "observaciones_cierre": "Cierre"},
        headers={**HEADERS, "X-Op-Id": str(uuid4()), "If-Match-Version": "1"},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["version_registro"] == 2
    assert data["estado_apertura"] == "CERRADA"
    assert data["id_usuario_cierre"] == 1
    assert data["fecha_hora_cierre"] is not None
    assert db_session.execute(text("SELECT COUNT(*) FROM outbox_event WHERE event_type='caja_operativa_cerrada'")).scalar() == 1


def test_cierre_validaciones_concurrencia_y_estado(client, db_session):
    _apply_patch(db_session)
    caja = _crear_caja(client)
    apertura = client.post(
        f"/api/v1/operativo/cajas/{caja['id_caja']}/aperturas",
        json=_apertura_payload(),
        headers={**HEADERS, "X-Op-Id": str(uuid4())},
    ).json()["data"]
    url = f"/api/v1/operativo/cajas/aperturas/{apertura['id_apertura_caja']}/cerrar"
    payload = {"fecha_hora_cierre": "2026-07-07T10:00:00", "saldo_declarado_cierre": 1200}

    assert client.patch(url, json=payload, headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 400
    wrong = client.patch(url, json=payload, headers={**HEADERS, "X-Op-Id": str(uuid4()), "If-Match-Version": "99"})
    assert wrong.status_code == 412
    before = client.patch(url, json={**payload, "fecha_hora_cierre": "2026-07-05T10:00:00"}, headers={**HEADERS, "X-Op-Id": str(uuid4()), "If-Match-Version": "1"})
    assert before.status_code == 400
    ok = client.patch(url, json=payload, headers={**HEADERS, "X-Op-Id": str(uuid4()), "If-Match-Version": "1"})
    assert ok.status_code == 200
    again = client.patch(url, json=payload, headers={**HEADERS, "X-Op-Id": str(uuid4()), "If-Match-Version": "2"})
    assert again.status_code == 409


def test_validaciones_contexto_headers_422_e_indices(client, db_session):
    _apply_patch(db_session)
    caja = _crear_caja(client)
    url = f"/api/v1/operativo/cajas/{caja['id_caja']}/aperturas"
    assert client.post(url, json=_apertura_payload(), headers={}).status_code == 400
    assert client.post("/api/v1/operativo/cajas/999999/aperturas", json=_apertura_payload(), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 404
    assert client.post(url, json=_apertura_payload(id_sucursal=999), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 404
    assert client.post(url, json=_apertura_payload(id_instalacion=999), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 404
    assert client.post(url, json=_apertura_payload(saldo_inicial=-1), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 422
    assert client.post(url, json=_apertura_payload(moneda="EUR"), headers={**HEADERS, "X-Op-Id": str(uuid4())}).status_code == 422

    indexes = set(db_session.execute(text("""
        SELECT indexname FROM pg_indexes
        WHERE schemaname = 'public' AND tablename = 'caja_operativa_apertura'
    """)).scalars().all())
    assert "ux_caja_operativa_apertura_uid_global" in indexes
    assert "ux_caja_operativa_apertura_op_id_alta" in indexes
    assert "ux_caja_operativa_apertura_vigente_caja" in indexes
