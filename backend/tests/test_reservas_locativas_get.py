from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_locativas_create import (
    _apply_patch,
    _crear_inmueble_disponible,
    _payload_reserva,
)


def _crear_reserva(client, db_session, *, codigo: str, codigo_inm: str) -> dict:
    id_inmueble = _crear_inmueble_disponible(client, db_session, codigo=codigo_inm)
    response = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json=_payload_reserva(codigo=codigo, id_inmueble=id_inmueble),
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_get_reserva_locativa_devuelve_detalle_con_objetos(client, db_session) -> None:
    _apply_patch(db_session)
    reserva = _crear_reserva(client, db_session, codigo="RL-GET-001", codigo_inm="INM-RL-GET-001")

    response = client.get(f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["id_reserva_locativa"] == reserva["id_reserva_locativa"]
    assert data["uid_global"] == reserva["uid_global"]
    assert data["version_registro"] == reserva["version_registro"]
    assert data["codigo_reserva"] == "RL-GET-001"
    assert data["estado_reserva"] == "pendiente"
    assert len(data["objetos"]) == 1
    assert data["objetos"][0]["id_inmueble"] == reserva["objetos"][0]["id_inmueble"]
    assert isinstance(data["objetos"][0]["id_reserva_locativa_objeto"], int)
    assert data["deleted_at"] is None


def test_get_reserva_locativa_devuelve_404_si_no_existe(client, db_session) -> None:
    _apply_patch(db_session)

    response = client.get("/api/v1/reservas-locativas/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
    assert body["error_message"] == "La reserva locativa indicada no existe."
