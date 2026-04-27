from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_locativas_create import _crear_inmueble_disponible
from tests.test_solicitudes_alquiler_create import _payload as _payload_solicitud


URL_CONVERTIR = "/api/v1/solicitudes-alquiler/{id}/convertir-a-reserva"


def _crear_solicitud_aprobada(client, *, codigo: str) -> dict:
    sol = client.post(
        "/api/v1/solicitudes-alquiler", headers=HEADERS, json=_payload_solicitud(codigo=codigo)
    )
    assert sol.status_code == 201
    data = sol.json()["data"]

    aprobada = client.patch(
        f"/api/v1/solicitudes-alquiler/{data['id_solicitud_alquiler']}/aprobar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    assert aprobada.status_code == 200
    return aprobada.json()["data"]


def _payload_reserva(*, codigo: str, id_inmueble: int, confirmar: bool = False) -> dict:
    return {
        "codigo_reserva": codigo,
        "fecha_reserva": "2026-06-01T10:00:00",
        "fecha_vencimiento": "2026-06-10T10:00:00",
        "observaciones": "Reserva generada desde solicitud",
        "objetos": [{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
        "confirmar": confirmar,
    }


# ── tests create ──────────────────────────────────────────────────────────────

def test_convertir_solicitud_aprobada_crea_reserva_pendiente(client, db_session) -> None:
    sol = _crear_solicitud_aprobada(client, codigo="SOL-CONV-001")
    id_inmueble = _crear_inmueble_disponible(client, codigo="INM-CONV-001")

    response = client.post(
        URL_CONVERTIR.format(id=sol["id_solicitud_alquiler"]),
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONV-001", id_inmueble=id_inmueble),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["estado_reserva"] == "pendiente"
    assert data["codigo_reserva"] == "RL-CONV-001"
    assert len(data["objetos"]) == 1
    assert data["objetos"][0]["id_inmueble"] == id_inmueble

    row = db_session.execute(
        text(
            "SELECT id_solicitud_alquiler FROM reserva_locativa WHERE id_reserva_locativa = :id"
        ),
        {"id": data["id_reserva_locativa"]},
    ).mappings().one()
    assert row["id_solicitud_alquiler"] == sol["id_solicitud_alquiler"]


def test_convertir_solicitud_con_confirmar_true_crea_reserva_confirmada(client, db_session) -> None:
    sol = _crear_solicitud_aprobada(client, codigo="SOL-CONV-CONF-001")
    id_inmueble = _crear_inmueble_disponible(client, codigo="INM-CONV-CONF-001")

    response = client.post(
        URL_CONVERTIR.format(id=sol["id_solicitud_alquiler"]),
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONV-CONF-001", id_inmueble=id_inmueble, confirmar=True),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["estado_reserva"] == "confirmada"
    assert data["version_registro"] == 2

    row = db_session.execute(
        text(
            "SELECT estado_reserva, id_solicitud_alquiler FROM reserva_locativa WHERE id_reserva_locativa = :id"
        ),
        {"id": data["id_reserva_locativa"]},
    ).mappings().one()
    assert row["estado_reserva"] == "confirmada"
    assert row["id_solicitud_alquiler"] == sol["id_solicitud_alquiler"]


def test_confirmar_emite_evento_outbox(client, db_session) -> None:
    sol = _crear_solicitud_aprobada(client, codigo="SOL-CONV-EVT-001")
    id_inmueble = _crear_inmueble_disponible(client, codigo="INM-CONV-EVT-001")

    response = client.post(
        URL_CONVERTIR.format(id=sol["id_solicitud_alquiler"]),
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONV-EVT-001", id_inmueble=id_inmueble, confirmar=True),
    )
    assert response.status_code == 201
    id_reserva = response.json()["data"]["id_reserva_locativa"]

    outbox_row = db_session.execute(
        text(
            """
            SELECT event_type, aggregate_type, aggregate_id, status
            FROM outbox_event
            WHERE aggregate_type = 'reserva_locativa' AND aggregate_id = :id
            ORDER BY id DESC LIMIT 1
            """
        ),
        {"id": id_reserva},
    ).mappings().one_or_none()
    assert outbox_row is not None
    assert outbox_row["event_type"] == "reserva_locativa_confirmada"
    assert outbox_row["status"] == "PENDING"


def test_sin_confirmar_no_emite_evento_outbox(client, db_session) -> None:
    sol = _crear_solicitud_aprobada(client, codigo="SOL-CONV-NOEVT-001")
    id_inmueble = _crear_inmueble_disponible(client, codigo="INM-CONV-NOEVT-001")

    response = client.post(
        URL_CONVERTIR.format(id=sol["id_solicitud_alquiler"]),
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONV-NOEVT-001", id_inmueble=id_inmueble, confirmar=False),
    )
    assert response.status_code == 201
    id_reserva = response.json()["data"]["id_reserva_locativa"]

    outbox_row = db_session.execute(
        text(
            """
            SELECT 1 FROM outbox_event
            WHERE aggregate_type = 'reserva_locativa' AND aggregate_id = :id
            """
        ),
        {"id": id_reserva},
    ).mappings().one_or_none()
    assert outbox_row is None


# ── tests errores ─────────────────────────────────────────────────────────────

def test_convertir_solicitud_inexistente_devuelve_404(client) -> None:
    id_inmueble = _crear_inmueble_disponible(client, codigo="INM-CONV-NF-001")

    response = client.post(
        URL_CONVERTIR.format(id=999999),
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONV-NF-001", id_inmueble=id_inmueble),
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_convertir_solicitud_no_aprobada_devuelve_400(client) -> None:
    sol = client.post(
        "/api/v1/solicitudes-alquiler",
        headers=HEADERS,
        json=_payload_solicitud(codigo="SOL-CONV-NOAP-001"),
    )
    assert sol.status_code == 201
    id_sol = sol.json()["data"]["id_solicitud_alquiler"]
    id_inmueble = _crear_inmueble_disponible(client, codigo="INM-CONV-NOAP-001")

    response = client.post(
        URL_CONVERTIR.format(id=id_sol),
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONV-NOAP-001", id_inmueble=id_inmueble),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert "aprobada" in body["error_message"]
    assert body["details"]["errors"] == ["SOLICITUD_NOT_APROBADA"]


def test_convertir_solicitud_ya_convertida_devuelve_400(client) -> None:
    sol = _crear_solicitud_aprobada(client, codigo="SOL-CONV-DUP-001")
    id_inmueble = _crear_inmueble_disponible(client, codigo="INM-CONV-DUP-001")

    first = client.post(
        URL_CONVERTIR.format(id=sol["id_solicitud_alquiler"]),
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONV-DUP-001A", id_inmueble=id_inmueble),
    )
    assert first.status_code == 201

    response = client.post(
        URL_CONVERTIR.format(id=sol["id_solicitud_alquiler"]),
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONV-DUP-001B", id_inmueble=id_inmueble),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["details"]["errors"] == ["SOLICITUD_YA_CONVERTIDA"]


def test_convertir_inmueble_inexistente_devuelve_404(client) -> None:
    sol = _crear_solicitud_aprobada(client, codigo="SOL-CONV-NFINM-001")

    response = client.post(
        URL_CONVERTIR.format(id=sol["id_solicitud_alquiler"]),
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONV-NFINM-001", id_inmueble=999999),
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_convertir_sin_disponibilidad_devuelve_400(client) -> None:
    from tests.test_reservas_venta_create import _crear_inmueble

    sol = _crear_solicitud_aprobada(client, codigo="SOL-CONV-NODISP-001")
    id_inmueble = _crear_inmueble(client, codigo="INM-CONV-NODISP-001")

    response = client.post(
        URL_CONVERTIR.format(id=sol["id_solicitud_alquiler"]),
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONV-NODISP-001", id_inmueble=id_inmueble),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["details"]["errors"] == ["OBJECT_NOT_AVAILABLE"]
