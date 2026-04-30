from decimal import Decimal

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


def _crear_contrato_activo(client, *, codigo: str) -> dict:
    contrato = _crear_contrato_borrador(client, codigo=codigo)
    # Rango cerrado en el pasado para no solapar con las condiciones que crean los tests.
    client.post(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/condiciones-economicas-alquiler",
        headers=HEADERS,
        json={"monto_base": "150000.00", "fecha_desde": "2024-01-01", "fecha_hasta": "2024-12-31"},
    )
    activate = client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/activar",
        headers={**HEADERS, "If-Match-Version": str(contrato["version_registro"])},
    )
    assert activate.status_code == 200
    return activate.json()["data"]


def _url(id_contrato: int) -> str:
    return f"/api/v1/contratos-alquiler/{id_contrato}/condiciones-economicas-alquiler"


def test_create_condicion_economica_exitosa_contrato_borrador(client, db_session) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-CRE-001")

    response = client.post(
        _url(contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json={
            "monto_base": "150000.00",
            "periodicidad": "mensual",
            "moneda": "ARS",
            "fecha_desde": "2026-05-01",
            "fecha_hasta": "2026-10-31",
            "observaciones": "Canon inicial",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert isinstance(data["id_condicion_economica"], int)
    assert data["id_contrato_alquiler"] == contrato["id_contrato_alquiler"]
    assert Decimal(data["monto_base"]) == Decimal("150000.00")
    assert data["periodicidad"] == "mensual"
    assert data["moneda"] == "ARS"
    assert data["fecha_desde"] == "2026-05-01"
    assert data["fecha_hasta"] == "2026-10-31"
    assert data["version_registro"] == 1
    assert data["deleted_at"] is None

    row = db_session.execute(
        text(
            """
            SELECT monto_base, moneda, periodicidad
            FROM condicion_economica_alquiler
            WHERE id_condicion_economica = :id
            """
        ),
        {"id": data["id_condicion_economica"]},
    ).mappings().one()
    assert row["moneda"] == "ARS"
    assert row["periodicidad"] == "mensual"


def test_create_condicion_economica_exitosa_contrato_activo(client) -> None:
    contrato = _crear_contrato_activo(client, codigo="CEA-CRE-002")

    response = client.post(
        _url(contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json={
            "monto_base": "200000.00",
            "fecha_desde": "2026-05-01",
        },
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["fecha_hasta"] is None
    assert data["periodicidad"] is None
    assert data["moneda"] is None


def test_create_condicion_economica_devuelve_404_si_contrato_no_existe(client) -> None:
    response = client.post(
        "/api/v1/contratos-alquiler/999999/condiciones-economicas-alquiler",
        headers=HEADERS,
        json={"monto_base": "100.00", "fecha_desde": "2026-05-01"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_create_condicion_economica_devuelve_400_si_contrato_cancelado(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-CRE-003")
    client.patch(
        f"/api/v1/contratos-alquiler/{contrato['id_contrato_alquiler']}/cancelar",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    response = client.post(
        _url(contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json={"monto_base": "100.00", "fecha_desde": "2026-05-01"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["details"]["errors"] == ["INVALID_CONTRATO_STATE"]


def test_create_condicion_economica_devuelve_400_si_monto_invalido(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-CRE-004")

    response = client.post(
        _url(contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json={"monto_base": "0.00", "fecha_desde": "2026-05-01"},
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_MONTO_BASE"]


def test_create_condicion_economica_devuelve_400_si_fecha_invalida(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-CRE-005")

    response = client.post(
        _url(contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json={
            "monto_base": "100.00",
            "fecha_desde": "2026-10-01",
            "fecha_hasta": "2026-05-01",
        },
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_DATE_RANGE"]


def test_create_condicion_economica_devuelve_400_si_solapamiento(client) -> None:
    contrato = _crear_contrato_borrador(client, codigo="CEA-CRE-006")

    first = client.post(
        _url(contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json={
            "monto_base": "100.00",
            "moneda": "ARS",
            "fecha_desde": "2026-05-01",
            "fecha_hasta": "2026-10-31",
        },
    )
    assert first.status_code == 201

    response = client.post(
        _url(contrato["id_contrato_alquiler"]),
        headers=HEADERS,
        json={
            "monto_base": "200.00",
            "moneda": "ARS",
            "fecha_desde": "2026-08-01",
            "fecha_hasta": "2027-01-31",
        },
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["CONDICION_ECONOMICA_SOLAPADA"]
