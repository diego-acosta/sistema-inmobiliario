from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_factura_servicio_sql import (
    _asociar_inmueble_servicio,
    _asociar_unidad_funcional_servicio,
    _crear_inmueble,
    _crear_servicio,
    _crear_unidad_funcional,
)


def _payload(
    *,
    id_servicio: int,
    id_inmueble: int | None = None,
    id_unidad_funcional: int | None = None,
    numero_factura: str = "A-0001-00001234",
) -> dict:
    return {
        "id_servicio": id_servicio,
        "id_inmueble": id_inmueble,
        "id_unidad_funcional": id_unidad_funcional,
        "proveedor": "CALF",
        "numero_factura": numero_factura,
        "fecha_emision": "2026-05-01",
        "fecha_vencimiento": "2026-05-15",
        "periodo_desde": "2026-04-01",
        "periodo_hasta": "2026-04-30",
        "importe_total": 25000.00,
        "observaciones": "Factura externa",
    }


def test_create_factura_servicio_asociada_a_inmueble_valido(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-API-INM-001")
    id_servicio = _crear_servicio(db_session, codigo="FS-API-SRV-001")
    _asociar_inmueble_servicio(
        db_session,
        id_inmueble=id_inmueble,
        id_servicio=id_servicio,
    )

    response = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            numero_factura="FS-API-FAC-001",
        ),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id_factura_servicio"] > 0
    assert data["id_servicio"] == id_servicio
    assert data["id_inmueble"] == id_inmueble
    assert data["id_unidad_funcional"] is None
    assert data["estado_factura_servicio"] == "REGISTRADA"
    assert data["importe_total"] == 25000.0


def test_create_factura_servicio_asociada_a_unidad_funcional_valida(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-API-INM-002")
    id_uf = _crear_unidad_funcional(
        db_session,
        id_inmueble=id_inmueble,
        codigo="FS-API-UF-002",
    )
    id_servicio = _crear_servicio(db_session, codigo="FS-API-SRV-002")
    _asociar_unidad_funcional_servicio(
        db_session,
        id_unidad_funcional=id_uf,
        id_servicio=id_servicio,
    )

    response = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_unidad_funcional=id_uf,
            numero_factura="FS-API-FAC-002",
        ),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id_inmueble"] is None
    assert data["id_unidad_funcional"] == id_uf


def test_create_factura_servicio_rechaza_xor_invalido(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-API-INM-003")
    id_uf = _crear_unidad_funcional(
        db_session,
        id_inmueble=id_inmueble,
        codigo="FS-API-UF-003",
    )
    id_servicio = _crear_servicio(db_session, codigo="FS-API-SRV-003")

    response = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_uf,
            numero_factura="FS-API-FAC-003",
        ),
    )

    assert response.status_code == 422


def test_create_factura_servicio_rechaza_servicio_no_asociado(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-API-INM-004")
    id_servicio = _crear_servicio(db_session, codigo="FS-API-SRV-004")

    response = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            numero_factura="FS-API-FAC-004",
        ),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "SERVICIO_NO_ASOCIADO"


def test_create_factura_servicio_rechaza_duplicado(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-API-INM-005")
    id_servicio = _crear_servicio(db_session, codigo="FS-API-SRV-005")
    _asociar_inmueble_servicio(
        db_session,
        id_inmueble=id_inmueble,
        id_servicio=id_servicio,
    )

    payload = _payload(
        id_servicio=id_servicio,
        id_inmueble=id_inmueble,
        numero_factura="FS-API-FAC-005",
    )

    first = client.post("/api/v1/facturas-servicio", headers=HEADERS, json=payload)
    second = client.post("/api/v1/facturas-servicio", headers=HEADERS, json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "FACTURA_SERVICIO_DUPLICADA"


def test_get_factura_servicio_por_id(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-API-INM-006")
    id_servicio = _crear_servicio(db_session, codigo="FS-API-SRV-006")
    _asociar_inmueble_servicio(
        db_session,
        id_inmueble=id_inmueble,
        id_servicio=id_servicio,
    )
    created = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            numero_factura="FS-API-FAC-006",
        ),
    )
    id_factura = created.json()["data"]["id_factura_servicio"]

    response = client.get(f"/api/v1/facturas-servicio/{id_factura}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id_factura_servicio"] == id_factura
    assert data["numero_factura"] == "FS-API-FAC-006"


def test_list_facturas_servicio(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-API-INM-007")
    id_servicio = _crear_servicio(db_session, codigo="FS-API-SRV-007")
    _asociar_inmueble_servicio(
        db_session,
        id_inmueble=id_inmueble,
        id_servicio=id_servicio,
    )
    created = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            numero_factura="FS-API-FAC-007",
        ),
    )
    id_factura = created.json()["data"]["id_factura_servicio"]

    response = client.get("/api/v1/facturas-servicio")

    assert response.status_code == 200
    ids = {item["id_factura_servicio"] for item in response.json()["data"]}
    assert id_factura in ids


def test_create_factura_servicio_no_crea_relacion_generadora_ni_obligacion(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-API-INM-008")
    id_servicio = _crear_servicio(db_session, codigo="FS-API-SRV-008")
    _asociar_inmueble_servicio(
        db_session,
        id_inmueble=id_inmueble,
        id_servicio=id_servicio,
    )
    obligaciones_antes = db_session.execute(
        text("SELECT COUNT(*) FROM obligacion_financiera")
    ).scalar_one()

    response = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            numero_factura="FS-API-FAC-008",
        ),
    )
    id_factura = response.json()["data"]["id_factura_servicio"]

    relaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM relacion_generadora
            WHERE tipo_origen = 'factura_servicio'
              AND id_origen = :id_factura
              AND deleted_at IS NULL
            """
        ),
        {"id_factura": id_factura},
    ).scalar_one()
    obligaciones_despues = db_session.execute(
        text("SELECT COUNT(*) FROM obligacion_financiera")
    ).scalar_one()

    assert response.status_code == 201
    assert relaciones == 0
    assert obligaciones_despues == obligaciones_antes
