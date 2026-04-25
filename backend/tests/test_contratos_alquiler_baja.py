from sqlalchemy import text

from tests.test_contratos_alquiler_create import _payload_base
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
)


def _crear_contrato_borrador(client, db_session, *, codigo: str, id_rol: int) -> dict:
    id_persona = _crear_persona(client, nombre="Cecilia", apellido="Payne")
    id_inmueble = _crear_inmueble(client, codigo=f"INM-{codigo}")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=id_rol)

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato=codigo,
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=id_persona,
            id_rol=id_rol,
        ),
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_baja_contrato_alquiler_exitosa_desde_borrador(client, db_session) -> None:
    contrato = _crear_contrato_borrador(client, db_session, codigo="CA-BAJA-001", id_rol=9801)
    assert contrato["estado_contrato"] == "borrador"
    assert contrato["version_registro"] == 1

    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/baja",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["id_contrato_alquiler"] == contrato["id_contrato_alquiler"]
    assert body["data"]["estado_contrato"] == "borrador"
    assert body["data"]["version_registro"] == 2
    assert body["data"]["deleted_at"] is not None

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
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Vera", apellido="Rubin")
    id_inmueble = _crear_inmueble(client, codigo="INM-CA-BAJA-002")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9802)

    create_response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-BAJA-002",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9802,
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
    client, db_session
) -> None:
    contrato = _crear_contrato_borrador(client, db_session, codigo="CA-BAJA-003", id_rol=9803)

    response = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/baja",
        headers={**HEADERS, "If-Match-Version": "999"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
    assert "If-Match-Version" in response.json()["error_message"]
