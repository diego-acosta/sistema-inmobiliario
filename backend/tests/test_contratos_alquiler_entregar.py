import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.test_contratos_alquiler_activate import _crear_contrato_borrador
from tests.test_disponibilidades_create import HEADERS


URL_ENTREGAR = "/api/v1/contratos-alquiler/{id}/entregar"


def _activar_contrato(client, contrato: dict) -> dict:
    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/activar",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _crear_contrato_activo(client, *, codigo: str) -> dict:
    borrador = _crear_contrato_borrador(client, codigo=codigo)
    client.post(
        f"/api/v1/contratos-alquiler/{borrador['id_contrato_alquiler']}/condiciones-economicas-alquiler",
        headers=HEADERS,
        json={"monto_base": "150000.00", "fecha_desde": "2026-05-01"},
    )
    return _activar_contrato(client, borrador)


def _payload_entrega() -> dict:
    return {"fecha_entrega": "2026-08-01", "observaciones": "Entrega de llaves"}


# ── tests exitosos ────────────────────────────────────────────────────────────

def test_registrar_entrega_locativa_exitosa(client, db_session) -> None:
    contrato = _crear_contrato_activo(client, codigo="CA-ENT-001")

    response = client.post(
        URL_ENTREGAR.format(id=contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json=_payload_entrega(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert isinstance(data["id_entrega_locativa"], int)
    assert data["id_contrato_alquiler"] == contrato["id_contrato_alquiler"]
    assert data["fecha_entrega"] == "2026-08-01"
    assert data["version_registro"] == 1
    assert data["deleted_at"] is None

    row = db_session.execute(
        text(
            "SELECT id_contrato_alquiler, fecha_entrega FROM entrega_locativa WHERE id_entrega_locativa = :id"
        ),
        {"id": data["id_entrega_locativa"]},
    ).mappings().one()
    assert row["id_contrato_alquiler"] == contrato["id_contrato_alquiler"]


def test_registrar_entrega_emite_evento_outbox(client, db_session) -> None:
    contrato = _crear_contrato_activo(client, codigo="CA-ENT-EVT-001")

    response = client.post(
        URL_ENTREGAR.format(id=contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json=_payload_entrega(),
    )
    assert response.status_code == 201

    outbox_row = db_session.execute(
        text(
            """
            SELECT event_type, aggregate_type, aggregate_id, status, payload
            FROM outbox_event
            WHERE aggregate_type = 'contrato_alquiler'
              AND aggregate_id = :id
              AND event_type = 'entrega_locativa_registrada'
            ORDER BY id DESC LIMIT 1
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).mappings().one_or_none()

    assert outbox_row is not None
    assert outbox_row["event_type"] == "entrega_locativa_registrada"
    assert outbox_row["status"] == "PENDING"
    payload = outbox_row["payload"]
    assert payload["id_contrato_alquiler"] == contrato["id_contrato_alquiler"]
    assert "objetos" in payload
    assert len(payload["objetos"]) == 1


def test_registrar_entrega_copia_todos_los_objetos(client, db_session) -> None:
    """El outbox incluye todos los objetos del contrato."""
    contrato = _crear_contrato_activo(client, codigo="CA-ENT-OBJ-001")

    client.post(
        URL_ENTREGAR.format(id=contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json=_payload_entrega(),
    )

    outbox_row = db_session.execute(
        text(
            """
            SELECT payload FROM outbox_event
            WHERE aggregate_type = 'contrato_alquiler'
              AND aggregate_id = :id
              AND event_type = 'entrega_locativa_registrada'
            ORDER BY id DESC LIMIT 1
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).mappings().one()

    objetos = outbox_row["payload"]["objetos"]
    assert len(objetos) == len(contrato["objetos"])
    for obj_evento, obj_contrato in zip(objetos, contrato["objetos"]):
        assert obj_evento["id_inmueble"] == obj_contrato["id_inmueble"]


# ── tests de error ────────────────────────────────────────────────────────────

def test_registrar_entrega_contrato_inexistente_devuelve_404(client) -> None:
    response = client.post(
        URL_ENTREGAR.format(id=999999),
        headers=HEADERS,
        json=_payload_entrega(),
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_registrar_entrega_contrato_no_activo_devuelve_400(client) -> None:
    borrador = _crear_contrato_borrador(client, codigo="CA-ENT-NOACT-001")

    response = client.post(
        URL_ENTREGAR.format(id=borrador["id_contrato_alquiler"]),
        headers=HEADERS,
        json=_payload_entrega(),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert "activo" in body["error_message"]
    assert body["details"]["errors"] == ["CONTRATO_NOT_ACTIVO"]


def test_registrar_entrega_doble_devuelve_400(client) -> None:
    contrato = _crear_contrato_activo(client, codigo="CA-ENT-DUP-001")

    first = client.post(
        URL_ENTREGAR.format(id=contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json=_payload_entrega(),
    )
    assert first.status_code == 201

    response = client.post(
        URL_ENTREGAR.format(id=contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json=_payload_entrega(),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["details"]["errors"] == ["CONTRATO_YA_TIENE_ENTREGA"]


def test_unique_index_impide_doble_entrega_por_contrato(client, db_session) -> None:
    """El unique index parcial rechaza a nivel DB una segunda entrega activa."""
    contrato = _crear_contrato_activo(client, codigo="CA-ENT-IDX-001")

    first = client.post(
        URL_ENTREGAR.format(id=contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json=_payload_entrega(),
    )
    assert first.status_code == 201

    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                """
                INSERT INTO entrega_locativa (
                    uid_global, version_registro, created_at, updated_at,
                    id_contrato_alquiler, fecha_entrega
                ) VALUES (
                    gen_random_uuid(), 1, now(), now(),
                    :id_contrato_alquiler, '2026-09-01'
                )
                """
            ),
            {"id_contrato_alquiler": contrato["id_contrato_alquiler"]},
        )
        db_session.flush()
