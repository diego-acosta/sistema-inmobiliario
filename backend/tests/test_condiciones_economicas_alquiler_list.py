from tests.test_condiciones_economicas_alquiler_create import (
    _crear_contrato_borrador,
    _url,
)
from tests.test_disponibilidades_create import HEADERS


def _crear_condicion(client, id_contrato: int, *, monto: str, fecha_desde: str,
                     fecha_hasta: str | None = None, moneda: str | None = None,
                     periodicidad: str | None = None) -> dict:
    payload: dict = {"monto_base": monto, "fecha_desde": fecha_desde}
    if fecha_hasta is not None:
        payload["fecha_hasta"] = fecha_hasta
    if moneda is not None:
        payload["moneda"] = moneda
    if periodicidad is not None:
        payload["periodicidad"] = periodicidad
    response = client.post(_url(id_contrato), headers=HEADERS, json=payload)
    assert response.status_code == 201
    return response.json()["data"]


def test_list_condiciones_economicas_devuelve_items_y_total(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-LST-001")
    id_contrato = contrato["id_contrato_alquiler"]

    _crear_condicion(client, id_contrato, monto="100.00", fecha_desde="2026-05-01",
                     fecha_hasta="2026-07-31", moneda="ARS")
    _crear_condicion(client, id_contrato, monto="200.00", fecha_desde="2026-08-01",
                     moneda="USD")

    response = client.get(_url(id_contrato))

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["total"] == 2
    assert len(body["data"]["items"]) == 2

    item = body["data"]["items"][0]
    assert "id_condicion_economica" in item
    assert "monto_base" in item
    assert "fecha_desde" in item
    assert "version_registro" in item
    assert "created_at" in item


def test_list_condiciones_economicas_devuelve_404_si_contrato_no_existe(client) -> None:
    response = client.get(
        "/api/v1/contratos-alquiler/999999/condiciones-economicas-alquiler"
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_list_condiciones_economicas_filtra_por_moneda(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-LST-002")
    id_contrato = contrato["id_contrato_alquiler"]

    _crear_condicion(client, id_contrato, monto="100.00", fecha_desde="2026-05-01",
                     fecha_hasta="2026-07-31", moneda="ARS")
    _crear_condicion(client, id_contrato, monto="200.00", fecha_desde="2026-08-01",
                     moneda="USD")

    response = client.get(f"{_url(id_contrato)}?moneda=ARS")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["moneda"] == "ARS"


def test_list_condiciones_economicas_filtra_por_periodicidad(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-LST-003")
    id_contrato = contrato["id_contrato_alquiler"]

    _crear_condicion(client, id_contrato, monto="100.00", fecha_desde="2026-05-01",
                     fecha_hasta="2026-07-31", periodicidad="mensual")
    _crear_condicion(client, id_contrato, monto="200.00", fecha_desde="2026-08-01",
                     periodicidad="trimestral")

    response = client.get(f"{_url(id_contrato)}?periodicidad=mensual")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["periodicidad"] == "mensual"


def test_list_condiciones_economicas_filtra_por_vigente(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-LST-004")
    id_contrato = contrato["id_contrato_alquiler"]

    # cerrada (pasada)
    _crear_condicion(client, id_contrato, monto="100.00",
                     fecha_desde="2020-01-01", fecha_hasta="2020-12-31")
    # vigente (sin fecha_hasta = abierta)
    _crear_condicion(client, id_contrato, monto="200.00",
                     fecha_desde="2026-01-01")

    response_vigente = client.get(f"{_url(id_contrato)}?vigente=true")
    assert response_vigente.status_code == 200
    assert response_vigente.json()["data"]["total"] == 1

    response_no_vigente = client.get(f"{_url(id_contrato)}?vigente=false")
    assert response_no_vigente.status_code == 200
    assert response_no_vigente.json()["data"]["total"] == 1


def test_get_contrato_embebe_condiciones(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-LST-005")
    id_contrato = contrato["id_contrato_alquiler"]

    _crear_condicion(client, id_contrato, monto="150000.00",
                     fecha_desde="2026-05-01", moneda="ARS")

    response = client.get(f"/api/v1/contratos-alquiler/{id_contrato}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data["condiciones_economicas_alquiler"]) == 1
    assert data["condiciones_economicas_alquiler"][0]["moneda"] == "ARS"
