from sqlalchemy import text

HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _crear_inmueble(client, codigo: str, estado: str = "ACTIVO") -> int:
    response = client.post(
        "/api/v1/inmuebles",
        headers={**HEADERS, "X-Op-Id": f"550e8400-e29b-41d4-a716-44665544{abs(hash(codigo)) % 10000:04d}"},
        json={
            "id_desarrollo": None,
            "codigo_inmueble": codigo,
            "nombre_inmueble": f"Inmueble {codigo}",
            "superficie": "100.00",
            "estado_administrativo": estado,
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_inmueble"]


def test_buscar_existentes_devuelve_inmuebles_por_codigos(client) -> None:
    id_inmueble = _crear_inmueble(client, "IMP-BATCH-001")

    response = client.post(
        "/api/v1/inmuebles/importacion/buscar-existentes",
        json={"codigos": ["IMP-BATCH-001", "IMP-BATCH-NO"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "existentes": [
                {
                    "codigo": "IMP-BATCH-001",
                    "id_inmueble": id_inmueble,
                    "estado_inmueble": "ACTIVO",
                }
            ]
        },
    }


def test_buscar_existentes_compara_codigo_normalizado_case_insensitive(client) -> None:
    id_inmueble = _crear_inmueble(client, "IMP-BATCH-CASE")

    response = client.post(
        "/api/v1/inmuebles/importacion/buscar-existentes",
        json={"codigos": [" imp-batch-case "]},
    )

    assert response.status_code == 200
    assert response.json()["data"]["existentes"] == [
        {
            "codigo": "IMP-BATCH-CASE",
            "id_inmueble": id_inmueble,
            "estado_inmueble": "ACTIVO",
        }
    ]


def test_buscar_existentes_ignora_codigos_vacios_y_repetidos(client) -> None:
    id_inmueble = _crear_inmueble(client, "IMP-BATCH-002")

    response = client.post(
        "/api/v1/inmuebles/importacion/buscar-existentes",
        json={"codigos": ["", "  ", "IMP-BATCH-002", "IMP-BATCH-002"]},
    )

    assert response.status_code == 200
    assert response.json()["data"]["existentes"] == [
        {"codigo": "IMP-BATCH-002", "id_inmueble": id_inmueble, "estado_inmueble": "ACTIVO"}
    ]


def test_buscar_existentes_no_devuelve_inmuebles_borrados(client, db_session) -> None:
    id_inmueble = _crear_inmueble(client, "IMP-BATCH-DELETED")
    db_session.execute(
        text("UPDATE inmueble SET deleted_at = NOW() WHERE id_inmueble = :id_inmueble"),
        {"id_inmueble": id_inmueble},
    )
    db_session.flush()

    response = client.post(
        "/api/v1/inmuebles/importacion/buscar-existentes",
        json={"codigos": ["IMP-BATCH-DELETED"]},
    )

    assert response.status_code == 200
    assert response.json()["data"]["existentes"] == []


def test_buscar_existentes_soporta_lista_sin_coincidencias(client) -> None:
    response = client.post(
        "/api/v1/inmuebles/importacion/buscar-existentes",
        json={"codigos": ["IMP-BATCH-NONE"]},
    )

    assert response.status_code == 200
    assert response.json() == {"ok": True, "data": {"existentes": []}}
