from sqlalchemy import text

from tests.test_contratos_alquiler_create import _payload_base
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_inmueble


def _crear_contrato_borrador(client, *, codigo: str) -> dict:
    id_inmueble = _crear_inmueble(client, codigo=f"INM-{codigo}")

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato=codigo,
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
        ),
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_cancel_contrato_alquiler_pasa_de_borrador_a_cancelado(client, db_session) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-CAN-001")
    assert contrato["estado_contrato"] == "borrador"
    assert contrato["version_registro"] == 1

    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_contrato_alquiler"] == contrato["id_contrato_alquiler"]
    assert body["data"]["estado_contrato"] == "cancelado"
    assert body["data"]["version_registro"] == 2
    assert body["data"]["codigo_contrato"] == "CA-CAN-001"
    assert len(body["data"]["objetos"]) == 1
    assert body["data"]["condiciones_economicas_alquiler"] == []

    row = db_session.execute(
        text(
            """
            SELECT estado_contrato, version_registro
            FROM contrato_alquiler
            WHERE id_contrato_alquiler = :id
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).mappings().one()
    assert row["estado_contrato"] == "cancelado"
    assert row["version_registro"] == 2


def test_cancel_contrato_alquiler_devuelve_404_si_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/contratos-alquiler/999999/cancelar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
    assert response.json()["error_message"] == "El contrato de alquiler indicado no existe."


def test_cancel_contrato_alquiler_devuelve_400_si_estado_no_es_borrador(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-CAN-002")

    first = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/cancelar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    assert first.status_code == 200
    version_tras_cancelar = first.json()["data"]["version_registro"]

    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/cancelar",
        headers={**HEADERS, "If-Match-Version": str(version_tras_cancelar)},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"
    assert response.json()["error_message"] == "Solo un contrato en estado borrador puede cancelarse."


def test_cancel_contrato_alquiler_devuelve_409_si_version_no_coincide(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-CAN-003")

    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/cancelar",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
    assert "If-Match-Version" in response.json()["error_message"]
