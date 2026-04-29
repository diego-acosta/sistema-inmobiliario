"""
Tests de integración para GET /api/v1/financiero/conceptos-financieros.
Requiere que seed_test_baseline.sql haya sido aplicado (17 conceptos).
"""
from tests.test_disponibilidades_create import HEADERS


URL = "/api/v1/financiero/conceptos-financieros"


def test_list_conceptos_devuelve_registros_del_seed(client) -> None:
    response = client.get(URL, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["total"] >= 1
    assert isinstance(body["data"]["items"], list)


def test_list_conceptos_shape_de_item(client) -> None:
    response = client.get(URL, headers=HEADERS)

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) >= 1

    item = items[0]
    assert isinstance(item["id_concepto_financiero"], int)
    assert isinstance(item["codigo_concepto_financiero"], str)
    assert isinstance(item["nombre_concepto_financiero"], str)
    assert isinstance(item["tipo_concepto_financiero"], str)
    assert isinstance(item["naturaleza_concepto"], str)
    assert isinstance(item["estado_concepto_financiero"], str)


def test_list_conceptos_contiene_canon_locativo(client) -> None:
    response = client.get(URL, headers=HEADERS)

    assert response.status_code == 200
    codigos = [i["codigo_concepto_financiero"] for i in response.json()["data"]["items"]]
    assert "CANON_LOCATIVO" in codigos


def test_list_conceptos_filtra_por_estado_activo(client) -> None:
    response = client.get(URL, params={"estado": "ACTIVO"}, headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["total"] >= 1
    assert all(
        i["estado_concepto_financiero"] == "ACTIVO"
        for i in body["data"]["items"]
    )


def test_list_conceptos_paginacion(client) -> None:
    response_all = client.get(URL, params={"limit": 200}, headers=HEADERS)
    total = response_all.json()["data"]["total"]

    response_page = client.get(URL, params={"limit": 2, "offset": 0}, headers=HEADERS)
    assert response_page.status_code == 200
    data = response_page.json()["data"]
    assert data["total"] == total
    assert len(data["items"]) == min(2, total)
