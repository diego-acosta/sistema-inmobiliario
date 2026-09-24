from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import text

from app.api.authentication import get_authenticated_principal
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import AdministrativeAuthorizationDecision

ENDPOINT = "/api/v1/administrativo/catalogos"


def _principal(id_usuario=1):
    return AuthenticatedPrincipal(id_usuario=id_usuario, codigo_usuario="TEST", login="test",
        id_sesion=uuid4(), mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=datetime.now(UTC).replace(tzinfo=None))


def _request(client, method, url, *, json=None, headers=None, user=1, granted=True):
    client.app.dependency_overrides[get_authenticated_principal] = lambda: _principal(user)
    decision = AdministrativeAuthorizationDecision.GRANTED if granted else AdministrativeAuthorizationDecision.DENIED
    with patch("app.api.administrative_authorization.AdministrativeAuthorizationService.authorize", return_value=decision):
        return client.request(method, url, json=json, headers=headers or {})


def _payload(code=None):
    return {"codigo_catalogo_maestro": code or f"CAT_{uuid4().hex[:8]}",
            "nombre_catalogo_maestro": "Catálogo", "descripcion": "Descripción"}


def _headers(op=None, version=None, legacy=False):
    value = {"X-Op-Id": str(op or uuid4())}
    if version is not None:
        value["If-Match-Version"] = str(version)
    if legacy:
        value |= {"X-Usuario-Id": "999", "X-Sucursal-Id": "999", "X-Instalacion-Id": "999"}
    return value


def _create(client, payload=None, op=None, user=1, legacy=False):
    return _request(client, "POST", ENDPOINT, json=payload or _payload(),
                    headers=_headers(op, legacy=legacy), user=user)


def test_create_central_receipt_provenance_replay_y_sin_outbox(client, db_session):
    op = uuid4(); payload = _payload()
    first = _create(client, payload, op, legacy=True); replay = _create(client, payload, op)
    assert first.status_code == replay.status_code == 201 and replay.json() == first.json()
    row = db_session.execute(text("SELECT id_instalacion_origen,id_instalacion_ultima_modificacion FROM catalogo_maestro WHERE id_catalogo_maestro=:id"), {"id": first.json()["data"]["id_catalogo_maestro"]}).one()
    assert row == (None, None)
    assert db_session.execute(text("SELECT id_usuario,id_sucursal,id_instalacion FROM operacion_idempotente WHERE op_id=:op"), {"op": op}).one() == (1, None, None)
    assert db_session.execute(text("SELECT count(*) FROM outbox_event WHERE aggregate_type='catalogo_maestro'")).scalar_one() == 0


def test_create_conflicts_duplicate_headers_and_authorization(client):
    payload = _payload(); op = uuid4()
    assert _create(client, payload, op).status_code == 201
    assert _create(client, {**payload, "nombre_catalogo_maestro": "Otro"}, op).json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert _create(client, payload).json()["error_code"] == "DUPLICATE_CODE"
    missing = _request(client, "POST", ENDPOINT, json=_payload())
    assert missing.status_code == 400 and missing.json()["details"]["header"] == "X-Op-Id"
    assert _request(client, "POST", ENDPOINT, json=_payload(), headers=_headers(), granted=False).status_code == 403


def test_update_cas_replay_actor_conflict_y_baja(client, db_session):
    created = _create(client).json()["data"]; url = f'{ENDPOINT}/{created["id_catalogo_maestro"]}'
    op = uuid4(); payload = _payload()
    first = _request(client, "PUT", url, json=payload, headers=_headers(op, created["version_registro"]))
    replay = _request(client, "PUT", url, json=payload, headers=_headers(op, created["version_registro"]))
    assert first.status_code == replay.status_code == 200 and first.json() == replay.json()
    cross = _request(client, "PUT", url, json=payload, headers=_headers(op, created["version_registro"]), user=2)
    assert cross.status_code == 409 and cross.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    stale_op = uuid4()
    assert _request(client, "PUT", url, json=_payload(), headers=_headers(stale_op, 1)).status_code == 412
    assert db_session.execute(
        text("SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"),
        {"op": stale_op},
    ).scalar_one() == 0
    current = first.json()["data"]
    baja_op = uuid4()
    baja_headers = _headers(baja_op, current["version_registro"])
    baja = _request(client, "PATCH", f"{url}/baja", headers=baja_headers)
    assert baja.status_code == 200 and baja.json()["data"]["deleted_at"] is not None
    replay_baja = _request(client, "PATCH", f"{url}/baja", headers=baja_headers)
    assert replay_baja.status_code == 200 and replay_baja.json() == baja.json()
    receipt = db_session.execute(
        text("SELECT id_usuario,id_sucursal,id_instalacion FROM operacion_idempotente WHERE op_id=:op"),
        {"op": baja_op},
    ).one()
    assert receipt == (1, None, None)
    nueva_baja = _request(
        client,
        "PATCH",
        f"{url}/baja",
        headers=_headers(version=baja.json()["data"]["version_registro"]),
    )
    assert nueva_baja.status_code == 404
    assert db_session.execute(text("SELECT count(*) FROM outbox_event WHERE aggregate_type='catalogo_maestro'")).scalar_one() == 0


def test_openapi_headers_centrales(client):
    paths = client.get("/openapi.json").json()["paths"]
    post = paths[ENDPOINT]["post"]["parameters"]
    put = paths[f"{ENDPOINT}/{{id_catalogo_maestro}}"]["put"]["parameters"]
    baja = paths[f"{ENDPOINT}/{{id_catalogo_maestro}}/baja"]["patch"]["parameters"]
    assert {p["name"] for p in post if p.get("required")} >= {"X-Op-Id"}
    for params in (put, baja):
        assert {p["name"] for p in params if p.get("required")} >= {"X-Op-Id", "If-Match-Version"}
    assert not {"X-Usuario-Id", "X-Sucursal-Id", "X-Instalacion-Id"} & {p["name"] for p in post + put + baja}
    assert "412" in paths[f"{ENDPOINT}/{{id_catalogo_maestro}}"]["put"]["responses"]
    assert "412" in paths[f"{ENDPOINT}/{{id_catalogo_maestro}}/baja"]["patch"]["responses"]
