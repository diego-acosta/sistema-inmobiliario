from sqlalchemy import text


def _seed_catalogo(db_session, codigo: str, nombre: str, descripcion: str | None = None) -> int:
    catalogo_id = db_session.execute(
        text("""
            INSERT INTO catalogo_maestro (
                codigo_catalogo_maestro, nombre_catalogo_maestro, descripcion
            ) VALUES (:codigo, :nombre, :descripcion)
            RETURNING id_catalogo_maestro
            """),
        {"codigo": codigo, "nombre": nombre, "descripcion": descripcion},
    ).scalar_one()
    db_session.flush()
    return catalogo_id


def _seed_item(
    db_session,
    catalogo_id: int,
    codigo: str,
    nombre: str,
    descripcion: str | None = None,
    estado: str | None = None,
) -> int:
    item_id = db_session.execute(
        text("""
            INSERT INTO item_catalogo (
                id_catalogo_maestro, codigo_item_catalogo, nombre_item_catalogo,
                descripcion, estado_item_catalogo
            ) VALUES (:catalogo_id, :codigo, :nombre, :descripcion, :estado)
            RETURNING id_item_catalogo
            """),
        {
            "catalogo_id": catalogo_id,
            "codigo": codigo,
            "nombre": nombre,
            "descripcion": descripcion,
            "estado": estado,
        },
    ).scalar_one()
    db_session.flush()
    return item_id


def _catalogos_data(response):
    return response.json()["data"]


def _items_data(response):
    return response.json()["data"]


def test_list_catalogos_devuelve_lista_vacia(client):
    response = client.get("/api/v1/administrativo/catalogos?q=ADM360_NO_EXISTE")

    assert response.status_code == 200
    data = _catalogos_data(response)
    assert data == {"items": [], "total": 0, "page": 1, "page_size": 50}


def test_list_catalogos_devuelve_varios_con_orden_determinista(client, db_session):
    beta = _seed_catalogo(db_session, "ADM360_BETA", "Beta")
    alfa = _seed_catalogo(db_session, "ADM360_ALFA", "Alfa")

    response = client.get("/api/v1/administrativo/catalogos?q=ADM360_&page_size=10")

    assert response.status_code == 200
    data = _catalogos_data(response)
    ids = [item["id_catalogo_maestro"] for item in data["items"]]
    assert ids == [alfa, beta]
    assert data["total"] == 2


def test_list_catalogos_busca_por_codigo_y_nombre(client, db_session):
    by_codigo = _seed_catalogo(db_session, "ADM360_COD_BUSCADO", "Nombre genérico")
    by_nombre = _seed_catalogo(db_session, "ADM360_OTRO", "Nombre buscado catálogo")

    codigo_response = client.get("/api/v1/administrativo/catalogos?q=COD_BUSCADO")
    nombre_response = client.get("/api/v1/administrativo/catalogos?q=buscado catálogo")

    assert codigo_response.status_code == 200
    assert [item["id_catalogo_maestro"] for item in _catalogos_data(codigo_response)["items"]] == [by_codigo]
    assert nombre_response.status_code == 200
    assert [item["id_catalogo_maestro"] for item in _catalogos_data(nombre_response)["items"]] == [by_nombre]


def test_list_catalogos_pagina_y_total_correcto(client, db_session):
    _seed_catalogo(db_session, "ADM360_PAGE_A", "Page A")
    second = _seed_catalogo(db_session, "ADM360_PAGE_B", "Page B")
    _seed_catalogo(db_session, "ADM360_PAGE_C", "Page C")

    response = client.get("/api/v1/administrativo/catalogos?q=ADM360_PAGE&page=2&page_size=1")

    assert response.status_code == 200
    data = _catalogos_data(response)
    assert data["total"] == 3
    assert data["page"] == 2
    assert data["page_size"] == 1
    assert [item["id_catalogo_maestro"] for item in data["items"]] == [second]


def test_list_catalogos_valida_page_y_page_size(client):
    page_response = client.get("/api/v1/administrativo/catalogos?page=0")
    page_size_response = client.get("/api/v1/administrativo/catalogos?page_size=0")

    assert page_response.status_code == 422
    assert page_size_response.status_code == 422


def test_get_catalogo_existente(client, db_session):
    catalogo_id = _seed_catalogo(db_session, "ADM360_DET", "Detalle", "Descripción")

    response = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}")

    assert response.status_code == 200
    assert response.json()["data"] == {
        "id_catalogo_maestro": catalogo_id,
        "codigo_catalogo_maestro": "ADM360_DET",
        "nombre_catalogo_maestro": "Detalle",
        "descripcion": "Descripción",
    }


def test_get_catalogo_inexistente_devuelve_404(client):
    response = client.get("/api/v1/administrativo/catalogos/999999999")

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_list_items_catalogo_existente_sin_items_devuelve_lista_vacia(client, db_session):
    catalogo_id = _seed_catalogo(db_session, "ADM360_EMPTY_ITEMS", "Sin ítems")

    response = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}/items")

    assert response.status_code == 200
    assert _items_data(response) == {"items": [], "total": 0, "page": 1, "page_size": 50}


def test_list_items_no_mezcla_catalogos_y_ordena(client, db_session):
    catalogo_id = _seed_catalogo(db_session, "ADM360_ITEMS", "Ítems")
    otro_catalogo_id = _seed_catalogo(db_session, "ADM360_ITEMS_OTRO", "Ítems otro")
    second = _seed_item(db_session, catalogo_id, "B", "Beta", estado="ACTIVO")
    first = _seed_item(db_session, catalogo_id, "A", "Alfa", estado="INACTIVO")
    _seed_item(db_session, otro_catalogo_id, "A", "No mezclado", estado="ACTIVO")

    response = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}/items")

    assert response.status_code == 200
    data = _items_data(response)
    assert [item["id_item_catalogo"] for item in data["items"]] == [first, second]
    assert {item["id_catalogo_maestro"] for item in data["items"]} == {catalogo_id}
    assert data["total"] == 2


def test_list_items_busca_por_codigo_y_nombre(client, db_session):
    catalogo_id = _seed_catalogo(db_session, "ADM360_ITEMS_SEARCH", "Buscar ítems")
    by_codigo = _seed_item(db_session, catalogo_id, "COD_BUSCADO", "Nombre genérico")
    by_nombre = _seed_item(db_session, catalogo_id, "OTRO", "Nombre buscado item")

    codigo_response = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}/items?q=COD_BUSCADO")
    nombre_response = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}/items?q=buscado item")

    assert codigo_response.status_code == 200
    assert [item["id_item_catalogo"] for item in _items_data(codigo_response)["items"]] == [by_codigo]
    assert nombre_response.status_code == 200
    assert [item["id_item_catalogo"] for item in _items_data(nombre_response)["items"]] == [by_nombre]


def test_list_items_filtra_estado_literal_y_preserva_nulo(client, db_session):
    catalogo_id = _seed_catalogo(db_session, "ADM360_ESTADOS", "Estados")
    activo = _seed_item(db_session, catalogo_id, "ACT", "Activo", estado="ACTIVO")
    nulo = _seed_item(db_session, catalogo_id, "NUL", "Nulo", estado=None)

    filtered = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}/items?estado_item_catalogo=ACTIVO")
    all_items = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}/items")

    assert filtered.status_code == 200
    assert [item["id_item_catalogo"] for item in _items_data(filtered)["items"]] == [activo]
    assert all_items.status_code == 200
    items_by_id = {item["id_item_catalogo"]: item for item in _items_data(all_items)["items"]}
    assert items_by_id[nulo]["estado_item_catalogo"] is None


def test_list_items_pagina_y_total_correcto(client, db_session):
    catalogo_id = _seed_catalogo(db_session, "ADM360_ITEMS_PAGE", "Page ítems")
    _seed_item(db_session, catalogo_id, "A", "A")
    second = _seed_item(db_session, catalogo_id, "B", "B")
    _seed_item(db_session, catalogo_id, "C", "C")

    response = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}/items?page=2&page_size=1")

    assert response.status_code == 200
    data = _items_data(response)
    assert data["total"] == 3
    assert data["page"] == 2
    assert data["page_size"] == 1
    assert [item["id_item_catalogo"] for item in data["items"]] == [second]


def test_list_items_catalogo_inexistente_devuelve_404(client):
    response = client.get("/api/v1/administrativo/catalogos/999999999/items")

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_catalogos_readlike_sin_headers_ni_efectos_laterales(client, db_session):
    catalogo_id = _seed_catalogo(db_session, "ADM360_READLIKE", "Read like")
    item_id = _seed_item(db_session, catalogo_id, "READ", "Read", estado=None)
    outbox_before = db_session.execute(text("SELECT COUNT(*) FROM outbox_event")).scalar_one()

    catalogos = client.get("/api/v1/administrativo/catalogos?q=ADM360_READLIKE")
    detalle = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}")
    items = client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}/items")

    assert catalogos.status_code == 200
    assert detalle.status_code == 200
    assert items.status_code == 200
    assert db_session.execute(text("SELECT COUNT(*) FROM outbox_event")).scalar_one() == outbox_before
    assert db_session.execute(text("SELECT COUNT(*) FROM catalogo_maestro WHERE id_catalogo_maestro = :id"), {"id": catalogo_id}).scalar_one() == 1
    assert db_session.execute(text("SELECT COUNT(*) FROM item_catalogo WHERE id_item_catalogo = :id"), {"id": item_id}).scalar_one() == 1


def test_catalogos_readonly_excluyen_bajas_logicas(client, db_session):
    catalogo_id = _seed_catalogo(db_session, "ADM363_BAJA", "Baja")
    item_id = _seed_item(db_session, catalogo_id, "BAJA", "Baja")
    db_session.execute(text("UPDATE item_catalogo SET deleted_at = CURRENT_TIMESTAMP WHERE id_item_catalogo = :id"), {"id": item_id})
    db_session.execute(text("UPDATE catalogo_maestro SET deleted_at = CURRENT_TIMESTAMP WHERE id_catalogo_maestro = :id"), {"id": catalogo_id})
    db_session.commit()

    assert client.get("/api/v1/administrativo/catalogos?q=ADM363_BAJA").json()["data"]["items"] == []
    assert client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}").status_code == 404
    assert client.get(f"/api/v1/administrativo/catalogos/{catalogo_id}/items").status_code == 404
