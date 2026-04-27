from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_locativas_create import (
    _apply_patch,
    _crear_inmueble_disponible,
    _payload_reserva,
)


def _crear_reserva_pendiente(client, db_session, *, codigo: str, codigo_inm: str) -> dict:
    id_inmueble = _crear_inmueble_disponible(client, db_session, codigo=codigo_inm)
    response = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json=_payload_reserva(codigo=codigo, id_inmueble=id_inmueble),
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_confirmar_reserva_locativa_pendiente_a_confirmada(client, db_session) -> None:
    _apply_patch(db_session)
    reserva = _crear_reserva_pendiente(
        client, db_session, codigo="RL-CONF-OK-001", codigo_inm="INM-RL-CONF-OK-001"
    )
    assert reserva["estado_reserva"] == "pendiente"
    assert reserva["version_registro"] == 1

    response = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["estado_reserva"] == "confirmada"
    assert data["version_registro"] == 2
    assert len(data["objetos"]) == 1

    row = db_session.execute(
        text(
            "SELECT estado_reserva, version_registro FROM reserva_locativa WHERE id_reserva_locativa = :id"
        ),
        {"id": reserva["id_reserva_locativa"]},
    ).mappings().one()
    assert row["estado_reserva"] == "confirmada"
    assert row["version_registro"] == 2


def test_confirmar_emite_outbox_reserva_locativa_confirmada(client, db_session) -> None:
    _apply_patch(db_session)
    reserva = _crear_reserva_pendiente(
        client, db_session, codigo="RL-CONF-EVT-001", codigo_inm="INM-RL-CONF-EVT-001"
    )

    client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    outbox_row = db_session.execute(
        text(
            """
            SELECT event_type, aggregate_type, aggregate_id, status
            FROM outbox_event
            WHERE aggregate_type = 'reserva_locativa'
              AND aggregate_id = :id
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"id": reserva["id_reserva_locativa"]},
    ).mappings().one_or_none()
    assert outbox_row is not None
    assert outbox_row["event_type"] == "reserva_locativa_confirmada"
    assert outbox_row["aggregate_id"] == reserva["id_reserva_locativa"]
    assert outbox_row["status"] == "PENDING"


def test_confirmar_reserva_locativa_devuelve_404_si_no_existe(client, db_session) -> None:
    _apply_patch(db_session)

    response = client.patch(
        "/api/v1/reservas-locativas/999999/confirmar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_confirmar_reserva_locativa_devuelve_400_si_estado_no_es_pendiente(
    client, db_session
) -> None:
    _apply_patch(db_session)
    reserva = _crear_reserva_pendiente(
        client, db_session, codigo="RL-CONF-ST-001", codigo_inm="INM-RL-CONF-ST-001"
    )

    first = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/confirmar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    assert first.status_code == 200
    version_confirmada = first.json()["data"]["version_registro"]

    response = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(version_confirmada)},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert "pendiente" in body["error_message"]


def test_confirmar_reserva_locativa_devuelve_409_si_version_no_coincide(
    client, db_session
) -> None:
    _apply_patch(db_session)
    reserva = _crear_reserva_pendiente(
        client, db_session, codigo="RL-CONF-VER-001", codigo_inm="INM-RL-CONF-VER-001"
    )

    response = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/confirmar",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "CONCURRENCY_ERROR"
    assert "If-Match-Version" in body["error_message"]
