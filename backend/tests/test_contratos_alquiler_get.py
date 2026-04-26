from tests.test_contratos_alquiler_create import _payload_base
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_inmueble


def _crear_contrato_base(client, *, codigo: str) -> dict:
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


def test_get_contrato_alquiler_devuelve_detalle_con_objetos_y_condiciones(
    client,
) -> None:
    contrato = _crear_contrato_base(client, codigo="CA-GET-001")

    response = client.get(f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
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

    assert data["condiciones_economicas_alquiler"] == []
    assert data["deleted_at"] is None
    assert "participaciones" not in data


def test_get_contrato_alquiler_devuelve_404_si_no_existe(client) -> None:
    response = client.get("/api/v1/contratos-alquiler/999999")

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
    assert body["error_message"] == "El contrato de alquiler indicado no existe."
