from sqlalchemy import text

from tests.test_contratos_alquiler_create import _payload_base
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_inmueble


def _crear_contrato_borrador(client, *, codigo: str) -> dict:
    id_inmueble = _crear_inmueble(client, codigo=f"INM-{codigo}")

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato=codigo,
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
        ),
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_baja_contrato_alquiler_exitosa_desde_borrador(client, db_session) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-BAJA-001")
    assert contrato["estado_contrato"] == "borrador"
    assert contrato["version_registro"] == 1

    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/baja",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_contrato_alquiler"] == contrato["id_contrato_alquiler"]
    assert body["data"]["estado_contrato"] == "borrador"
    assert body["data"]["version_registro"] == 2
    assert body["data"]["deleted_at"] is not None
    assert len(body["data"]["objetos"]) == 1
    assert body["data"]["condiciones_economicas_alquiler"] == []

    row = db_session.execute(
        text(
            """
            SELECT version_registro, deleted_at
            FROM contrato_alquiler
            WHERE id_contrato_alquiler = :id
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).mappings().one()
    assert row["version_registro"] == 2
    assert row["deleted_at"] is not None

    hijos_contrato_objeto = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM contrato_objeto_locativo
            WHERE id_contrato_alquiler = :id
              AND deleted_at IS NULL
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).mappings().one()
    assert hijos_contrato_objeto["total"] >= 1


def test_baja_contrato_alquiler_devuelve_404_si_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/contratos-alquiler/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
    assert response.json()["error_message"] == "El contrato de alquiler indicado no existe."


def test_baja_contrato_alquiler_devuelve_400_si_estado_no_es_borrador(
    client,
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-CA-BAJA-002")

    create_response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-BAJA-002",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
        ),
    )
    assert create_response.status_code == 201
    contrato = create_response.json()["data"]

    activate_response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/activar",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )
    assert activate_response.status_code == 200
    contrato_activo = activate_response.json()["data"]
    assert contrato_activo["estado_contrato"] == "activo"

    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/baja",
        headers={**HEADERS, "If-Match-Version": str(contrato_activo["version_registro"])},
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"
    assert response.json()["error_message"] == "Solo un contrato en estado borrador puede darse de baja."


def test_baja_contrato_alquiler_devuelve_409_si_version_no_coincide(
    client,
) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CA-BAJA-003")

    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/baja",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
    assert "If-Match-Version" in response.json()["error_message"]
