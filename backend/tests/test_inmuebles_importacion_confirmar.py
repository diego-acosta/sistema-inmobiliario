from sqlalchemy import text

HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}

URL = "/api/v1/inmuebles/importacion/confirmar"


def _item(fila: int, codigo: str, *, partida: str | None = None) -> dict:
    item = {
        "fila": fila,
        "inmueble": {
            "codigo_inmueble": codigo,
            "nombre_inmueble": f"Lote {codigo}",
            "superficie": "10.5",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
        },
    }
    if partida:
        item["dato_catastral_registral"] = {
            "partida_inmobiliaria": partida,
            "manzana": "M1",
            "lote": "L1",
            "estado_dato": "ACTIVO",
        }
    return item


def test_confirmacion_batch_crea_multiples_inmuebles_y_devuelve_data(client, db_session) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json={"items": [_item(2, "IMP-BAT-001"), _item(3, "IMP-BAT-002")]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["creados"] == 2
    assert [item["codigo_inmueble"] for item in body["data"]["items"]] == [
        "IMP-BAT-001",
        "IMP-BAT-002",
    ]

    count = db_session.execute(
        text(
            "SELECT count(*) FROM inmueble "
            "WHERE codigo_inmueble IN ('IMP-BAT-001', 'IMP-BAT-002')"
        )
    ).scalar_one()
    assert count == 2


def test_confirmacion_batch_crea_dato_catastral_asociado(client, db_session) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json={"items": [_item(2, "IMP-BAT-CAT-001", partida="P-001")]},
    )

    assert response.status_code == 201
    item = response.json()["data"]["items"][0]
    assert item["id_dato_catastral_registral"] is not None

    row = db_session.execute(
        text(
            """
            SELECT d.partida_inmobiliaria
            FROM inmueble_dato_catastral_registral d
            WHERE d.id_inmueble = :id_inmueble
            """
        ),
        {"id_inmueble": item["id_inmueble"]},
    ).mappings().one()
    assert row["partida_inmobiliaria"] == "P-001"


def test_confirmacion_batch_rollback_total_si_falla_una_fila(client, db_session) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json={
            "items": [
                _item(2, "IMP-BAT-RB-001"),
                _item(3, "IMP-BAT-RB-002", partida="P-FAIL"),
            ]
        },
    )
    assert response.status_code == 201

    response_dup = client.post(
        URL,
        headers={**HEADERS, "X-Op-Id": "550e8400-e29b-41d4-a716-446655440001"},
        json={"items": [_item(4, "IMP-BAT-RB-003"), _item(5, "IMP-BAT-RB-003")]},
    )
    assert response_dup.status_code == 400

    count = db_session.execute(
        text("SELECT count(*) FROM inmueble WHERE codigo_inmueble IN ('IMP-BAT-RB-003')")
    ).scalar_one()
    assert count == 0


def test_confirmacion_batch_rechaza_duplicado_existente(client) -> None:
    first = client.post(
        URL, headers=HEADERS, json={"items": [_item(2, "IMP-BAT-DUP-001")]}
    )
    assert first.status_code == 201

    second = client.post(
        URL,
        headers={**HEADERS, "X-Op-Id": "550e8400-e29b-41d4-a716-446655440002"},
        json={"items": [_item(3, "IMP-BAT-DUP-001")]},
    )
    assert second.status_code == 400


def test_confirmacion_batch_requiere_headers_core_ef(client) -> None:
    headers = dict(HEADERS)
    headers.pop("X-Op-Id")
    response = client.post(
        URL, headers=headers, json={"items": [_item(2, "IMP-BAT-HDR-001")]}
    )
    assert response.status_code == 400
    assert response.json()["error_code"] == "CORE_EF_HEADER_REQUIRED"


def test_confirmacion_batch_no_requiere_if_match_version(client) -> None:
    response = client.post(
        URL, headers=HEADERS, json={"items": [_item(2, "IMP-BAT-NOIF-001")]}
    )
    assert response.status_code == 201
