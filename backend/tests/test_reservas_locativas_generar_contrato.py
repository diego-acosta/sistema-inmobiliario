import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_locativas_create import _crear_inmueble_disponible, _payload_reserva


URL_GENERAR = "/api/v1/reservas-locativas/{id}/generar-contrato"


def _crear_reserva_confirmada(client, *, codigo_reserva: str, codigo_inm: str) -> dict:
    id_inmueble = _crear_inmueble_disponible(client, codigo=codigo_inm)
    reserva_resp = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json=_payload_reserva(codigo=codigo_reserva, id_inmueble=id_inmueble),
    )
    assert reserva_resp.status_code == 201
    reserva = reserva_resp.json()["data"]

    conf_resp = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/confirmar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    assert conf_resp.status_code == 200
    return conf_resp.json()["data"]


def _payload_contrato(*, codigo: str) -> dict:
    return {
        "codigo_contrato": codigo,
        "fecha_inicio": "2026-07-01",
        "fecha_fin": "2027-06-30",
        "observaciones": "Contrato generado desde reserva",
    }


# ── tests create ──────────────────────────────────────────────────────────────

def test_generar_contrato_desde_reserva_confirmada(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(
        client, codigo_reserva="RL-GEN-001", codigo_inm="INM-GEN-001"
    )

    response = client.post(
        URL_GENERAR.format(id=reserva["id_reserva_locativa"]),
        headers=HEADERS,
        json=_payload_contrato(codigo="CA-GEN-001"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert isinstance(data["id_contrato_alquiler"], int)
    assert data["estado_contrato"] == "borrador"
    assert data["codigo_contrato"] == "CA-GEN-001"
    assert len(data["objetos"]) == 1
    assert data["objetos"][0]["id_inmueble"] == reserva["objetos"][0]["id_inmueble"]
    assert isinstance(data["objetos"][0]["id_contrato_objeto"], int)
    assert data["condiciones_economicas_alquiler"] == []


def test_generar_contrato_fk_id_reserva_locativa_seteado(client, db_session) -> None:
    reserva = _crear_reserva_confirmada(
        client, codigo_reserva="RL-GEN-FK-001", codigo_inm="INM-GEN-FK-001"
    )

    response = client.post(
        URL_GENERAR.format(id=reserva["id_reserva_locativa"]),
        headers=HEADERS,
        json=_payload_contrato(codigo="CA-GEN-FK-001"),
    )

    assert response.status_code == 201
    id_contrato = response.json()["data"]["id_contrato_alquiler"]

    row = db_session.execute(
        text(
            "SELECT id_reserva_locativa FROM contrato_alquiler WHERE id_contrato_alquiler = :id"
        ),
        {"id": id_contrato},
    ).mappings().one()
    assert row["id_reserva_locativa"] == reserva["id_reserva_locativa"]


def test_generar_contrato_copia_multiples_objetos(client, db_session) -> None:
    id_inm_a = _crear_inmueble_disponible(client, codigo="INM-GEN-MULTI-001A")
    id_inm_b = _crear_inmueble_disponible(client, codigo="INM-GEN-MULTI-001B")

    reserva_resp = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json={
            "codigo_reserva": "RL-GEN-MULTI-001",
            "fecha_reserva": "2026-06-01T10:00:00",
            "objetos": [
                {"id_inmueble": id_inm_a, "id_unidad_funcional": None, "observaciones": None},
                {"id_inmueble": id_inm_b, "id_unidad_funcional": None, "observaciones": None},
            ],
        },
    )
    assert reserva_resp.status_code == 201
    reserva = reserva_resp.json()["data"]

    conf = client.patch(
        f"/api/v1/reservas-locativas/{reserva['id_reserva_locativa']}/confirmar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    assert conf.status_code == 200
    reserva_conf = conf.json()["data"]

    response = client.post(
        URL_GENERAR.format(id=reserva_conf["id_reserva_locativa"]),
        headers=HEADERS,
        json=_payload_contrato(codigo="CA-GEN-MULTI-001"),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert len(data["objetos"]) == 2
    ids_inmueble = {o["id_inmueble"] for o in data["objetos"]}
    assert ids_inmueble == {id_inm_a, id_inm_b}


# ── tests errores ─────────────────────────────────────────────────────────────

def test_generar_contrato_reserva_inexistente_devuelve_404(client) -> None:
    response = client.post(
        URL_GENERAR.format(id=999999),
        headers=HEADERS,
        json=_payload_contrato(codigo="CA-GEN-NF-001"),
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_generar_contrato_reserva_no_confirmada_devuelve_400(client) -> None:
    id_inmueble = _crear_inmueble_disponible(client, codigo="INM-GEN-PEND-001")
    reserva_resp = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-GEN-PEND-001", id_inmueble=id_inmueble),
    )
    assert reserva_resp.status_code == 201
    reserva = reserva_resp.json()["data"]

    response = client.post(
        URL_GENERAR.format(id=reserva["id_reserva_locativa"]),
        headers=HEADERS,
        json=_payload_contrato(codigo="CA-GEN-PEND-001"),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert "confirmada" in body["error_message"]
    assert body["details"]["errors"] == ["RESERVA_NOT_CONFIRMADA"]


def test_generar_contrato_ya_tiene_contrato_devuelve_400(client) -> None:
    reserva = _crear_reserva_confirmada(
        client, codigo_reserva="RL-GEN-DUP-001", codigo_inm="INM-GEN-DUP-001"
    )

    first = client.post(
        URL_GENERAR.format(id=reserva["id_reserva_locativa"]),
        headers=HEADERS,
        json=_payload_contrato(codigo="CA-GEN-DUP-001A"),
    )
    assert first.status_code == 201

    response = client.post(
        URL_GENERAR.format(id=reserva["id_reserva_locativa"]),
        headers=HEADERS,
        json=_payload_contrato(codigo="CA-GEN-DUP-001B"),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["details"]["errors"] == ["RESERVA_YA_TIENE_CONTRATO"]


def test_unique_index_impide_doble_contrato_activo_por_reserva(client, db_session) -> None:
    """El unique index parcial rechaza a nivel DB un segundo contrato activo por reserva."""
    reserva = _crear_reserva_confirmada(
        client, codigo_reserva="RL-GEN-IDX-001", codigo_inm="INM-GEN-IDX-001"
    )
    id_reserva = reserva["id_reserva_locativa"]

    # primer contrato vía endpoint
    first = client.post(
        URL_GENERAR.format(id=id_reserva),
        headers=HEADERS,
        json=_payload_contrato(codigo="CA-GEN-IDX-001A"),
    )
    assert first.status_code == 201

    # segundo INSERT directo, saltando la validación del service
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO contrato_alquiler (
                    uid_global, version_registro, created_at, updated_at,
                    id_instalacion_origen, id_instalacion_ultima_modificacion,
                    id_reserva_locativa, codigo_contrato,
                    fecha_inicio, estado_contrato
                ) VALUES (
                    gen_random_uuid(), 1, now(), now(),
                    NULL, NULL,
                    :id_reserva_locativa, 'CA-GEN-IDX-001B',
                    '2026-07-01', 'borrador'
                )
                """
            ),
            {"id_reserva_locativa": id_reserva},
        )
        db_session.flush()
