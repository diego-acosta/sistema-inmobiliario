from uuid import uuid4

HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _headers(**extra):
    return {**HEADERS, "X-Op-Id": str(uuid4()), **extra}


def _crear_inmueble(client, codigo="INM-DCR-001") -> int:
    response = client.post(
        "/api/v1/inmuebles",
        headers=_headers(),
        json={
            "id_desarrollo": None,
            "codigo_inmueble": codigo,
            "nombre_inmueble": "Inmueble dato catastral",
            "superficie": "100.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_inmueble"]


def _payload(**overrides):
    payload = {
        "nomenclatura_catastral": "NC-001",
        "partida_inmobiliaria": "PI-001",
        "matricula": "MAT-001",
        "folio_real": "FR-001",
        "circunscripcion": "C1",
        "seccion": "S1",
        "chacra": None,
        "quinta": None,
        "fraccion": None,
        "manzana": "M1",
        "lote": "L1",
        "parcela": "P1",
        "subparcela": None,
        "superficie_titulo": "100.25",
        "superficie_mensura": "99.50",
        "medidas": "10x10",
        "situacion_posesoria": "POSESION",
        "situacion_dominial": "DOMINIO",
        "organismo_origen": "Catastro",
        "fecha_desde": "2026-01-01T00:00:00",
        "fecha_hasta": "2026-12-31T00:00:00",
        "estado_dato": "ACTIVO",
        "observaciones": "dato inicial",
    }
    payload.update(overrides)
    return payload


def test_crear_listar_actualizar_y_baja_dato_catastral_registral(client):
    id_inmueble = _crear_inmueble(client)

    create = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales",
        headers=_headers(),
        json=_payload(),
    )
    assert create.status_code == 201
    data = create.json()["data"]
    assert data["id_inmueble"] == id_inmueble
    assert data["version_registro"] == 1
    assert "linderos" not in data
    id_dato = data["id_dato_catastral_registral"]

    listed = client.get(f"/api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales")
    assert listed.status_code == 200
    assert len(listed.json()["data"]) == 1
    assert "linderos" not in listed.json()["data"][0]

    updated = client.put(
        f"/api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales/{id_dato}",
        headers=_headers(**{"If-Match-Version": "1"}),
        json=_payload(matricula="MAT-002", estado_dato="HISTORICO"),
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["version_registro"] == 2
    assert updated.json()["data"]["matricula"] == "MAT-002"

    conflict = client.put(
        f"/api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales/{id_dato}",
        headers=_headers(**{"If-Match-Version": "1"}),
        json=_payload(matricula="MAT-003"),
    )
    assert conflict.status_code == 409
    assert conflict.json()["error_code"] == "CONCURRENCY_ERROR"

    baja = client.patch(
        f"/api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales/{id_dato}/baja",
        headers=_headers(**{"If-Match-Version": "2"}),
    )
    assert baja.status_code == 200
    assert baja.json()["data"] == {
        "id_dato_catastral_registral": id_dato,
        "id_inmueble": id_inmueble,
        "version_registro": 3,
        "deleted": True,
    }

    empty = client.get(f"/api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales")
    assert empty.status_code == 200
    assert empty.json()["data"] == []


def test_no_permite_inmueble_inexistente(client):
    response = client.post(
        "/api/v1/inmuebles/999999/datos-catastrales-registrales",
        headers=_headers(),
        json=_payload(),
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND_INMUEBLE"


def test_no_permite_superficie_negativa(client):
    id_inmueble = _crear_inmueble(client, "INM-DCR-NEG")
    response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales",
        headers=_headers(),
        json=_payload(superficie_titulo="-1.00"),
    )
    assert response.status_code == 422
    assert "INVALID_SUPERFICIE" in response.text


def test_no_permite_fecha_hasta_menor_a_fecha_desde(client):
    id_inmueble = _crear_inmueble(client, "INM-DCR-FEC")
    response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales",
        headers=_headers(),
        json=_payload(fecha_desde="2026-02-01T00:00:00", fecha_hasta="2026-01-01T00:00:00"),
    )
    assert response.status_code == 422
    assert "INVALID_DATE_RANGE" in response.text


def test_no_incluye_linderos_en_request_response(client):
    id_inmueble = _crear_inmueble(client, "INM-DCR-LIN")
    response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/datos-catastrales-registrales",
        headers=_headers(),
        json=_payload(linderos="no debe existir"),
    )
    assert response.status_code == 201
    assert "linderos" not in response.json()["data"]
