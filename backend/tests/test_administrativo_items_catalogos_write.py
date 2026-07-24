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


def test_estado_repetido_es_transicion_invalida_y_replay(client):
    catalogo = _catalogo(client)
    created, _ = _item(client, catalogo)
    item = created.json()["data"]
    op_id = str(uuid4())
    url = f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}/estado"
    first = client.patch(
        url,
        json={"estado_item_catalogo": "INACTIVO"},
        headers=_headers(item["version_registro"], op_id),
    )
    replay = client.patch(
        url,
        json={"estado_item_catalogo": "INACTIVO"},
        headers=_headers(item["version_registro"], op_id),
    )
    repeated = client.patch(
        url,
        json={"estado_item_catalogo": "INACTIVO"},
        headers=_headers(first.json()["data"]["version_registro"]),
    )
    assert first.status_code == replay.status_code == 200
    assert replay.json()["data"] == first.json()["data"]
    assert repeated.status_code == 409
    assert repeated.json()["error_code"] == "INVALID_STATE_TRANSITION"


def test_baja_repetida_replay_y_otro_op_es_not_found(client, db_session):
    catalogo = _catalogo(client)
    created, _ = _item(client, catalogo)
    item = created.json()["data"]
    op_id = str(uuid4())
    url = f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items/{item['id_item_catalogo']}/baja"
    first = client.patch(url, headers=_headers(item["version_registro"], op_id))
    replay = client.patch(url, headers=_headers(item["version_registro"], op_id))
    repeated = client.patch(
        url, headers=_headers(first.json()["data"]["version_registro"])
    )
    assert first.status_code == replay.status_code == 200
    assert replay.json()["data"] == first.json()["data"]
    assert repeated.status_code == 404
    assert (
        db_session.execute(
            text(
                "SELECT count(*) FROM outbox_event WHERE aggregate_id=:id AND event_type='item_catalogo_desactivado'"
            ),
            {"id": item["id_item_catalogo"]},
        ).scalar_one()
        == 1
    )


def test_error_tecnico_no_expone_detalle_interno(client, monkeypatch):
    catalogo = _catalogo(client)
    from app.infrastructure.persistence.repositories.item_catalogo_repository import (
        ItemCatalogoRepository,
    )

    secret = "SQL uq_item_catalogo driver-secret"
    monkeypatch.setattr(
        ItemCatalogoRepository,
        "create",
        lambda *args: (_ for _ in ()).throw(RuntimeError(secret)),
    )
    response = client.post(
        f"/api/v1/administrativo/catalogos/{catalogo['id_catalogo_maestro']}/items",
        json={"codigo_item_catalogo": "SECRETO", "nombre_item_catalogo": "Secreto"},
        headers=_headers(),
    )
    assert response.status_code == 500
    assert response.json() == {
        "ok": False,
        "error_code": "TECHNICAL_INCONSISTENCY",
        "error_message": "No se pudo procesar el ítem del catálogo.",
        "details": {},
    }
    assert secret not in response.text
