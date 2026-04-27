from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_locativas_create import (
    _crear_inmueble_disponible,
    _payload_reserva,
)


def _crear_reserva_pendiente(client, *, codigo: str, codigo_inm: str) -> dict:
    id_inmueble = _crear_inmueble_disponible(client, codigo=codigo_inm)
    response = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json=_payload_reserva(codigo=codigo, id_inmueble=id_inmueble),
    )
    assert response.status_code == 201
    return response.json()["data"]


def _confirmar(client, reserva: dict) -> dict:
    response = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/confirmar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )
    assert response.status_code == 200
    return response.json()["data"]


def test_cancelar_reserva_locativa_desde_pendiente(client, db_session) -> None:
    reserva = _crear_reserva_pendiente(
        client, codigo="RL-CAN-001", codigo_inm="INM-RL-CAN-001"
    )

    response = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["estado_reserva"] == "cancelada"
    assert body["data"]["version_registro"] == 2

    row = db_session.execute(
        text("SELECT estado_reserva FROM reserva_locativa WHERE id_reserva_locativa = :id"),
        {"id": reserva["id_reserva_locativa"]},
    ).mappings().one()
    assert row["estado_reserva"] == "cancelada"


def test_cancelar_reserva_locativa_desde_confirmada(client) -> None:
    reserva = _crear_reserva_pendiente(
        client, codigo="RL-CAN-002", codigo_inm="INM-RL-CAN-002"
    )
    confirmada = _confirmar(client, reserva)
    assert confirmada["estado_reserva"] == "confirmada"

    response = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(confirmada["version_registro"])},
    )

    assert response.status_code == 200
    assert response.json()["data"]["estado_reserva"] == "cancelada"


def test_cancelar_reserva_locativa_devuelve_404_si_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/reservas-locativas/999999/cancelar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_cancelar_reserva_locativa_devuelve_400_si_ya_cancelada(client) -> None:
    reserva = _crear_reserva_pendiente(
        client, codigo="RL-CAN-003", codigo_inm="INM-RL-CAN-003"
    )

    first = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/cancelar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    assert first.status_code == 200
    version_cancelada = first.json()["data"]["version_registro"]

    response = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(version_cancelada)},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"


def test_cancelar_reserva_locativa_devuelve_409_si_version_no_coincide(client) -> None:
    reserva = _crear_reserva_pendiente(
        client, codigo="RL-CAN-004", codigo_inm="INM-RL-CAN-004"
    )

    response = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/cancelar",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "CONCURRENCY_ERROR"
    assert "If-Match-Version" in body["error_message"]
