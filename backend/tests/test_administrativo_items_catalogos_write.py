from uuid import uuid4
from sqlalchemy import text

from tests.test_administrativo_catalogos_write import _headers, _payload, _request


def _catalogo(client):
    return _request(client, "POST", "/api/v1/administrativo/catalogos",
                    json=_payload(), headers=_headers()).json()["data"]


def _item_payload(code=None):
    return {"codigo_item_catalogo": code or f"ITEM_{uuid4().hex[:8]}",
            "nombre_item_catalogo": "Ítem", "descripcion": "Descripción"}


def _base(catalogo):
    return f'/api/v1/administrativo/catalogos/{catalogo["id_catalogo_maestro"]}/items'


def test_item_create_central_replay_provenance_y_sin_outbox(client, db_session):
    catalogo = _catalogo(client); op = uuid4(); payload = _item_payload(); url = _base(catalogo)
    first = _request(client, "POST", url, json=payload, headers=_headers(op, legacy=True))
    replay = _request(client, "POST", url, json=payload, headers=_headers(op))
    assert first.status_code == replay.status_code == 201 and first.json() == replay.json()
    item = first.json()["data"]
    assert db_session.execute(text("SELECT id_instalacion_origen,id_instalacion_ultima_modificacion FROM item_catalogo WHERE id_item_catalogo=:id"), {"id": item["id_item_catalogo"]}).one() == (None, None)
    assert db_session.execute(text("SELECT id_usuario,id_sucursal,id_instalacion FROM operacion_idempotente WHERE op_id=:op"), {"op": op}).one() == (1, None, None)
    assert db_session.execute(text("SELECT count(*) FROM outbox_event WHERE aggregate_type='item_catalogo'")).scalar_one() == 0


def test_item_crud_cas_lifecycle_replay_and_parent(client):
    catalogo = _catalogo(client); url = _base(catalogo); payload = _item_payload()
    item = _request(client, "POST", url, json=payload, headers=_headers()).json()["data"]
    item_url = f'{url}/{item["id_item_catalogo"]}'
    updated = _request(client, "PUT", item_url, json={**payload, "nombre_item_catalogo": "Nuevo"}, headers=_headers(version=1))
    assert updated.status_code == 200
    inactive = _request(client, "PATCH", f"{item_url}/estado", json={"estado_item_catalogo": "INACTIVO"}, headers=_headers(version=2))
    assert inactive.status_code == 200 and inactive.json()["data"]["estado_item_catalogo"] == "INACTIVO"
    repeated = _request(client, "PATCH", f"{item_url}/estado", json={"estado_item_catalogo": "INACTIVO"}, headers=_headers(version=3))
    assert repeated.status_code == 409 and repeated.json()["error_code"] == "INVALID_STATE_TRANSITION"
    baja = _request(client, "PATCH", f"{item_url}/baja", headers=_headers(version=3))
    assert baja.status_code == 200 and baja.json()["data"]["deleted_at"] is not None


def test_item_conflicts_scope_and_authorization(client):
    catalogo = _catalogo(client); url = _base(catalogo); payload = _item_payload(); op = uuid4()
    assert _request(client, "POST", url, json=payload, headers=_headers(op)).status_code == 201
    changed = _request(client, "POST", url, json={**payload, "nombre_item_catalogo": "Otro"}, headers=_headers(op))
    assert changed.status_code == 409 and changed.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert _request(client, "POST", url, json=_item_payload(), headers=_headers(), granted=False).status_code == 403
    assert _request(client, "POST", "/api/v1/administrativo/catalogos/999999/items", json=_item_payload(), headers=_headers()).status_code == 404


def test_item_openapi_headers_centrales(client):
    paths = client.get("/openapi.json").json()["paths"]
    base = "/api/v1/administrativo/catalogos/{id_catalogo_maestro}/items"
    item = base + "/{id_item_catalogo}"
    assert {p["name"] for p in paths[base]["post"]["parameters"] if p.get("required")} >= {"X-Op-Id"}
    for path, method in ((item, "put"), (item + "/estado", "patch"), (item + "/baja", "patch")):
        assert {p["name"] for p in paths[path][method]["parameters"] if p.get("required")} >= {"X-Op-Id", "If-Match-Version"}
