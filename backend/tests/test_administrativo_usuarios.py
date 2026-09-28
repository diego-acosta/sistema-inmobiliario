from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import text

from app.api.authentication import get_authenticated_principal
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import AdministrativeAuthorizationDecision

ENDPOINT = "/api/v1/administrativo/usuarios"


def _principal(id_usuario=1):
    return AuthenticatedPrincipal(
        id_usuario=id_usuario, codigo_usuario="TEST", login="test",
        id_sesion=uuid4(), mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=datetime.now(UTC).replace(tzinfo=None),
    )


def _central_request(client, method, url, *, json=None, headers=None, user=1, granted=True):
    client.app.dependency_overrides[get_authenticated_principal] = lambda: _principal(user)
    decision = AdministrativeAuthorizationDecision.GRANTED if granted else AdministrativeAuthorizationDecision.DENIED
    with patch("app.api.administrative_authorization.AdministrativeAuthorizationService.authorize", return_value=decision):
        return client.request(method, url, json=json, headers=headers or {})


def _central_headers(op=None, version=None, legacy=False):
    result = {"X-Op-Id": str(op or uuid4())}
    if version is not None:
        result["If-Match-Version"] = str(version)
    if legacy:
        result |= {"X-Usuario-Id": "999", "X-Sucursal-Id": "999", "X-Instalacion-Id": "999"}
    return result


def _payload(suffix="001"):
    return {
        "codigo_usuario": f"USR-ADM-{suffix}", "login": f"usr.adm.{suffix}",
        "email": f"usr.adm.{suffix}@example.com", "estado_usuario": "ACTIVO",
        "usuario_sistema_interno": False, "observaciones": "Usuario de prueba",
    }


def _create(client, suffix="CRUD", *, op=None, user=1, legacy=False):
    return _central_request(client, "POST", ENDPOINT, json=_payload(suffix),
                            headers=_central_headers(op, legacy=legacy), user=user)


def test_create_central_receipt_provenance_replay_y_sin_outbox(client, db_session):
    op = uuid4()
    first = _create(client, "CENTRAL", op=op, legacy=True)
    replay = _create(client, "CENTRAL", op=op)
    assert first.status_code == replay.status_code == 201
    assert replay.json() == first.json()
    user_id = first.json()["data"]["id_usuario"]
    assert db_session.execute(text("SELECT id_instalacion_origen,id_instalacion_ultima_modificacion FROM usuario WHERE id_usuario=:id"), {"id": user_id}).one() == (None, None)
    assert db_session.execute(text("SELECT id_usuario,id_sucursal,id_instalacion FROM operacion_idempotente WHERE op_id=:op"), {"op": op}).one() == (1, None, None)
    assert db_session.execute(text("SELECT count(*) FROM outbox_event WHERE aggregate_type='usuario'")).scalar_one() == 0


def test_create_headers_conflicts_y_autorizacion(client):
    missing = _central_request(client, "POST", ENDPOINT, json=_payload("MISSING"))
    assert missing.status_code == 400 and missing.json()["details"]["header"] == "X-Op-Id"
    assert _central_request(client, "POST", ENDPOINT, json=_payload("DENIED"), headers=_central_headers(), granted=False).status_code == 403
    op = uuid4(); payload = _payload("CONFLICT")
    assert _central_request(client, "POST", ENDPOINT, json=payload, headers=_central_headers(op)).status_code == 201
    conflict = _central_request(client, "POST", ENDPOINT, json={**payload, "login": "otro.login"}, headers=_central_headers(op))
    assert conflict.status_code == 409 and conflict.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"


def test_baja_cas_replay_actor_conflict_y_provenance(client, db_session):
    created = _create(client, "BAJA").json()["data"]
    url = f"{ENDPOINT}/{created['id_usuario']}/baja"; op = uuid4()
    headers = _central_headers(op, created["version_registro"], legacy=True)
    first = _central_request(client, "PATCH", url, headers=headers)
    replay = _central_request(client, "PATCH", url, headers=headers)
    assert first.status_code == replay.status_code == 200 and replay.json() == first.json()
    assert first.json()["data"]["estado_usuario"] == "INACTIVO"
    cross = _central_request(client, "PATCH", url, headers=headers, user=created["id_usuario"])
    assert cross.status_code == 409 and cross.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert db_session.execute(text("SELECT id_sucursal,id_instalacion FROM operacion_idempotente WHERE op_id=:op"), {"op": op}).one() == (None, None)
    assert db_session.execute(text("SELECT id_instalacion_origen,id_instalacion_ultima_modificacion FROM usuario WHERE id_usuario=:id"), {"id": created["id_usuario"]}).one() == (None, None)


def test_baja_stale_412_rollback_y_autorizacion_antes_de_replay(client, db_session):
    created = _create(client, "STALE").json()["data"]
    url = f"{ENDPOINT}/{created['id_usuario']}/baja"; stale_op = uuid4()
    stale = _central_request(client, "PATCH", url, headers=_central_headers(stale_op, created["version_registro"] + 1))
    assert stale.status_code == 412 and stale.json()["error_code"] == "CONCURRENCY_ERROR"
    assert db_session.execute(text("SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"), {"op": stale_op}).scalar_one() == 0
    op = uuid4(); headers = _central_headers(op, created["version_registro"])
    assert _central_request(client, "PATCH", url, headers=headers).status_code == 200
    assert _central_request(client, "PATCH", url, headers=headers, granted=False).status_code == 403


def test_baja_metadata_y_nueva_baja(client):
    created = _create(client, "META").json()["data"]
    url = f"{ENDPOINT}/{created['id_usuario']}/baja"
    assert _central_request(client, "PATCH", url, headers=_central_headers()).status_code == 400
    first = _central_request(client, "PATCH", url, headers=_central_headers(version=created["version_registro"]))
    assert first.status_code == 200
    second = _central_request(client, "PATCH", url, headers=_central_headers(version=first.json()["data"]["version_registro"]))
    assert second.status_code == 404


def test_baja_usuario_fisicamente_inexistente_404(client):
    response = _central_request(
        client,
        "PATCH",
        f"{ENDPOINT}/2147483647/baja",
        headers=_central_headers(version=1),
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_openapi_usuario_central(client):
    paths = client.get("/openapi.json").json()["paths"]
    post = paths[ENDPOINT]["post"]; baja = paths[f"{ENDPOINT}/{{id_usuario}}/baja"]["patch"]
    assert {p["name"] for p in post["parameters"] if p.get("required")} >= {"X-Op-Id"}
    assert {p["name"] for p in baja["parameters"] if p.get("required")} >= {"X-Op-Id", "If-Match-Version"}
    assert not {"X-Usuario-Id", "X-Sucursal-Id", "X-Instalacion-Id"} & {p["name"] for p in post["parameters"] + baja["parameters"]}
    assert "412" in baja["responses"]
