from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_factura_servicio_sql import (
    _asociar_inmueble_servicio,
    _asociar_unidad_funcional_servicio,
    _crear_inmueble,
    _crear_servicio,
    _crear_unidad_funcional,
)
from tests.test_asignacion_servicio_responsable_api import _crear_persona


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


def _headers_sin_op_id() -> dict:
    return {k: v for k, v in HEADERS.items() if k != "X-Op-Id"}


def _crear_cuenta_financiera(
    db_session,
    *,
    nombre: str = "Cuenta egreso proveedor",
    estado: str = "ACTIVA",
) -> int:
    row = db_session.execute(
        text(
            """
            INSERT INTO cuenta_financiera (
                tipo_cuenta,
                nombre_cuenta,
                moneda,
                id_sucursal_operativa,
                estado,
                observaciones
            )
            VALUES (
                'BANCO',
                :nombre,
                'ARS',
                1,
                :estado,
                'Cuenta test egreso proveedor'
            )
            RETURNING id_cuenta_financiera
            """
        ),
        {"nombre": nombre, "estado": estado},
    ).scalar_one()
    db_session.flush()
    return row


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


def test_create_factura_servicio_permite_periodo_null(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-API-INM-009")
    id_servicio = _crear_servicio(db_session, codigo="FS-API-SRV-009")
    _asociar_inmueble_servicio(
        db_session,
        id_inmueble=id_inmueble,
        id_servicio=id_servicio,
    )
    payload = _payload(
        id_servicio=id_servicio,
        id_inmueble=id_inmueble,
        numero_factura="FS-API-FAC-009",
    )
    payload["periodo_desde"] = None
    payload["periodo_hasta"] = None

    response = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=payload,
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["periodo_desde"] is None
    assert data["periodo_hasta"] is None


def _crear_factura_servicio_con_responsable(
    client,
    db_session,
    *,
    codigo: str,
    porcentaje: float = 100.0,
) -> tuple[int, int, int, int]:
    id_inmueble = _crear_inmueble(db_session, codigo=f"FS-MAT-INM-{codigo}")
    id_servicio = _crear_servicio(db_session, codigo=f"FS-MAT-SRV-{codigo}")
    id_persona = _crear_persona(db_session, codigo=f"FS-MAT-PER-{codigo}")
    _asociar_inmueble_servicio(
        db_session,
        id_inmueble=id_inmueble,
        id_servicio=id_servicio,
    )
    asignacion = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json={
            "id_servicio": id_servicio,
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "id_persona": id_persona,
            "porcentaje_responsabilidad": porcentaje,
            "fecha_desde": "2026-01-01",
            "fecha_hasta": None,
            "estado_asignacion": "ACTIVA",
            "observaciones": "Responsable materializacion",
        },
    )
    assert asignacion.status_code == 201, asignacion.text
    factura = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            numero_factura=f"FS-MAT-FAC-{codigo}",
        ),
    )
    assert factura.status_code == 201, factura.text
    return (
        factura.json()["data"]["id_factura_servicio"],
        id_inmueble,
        id_servicio,
        id_persona,
    )


def _crear_factura_servicio_con_responsables_50_50(
    client,
    db_session,
    *,
    codigo: str,
) -> tuple[int, int, int, int, int]:
    id_inmueble = _crear_inmueble(db_session, codigo=f"FS-MAT-INM-{codigo}")
    id_servicio = _crear_servicio(db_session, codigo=f"FS-MAT-SRV-{codigo}")
    id_persona_1 = _crear_persona(db_session, codigo=f"FS-MAT-PER-{codigo}-A")
    id_persona_2 = _crear_persona(db_session, codigo=f"FS-MAT-PER-{codigo}-B")
    _asociar_inmueble_servicio(
        db_session,
        id_inmueble=id_inmueble,
        id_servicio=id_servicio,
    )
    for id_persona in (id_persona_1, id_persona_2):
        asignacion = client.post(
            "/api/v1/asignaciones-servicio-responsable",
            headers=HEADERS,
            json={
                "id_servicio": id_servicio,
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "id_persona": id_persona,
                "porcentaje_responsabilidad": 50,
                "fecha_desde": "2026-01-01",
                "fecha_hasta": None,
                "estado_asignacion": "ACTIVA",
                "observaciones": "Responsable materializacion 50/50",
            },
        )
        assert asignacion.status_code == 201, asignacion.text
    factura = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            numero_factura=f"FS-MAT-FAC-{codigo}",
        ),
    )
    assert factura.status_code == 201, factura.text
    return (
        factura.json()["data"]["id_factura_servicio"],
        id_inmueble,
        id_servicio,
        id_persona_1,
        id_persona_2,
    )


def _materializar(client, id_factura: int):
    return client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/materializar",
        headers=HEADERS,
    )


def _pago_externo(
    client,
    id_factura: int,
    *,
    importe: float = 25000.00,
    headers: dict | None = None,
    referencia: str = "Comprobante proveedor 123456",
    observaciones: str = "Pagado directamente por el responsable al proveedor",
):
    return client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/pago-externo",
        headers=headers or HEADERS,
        json={
            "fecha_pago": "2026-05-20",
            "importe_pagado": importe,
            "referencia_pago": referencia,
            "medio_pago_externo": "PAGO_DIRECTO_PROVEEDOR",
            "observaciones": observaciones,
        },
    )


def test_materializar_factura_servicio_responsable_100_crea_relacion_obligacion_composicion_y_obligado(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="001"
    )

    response = _materializar(client, id_factura)

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["resultado"] == "MATERIALIZADA"
    assert data["id_factura_servicio"] == id_factura
    assert data["relacion_generadora_created"] is True
    assert data["obligacion_created"] is True
    assert data["obligados_creados"] == 1

    row = db_session.execute(
        text(
            """
            SELECT
                rg.tipo_origen,
                rg.id_origen,
                o.estado_obligacion,
                o.fecha_emision,
                o.fecha_vencimiento,
                o.periodo_desde,
                o.periodo_hasta,
                o.importe_total,
                o.saldo_pendiente,
                o.moneda,
                cf.codigo_concepto_financiero,
                co.importe_componente,
                oo.id_persona,
                oo.rol_obligado,
                oo.porcentaje_responsabilidad
            FROM relacion_generadora rg
            JOIN obligacion_financiera o ON o.id_relacion_generadora = rg.id_relacion_generadora
            JOIN composicion_obligacion co ON co.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf ON cf.id_concepto_financiero = co.id_concepto_financiero
            JOIN obligacion_obligado oo ON oo.id_obligacion_financiera = o.id_obligacion_financiera
            WHERE rg.id_relacion_generadora = :id_rg
            """
        ),
        {"id_rg": data["id_relacion_generadora"]},
    ).mappings().one()

    assert row["tipo_origen"] == "factura_servicio"
    assert row["id_origen"] == id_factura
    assert row["estado_obligacion"] == "EMITIDA"
    assert row["fecha_emision"].isoformat() == "2026-05-01"
    assert row["fecha_vencimiento"].isoformat() == "2026-05-15"
    assert row["periodo_desde"].isoformat() == "2026-04-01"
    assert row["periodo_hasta"].isoformat() == "2026-04-30"
    assert float(row["importe_total"]) == 25000.0
    assert float(row["saldo_pendiente"]) == 25000.0
    assert row["moneda"] == "ARS"
    assert row["codigo_concepto_financiero"] == "SERVICIO_TRASLADADO"
    assert float(row["importe_componente"]) == 25000.0
    assert row["id_persona"] == id_persona
    assert row["rol_obligado"] == "RESPONSABLE_SERVICIO"
    assert float(row["porcentaje_responsabilidad"]) == 100.0


def test_materializar_factura_servicio_responsables_50_50_crea_dos_obligados(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-MAT-INM-002")
    id_servicio = _crear_servicio(db_session, codigo="FS-MAT-SRV-002")
    id_persona_1 = _crear_persona(db_session, codigo="FS-MAT-PER-002-A")
    id_persona_2 = _crear_persona(db_session, codigo="FS-MAT-PER-002-B")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)
    for id_persona in (id_persona_1, id_persona_2):
        created = client.post(
            "/api/v1/asignaciones-servicio-responsable",
            headers=HEADERS,
            json={
                "id_servicio": id_servicio,
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "id_persona": id_persona,
                "porcentaje_responsabilidad": 50,
                "fecha_desde": "2026-01-01",
                "fecha_hasta": None,
                "estado_asignacion": "ACTIVA",
                "observaciones": None,
            },
        )
        assert created.status_code == 201, created.text
    factura = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            numero_factura="FS-MAT-FAC-002",
        ),
    )
    id_factura = factura.json()["data"]["id_factura_servicio"]

    response = _materializar(client, id_factura)

    assert response.status_code == 201, response.text
    id_obligacion = response.json()["data"]["id_obligacion_financiera"]
    rows = db_session.execute(
        text(
            """
            SELECT id_persona, porcentaje_responsabilidad
            FROM obligacion_obligado
            WHERE id_obligacion_financiera = :id
            ORDER BY id_persona
            """
        ),
        {"id": id_obligacion},
    ).mappings().all()
    assert [row["id_persona"] for row in rows] == sorted([id_persona_1, id_persona_2])
    assert [float(row["porcentaje_responsabilidad"]) for row in rows] == [50.0, 50.0]


def test_materializar_factura_servicio_retry_no_duplica_relacion_ni_obligacion(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="003"
    )

    first = _materializar(client, id_factura)
    second = _materializar(client, id_factura)

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["data"]["resultado"] == "YA_MATERIALIZADA"
    assert second.json()["data"]["id_obligacion_financiera"] == first.json()["data"]["id_obligacion_financiera"]
    counts = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM relacion_generadora WHERE tipo_origen = 'factura_servicio' AND id_origen = :id_factura AND deleted_at IS NULL) AS relaciones,
                (SELECT COUNT(*) FROM obligacion_financiera WHERE id_relacion_generadora = :id_rg AND deleted_at IS NULL) AS obligaciones
            """
        ),
        {
            "id_factura": id_factura,
            "id_rg": first.json()["data"]["id_relacion_generadora"],
        },
    ).mappings().one()
    assert counts["relaciones"] == 1
    assert counts["obligaciones"] == 1


def test_pago_externo_factura_servicio_total_cancela_obligacion(client, db_session) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="010"
    )
    mat = _materializar(client, id_factura)
    assert mat.status_code == 201, mat.text

    response = _pago_externo(client, id_factura)

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["id_factura_servicio"] == id_factura
    assert data["id_relacion_generadora"] == mat.json()["data"]["id_relacion_generadora"]
    assert data["id_obligacion_financiera"] == mat.json()["data"]["id_obligacion_financiera"]
    assert data["monto_ingresado"] == 25000.0
    assert data["monto_aplicado"] == 25000.0
    assert data["remanente_no_aplicado"] == 0.0
    assert data["estado_obligacion_resultante"] == "CANCELADA"
    assert data["impacta_caja"] is False
    assert data["genera_recibo_interno"] is False

    row = db_session.execute(
        text(
            """
            SELECT
                o.estado_obligacion,
                o.saldo_pendiente,
                co.saldo_componente,
                m.tipo_movimiento,
                m.codigo_pago_grupo,
                a.tipo_aplicacion
            FROM obligacion_financiera o
            JOIN composicion_obligacion co ON co.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN aplicacion_financiera a ON a.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN movimiento_financiero m ON m.id_movimiento_financiero = a.id_movimiento_financiero
            WHERE o.id_obligacion_financiera = :id
            """
        ),
        {"id": data["id_obligacion_financiera"]},
    ).mappings().one()
    assert row["estado_obligacion"] == "CANCELADA"
    assert float(row["saldo_pendiente"]) == 0.0
    assert float(row["saldo_componente"]) == 0.0
    assert row["tipo_movimiento"] == "PAGO_EXTERNO_INFORMADO"
    assert row["tipo_aplicacion"] == "PAGO_EXTERNO_INFORMADO"
    assert row["codigo_pago_grupo"] is None

    estado = client.get(f"/api/v1/financiero/personas/{id_persona}/estado-cuenta")
    assert estado.status_code == 200, estado.text
    assert estado.json()["data"]["resumen"]["saldo_total"] == 0.0


def test_pago_externo_factura_servicio_parcial_reduce_saldo_y_estado_cuenta(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="011"
    )
    mat = _materializar(client, id_factura)
    assert mat.status_code == 201, mat.text

    response = _pago_externo(client, id_factura, importe=10000.00)

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["monto_aplicado"] == 10000.0
    assert data["remanente_no_aplicado"] == 0.0
    assert data["estado_obligacion_resultante"] == "PARCIALMENTE_CANCELADA"
    saldo = db_session.execute(
        text(
            """
            SELECT saldo_pendiente
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id
            """
        ),
        {"id": data["id_obligacion_financiera"]},
    ).scalar_one()
    assert float(saldo) == 15000.0

    estado = client.get(f"/api/v1/financiero/personas/{id_persona}/estado-cuenta")
    assert estado.status_code == 200, estado.text
    resumen = estado.json()["data"]["resumen"]
    assert resumen["saldo_total"] == 15000.0
    assert resumen["saldo_trasladados"] == 15000.0


def test_pago_externo_factura_servicio_excedente_devuelve_remanente(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="012"
    )
    mat = _materializar(client, id_factura)
    assert mat.status_code == 201, mat.text

    response = _pago_externo(client, id_factura, importe=30000.00)

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["monto_ingresado"] == 30000.0
    assert data["monto_aplicado"] == 25000.0
    assert data["remanente_no_aplicado"] == 5000.0
    assert data["estado_obligacion_resultante"] == "CANCELADA"


def test_pago_externo_factura_servicio_no_materializada_devuelve_error(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="013"
    )

    response = _pago_externo(client, id_factura)

    assert response.status_code == 409
    assert response.json()["error_code"] == "FACTURA_SERVICIO_NO_MATERIALIZADA"


def test_pago_externo_factura_servicio_50_50_bloquea_responsable_no_unico(
    client, db_session
) -> None:
    id_factura, _, _, _, _ = _crear_factura_servicio_con_responsables_50_50(
        client, db_session, codigo="018"
    )
    assert _materializar(client, id_factura).status_code == 201
    movimientos_antes = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM movimiento_financiero
            WHERE tipo_movimiento = 'PAGO_EXTERNO_INFORMADO'
              AND deleted_at IS NULL
            """
        )
    ).scalar_one()

    response = _pago_externo(client, id_factura)

    assert response.status_code == 409
    assert response.json()["error_code"] == "PAGO_EXTERNO_REQUIERE_RESPONSABLE_UNICO"
    movimientos_despues = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM movimiento_financiero
            WHERE tipo_movimiento = 'PAGO_EXTERNO_INFORMADO'
              AND deleted_at IS NULL
            """
        )
    ).scalar_one()
    assert movimientos_despues == movimientos_antes


def test_pago_externo_factura_servicio_unico_responsable_menor_100_bloquea(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="019"
    )
    mat = _materializar(client, id_factura)
    assert mat.status_code == 201, mat.text
    db_session.execute(
        text(
            """
            UPDATE obligacion_obligado
            SET porcentaje_responsabilidad = 75
            WHERE id_obligacion_financiera = :id_obligacion
            """
        ),
        {"id_obligacion": mat.json()["data"]["id_obligacion_financiera"]},
    )
    db_session.flush()

    response = _pago_externo(client, id_factura)

    assert response.status_code == 409
    assert response.json()["error_code"] == "PAGO_EXTERNO_REQUIERE_RESPONSABLE_UNICO"


def test_pago_externo_factura_servicio_sin_saldo_aplicable_devuelve_error(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="014"
    )
    assert _materializar(client, id_factura).status_code == 201
    first = _pago_externo(client, id_factura)
    assert first.status_code == 201, first.text

    response = _pago_externo(
        client,
        id_factura,
        headers={
            **HEADERS,
            "X-Op-Id": "77777777-7777-4777-8777-777777777714",
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "SIN_SALDO_APLICABLE"


def test_pago_externo_factura_servicio_no_crea_tesoreria_ni_recibo_interno(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="015"
    )
    assert _materializar(client, id_factura).status_code == 201
    tesoreria_antes = db_session.execute(
        text("SELECT COUNT(*) FROM movimiento_tesoreria")
    ).scalar_one()

    response = _pago_externo(client, id_factura)

    assert response.status_code == 201, response.text
    tesoreria_despues = db_session.execute(
        text("SELECT COUNT(*) FROM movimiento_tesoreria")
    ).scalar_one()
    assert tesoreria_despues == tesoreria_antes
    movimiento = db_session.execute(
        text(
            """
            SELECT codigo_pago_grupo
            FROM movimiento_financiero
            WHERE id_movimiento_financiero = :id
            """
        ),
        {"id": response.json()["data"]["id_movimiento_financiero"]},
    ).mappings().one()
    assert movimiento["codigo_pago_grupo"] is None
    pagos = client.get(f"/api/v1/financiero/personas/{id_persona}/pagos")
    assert pagos.status_code == 200, pagos.text
    assert pagos.json()["data"] == []


def test_pago_externo_factura_servicio_retry_mismo_op_id_no_duplica(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="016"
    )
    assert _materializar(client, id_factura).status_code == 201
    headers = {
        **HEADERS,
        "X-Op-Id": "77777777-7777-4777-8777-777777777716",
    }

    first = _pago_externo(client, id_factura, importe=10000.00, headers=headers)
    second = _pago_externo(client, id_factura, importe=10000.00, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["data"]["id_movimiento_financiero"] == first.json()["data"][
        "id_movimiento_financiero"
    ]
    count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM movimiento_financiero
            WHERE tipo_movimiento = 'PAGO_EXTERNO_INFORMADO'
              AND op_id_alta = CAST(:op_id AS uuid)
              AND deleted_at IS NULL
            """
        ),
        {"op_id": headers["X-Op-Id"]},
    ).scalar_one()
    assert count == 1


def test_pago_externo_factura_servicio_mismo_op_id_payload_distinto_conflicto(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="017"
    )
    assert _materializar(client, id_factura).status_code == 201
    headers = {
        **HEADERS,
        "X-Op-Id": "77777777-7777-4777-8777-777777777717",
    }
    first = _pago_externo(client, id_factura, importe=10000.00, headers=headers)
    assert first.status_code == 201, first.text

    response = _pago_externo(client, id_factura, importe=12000.00, headers=headers)

    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"


def test_egreso_proveedor_factura_servicio_total_crea_movimiento_y_puente(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-001"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR 001")

    response = client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 25000.00,
            "medio_pago": "TRANSFERENCIA",
            "referencia_comprobante": "TRX-001",
            "observaciones": "Pago proveedor CALF",
        },
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id_factura_servicio"] == id_factura
    assert data["id_movimiento_tesoreria"] > 0
    assert data["importe_pagado"] == 25000.0
    assert data["impacta_tesoreria"] is True
    assert data["crea_movimiento_financiero"] is False
    assert data["crea_obligacion_financiera"] is False

    row = db_session.execute(
        text(
            """
            SELECT
                mt.tipo_movimiento_tesoreria,
                mt.id_cuenta_financiera_origen,
                mt.id_cuenta_financiera_destino,
                mt.importe,
                mt.estado,
                mt.referencia_externa,
                e.id_factura_servicio,
                e.importe_pagado,
                e.estado_egreso
            FROM egreso_proveedor_factura_servicio e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
            WHERE e.id_egreso_proveedor_factura_servicio = :id
            """
        ),
        {"id": data["id_egreso_proveedor_factura_servicio"]},
    ).mappings().one()

    assert row["tipo_movimiento_tesoreria"] == "EGRESO_PROVEEDOR_FACTURA_SERVICIO"
    assert row["id_cuenta_financiera_origen"] == id_cuenta
    assert row["id_cuenta_financiera_destino"] is None
    assert float(row["importe"]) == 25000.0
    assert row["estado"] == "REGISTRADO"
    assert row["referencia_externa"] == f"FACTURA_SERVICIO:{id_factura}"
    assert row["id_factura_servicio"] == id_factura
    assert float(row["importe_pagado"]) == 25000.0
    assert row["estado_egreso"] == "REGISTRADO"


def test_egreso_proveedor_factura_servicio_parcial(client, db_session) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-002"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR 002")

    response = client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 10000.00,
            "medio_pago": "TRANSFERENCIA",
            "referencia_comprobante": "TRX-002",
        },
    )

    assert response.status_code == 201
    assert response.json()["data"]["importe_pagado"] == 10000.0


def test_egreso_proveedor_factura_servicio_multiples_parciales_hasta_total(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-003"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR 003")
    url = f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor"

    first = client.post(
        url,
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 10000.00,
        },
    )
    second = client.post(
        url,
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-21",
            "importe_pagado": 15000.00,
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    total = db_session.execute(
        text(
            """
            SELECT COALESCE(SUM(importe_pagado), 0)
            FROM egreso_proveedor_factura_servicio
            WHERE id_factura_servicio = :id
              AND estado_egreso = 'REGISTRADO'
              AND deleted_at IS NULL
            """
        ),
        {"id": id_factura},
    ).scalar_one()
    assert float(total) == 25000.0


def test_egreso_proveedor_factura_servicio_rechaza_sobrepago(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-004"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR 004")

    response = client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 25000.01,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "EGRESO_SUPERA_IMPORTE_FACTURA"


def test_egreso_proveedor_factura_servicio_retry_mismo_op_id_no_duplica(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-005"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR 005")
    headers = {**HEADERS, "X-Op-Id": "11111111-2222-3333-4444-555555555555"}
    payload = {
        "id_cuenta_financiera_origen": id_cuenta,
        "fecha_pago": "2026-05-20",
        "importe_pagado": 12000.00,
        "medio_pago": "TRANSFERENCIA",
        "referencia_comprobante": "TRX-005",
    }
    url = f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor"

    first = client.post(url, headers=headers, json=payload)
    second = client.post(url, headers=headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["data"]["resultado"] == "YA_REGISTRADO"
    assert second.json()["data"]["id_egreso_proveedor_factura_servicio"] == first.json()[
        "data"
    ]["id_egreso_proveedor_factura_servicio"]
    count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM egreso_proveedor_factura_servicio
            WHERE id_factura_servicio = :id
              AND deleted_at IS NULL
            """
        ),
        {"id": id_factura},
    ).scalar_one()
    assert count == 1


def test_egreso_proveedor_factura_servicio_mismo_op_id_payload_distinto_conflicto(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-006"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR 006")
    headers = {**HEADERS, "X-Op-Id": "22222222-3333-4444-5555-666666666666"}
    url = f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor"
    payload = {
        "id_cuenta_financiera_origen": id_cuenta,
        "fecha_pago": "2026-05-20",
        "importe_pagado": 12000.00,
    }

    first = client.post(url, headers=headers, json=payload)
    second = client.post(
        url,
        headers=headers,
        json={**payload, "importe_pagado": 13000.00},
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"


def test_egreso_proveedor_factura_servicio_no_crea_financiero_ni_obligacion(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-007"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR 007")
    mov_fin_before = db_session.execute(
        text("SELECT COUNT(*) FROM movimiento_financiero")
    ).scalar_one()
    oblig_before = db_session.execute(
        text("SELECT COUNT(*) FROM obligacion_financiera")
    ).scalar_one()

    response = client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 5000.00,
        },
    )

    assert response.status_code == 201
    assert (
        db_session.execute(text("SELECT COUNT(*) FROM movimiento_financiero")).scalar_one()
        == mov_fin_before
    )
    assert (
        db_session.execute(text("SELECT COUNT(*) FROM obligacion_financiera")).scalar_one()
        == oblig_before
    )


def test_egreso_proveedor_factura_servicio_no_afecta_estado_cuenta(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-008"
    )
    mat = client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/materializar",
        headers=HEADERS,
    )
    assert mat.status_code == 201
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR 008")
    estado_before = client.get(
        f"/api/v1/financiero/personas/{id_persona}/estado-cuenta",
        headers=HEADERS,
    ).json()["data"]

    response = client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 25000.00,
        },
    )

    assert response.status_code == 201
    estado_after = client.get(
        f"/api/v1/financiero/personas/{id_persona}/estado-cuenta",
        headers=HEADERS,
    ).json()["data"]
    assert estado_after["resumen"] == estado_before["resumen"]
    assert estado_after["grupos_deuda"] == estado_before["grupos_deuda"]


def test_get_egresos_proveedor_factura_sin_egresos_devuelve_sin_pago(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-GET-001"
    )

    response = client.get(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id_factura_servicio"] == id_factura
    assert data["importe_total_factura"] == 25000.0
    assert data["total_egresado"] == 0.0
    assert data["saldo_pendiente_pago_proveedor"] == 25000.0
    assert data["estado_pago_proveedor"] == "SIN_PAGO"
    assert data["egresos"] == []


def test_get_egresos_proveedor_factura_con_egreso_parcial_devuelve_pago_parcial(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-GET-002"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR GET 002")
    client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 10000.00,
            "medio_pago": "TRANSFERENCIA",
            "referencia_comprobante": "TRX-GET-002",
            "observaciones": "Parcial proveedor",
        },
    )

    response = client.get(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_egresado"] == 10000.0
    assert data["saldo_pendiente_pago_proveedor"] == 15000.0
    assert data["estado_pago_proveedor"] == "PAGO_PARCIAL"
    assert len(data["egresos"]) == 1
    assert data["egresos"][0]["importe_pagado"] == 10000.0
    assert data["egresos"][0]["observaciones"] == "Parcial proveedor"


def test_get_egresos_proveedor_factura_con_egreso_total_devuelve_pagada(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-GET-003"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR GET 003")
    client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 25000.00,
        },
    )

    response = client.get(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=HEADERS,
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_egresado"] == 25000.0
    assert data["saldo_pendiente_pago_proveedor"] == 0.0
    assert data["estado_pago_proveedor"] == "PAGADA"


def test_get_egresos_proveedor_factura_lista_multiples_egresos(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-GET-004"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR GET 004")
    url = f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor"
    client.post(
        url,
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-21",
            "importe_pagado": 15000.00,
            "referencia_comprobante": "TRX-GET-004-B",
        },
    )
    client.post(
        url,
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 10000.00,
            "referencia_comprobante": "TRX-GET-004-A",
        },
    )

    response = client.get(url, headers=HEADERS)

    assert response.status_code == 200
    egresos = response.json()["data"]["egresos"]
    assert [e["referencia_comprobante"] for e in egresos] == [
        "TRX-GET-004-A",
        "TRX-GET-004-B",
    ]


def test_get_egresos_proveedor_factura_inexistente_devuelve_404(client) -> None:
    response = client.get(
        "/api/v1/financiero/facturas-servicio/999999999/egresos-proveedor",
        headers=HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "FACTURA_SERVICIO_NOT_FOUND"


def test_get_egresos_proveedor_factura_anulados_y_deleted_no_cuentan(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-GET-005"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR GET 005")
    url = f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor"
    registrado = client.post(
        url,
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 10000.00,
            "referencia_comprobante": "TRX-REG",
        },
    ).json()["data"]
    anulado = client.post(
        url,
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-21",
            "importe_pagado": 5000.00,
            "referencia_comprobante": "TRX-ANU",
        },
    ).json()["data"]
    deleted = client.post(
        url,
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-22",
            "importe_pagado": 2000.00,
            "referencia_comprobante": "TRX-DEL",
        },
    ).json()["data"]
    db_session.execute(
        text(
            """
            UPDATE egreso_proveedor_factura_servicio
            SET estado_egreso = 'ANULADO'
            WHERE id_egreso_proveedor_factura_servicio = :id
            """
        ),
        {"id": anulado["id_egreso_proveedor_factura_servicio"]},
    )
    db_session.execute(
        text(
            """
            UPDATE egreso_proveedor_factura_servicio
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_egreso_proveedor_factura_servicio = :id
            """
        ),
        {"id": deleted["id_egreso_proveedor_factura_servicio"]},
    )
    db_session.flush()

    response = client.get(url, headers=HEADERS)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_egresado"] == 10000.0
    assert data["estado_pago_proveedor"] == "PAGO_PARCIAL"
    assert {e["referencia_comprobante"] for e in data["egresos"]} == {
        "TRX-REG",
        "TRX-ANU",
    }
    assert all(e["referencia_comprobante"] != "TRX-DEL" for e in data["egresos"])
    assert any(
        e["id_egreso_proveedor_factura_servicio"]
        == registrado["id_egreso_proveedor_factura_servicio"]
        for e in data["egresos"]
    )


def test_materializar_factura_servicio_sin_responsable_devuelve_obligado_no_resuelto(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-MAT-INM-004")
    id_servicio = _crear_servicio(db_session, codigo="FS-MAT-SRV-004")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)
    factura = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            numero_factura="FS-MAT-FAC-004",
        ),
    )
    id_factura = factura.json()["data"]["id_factura_servicio"]

    response = _materializar(client, id_factura)

    assert response.status_code == 409
    assert response.json()["error_code"] == "OBLIGADO_NO_RESUELTO"
    assert db_session.execute(text("SELECT COUNT(*) FROM obligacion_financiera")).scalar_one() == 0


def test_materializar_factura_servicio_sin_periodo_devuelve_periodo_requerido_y_no_crea_financiero(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-MAT-INM-009")
    id_servicio = _crear_servicio(db_session, codigo="FS-MAT-SRV-009")
    id_persona = _crear_persona(db_session, codigo="FS-MAT-PER-009")
    _asociar_inmueble_servicio(
        db_session,
        id_inmueble=id_inmueble,
        id_servicio=id_servicio,
    )
    asignacion = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json={
            "id_servicio": id_servicio,
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "id_persona": id_persona,
            "porcentaje_responsabilidad": 100,
            "fecha_desde": "2026-01-01",
            "fecha_hasta": None,
            "estado_asignacion": "ACTIVA",
            "observaciones": "Responsable sin periodo factura",
        },
    )
    assert asignacion.status_code == 201, asignacion.text
    payload = _payload(
        id_servicio=id_servicio,
        id_inmueble=id_inmueble,
        numero_factura="FS-MAT-FAC-009",
    )
    payload["periodo_desde"] = None
    payload["periodo_hasta"] = None
    factura = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=payload,
    )
    assert factura.status_code == 201, factura.text
    id_factura = factura.json()["data"]["id_factura_servicio"]

    response = _materializar(client, id_factura)

    assert response.status_code == 409
    assert response.json()["error_code"] == "PERIODO_FACTURA_REQUERIDO"
    counts = db_session.execute(
        text(
            """
            SELECT
                (
                    SELECT COUNT(*)
                    FROM relacion_generadora
                    WHERE tipo_origen = 'factura_servicio'
                      AND id_origen = :id_factura
                      AND deleted_at IS NULL
                ) AS relaciones,
                (
                    SELECT COUNT(*)
                    FROM obligacion_financiera o
                    JOIN relacion_generadora rg
                      ON rg.id_relacion_generadora = o.id_relacion_generadora
                    WHERE rg.tipo_origen = 'factura_servicio'
                      AND rg.id_origen = :id_factura
                      AND o.deleted_at IS NULL
                ) AS obligaciones
            """
        ),
        {"id_factura": id_factura},
    ).mappings().one()
    assert counts["relaciones"] == 0
    assert counts["obligaciones"] == 0


def test_materializar_factura_servicio_responsables_suma_distinta_100_devuelve_error(
    client, db_session
) -> None:
    id_factura, id_inmueble, id_servicio, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="005", porcentaje=60
    )

    response = _materializar(client, id_factura)

    assert response.status_code == 409
    assert response.json()["error_code"] == "RESPONSABLE_SERVICIO_AMBIGUO"
    count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM obligacion_obligado oo
            JOIN obligacion_financiera o ON o.id_obligacion_financiera = oo.id_obligacion_financiera
            JOIN relacion_generadora rg ON rg.id_relacion_generadora = o.id_relacion_generadora
            WHERE rg.tipo_origen = 'factura_servicio'
              AND rg.id_origen = :id_factura
              AND oo.id_persona = :id_persona
            """
        ),
        {"id_factura": id_factura, "id_persona": id_persona},
    ).scalar_one()
    assert id_inmueble > 0
    assert id_servicio > 0
    assert count == 0


def test_materializar_factura_servicio_cruza_cambio_responsable_devuelve_error(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-MAT-INM-006")
    id_servicio = _crear_servicio(db_session, codigo="FS-MAT-SRV-006")
    id_persona_1 = _crear_persona(db_session, codigo="FS-MAT-PER-006-A")
    id_persona_2 = _crear_persona(db_session, codigo="FS-MAT-PER-006-B")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)
    for id_persona, desde, hasta in (
        (id_persona_1, "2026-01-01", "2026-04-15"),
        (id_persona_2, "2026-04-16", None),
    ):
        db_session.execute(
            text(
                """
                INSERT INTO asignacion_servicio_responsable (
                    uid_global, version_registro, created_at, updated_at,
                    id_instalacion_origen, id_instalacion_ultima_modificacion,
                    op_id_alta, op_id_ultima_modificacion,
                    id_servicio, id_inmueble, id_unidad_funcional, id_persona,
                    porcentaje_responsabilidad, fecha_desde, fecha_hasta,
                    estado_asignacion
                )
                VALUES (
                    gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                    1, 1, :op_id, :op_id,
                    :id_servicio, :id_inmueble, NULL, :id_persona,
                    100.00, :desde, CAST(:hasta AS date),
                    'ACTIVA'
                )
                """
            ),
            {
                "op_id": HEADERS["X-Op-Id"],
                "id_servicio": id_servicio,
                "id_inmueble": id_inmueble,
                "id_persona": id_persona,
                "desde": desde,
                "hasta": hasta,
            },
        )
    factura = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            numero_factura="FS-MAT-FAC-006",
        ),
    )
    id_factura = factura.json()["data"]["id_factura_servicio"]

    response = _materializar(client, id_factura)

    assert response.status_code == 409
    assert response.json()["error_code"] == "FACTURA_CRUZA_CAMBIO_RESPONSABLE"


def test_materializar_factura_servicio_estado_cuenta_y_deuda_incluyen_servicio_trasladado(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="007"
    )
    materializada = _materializar(client, id_factura)
    id_rg = materializada.json()["data"]["id_relacion_generadora"]

    estado = client.get(f"/api/v1/financiero/personas/{id_persona}/estado-cuenta")
    deuda = client.get(f"/api/v1/financiero/deuda?id_relacion_generadora={id_rg}")
    consolidado = client.get("/api/v1/financiero/deuda/consolidado?tipo_origen=FACTURA_SERVICIO")

    assert estado.status_code == 200, estado.text
    assert any(
        item["id_relacion_generadora"] == id_rg
        and item["tipo_origen"] == "FACTURA_SERVICIO"
        for item in estado.json()["data"]["obligaciones"]
    )
    assert deuda.status_code == 200, deuda.text
    assert deuda.json()["data"]["items"][0]["composiciones"][0]["codigo_concepto_financiero"] == "SERVICIO_TRASLADADO"
    assert consolidado.status_code == 200, consolidado.text
    assert consolidado.json()["data"]["por_tipo_origen"]["FACTURA_SERVICIO"]["saldo_pendiente_total"] >= 25000.0


def test_materializar_factura_servicio_no_crea_obligacion_si_falta_concepto(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="008"
    )
    db_session.execute(
        text(
            """
            UPDATE concepto_financiero
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE codigo_concepto_financiero = 'SERVICIO_TRASLADADO'
            """
        )
    )

    response = _materializar(client, id_factura)

    assert response.status_code == 409
    assert response.json()["error_code"] == "NOT_FOUND_CONCEPTO"
    count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM obligacion_financiera o
            JOIN relacion_generadora rg ON rg.id_relacion_generadora = o.id_relacion_generadora
            WHERE rg.tipo_origen = 'factura_servicio'
              AND rg.id_origen = :id_factura
              AND o.deleted_at IS NULL
            """
        ),
        {"id_factura": id_factura},
    ).scalar_one()
    assert count == 0
