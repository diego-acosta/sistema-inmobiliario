from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

from app.api.authentication import get_authenticated_principal
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
)
from sqlalchemy import text

ENDPOINT = "/api/v1/administrativo/configuracion/parametros/PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO/valor-global"


def _principal():
    return AuthenticatedPrincipal(
        id_usuario=1,
        codigo_usuario="USR-TEST",
        login="test",
        id_sesion=uuid4(),
        mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=datetime.now(UTC).replace(tzinfo=None),
        id_instalacion_origen_sesion=1,
        id_sucursal_operativa=None,
    )


def _headers(op_id, version=1, **extra):
    return {
        "X-Op-Id": str(op_id),
        "X-Sucursal-Id": "1",
        "X-Instalacion-Id": "1",
        "If-Match-Version": str(version),
        **extra,
    }


def _grant(client):
    client.app.dependency_overrides[get_authenticated_principal] = _principal
    return patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService.authorize",
        return_value=AdministrativeAuthorizationDecision.GRANTED,
    )


def test_patch_material_replay_y_x_usuario_id_no_influye(client, db_session):
    op_id = uuid4()
    with _grant(client):
        first = client.patch(
            ENDPOINT,
            json={"valor_tipado": 16},
            headers=_headers(op_id, **{"X-Usuario-Id": "999999"}),
        )
        replay = client.patch(
            ENDPOINT, json={"valor_tipado": 16}, headers=_headers(op_id)
        )
    assert first.status_code == replay.status_code == 200
    assert first.json() == replay.json()
    assert first.json()["data"]["version_registro"] == 2
    assert not first.json()["data"]["updated_at"].endswith(("Z", "+00:00"))
    assert (
        db_session.execute(
            text(
                "SELECT count(*) FROM outbox_event WHERE event_type='valor_parametro_modificado'"
            )
        ).scalar_one()
        == 1
    )
    assert (
        db_session.execute(
            text("SELECT count(*) FROM operacion_idempotente WHERE op_id=:op"),
            {"op": op_id},
        ).scalar_one()
        == 1
    )


def test_headers_y_body_estructurales(client):
    with _grant(client):
        missing = client.patch(ENDPOINT, json={"valor_tipado": 16})
        boolean = client.patch(
            ENDPOINT, json={"valor_tipado": True}, headers=_headers(uuid4())
        )
        extra = client.patch(
            ENDPOINT, json={"valor_tipado": 16, "extra": 1}, headers=_headers(uuid4())
        )
    assert missing.status_code == 400
    assert missing.json()["error_code"] == "VALIDATION_ERROR"
    assert boolean.status_code == extra.status_code == 422


def test_noop_preserva_fisico_version_y_no_genera_outbox(client, db_session):
    db_session.execute(
        text(
            "UPDATE valor_parametro SET valor_parametro='015' WHERE id_valor_parametro=1"
        )
    )
    row = db_session.execute(
        text(
            "SELECT version_registro, updated_at FROM valor_parametro WHERE id_valor_parametro=1"
        )
    ).one()
    with _grant(client):
        response = client.patch(
            ENDPOINT,
            json={"valor_tipado": 15},
            headers=_headers(uuid4(), row.version_registro),
        )
    assert response.status_code == 200
    after = db_session.execute(
        text(
            "SELECT valor_parametro, version_registro, updated_at FROM valor_parametro WHERE id_valor_parametro=1"
        )
    ).one()
    assert after == ("015", row.version_registro, row.updated_at)
    assert (
        db_session.execute(text("SELECT count(*) FROM outbox_event")).scalar_one() == 0
    )
