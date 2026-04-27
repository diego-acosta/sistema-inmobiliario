from tests.test_disponibilidades_create import HEADERS
from tests.test_solicitudes_alquiler_create import _payload


def _crear_solicitud(client, *, codigo: str) -> dict:
    response = client.post(
        "/api/v1/solicitudes-alquiler", headers=HEADERS, json=_payload(codigo=codigo)
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_cancelar_solicitud_alquiler_desde_pendiente(client) -> None:
    sol = _crear_solicitud(client, codigo="SOL-CAN-001")

    response = client.patch(
        f"/api/v1/solicitudes-alquiler/{sol['id_solicitud_alquiler']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(sol["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["estado_solicitud"] == "cancelada"
    assert body["data"]["version_registro"] == 2


def test_cancelar_solicitud_alquiler_desde_aprobada(client) -> None:
    sol = _crear_solicitud(client, codigo="SOL-CAN-002")

    aprobada = client.patch(
        f"/api/v1/solicitudes-alquiler/{sol['id_solicitud_alquiler']}/aprobar",
        headers={**HEADERS, "If-Match-Version": str(sol["version_registro"])},
    )
    assert aprobada.status_code == 200
    version_aprobada = aprobada.json()["data"]["version_registro"]

    response = client.patch(
        f"/api/v1/solicitudes-alquiler/{sol['id_solicitud_alquiler']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(version_aprobada)},
    )

    assert response.status_code == 200
    assert response.json()["data"]["estado_solicitud"] == "cancelada"


def test_cancelar_solicitud_alquiler_devuelve_400_desde_rechazada(client) -> None:
    sol = _crear_solicitud(client, codigo="SOL-CAN-003")

    rechazada = client.patch(
        f"/api/v1/solicitudes-alquiler/{sol['id_solicitud_alquiler']}/rechazar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    assert rechazada.status_code == 200
    version_rechazada = rechazada.json()["data"]["version_registro"]

    response = client.patch(
        f"/api/v1/solicitudes-alquiler/{sol['id_solicitud_alquiler']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(version_rechazada)},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"


def test_cancelar_solicitud_alquiler_devuelve_404_si_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/solicitudes-alquiler/999999/cancelar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_cancelar_solicitud_alquiler_devuelve_409_si_version_no_coincide(client) -> None:
    sol = _crear_solicitud(client, codigo="SOL-CAN-004")

    response = client.patch(
        f"/api/v1/solicitudes-alquiler/{sol['id_solicitud_alquiler']}/cancelar",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
    assert "If-Match-Version" in response.json()["error_message"]
