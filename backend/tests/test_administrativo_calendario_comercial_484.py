from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.api.authentication import get_authenticated_principal
from app.application.administrativo.authentication import AuthenticatedPrincipal
from app.application.administrativo.authorization import (
    AdministrativeAuthorizationDecision,
)

ENDPOINT = "/api/v1/administrativo/configuracion/calendario-comercial"
PAYLOAD = {"dia_cierre_comercial": 20,
           "dia_vencimiento_predeterminado_cuotas": 10,
           "vigente_desde": "2026-09-01"}


@pytest.fixture(autouse=True)
def _preserve_root_identity_sequence(db_session):
    sequence = db_session.execute(text(
        "SELECT pg_get_serial_sequence('configuracion_calendario_comercial', "
        "'id_configuracion_calendario_comercial')"
    )).scalar_one()
    state = db_session.execute(text(
        "SELECT last_value, is_called FROM " + sequence
    )).one()
    yield
    db_session.execute(
        text("SELECT setval(:sequence, :value, :called)"),
        {"sequence": sequence, "value": state.last_value,
         "called": state.is_called},
    )


def _principal():
    return AuthenticatedPrincipal(
        id_usuario=1, codigo_usuario="ROL-ALTERNATIVO", login="bootstrap",
        id_sesion=uuid4(), mecanismo_autenticacion="SESION_SERVIDOR",
        autenticado_en=datetime.now(UTC).replace(tzinfo=None),
        id_instalacion_origen_sesion=1, id_sucursal_operativa=None)


def _headers(op_id=None):
    return {"X-Op-Id": str(op_id or uuid4()), "X-Sucursal-Id": "1",
            "X-Instalacion-Id": "1", "X-Usuario-Id": "no-participa"}


def _post(client, payload=PAYLOAD, headers=None):
    client.app.dependency_overrides[get_authenticated_principal] = _principal
    with patch(
        "app.api.administrative_authorization.AdministrativeAuthorizationService.authorize",
        return_value=AdministrativeAuthorizationDecision.GRANTED,
    ):
        return client.post(ENDPOINT, json=payload, headers=headers or {})


def _counts(db_session):
    return db_session.execute(text("""
        SELECT (SELECT count(*) FROM configuracion_calendario_comercial),
               (SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p
                 USING(id_parametro_sistema) WHERE p.codigo_parametro IN
                 ('DIA_CIERRE_COMERCIAL',
                  'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS'))
    """)).one()


def test_bootstrap_y_replay_durable_sin_efectos_adicionales(client, db_session):
    op_id = uuid4()
    first = _post(client, headers=_headers(op_id))
    assert first.status_code == 201
    assert first.json()["data"]["estado"] == "COMPLETA"
    assert _counts(db_session) == (1, 2)
    replay = _post(client, headers={**_headers(op_id), "X-Sucursal-Id": "999999"})
    assert replay.status_code == 201
    assert replay.json() == first.json()
    assert _counts(db_session) == (1, 2)


def test_bootstrap_payload_conflict(client, db_session):
    op_id = uuid4()
    assert _post(client, headers=_headers(op_id)).status_code == 201
    changed = {**PAYLOAD, "dia_cierre_comercial": 21}
    response = _post(client, changed, _headers(op_id))
    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"
    assert _counts(db_session) == (1, 2)


def test_estado_parcial_no_se_repara(client, db_session):
    db_session.execute(text("INSERT INTO configuracion_calendario_comercial DEFAULT VALUES"))
    db_session.commit()
    response = _post(client, headers=_headers())
    assert response.status_code == 409
    assert response.json()["error_code"] == "CONFIGURACION_CALENDARIO_COMERCIAL_CONFLICTO"
    assert _counts(db_session) == (1, 0)


def test_headers_y_openapi(client):
    response = _post(client)
    assert response.status_code == 422
    operation = client.get("/openapi.json").json()["paths"][ENDPOINT]["post"]
    parameters = {item["name"]: item for item in operation["parameters"]}
    assert all(parameters[name]["required"] for name in
               ("X-Op-Id", "X-Sucursal-Id", "X-Instalacion-Id"))
    assert "X-Usuario-Id" not in parameters
    assert "If-Match-Version" not in parameters


def test_dias_son_enteros_estrictos_y_fecha_explicita(client):
    for invalid in (0, 32, 1.5, "20", True, None):
        response = _post(client, {**PAYLOAD, "dia_cierre_comercial": invalid}, _headers())
        assert response.status_code == 422
    assert _post(client, {k: v for k, v in PAYLOAD.items() if k != "vigente_desde"},
                 _headers()).status_code == 422
