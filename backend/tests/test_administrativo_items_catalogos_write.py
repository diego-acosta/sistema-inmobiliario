from uuid import uuid4

from sqlalchemy import text


def _headers(version=None, op_id=None):
    value = {
        "X-Op-Id": op_id or str(uuid4()),
        "X-Usuario-Id": "1",
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
    }
    if version is not None:
        value["If-Match-Version"] = str(version)
    return value


def _catalogo(client):
    return client.post(
        "/api/v1/administrativo/catalogos",
        json={
            "codigo_catalogo_maestro": f"IT_{uuid4().hex[:10]}",
            "nombre_catalogo_maestro": "Items",
            "descripcion": None,
        },
        headers=_headers(),
    ).json()["data"]


def _item(client, catalogo, op_id=None):
    payload = {
        "codigo_item_catalogo": f"I_{uuid4().hex[:10]}",
        "nombre_item_catalogo": "Ítem",
        "descripcion": None,
    }
    response = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(op_id=op_id),
    )
    return response, payload


def test_item_write_crud_idempotencia_y_outbox(client, db_session):
    catalogo = _catalogo(client)
    op = str(uuid4())
    create, payload = _item(client, catalogo, op)
    assert create.status_code == 201
    item = create.json()["data"]
    assert item["estado_item_catalogo"] == "ACTIVO" and item["version_registro"] == 1
    replay = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(op_id=op),
    )
    assert replay.status_code == 201 and replay.json()["data"] == item
    updated_payload = {**payload, "nombre_item_catalogo": "Ítem editado"}
    updated = client.put(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}",
        json=updated_payload,
        headers=_headers(item["version_registro"]),
    )
    assert (
        updated.status_code == 200 and updated.json()["data"]["version_registro"] == 2
    )
    inactive = client.patch(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}/estado",
        json={"estado_item_catalogo": "INACTIVO"},
        headers=_headers(2),
    )
    assert (
        inactive.status_code == 200
        and inactive.json()["data"]["estado_item_catalogo"] == "INACTIVO"
    )
    baja = client.patch(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}/baja",
        headers=_headers(3),
    )
    assert baja.status_code == 200 and baja.json()["data"]["deleted_at"] is not None
    assert (
        client.get(
            f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items"
        ).json()["data"]["items"]
        == []
    )
    assert (
        db_session.execute(
            text(
                "SELECT count(*) FROM outbox_event WHERE aggregate_type='item_catalogo' AND aggregate_id=:id"
            ),
            {"id": item["id_item_catalogo"]},
        ).scalar_one()
        == 4
    )


def test_item_write_headers_duplicate_and_stale_version(client):
    catalogo = _catalogo(client)
    missing = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json={"codigo_item_catalogo": "A", "nombre_item_catalogo": "A"},
    )
    assert missing.status_code == 400
    first, payload = _item(client, catalogo)
    item = first.json()["data"]
    duplicate = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json=payload,
        headers=_headers(),
    )
    assert (
        duplicate.status_code == 409
        and duplicate.json()["error_code"] == "DUPLICATE_CODE"
    )
    stale = client.put(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}",
        json=payload,
        headers=_headers(99),
    )
    assert (
        stale.status_code == 409 and stale.json()["error_code"] == "CONCURRENCY_ERROR"
    )
