from tests.test_contratos_alquiler_create import _payload_base
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
)


def _crear_contrato_base(client, db_session, *, codigo: str, id_rol: int) -> dict:
    id_persona = _crear_persona(client, nombre="Rosalind", apellido="Franklin")
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
    data = response.json()["data"]
    data["id_persona"] = id_persona
    return data


def test_get_contrato_alquiler_devuelve_detalle_con_objetos_y_participaciones(
    client, db_session
) -> None:
    contrato = _crear_contrato_base(client, db_session, codigo="CA-GET-001", id_rol=9301)

    response = client.get(f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}")

    assert response.status_code == 200
    body = response.json()
    data = body["data"]

    assert data["id_contrato_alquiler"] == contrato["id_contrato_alquiler"]
    assert data["uid_global"] == contrato["uid_global"]
    assert data["version_registro"] == contrato["version_registro"]
    assert data["codigo_contrato"] == "CA-GET-001"
    assert data["estado_contrato"] == "borrador"
    assert data["fecha_inicio"] == "2026-05-01"
    assert data["fecha_fin"] == "2026-10-31"

    assert len(data["objetos"]) == 1
    assert data["objetos"][0]["id_inmueble"] == contrato["objetos"][0]["id_inmueble"]
    assert data["objetos"][0]["id_unidad_funcional"] is None
    assert isinstance(data["objetos"][0]["id_contrato_objeto"], int)

    assert len(data["participaciones"]) == 1
    assert data["participaciones"][0]["id_persona"] == contrato["id_persona"]
    assert data["participaciones"][0]["id_rol_participacion"] == 9301
    assert isinstance(data["participaciones"][0]["id_relacion_persona_rol"], int)

    assert "deleted_at" not in data


def test_get_contrato_alquiler_devuelve_404_si_no_existe(client) -> None:
    response = client.get("/api/v1/contratos-alquiler/999999")

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
    assert response.json()["error_message"] == "El contrato de alquiler indicado no existe."
