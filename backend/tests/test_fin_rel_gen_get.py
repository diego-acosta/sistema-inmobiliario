"""
Tests de integración para GET /api/v1/financiero/relaciones-generadoras/{id}
y GET /api/v1/financiero/relaciones-generadoras (list).
"""
from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_rel_gen_create import _crear_contrato, _crear_relacion_generadora


URL_DETAIL = "/api/v1/financiero/relaciones-generadoras/{id}"
URL_LIST = "/api/v1/financiero/relaciones-generadoras"


# ── GET by id ─────────────────────────────────────────────────────────────────

def test_fin_rel_gen_get_by_id_ok(client) -> None:
    contrato = _crear_contrato(client, codigo="FIN-RG-GET-001")
    rg = _crear_relacion_generadora(
        client, id_origen=contrato["id_contrato_alquiler"], descripcion="Cuota 1"
    )

    response = client.get(URL_DETAIL.format(id=rg["id_relacion_generadora"]))

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["id_relacion_generadora"] == rg["id_relacion_generadora"]
    assert data["tipo_origen"] == "CONTRATO_ALQUILER"
    assert data["id_origen"] == contrato["id_contrato_alquiler"]
    assert data["descripcion"] == "Cuota 1"
    assert data["version_registro"] == 1
    assert data["uid_global"] == rg["uid_global"]
    assert data["fecha_alta"] is not None


def test_fin_rel_gen_get_by_id_not_found(client) -> None:
    response = client.get(URL_DETAIL.format(id=999999))

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


# ── GET list ──────────────────────────────────────────────────────────────────

def test_fin_rel_gen_list_devuelve_registros(client) -> None:
    contrato = _crear_contrato(client, codigo="FIN-RG-LST-001")
    _crear_relacion_generadora(client, id_origen=contrato["id_contrato_alquiler"])

    response = client.get(URL_LIST)

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["total"] >= 1
    assert isinstance(body["data"]["items"], list)


def test_fin_rel_gen_list_filtra_por_tipo_origen(client) -> None:
    contrato = _crear_contrato(client, codigo="FIN-RG-FTIPO-001")
    rg = _crear_relacion_generadora(
        client, id_origen=contrato["id_contrato_alquiler"]
    )

    response = client.get(URL_LIST, params={"tipo_origen": "CONTRATO_ALQUILER"})

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert all(i["tipo_origen"] == "CONTRATO_ALQUILER" for i in items)
    ids = [i["id_relacion_generadora"] for i in items]
    assert rg["id_relacion_generadora"] in ids


def test_fin_rel_gen_list_filtra_por_id_origen(client) -> None:
    contrato = _crear_contrato(client, codigo="FIN-RG-FORIG-001")
    rg = _crear_relacion_generadora(
        client, id_origen=contrato["id_contrato_alquiler"]
    )

    response = client.get(
        URL_LIST,
        params={"id_origen": contrato["id_contrato_alquiler"]},
    )

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert len(items) >= 1
    assert all(i["id_origen"] == contrato["id_contrato_alquiler"] for i in items)
    ids = [i["id_relacion_generadora"] for i in items]
    assert rg["id_relacion_generadora"] in ids


def test_fin_rel_gen_list_tipo_invalido_no_devuelve_resultados(client) -> None:
    response = client.get(URL_LIST, params={"tipo_origen": "NO_EXISTE"})

    assert response.status_code == 200
    assert response.json()["data"]["total"] == 0


def test_fin_rel_gen_list_paginacion(client) -> None:
    contrato = _crear_contrato(client, codigo="FIN-RG-PAG-001")
    for i in range(3):
        _crear_relacion_generadora(
            client,
            id_origen=contrato["id_contrato_alquiler"],
            descripcion=f"Item {i}",
        )

    response = client.get(
        URL_LIST,
        params={
            "id_origen": contrato["id_contrato_alquiler"],
            "limit": 2,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 3
    assert len(data["items"]) == 2
