from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS


def _payload(*, codigo: str) -> dict:
    return {
        "codigo_solicitud": codigo,
        "fecha_solicitud": "2026-05-01T10:00:00",
        "observaciones": "Solicitud de prueba",
    }


def test_create_solicitud_alquiler_exitosa(client, db_session) -> None:
    response = client.post(
        "/api/v1/solicitudes-alquiler",
        headers=HEADERS,
        json=_payload(codigo="SOL-CRE-001"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert isinstance(data["id_solicitud_alquiler"], int)
    assert data["estado_solicitud"] == "pendiente"
    assert data["codigo_solicitud"] == "SOL-CRE-001"
    assert data["version_registro"] == 1
    assert data["deleted_at"] is None

    row = db_session.execute(
        text(
            "SELECT estado_solicitud FROM solicitud_alquiler WHERE id_solicitud_alquiler = :id"
        ),
        {"id": data["id_solicitud_alquiler"]},
    ).mappings().one()
    assert row["estado_solicitud"] == "pendiente"


def test_create_solicitud_alquiler_sin_codigo_devuelve_400(client) -> None:
    response = client.post(
        "/api/v1/solicitudes-alquiler",
        headers=HEADERS,
        json={"codigo_solicitud": "  ", "fecha_solicitud": "2026-05-01T10:00:00"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["details"]["errors"] == ["INVALID_REQUIRED_FIELDS"]


def test_get_solicitud_alquiler_devuelve_detalle(client) -> None:
    create = client.post(
        "/api/v1/solicitudes-alquiler",
        headers=HEADERS,
        json=_payload(codigo="SOL-GET-001"),
    )
    assert create.status_code == 201
    id_sol = create.json()["data"]["id_solicitud_alquiler"]

    response = client.get(f"/api/v1/solicitudes-alquiler/{id_sol}")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_solicitud_alquiler"] == id_sol
    assert body["data"]["codigo_solicitud"] == "SOL-GET-001"
    assert body["data"]["estado_solicitud"] == "pendiente"


def test_get_solicitud_alquiler_devuelve_404_si_no_existe(client) -> None:
    response = client.get("/api/v1/solicitudes-alquiler/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
