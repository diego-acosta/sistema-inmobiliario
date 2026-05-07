from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_factura_servicio_sql import _crear_inmueble, _crear_unidad_funcional


def _payload_base(**overrides):
    payload = {
        "id_inmueble": overrides.pop("id_inmueble", None),
        "id_unidad_funcional": overrides.pop("id_unidad_funcional", None),
        "organismo": "Municipalidad de Neuquen",
        "tipo_impuesto": "TASA_MUNICIPAL",
        "partida_nomenclatura": "NC-123",
        "numero_comprobante": "MUN-2026-0001",
        "periodo_desde": "2026-05-01",
        "periodo_hasta": "2026-05-31",
        "fecha_emision": "2026-05-01",
        "fecha_vencimiento": "2026-05-20",
        "importe_total": 15000.00,
        "modalidad_gestion_impuesto": "EMPRESA_PAGA_Y_RECUPERA",
        "observaciones": "Comprobante fiscal externo",
    }
    payload.update(overrides)
    return payload


def _crear_comprobante(client, db_session, **overrides):
    if "id_inmueble" not in overrides and "id_unidad_funcional" not in overrides:
        overrides["id_inmueble"] = _crear_inmueble(db_session, codigo="IMP-INM")
    return client.post(
        "/api/v1/comprobantes-impuesto",
        json=_payload_base(**overrides),
        headers=HEADERS,
    )


def test_crear_comprobante_impuesto_asociado_a_inmueble(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="IMP-INM-001")

    response = _crear_comprobante(
        client,
        db_session,
        id_inmueble=id_inmueble,
        numero_comprobante="MUN-2026-INM-001",
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id_comprobante_impuesto"] > 0
    assert data["id_inmueble"] == id_inmueble
    assert data["id_unidad_funcional"] is None
    assert data["organismo"] == "Municipalidad de Neuquen"
    assert data["modalidad_gestion_impuesto"] == "EMPRESA_PAGA_Y_RECUPERA"
    assert data["estado_comprobante_impuesto"] == "REGISTRADO"


def test_crear_comprobante_impuesto_asociado_a_unidad_funcional(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="IMP-INM-002")
    id_unidad = _crear_unidad_funcional(
        db_session,
        id_inmueble=id_inmueble,
        codigo="IMP-UF-002",
    )

    response = _crear_comprobante(
        client,
        db_session,
        id_unidad_funcional=id_unidad,
        numero_comprobante="MUN-2026-UF-002",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id_inmueble"] is None
    assert data["id_unidad_funcional"] == id_unidad
    assert data["modalidad_gestion_impuesto"] == "DIRECTO_RESPONSABLE"


def test_crear_comprobante_impuesto_rechaza_xor_invalido(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="IMP-XOR-001")
    id_unidad = _crear_unidad_funcional(
        db_session,
        id_inmueble=id_inmueble,
        codigo="IMP-XOR-UF",
    )

    response = client.post(
        "/api/v1/comprobantes-impuesto",
        json=_payload_base(
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad,
            numero_comprobante="MUN-2026-XOR",
        ),
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_crear_comprobante_impuesto_rechaza_importe_negativo(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="IMP-NEG-001")

    response = client.post(
        "/api/v1/comprobantes-impuesto",
        json=_payload_base(
            id_inmueble=id_inmueble,
            numero_comprobante="MUN-2026-NEG",
            importe_total=-1,
        ),
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_crear_comprobante_impuesto_rechaza_periodo_invalido(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="IMP-PER-001")

    response = client.post(
        "/api/v1/comprobantes-impuesto",
        json=_payload_base(
            id_inmueble=id_inmueble,
            numero_comprobante="MUN-2026-PER",
            periodo_desde="2026-06-01",
            periodo_hasta="2026-05-01",
        ),
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_crear_comprobante_impuesto_rechaza_vencimiento_anterior_a_emision(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="IMP-FEC-001")

    response = client.post(
        "/api/v1/comprobantes-impuesto",
        json=_payload_base(
            id_inmueble=id_inmueble,
            numero_comprobante="MUN-2026-FEC",
            fecha_emision="2026-05-20",
            fecha_vencimiento="2026-05-01",
        ),
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_crear_comprobante_impuesto_rechaza_modalidad_invalida(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="IMP-MOD-001")

    response = client.post(
        "/api/v1/comprobantes-impuesto",
        json=_payload_base(
            id_inmueble=id_inmueble,
            numero_comprobante="MUN-2026-MOD",
            modalidad_gestion_impuesto="NO_EXISTE",
        ),
        headers=HEADERS,
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "COMPROBANTE_IMPUESTO_INVALIDO"


def test_crear_comprobante_impuesto_rechaza_duplicado_organismo_numero(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="IMP-DUP-001")
    payload = _payload_base(
        id_inmueble=id_inmueble,
        numero_comprobante="MUN-2026-DUP",
    )

    first = client.post("/api/v1/comprobantes-impuesto", json=payload, headers=HEADERS)
    second = client.post("/api/v1/comprobantes-impuesto", json=payload, headers=HEADERS)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "COMPROBANTE_IMPUESTO_DUPLICADO"


def test_get_comprobante_impuesto_por_id(client, db_session) -> None:
    created = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-GET",
    ).json()["data"]

    response = client.get(
        f"/api/v1/comprobantes-impuesto/{created['id_comprobante_impuesto']}"
    )

    assert response.status_code == 200
    assert response.json()["data"]["id_comprobante_impuesto"] == created[
        "id_comprobante_impuesto"
    ]


def test_list_comprobantes_impuesto_basico(client, db_session) -> None:
    first = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LST-1",
    ).json()["data"]
    second = _crear_comprobante(
        client,
        db_session,
        id_inmueble=_crear_inmueble(db_session, codigo="IMP-LST-002"),
        numero_comprobante="MUN-2026-LST-2",
        modalidad_gestion_impuesto="EMPRESA_ASUME",
    ).json()["data"]

    response = client.get("/api/v1/comprobantes-impuesto")

    assert response.status_code == 200
    ids = {item["id_comprobante_impuesto"] for item in response.json()["data"]}
    assert first["id_comprobante_impuesto"] in ids
    assert second["id_comprobante_impuesto"] in ids


def test_crear_comprobante_impuesto_no_crea_efectos_financieros(
    client, db_session
) -> None:
    before = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_tesoreria) AS tesoreria,
                (SELECT COUNT(*) FROM relacion_generadora) AS relaciones,
                (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones
            """
        )
    ).mappings().one()

    response = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-SIN-EFECTOS",
    )

    after = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_tesoreria) AS tesoreria,
                (SELECT COUNT(*) FROM relacion_generadora) AS relaciones,
                (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones
            """
        )
    ).mappings().one()

    assert response.status_code == 201
    assert after["tesoreria"] == before["tesoreria"]
    assert after["relaciones"] == before["relaciones"]
    assert after["obligaciones"] == before["obligaciones"]
