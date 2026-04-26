from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_inmueble


def _payload_base(
    *,
    codigo_contrato: str,
    objetos: list[dict],
    fecha_inicio: str = "2026-05-01",
    fecha_fin: str | None = "2026-10-31",
) -> dict:
    return {
        "codigo_contrato": codigo_contrato,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "observaciones": "Contrato de prueba",
        "objetos": objetos,
    }


def test_create_contrato_alquiler_exitoso(client, db_session) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-CA-OK-001")

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-OK-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": "Objeto A"}],
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert isinstance(body["data"]["id_contrato_alquiler"], int)
    assert body["data"]["estado_contrato"] == "borrador"
    assert body["data"]["codigo_contrato"] == "CA-OK-001"
    assert len(body["data"]["objetos"]) == 1
    assert body["data"]["objetos"][0]["id_inmueble"] == id_inmueble
    assert isinstance(body["data"]["objetos"][0]["id_contrato_objeto"], int)
    assert body["data"]["condiciones_economicas_alquiler"] == []
    assert "canon_inicial" not in body["data"]
    assert "moneda" not in body["data"]
    assert "participaciones" not in body["data"]


def test_create_contrato_alquiler_objeto_inexistente_devuelve_404(client) -> None:
    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-NF-INM-001",
            objetos=[{"id_inmueble": 999999, "id_unidad_funcional": None, "observaciones": None}],
        ),
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
    assert body["details"]["errors"] == ["NOT_FOUND_INMUEBLE"]


def test_create_contrato_alquiler_sin_objetos_devuelve_400(client) -> None:
    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-NOOBJ-001",
            objetos=[],
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["OBJETOS_REQUIRED"]


def test_create_contrato_alquiler_fecha_fin_menor_a_fecha_inicio_devuelve_400(
    client,
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-CA-FECH-001")

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-FECH-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            fecha_inicio="2026-05-01",
            fecha_fin="2026-04-01",
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_DATE_RANGE"]
