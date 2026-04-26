from tests.test_contratos_alquiler_create import _payload_base
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_inmueble


def _crear_contrato_simple(client, *, codigo: str) -> dict:
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
    data = response.json()["data"]
    data["id_inmueble"] = id_inmueble
    return data


def test_list_contratos_alquiler_devuelve_items_y_total(client) -> None:
    contrato_a = _crear_contrato_simple(client, codigo="CA-LIST-001")
    contrato_b = _crear_contrato_simple(client, codigo="CA-LIST-002")

    response = client.get("/api/v1/contratos-alquiler")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert "data" in body
    assert body["data"]["total"] >= 2
    assert len(body["data"]["items"]) >= 2

    item = body["data"]["items"][0]
    assert "id_contrato_alquiler" in item
    assert "uid_global" in item
    assert "version_registro" in item
    assert "codigo_contrato" in item
    assert "fecha_inicio" in item
    assert "estado_contrato" in item
    assert "deleted_at" not in item

    codigos = {i["codigo_contrato"] for i in body["data"]["items"]}
    assert contrato_a["codigo_contrato"] in codigos
    assert contrato_b["codigo_contrato"] in codigos


def test_list_contratos_alquiler_filtra_por_estado(client) -> None:
    _crear_contrato_simple(client, codigo="CA-LIST-EST-001")

    response_borrador = client.get(
        "/api/v1/contratos-alquiler?estado_contrato=borrador&codigo_contrato=CA-LIST-EST-001"
    )
    assert response_borrador.status_code == 200
    body = response_borrador.json()
    assert body["data"]["total"] == 1
    assert body["data"]["items"][0]["codigo_contrato"] == "CA-LIST-EST-001"
    assert body["data"]["items"][0]["estado_contrato"] == "borrador"

    response_inexistente = client.get(
        "/api/v1/contratos-alquiler?estado_contrato=activo&codigo_contrato=CA-LIST-EST-001"
    )
    assert response_inexistente.status_code == 200
    assert response_inexistente.json()["data"]["total"] == 0
    assert response_inexistente.json()["data"]["items"] == []


def test_list_contratos_alquiler_paginacion(client) -> None:
    _crear_contrato_simple(client, codigo="CA-LIST-PGN-001")
    _crear_contrato_simple(client, codigo="CA-LIST-PGN-002")
    _crear_contrato_simple(client, codigo="CA-LIST-PGN-003")

    response_page1 = client.get("/api/v1/contratos-alquiler?limit=2&offset=0")
    assert response_page1.status_code == 200
    body_page1 = response_page1.json()
    assert body_page1["data"]["total"] >= 3
    assert len(body_page1["data"]["items"]) == 2

    response_page2 = client.get("/api/v1/contratos-alquiler?limit=2&offset=2")
    assert response_page2.status_code == 200
    body_page2 = response_page2.json()
    assert len(body_page2["data"]["items"]) >= 1

    ids_page1 = {i["id_contrato_alquiler"] for i in body_page1["data"]["items"]}
    ids_page2 = {i["id_contrato_alquiler"] for i in body_page2["data"]["items"]}
    assert ids_page1.isdisjoint(ids_page2)


def test_list_contratos_alquiler_filtra_por_id_inmueble(client) -> None:
    contrato = _crear_contrato_simple(client, codigo="CA-LIST-INM-001")
    id_inmueble = contrato["id_inmueble"]

    response = client.get(f"/api/v1/contratos-alquiler?id_inmueble={id_inmueble}")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["total"] >= 1
    codigos = {i["codigo_contrato"] for i in body["data"]["items"]}
    assert "CA-LIST-INM-001" in codigos

    response_otro = client.get("/api/v1/contratos-alquiler?id_inmueble=999999")
    assert response_otro.status_code == 200
    assert response_otro.json()["data"]["total"] == 0
