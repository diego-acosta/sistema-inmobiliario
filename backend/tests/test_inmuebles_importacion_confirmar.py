from sqlalchemy import text

HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}

URL = "/api/v1/inmuebles/importacion/confirmar"


def _item(
    fila: int,
    codigo: str,
    *,
    partida: str | None = None,
    id_desarrollo: int | None = None,
) -> dict:
    item = {
        "fila": fila,
        "inmueble": {
            "codigo_inmueble": codigo,
            "nombre_inmueble": f"Lote {codigo}",
            "superficie": "10.5",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "id_desarrollo": id_desarrollo,
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
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "X-Op-Id" in body["error_message"]
    assert body["details"] == {"header": "X-Op-Id"}


def test_confirmacion_batch_no_requiere_if_match_version(client) -> None:
    response = client.post(
        URL, headers=HEADERS, json={"items": [_item(2, "IMP-BAT-NOIF-001")]}
    )
    assert response.status_code == 201


def test_confirmacion_batch_retry_mismo_op_id_devuelve_ids_existentes(client, db_session) -> None:
    headers = {**HEADERS, "X-Op-Id": "550e8400-e29b-41d4-a716-4466554400aa"}
    payload = {
        "items": [
            _item(2, "IMP-BAT-IDEMP-001", partida="P-IDEMP-1"),
            _item(3, "IMP-BAT-IDEMP-002"),
        ]
    }

    first = client.post(URL, headers=headers, json=payload)
    assert first.status_code == 201
    first_items = first.json()["data"]["items"]

    retry = client.post(URL, headers=headers, json=payload)
    assert retry.status_code == 201
    retry_body = retry.json()
    assert retry_body["ok"] is True
    assert retry_body["data"]["creados"] == 2
    assert retry_body["data"]["items"] == first_items

    count = db_session.execute(
        text(
            "SELECT count(*) FROM inmueble "
            "WHERE codigo_inmueble IN ('IMP-BAT-IDEMP-001', 'IMP-BAT-IDEMP-002')"
        )
    ).scalar_one()
    assert count == 2


def test_confirmacion_batch_mismo_codigo_con_otro_op_id_es_duplicado(client) -> None:
    first = client.post(
        URL,
        headers={**HEADERS, "X-Op-Id": "550e8400-e29b-41d4-a716-4466554400ab"},
        json={"items": [_item(2, "IMP-BAT-CONFLICT-001")]},
    )
    assert first.status_code == 201

    conflict = client.post(
        URL,
        headers={**HEADERS, "X-Op-Id": "550e8400-e29b-41d4-a716-4466554400ac"},
        json={"items": [_item(2, "IMP-BAT-CONFLICT-001")]},
    )
    assert conflict.status_code == 400
    assert "CODIGO_INMUEBLE_YA_EXISTE" in conflict.json()["details"]["errors"]


def test_confirmacion_batch_rollback_real_despues_de_insert_parcial(client, db_session) -> None:
    response = client.post(
        URL,
        headers={**HEADERS, "X-Op-Id": "550e8400-e29b-41d4-a716-4466554400ad"},
        json={
            "items": [
                _item(2, "IMP-BAT-ROLLBACK-REAL-001"),
                _item(3, "IMP-BAT-ROLLBACK-REAL-002", id_desarrollo=999999),
            ]
        },
    )

    assert response.status_code == 400
    assert "NOT_FOUND_DESARROLLO" in response.json()["details"]["errors"]
    count = db_session.execute(
        text(
            "SELECT count(*) FROM inmueble "
            "WHERE codigo_inmueble IN "
            "('IMP-BAT-ROLLBACK-REAL-001', 'IMP-BAT-ROLLBACK-REAL-002')"
        )
    ).scalar_one()
    assert count == 0
