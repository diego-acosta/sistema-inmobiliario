from sqlalchemy import text

from tests.test_condiciones_economicas_alquiler_create import (
    _crear_contrato_borrador,
    _url,
)
from tests.test_disponibilidades_create import HEADERS


def _crear_condicion(client, id_contrato: int, *, monto: str, fecha_desde: str,
                     fecha_hasta: str | None = None) -> dict:
    payload: dict = {"monto_base": monto, "fecha_desde": fecha_desde}
    if fecha_hasta is not None:
        payload["fecha_hasta"] = fecha_hasta
    response = client.post(_url(id_contrato), headers=HEADERS, json=payload)
    assert response.status_code == 201
    return response.json()["data"]


def _url_cerrar(id_contrato: int, id_condicion: int) -> str:
    return (
        f"/api/v1/contratos-alquiler/{id_contrato}"
        f"/condiciones-economicas-alquiler/{id_condicion}/cerrar-vigencia"
    )


def test_cerrar_vigencia_exitosa(client, db_session) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-CIE-001")
    id_contrato = contrato["id_contrato_alquiler"]
    condicion = _crear_condicion(client, id_contrato,
                                 monto="100.00", fecha_desde="2026-05-01")
    assert condicion["fecha_hasta"] is None
    assert condicion["version_registro"] == 1

    response = client.patch(
        _url_cerrar(id_contrato, condicion["id_condicion_economica"]),
        headers={**HEADERS, "If-Match-Version": str(condicion["version_registro"])},
        json={"fecha_hasta": "2026-10-31"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert data["id_condicion_economica"] == condicion["id_condicion_economica"]
    assert data["fecha_hasta"] == "2026-10-31"
    assert data["version_registro"] == 2
    assert data["fecha_desde"] == "2026-05-01"

    row = db_session.execute(
        text(
            """
            SELECT fecha_hasta, version_registro
            FROM condicion_economica_alquiler
            WHERE id_condicion_economica = :id
            """
        ),
        {"id": condicion["id_condicion_economica"]},
    ).mappings().one()
    assert str(row["fecha_hasta"]) == "2026-10-31"
    assert row["version_registro"] == 2


def test_cerrar_vigencia_devuelve_404_si_contrato_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/contratos-alquiler/999999/condiciones-economicas-alquiler/1/cerrar-vigencia",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={"fecha_hasta": "2026-10-31"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_cerrar_vigencia_devuelve_404_si_condicion_no_existe(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-CIE-002")

    response = client.patch(
        _url_cerrar(contrato["id_contrato_alquiler"], 999999),
        headers={**HEADERS, "If-Match-Version": "1"},
        json={"fecha_hasta": "2026-10-31"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
    assert body["details"]["errors"] == ["NOT_FOUND_CONDICION_ECONOMICA"]


def test_cerrar_vigencia_devuelve_409_si_version_no_coincide(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-CIE-003")
    id_contrato = contrato["id_contrato_alquiler"]
    condicion = _crear_condicion(client, id_contrato,
                                 monto="100.00", fecha_desde="2026-05-01")

    response = client.patch(
        _url_cerrar(id_contrato, condicion["id_condicion_economica"]),
        headers={**HEADERS, "If-Match-Version": "999"},
        json={"fecha_hasta": "2026-10-31"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "CONCURRENCY_ERROR"
    assert "If-Match-Version" in body["error_message"]


def test_cerrar_vigencia_devuelve_400_si_fecha_hasta_anterior_a_fecha_desde(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-CIE-004")
    id_contrato = contrato["id_contrato_alquiler"]
    condicion = _crear_condicion(client, id_contrato,
                                 monto="100.00", fecha_desde="2026-05-01")

    response = client.patch(
        _url_cerrar(id_contrato, condicion["id_condicion_economica"]),
        headers={**HEADERS, "If-Match-Version": str(condicion["version_registro"])},
        json={"fecha_hasta": "2026-04-01"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["details"]["errors"] == ["INVALID_DATE_RANGE"]
