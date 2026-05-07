from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_asignacion_servicio_responsable_api import _crear_persona
from tests.test_factura_servicio_api import _crear_cuenta_financiera
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


def _headers_op(op_id: str) -> dict:
    headers = dict(HEADERS)
    headers["X-Op-Id"] = op_id
    return headers


def _registrar_egreso_impuesto(
    client,
    db_session,
    *,
    id_comprobante_impuesto: int,
    importe_pagado: float = 15000.00,
    id_cuenta_financiera_origen: int | None = None,
    op_id: str = "00000000-0000-0000-0000-00000000e001",
    fecha_pago: str = "2026-05-20",
    medio_pago: str = "TRANSFERENCIA",
    referencia_comprobante: str = "TRX-MUN-123",
    observaciones: str = "Pago tasa municipal",
):
    if id_cuenta_financiera_origen is None:
        id_cuenta_financiera_origen = _crear_cuenta_financiera(
            db_session, nombre=f"Cuenta impuesto {op_id[-4:]}"
        )
    return client.post(
        (
            "/api/v1/financiero/comprobantes-impuesto/"
            f"{id_comprobante_impuesto}/egresos"
        ),
        json={
            "id_cuenta_financiera_origen": id_cuenta_financiera_origen,
            "fecha_pago": fecha_pago,
            "importe_pagado": importe_pagado,
            "medio_pago": medio_pago,
            "referencia_comprobante": referencia_comprobante,
            "observaciones": observaciones,
        },
        headers=_headers_op(op_id),
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


def test_registrar_egreso_impuesto_total_empresa_asume(client, db_session) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-ASUME",
        modalidad_gestion_impuesto="EMPRESA_ASUME",
        importe_total=15000,
    ).json()["data"]

    response = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000e101",
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id_egreso_impuesto_empresa"] > 0
    assert data["id_comprobante_impuesto"] == comprobante["id_comprobante_impuesto"]
    assert data["importe_pagado"] == 15000.0
    assert data["estado_egreso"] == "REGISTRADO"
    assert data["impacta_tesoreria"] is True
    assert data["crea_movimiento_financiero"] is False
    assert data["crea_relacion_generadora"] is False
    assert data["crea_obligacion_financiera"] is False


def test_registrar_egreso_impuesto_total_empresa_paga_y_recupera(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-RECUPERA",
        modalidad_gestion_impuesto="EMPRESA_PAGA_Y_RECUPERA",
        importe_total=15000,
    ).json()["data"]

    response = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000e102",
    )

    assert response.status_code == 201
    assert response.json()["data"]["importe_pagado"] == 15000.0


def test_registrar_egreso_impuesto_rechaza_directo_responsable(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-DIRECTO",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]

    response = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000e103",
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "EGRESO_IMPUESTO_NO_APLICA_MODALIDAD"


def test_registrar_egreso_impuesto_parcial(client, db_session) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-PARCIAL",
        importe_total=15000,
    ).json()["data"]

    response = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        importe_pagado=7000,
        op_id="00000000-0000-0000-0000-00000000e104",
    )

    assert response.status_code == 201
    assert response.json()["data"]["importe_pagado"] == 7000.0


def test_registrar_egreso_impuesto_multiples_parciales_hasta_total(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-PARCIALES",
        importe_total=15000,
    ).json()["data"]
    cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta impuesto parciales")

    first = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_cuenta_financiera_origen=cuenta,
        importe_pagado=6000,
        op_id="00000000-0000-0000-0000-00000000e105",
    )
    second = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_cuenta_financiera_origen=cuenta,
        importe_pagado=9000,
        op_id="00000000-0000-0000-0000-00000000e106",
        referencia_comprobante="TRX-MUN-124",
    )

    assert first.status_code == 201
    assert second.status_code == 201
    total = db_session.execute(
        text(
            """
            SELECT SUM(importe_pagado)
            FROM egreso_impuesto_empresa
            WHERE id_comprobante_impuesto = :id
              AND estado_egreso = 'REGISTRADO'
              AND deleted_at IS NULL
            """
        ),
        {"id": comprobante["id_comprobante_impuesto"]},
    ).scalar_one()
    assert float(total) == 15000.0


def test_registrar_egreso_impuesto_rechaza_sobrepago(client, db_session) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-SOBREPAGO",
        importe_total=15000,
    ).json()["data"]
    cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta impuesto sobrepago")

    first = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_cuenta_financiera_origen=cuenta,
        importe_pagado=10000,
        op_id="00000000-0000-0000-0000-00000000e107",
    )
    second = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_cuenta_financiera_origen=cuenta,
        importe_pagado=6000,
        op_id="00000000-0000-0000-0000-00000000e108",
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "EGRESO_SUPERA_IMPORTE_COMPROBANTE"


def test_registrar_egreso_impuesto_retry_mismo_op_id_no_duplica(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-IDEMP",
    ).json()["data"]
    cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta impuesto idem")
    op_id = "00000000-0000-0000-0000-00000000e109"

    first = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_cuenta_financiera_origen=cuenta,
        op_id=op_id,
    )
    second = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_cuenta_financiera_origen=cuenta,
        op_id=op_id,
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["data"]["resultado"] == "YA_REGISTRADO"
    assert second.json()["data"]["id_egreso_impuesto_empresa"] == first.json()[
        "data"
    ]["id_egreso_impuesto_empresa"]
    count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM egreso_impuesto_empresa
            WHERE id_comprobante_impuesto = :id
            """
        ),
        {"id": comprobante["id_comprobante_impuesto"]},
    ).scalar_one()
    assert count == 1


def test_registrar_egreso_impuesto_mismo_op_id_payload_distinto_conflicto(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-IDEMP-CONFLICT",
    ).json()["data"]
    cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta impuesto conflict")
    op_id = "00000000-0000-0000-0000-00000000e110"

    first = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_cuenta_financiera_origen=cuenta,
        importe_pagado=7000,
        op_id=op_id,
    )
    second = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_cuenta_financiera_origen=cuenta,
        importe_pagado=8000,
        op_id=op_id,
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"


def test_registrar_egreso_impuesto_crea_tesoreria_y_puente(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-PUENTE",
    ).json()["data"]

    response = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000e111",
    )

    assert response.status_code == 201
    data = response.json()["data"]
    row = db_session.execute(
        text(
            """
            SELECT
                e.id_egreso_impuesto_empresa,
                e.id_comprobante_impuesto,
                e.importe_pagado,
                mt.tipo_movimiento_tesoreria,
                mt.estado,
                mt.referencia_externa,
                mt.id_movimiento_financiero
            FROM egreso_impuesto_empresa e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
            WHERE e.id_egreso_impuesto_empresa = :id
            """
        ),
        {"id": data["id_egreso_impuesto_empresa"]},
    ).mappings().one()

    assert row["id_comprobante_impuesto"] == comprobante["id_comprobante_impuesto"]
    assert float(row["importe_pagado"]) == 15000.0
    assert row["tipo_movimiento_tesoreria"] == "EGRESO_IMPUESTO_EMPRESA"
    assert row["estado"] == "REGISTRADO"
    assert row["referencia_externa"] == (
        f"COMPROBANTE_IMPUESTO:{comprobante['id_comprobante_impuesto']}"
    )
    assert row["id_movimiento_financiero"] is None


def test_registrar_egreso_impuesto_no_crea_efectos_financieros(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-SIN-EFECTOS",
    ).json()["data"]
    before = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_financiero) AS financieros,
                (SELECT COUNT(*) FROM relacion_generadora) AS relaciones,
                (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones
            """
        )
    ).mappings().one()

    response = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000e112",
    )

    after = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_financiero) AS financieros,
                (SELECT COUNT(*) FROM relacion_generadora) AS relaciones,
                (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones
            """
        )
    ).mappings().one()

    assert response.status_code == 201
    assert after["financieros"] == before["financieros"]
    assert after["relaciones"] == before["relaciones"]
    assert after["obligaciones"] == before["obligaciones"]


def test_registrar_egreso_impuesto_no_afecta_estado_cuenta(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-EIE-EC")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-ESTADO-CUENTA",
    ).json()["data"]

    before = client.get(
        f"/api/v1/financiero/personas/{id_persona}/estado-cuenta",
        headers=HEADERS,
        params={"fecha_corte": "2026-05-20"},
    )
    response = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000e113",
    )
    after = client.get(
        f"/api/v1/financiero/personas/{id_persona}/estado-cuenta",
        headers=HEADERS,
        params={"fecha_corte": "2026-05-20"},
    )

    assert before.status_code == 200
    assert response.status_code == 201
    assert after.status_code == 200
    assert after.json()["data"]["resumen"] == before.json()["data"]["resumen"]
    assert after.json()["data"]["obligaciones"] == before.json()["data"]["obligaciones"]


def test_get_egresos_impuesto_sin_egresos_devuelve_sin_pago(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-GET-SIN",
        importe_total=15000,
    ).json()["data"]

    response = client.get(
        (
            "/api/v1/financiero/comprobantes-impuesto/"
            f"{comprobante['id_comprobante_impuesto']}/egresos"
        ),
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id_comprobante_impuesto"] == comprobante["id_comprobante_impuesto"]
    assert data["importe_total_comprobante"] == 15000.0
    assert data["total_egresado"] == 0.0
    assert data["saldo_pendiente_pago_impuesto"] == 15000.0
    assert data["estado_pago_impuesto"] == "SIN_PAGO"
    assert data["egresos"] == []


def test_get_egresos_impuesto_con_parcial_devuelve_pago_parcial(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-GET-PARCIAL",
        importe_total=15000,
    ).json()["data"]
    _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        importe_pagado=10000,
        op_id="00000000-0000-0000-0000-00000000e201",
    )

    response = client.get(
        (
            "/api/v1/financiero/comprobantes-impuesto/"
            f"{comprobante['id_comprobante_impuesto']}/egresos"
        ),
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_egresado"] == 10000.0
    assert data["saldo_pendiente_pago_impuesto"] == 5000.0
    assert data["estado_pago_impuesto"] == "PAGO_PARCIAL"
    assert len(data["egresos"]) == 1
    assert data["egresos"][0]["estado_egreso"] == "REGISTRADO"


def test_get_egresos_impuesto_con_total_devuelve_pagado(client, db_session) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-GET-TOTAL",
        importe_total=15000,
    ).json()["data"]
    _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        importe_pagado=15000,
        op_id="00000000-0000-0000-0000-00000000e202",
    )

    response = client.get(
        (
            "/api/v1/financiero/comprobantes-impuesto/"
            f"{comprobante['id_comprobante_impuesto']}/egresos"
        ),
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_egresado"] == 15000.0
    assert data["saldo_pendiente_pago_impuesto"] == 0.0
    assert data["estado_pago_impuesto"] == "PAGADO"


def test_get_egresos_impuesto_lista_multiples_egresos(client, db_session) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-GET-MULTI",
        importe_total=15000,
    ).json()["data"]
    cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta impuesto get multi")
    _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_cuenta_financiera_origen=cuenta,
        importe_pagado=6000,
        op_id="00000000-0000-0000-0000-00000000e203",
    )
    _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_cuenta_financiera_origen=cuenta,
        importe_pagado=9000,
        referencia_comprobante="TRX-MUN-456",
        observaciones="Segundo pago municipal",
        op_id="00000000-0000-0000-0000-00000000e204",
    )

    response = client.get(
        (
            "/api/v1/financiero/comprobantes-impuesto/"
            f"{comprobante['id_comprobante_impuesto']}/egresos"
        ),
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["estado_pago_impuesto"] == "PAGADO"
    assert [item["importe_pagado"] for item in data["egresos"]] == [6000.0, 9000.0]
    assert data["egresos"][1]["observaciones"] == "Segundo pago municipal"


def test_get_egresos_impuesto_comprobante_inexistente_devuelve_404(client) -> None:
    response = client.get(
        "/api/v1/financiero/comprobantes-impuesto/999999999/egresos",
        headers=HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "COMPROBANTE_IMPUESTO_NOT_FOUND"


def test_anular_egreso_impuesto_registrado_anula_egreso_y_tesoreria(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-ANULAR",
    ).json()["data"]
    egreso = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000e205",
    ).json()["data"]

    response = client.patch(
        (
            "/api/v1/financiero/egresos-impuesto-empresa/"
            f"{egreso['id_egreso_impuesto_empresa']}/anular"
        ),
        json={"motivo": "Carga duplicada"},
        headers=_headers_op("00000000-0000-0000-0000-00000000e206"),
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["resultado"] == "ANULADO"
    assert data["estado_egreso"] == "ANULADO"
    assert data["estado_movimiento_tesoreria"] == "ANULADO"
    assert data["ya_anulado"] is False
    row = db_session.execute(
        text(
            """
            SELECT e.estado_egreso, mt.estado AS estado_mt
            FROM egreso_impuesto_empresa e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
            WHERE e.id_egreso_impuesto_empresa = :id
            """
        ),
        {"id": egreso["id_egreso_impuesto_empresa"]},
    ).mappings().one()
    assert row["estado_egreso"] == "ANULADO"
    assert row["estado_mt"] == "ANULADO"


def test_get_egresos_impuesto_no_suma_egreso_anulado(client, db_session) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-ANULADO-NO-SUMA",
        importe_total=15000,
    ).json()["data"]
    egreso = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        importe_pagado=10000,
        op_id="00000000-0000-0000-0000-00000000e207",
    ).json()["data"]
    client.patch(
        (
            "/api/v1/financiero/egresos-impuesto-empresa/"
            f"{egreso['id_egreso_impuesto_empresa']}/anular"
        ),
        json={"motivo": "Error de carga"},
        headers=_headers_op("00000000-0000-0000-0000-00000000e208"),
    )

    response = client.get(
        (
            "/api/v1/financiero/comprobantes-impuesto/"
            f"{comprobante['id_comprobante_impuesto']}/egresos"
        ),
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_egresado"] == 0.0
    assert data["estado_pago_impuesto"] == "SIN_PAGO"
    assert data["egresos"][0]["estado_egreso"] == "ANULADO"


def test_anular_egreso_impuesto_repetido_devuelve_ya_anulado(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-ANULAR-IDEMP",
    ).json()["data"]
    egreso = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000e209",
    ).json()["data"]
    url = (
        "/api/v1/financiero/egresos-impuesto-empresa/"
        f"{egreso['id_egreso_impuesto_empresa']}/anular"
    )

    first = client.patch(
        url,
        json={"motivo": "Carga duplicada"},
        headers=_headers_op("00000000-0000-0000-0000-00000000e210"),
    )
    second = client.patch(
        url,
        json={"motivo": "Otro intento"},
        headers=_headers_op("00000000-0000-0000-0000-00000000e211"),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["resultado"] == "YA_ANULADO"
    assert second.json()["data"]["ya_anulado"] is True
    assert second.json()["data"]["motivo"] == "Carga duplicada"


def test_anular_egreso_impuesto_inexistente_devuelve_404(client) -> None:
    response = client.patch(
        "/api/v1/financiero/egresos-impuesto-empresa/999999999/anular",
        json={"motivo": "No existe"},
        headers=_headers_op("00000000-0000-0000-0000-00000000e212"),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "EGRESO_IMPUESTO_NOT_FOUND"


def test_anular_egreso_impuesto_no_crea_efectos_financieros(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-EIE-ANULAR-SIN-EFECTOS",
    ).json()["data"]
    egreso = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000e213",
    ).json()["data"]
    before = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_financiero) AS financieros,
                (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones
            """
        )
    ).mappings().one()

    response = client.patch(
        (
            "/api/v1/financiero/egresos-impuesto-empresa/"
            f"{egreso['id_egreso_impuesto_empresa']}/anular"
        ),
        json={"motivo": "Error de carga"},
        headers=_headers_op("00000000-0000-0000-0000-00000000e214"),
    )

    after = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_financiero) AS financieros,
                (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones
            """
        )
    ).mappings().one()

    assert response.status_code == 200
    assert after["financieros"] == before["financieros"]
    assert after["obligaciones"] == before["obligaciones"]


def _liquidar_impuesto(
    client,
    *,
    id_comprobante_impuesto: int,
    id_persona: int,
    importe_total_trasladar: float = 15000.00,
    op_id: str = "00000000-0000-0000-0000-00000000f001",
    porcentaje_responsabilidad: float = 100.00,
):
    return client.post(
        (
            "/api/v1/financiero/comprobantes-impuesto/"
            f"{id_comprobante_impuesto}/liquidaciones-impuesto-trasladado"
        ),
        json={
            "fecha_liquidacion": "2026-05-25",
            "fecha_vencimiento": "2026-06-10",
            "importe_total_trasladar": importe_total_trasladar,
            "responsables": [
                {
                    "id_persona": id_persona,
                    "porcentaje_responsabilidad": porcentaje_responsabilidad,
                }
            ],
            "observaciones": "Liquidacion impuesto municipal",
        },
        headers=_headers_op(op_id),
    )


def test_liquidacion_impuesto_empresa_asume_bloquea(client, db_session) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-ASUME")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-ASUME",
        modalidad_gestion_impuesto="EMPRESA_ASUME",
    ).json()["data"]

    response = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f101",
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "IMPUESTO_EMPRESA_ASUME_NO_TRASLADABLE"


def test_liquidacion_impuesto_directo_responsable_sin_egreso_empresa(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-DIRECTO")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-DIRECTO",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
        importe_total=15000,
    ).json()["data"]

    response = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f102",
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["modalidad_gestion_impuesto"] == "DIRECTO_RESPONSABLE"
    assert data["importe_total_base"] == 15000.0
    assert data["importe_total_trasladar"] == 15000.0
    assert data["importe_absorbido_empresa"] == 0.0
    assert data["id_relacion_generadora"] > 0
    assert data["id_obligacion_financiera"] > 0


def test_liquidacion_impuesto_empresa_paga_y_recupera_requiere_egreso(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-SIN-EGRESO")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-SIN-EGRESO",
        modalidad_gestion_impuesto="EMPRESA_PAGA_Y_RECUPERA",
    ).json()["data"]

    response = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f103",
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "EGRESO_IMPUESTO_REQUERIDO"


def test_liquidacion_impuesto_empresa_paga_y_recupera_con_egreso(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-RECUPERA")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-RECUPERA",
        modalidad_gestion_impuesto="EMPRESA_PAGA_Y_RECUPERA",
        importe_total=15000,
    ).json()["data"]
    _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000f104",
    )

    response = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f105",
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["modalidad_gestion_impuesto"] == "EMPRESA_PAGA_Y_RECUPERA"
    assert data["importe_total_base"] == 15000.0
    assert data["importe_total_trasladar"] == 15000.0


def test_liquidacion_impuesto_crea_relacion_obligacion_composicion_y_obligado(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-FIN")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-FIN",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]

    response = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f106",
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    row = db_session.execute(
        text(
            """
            SELECT
                rg.tipo_origen,
                rg.id_origen,
                o.estado_obligacion,
                o.saldo_pendiente,
                cf.codigo_concepto_financiero,
                oo.id_persona,
                oo.rol_obligado,
                litc.numero_comprobante
            FROM liquidacion_impuesto_trasladado lit
            JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = lit.id_relacion_generadora
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = lit.id_obligacion_financiera
            JOIN composicion_obligacion co
              ON co.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = co.id_concepto_financiero
            JOIN obligacion_obligado oo
              ON oo.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN liquidacion_impuesto_trasladado_comprobante litc
              ON litc.id_liquidacion_impuesto_trasladado =
                 lit.id_liquidacion_impuesto_trasladado
            WHERE lit.id_liquidacion_impuesto_trasladado = :id
            """
        ),
        {"id": data["id_liquidacion_impuesto_trasladado"]},
    ).mappings().one()
    assert row["tipo_origen"] == "liquidacion_impuesto_trasladado"
    assert row["id_origen"] == data["id_liquidacion_impuesto_trasladado"]
    assert row["estado_obligacion"] == "EMITIDA"
    assert float(row["saldo_pendiente"]) == 15000.0
    assert row["codigo_concepto_financiero"] == "IMPUESTO_TRASLADADO"
    assert row["id_persona"] == id_persona
    assert row["rol_obligado"] == "RESPONSABLE_IMPUESTO_TRASLADADO"
    assert row["numero_comprobante"] == "MUN-2026-LIT-FIN"


def test_liquidacion_impuesto_no_crea_tesoreria_ni_pago_externo(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-SIN-EFECTOS")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-SIN-EFECTOS",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]
    before = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_tesoreria) AS tesoreria,
                (SELECT COUNT(*) FROM movimiento_financiero
                 WHERE tipo_movimiento = 'PAGO_EXTERNO_INFORMADO') AS externos
            """
        )
    ).mappings().one()

    response = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f107",
    )

    after = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_tesoreria) AS tesoreria,
                (SELECT COUNT(*) FROM movimiento_financiero
                 WHERE tipo_movimiento = 'PAGO_EXTERNO_INFORMADO') AS externos
            """
        )
    ).mappings().one()
    assert response.status_code == 201
    assert after["tesoreria"] == before["tesoreria"]
    assert after["externos"] == before["externos"]


def test_liquidacion_impuesto_no_reutiliza_egreso_con_vinculo_activo(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-NO-REUSA")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-NO-REUSA",
        modalidad_gestion_impuesto="EMPRESA_PAGA_Y_RECUPERA",
    ).json()["data"]
    _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000f108",
    )
    first = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f109",
    )
    second = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f110",
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "EGRESO_IMPUESTO_NO_DISPONIBLE"


def test_liquidacion_impuesto_porcentajes_invalidos_fallan(client, db_session) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-PCT")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-PCT",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]
    response = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        porcentaje_responsabilidad=50,
        op_id="00000000-0000-0000-0000-00000000f111",
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "PORCENTAJES_RESPONSABLES_INVALIDOS"


def test_liquidacion_impuesto_retry_mismo_op_id_no_duplica(client, db_session) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-IDEMP")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-IDEMP",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]
    op_id = "00000000-0000-0000-0000-00000000f112"

    first = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id=op_id,
    )
    second = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id=op_id,
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["data"]["resultado"] == "YA_EMITIDA"
    assert second.json()["data"]["id_liquidacion_impuesto_trasladado"] == first.json()[
        "data"
    ]["id_liquidacion_impuesto_trasladado"]


def test_liquidacion_impuesto_mismo_op_id_payload_distinto_falla(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-IDEMP-CONFLICT")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-IDEMP-CONFLICT",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]
    op_id = "00000000-0000-0000-0000-00000000f113"
    first = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        importe_total_trasladar=10000,
        op_id=op_id,
    )
    second = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        importe_total_trasladar=12000,
        op_id=op_id,
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"


def test_liquidacion_impuesto_estado_cuenta_muestra_trasladado(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-EC")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-EC",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]
    liquidacion = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f114",
    ).json()["data"]

    response = client.get(
        f"/api/v1/financiero/personas/{id_persona}/estado-cuenta",
        headers=HEADERS,
        params={"fecha_corte": "2026-05-25"},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    trasladados = next(
        g for g in data["grupos_deuda"] if g["grupo_origen_deuda"] == "TRASLADADOS"
    )
    relacion = next(
        r
        for r in trasladados["relaciones"]
        if r["id_relacion_generadora"] == liquidacion["id_relacion_generadora"]
    )
    assert relacion["tipo_origen"] == "LIQUIDACION_IMPUESTO_TRASLADADO"
    assert relacion["obligaciones"][0]["composiciones"][0][
        "codigo_concepto_financiero"
    ] == "IMPUESTO_TRASLADADO"


def test_liquidacion_impuesto_pago_normal_reduce_saldo(client, db_session) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-PAGO")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-PAGO",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]
    liquidacion = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f115",
    ).json()["data"]

    pago = client.post(
        "/api/v1/financiero/pagos",
        headers=_headers_op("00000000-0000-0000-0000-00000000f116"),
        params={"id_persona": id_persona},
        json={"monto": 15000.00, "fecha_pago": "2026-05-30"},
    )
    assert pago.status_code == 201, pago.text
    assert pago.json()["data"]["obligaciones_pagadas"][0][
        "id_obligacion_financiera"
    ] == liquidacion["id_obligacion_financiera"]
    saldo = db_session.execute(
        text(
            """
            SELECT saldo_pendiente
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id
            """
        ),
        {"id": liquidacion["id_obligacion_financiera"]},
    ).scalar_one()
    assert float(saldo) == 0.0


def test_get_liquidacion_impuesto_directo_responsable_sin_egresos(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-GET-DIRECTO")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-GET-DIRECTO",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]
    liquidacion = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f201",
    ).json()["data"]

    response = client.get(
        (
            "/api/v1/financiero/liquidaciones-impuesto-trasladado/"
            f"{liquidacion['id_liquidacion_impuesto_trasladado']}"
        ),
        headers=HEADERS,
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["modalidad_gestion_impuesto"] == "DIRECTO_RESPONSABLE"
    assert data["egresos"] == []
    assert data["comprobantes"][0]["id_comprobante_impuesto"] == comprobante[
        "id_comprobante_impuesto"
    ]
    assert data["responsables"][0]["id_persona"] == id_persona
    assert data["id_relacion_generadora"] == liquidacion["id_relacion_generadora"]
    assert data["obligacion"]["id_obligacion_financiera"] == liquidacion[
        "id_obligacion_financiera"
    ]
    assert data["obligacion"]["composiciones"][0][
        "codigo_concepto_financiero"
    ] == "IMPUESTO_TRASLADADO"
    assert data["obligacion"]["obligados"][0]["rol_obligado"] == (
        "RESPONSABLE_IMPUESTO_TRASLADADO"
    )


def test_get_liquidacion_impuesto_empresa_paga_y_recupera_con_egreso(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-GET-RECUPERA")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-GET-RECUPERA",
        modalidad_gestion_impuesto="EMPRESA_PAGA_Y_RECUPERA",
    ).json()["data"]
    egreso = _registrar_egreso_impuesto(
        client,
        db_session,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        op_id="00000000-0000-0000-0000-00000000f202",
    ).json()["data"]
    liquidacion = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f203",
    ).json()["data"]

    response = client.get(
        (
            "/api/v1/financiero/liquidaciones-impuesto-trasladado/"
            f"{liquidacion['id_liquidacion_impuesto_trasladado']}"
        ),
        headers=HEADERS,
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["modalidad_gestion_impuesto"] == "EMPRESA_PAGA_Y_RECUPERA"
    assert data["comprobantes"][0]["numero_comprobante"] == (
        "MUN-2026-LIT-GET-RECUPERA"
    )
    assert data["egresos"][0]["id_egreso_impuesto_empresa"] == egreso[
        "id_egreso_impuesto_empresa"
    ]
    assert data["egresos"][0]["id_movimiento_tesoreria"] == egreso[
        "id_movimiento_tesoreria"
    ]
    assert data["egresos"][0]["estado_egreso"] == "REGISTRADO"
    assert data["responsables"][0]["importe_responsable"] == 15000.0


def test_list_liquidaciones_impuesto_por_comprobante_devuelve_liquidacion(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-LIST")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-LIST",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]
    liquidacion = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f204",
    ).json()["data"]

    response = client.get(
        (
            "/api/v1/financiero/comprobantes-impuesto/"
            f"{comprobante['id_comprobante_impuesto']}"
            "/liquidaciones-impuesto-trasladado"
        ),
        headers=HEADERS,
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id_comprobante_impuesto"] == comprobante["id_comprobante_impuesto"]
    assert data["total"] == 1
    item = data["items"][0]
    assert item["id_liquidacion_impuesto_trasladado"] == liquidacion[
        "id_liquidacion_impuesto_trasladado"
    ]
    assert item["modalidad_gestion_impuesto"] == "DIRECTO_RESPONSABLE"
    assert item["id_obligacion_financiera"] == liquidacion["id_obligacion_financiera"]
    assert item["saldo_pendiente"] == 15000.0
    assert item["cantidad_responsables"] == 1


def test_list_liquidaciones_impuesto_comprobante_sin_liquidaciones_devuelve_vacio(
    client, db_session
) -> None:
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-LIST-VACIO",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]

    response = client.get(
        (
            "/api/v1/financiero/comprobantes-impuesto/"
            f"{comprobante['id_comprobante_impuesto']}"
            "/liquidaciones-impuesto-trasladado"
        ),
        headers=HEADERS,
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["items"] == []
    assert response.json()["data"]["total"] == 0


def test_get_liquidacion_impuesto_inexistente_devuelve_404(client) -> None:
    response = client.get(
        "/api/v1/financiero/liquidaciones-impuesto-trasladado/999999",
        headers=HEADERS,
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "LIQUIDACION_IMPUESTO_TRASLADADO_NOT_FOUND"


def test_list_liquidaciones_impuesto_comprobante_inexistente_devuelve_404(
    client,
) -> None:
    response = client.get(
        (
            "/api/v1/financiero/comprobantes-impuesto/999999/"
            "liquidaciones-impuesto-trasladado"
        ),
        headers=HEADERS,
    )
    assert response.status_code == 404
    assert response.json()["error_code"] == "COMPROBANTE_IMPUESTO_NOT_FOUND"


def test_consulta_liquidacion_impuesto_no_crea_movimientos_ni_obligaciones(
    client, db_session
) -> None:
    id_persona = _crear_persona(db_session, codigo="IMP-LIT-GET-SIN-EFECTOS")
    comprobante = _crear_comprobante(
        client,
        db_session,
        numero_comprobante="MUN-2026-LIT-GET-SIN-EFECTOS",
        modalidad_gestion_impuesto="DIRECTO_RESPONSABLE",
    ).json()["data"]
    liquidacion = _liquidar_impuesto(
        client,
        id_comprobante_impuesto=comprobante["id_comprobante_impuesto"],
        id_persona=id_persona,
        op_id="00000000-0000-0000-0000-00000000f205",
    ).json()["data"]
    before = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_tesoreria) AS tesoreria,
                (SELECT COUNT(*) FROM movimiento_financiero) AS financieros,
                (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones
            """
        )
    ).mappings().one()

    detail = client.get(
        (
            "/api/v1/financiero/liquidaciones-impuesto-trasladado/"
            f"{liquidacion['id_liquidacion_impuesto_trasladado']}"
        ),
        headers=HEADERS,
    )
    listing = client.get(
        (
            "/api/v1/financiero/comprobantes-impuesto/"
            f"{comprobante['id_comprobante_impuesto']}"
            "/liquidaciones-impuesto-trasladado"
        ),
        headers=HEADERS,
    )
    after = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_tesoreria) AS tesoreria,
                (SELECT COUNT(*) FROM movimiento_financiero) AS financieros,
                (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones
            """
        )
    ).mappings().one()

    assert detail.status_code == 200
    assert listing.status_code == 200
    assert after["tesoreria"] == before["tesoreria"]
    assert after["financieros"] == before["financieros"]
    assert after["obligaciones"] == before["obligaciones"]
