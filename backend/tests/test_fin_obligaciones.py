"""
Tests de integración para GET /api/v1/financiero/obligaciones/{id}.
No existe seed de obligaciones: los tests de 404 son suficientes para
verificar que el endpoint responde correctamente sin datos.
"""
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_rel_gen_create import URL as URL_RELACIONES, _payload


URL_OBLIGACION = "/api/v1/financiero/obligaciones/{id}"


def test_get_obligacion_not_found_devuelve_404(client) -> None:
    response = client.get(URL_OBLIGACION.format(id=999999), headers=HEADERS)

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_get_obligacion_shape_de_error(client) -> None:
    response = client.get(URL_OBLIGACION.format(id=999998), headers=HEADERS)

    assert response.status_code == 404
    body = response.json()
    assert "error_code" in body
    assert "error_message" in body


def test_servicio_trasladado_ya_no_es_aceptado(client) -> None:
    """SERVICIO_TRASLADADO fue removido: el trigger SQL solo permite venta y contrato_alquiler."""
    response = client.post(
        URL_RELACIONES,
        headers=HEADERS,
        json=_payload(tipo_origen="SERVICIO_TRASLADADO", id_origen=1),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["details"]["errors"] == ["TIPO_ORIGEN_INVALIDO"]
