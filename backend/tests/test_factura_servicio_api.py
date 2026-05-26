from uuid import uuid4
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
    return {**HEADERS, "X-Op-Id": str(uuid4())}


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


def _registrar_egreso_proveedor(
    client,
    db_session,
    id_factura: int,
    *,
    importe: float = 25000.00,
    fecha_pago: str = "2026-05-20",
):
    id_cuenta = _crear_cuenta_financiera(
        db_session, nombre=f"Cuenta recupero {id_factura}-{fecha_pago}"
    )
    return client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": fecha_pago,
            "importe_pagado": importe,
            "medio_pago": "TRANSFERENCIA",
            "referencia_comprobante": f"TRX-REC-{id_factura}-{fecha_pago}",
        },
    )


def _liquidar_recupero(
    client,
    id_factura: int,
    responsables: list[dict],
    *,
    importe: float = 25000.00,
    headers: dict | None = None,
):
    return client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/liquidaciones-recupero",
        headers=headers or _headers_sin_op_id(),
        json={
            "fecha_liquidacion": "2026-05-25",
            "fecha_vencimiento": "2026-06-10",
            "importe_total_recuperar": importe,
            "responsables": responsables,
            "observaciones": "Recupero factura pagada por empresa",
        },
    )


def _anular_liquidacion_recupero(
    client,
    id_liquidacion: int,
    *,
    motivo: str = "Liquidacion cargada por error",
    headers: dict | None = None,
):
    return client.patch(
        f"/api/v1/financiero/liquidaciones-recupero/{id_liquidacion}/anular",
        headers=headers or _headers_sin_op_id(),
        json={"motivo": motivo},
    )




def test_registrar_egreso_proveedor_rechaza_header_x_op_id_faltante(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-EF-HDR-001")
    id_servicio = _crear_servicio(db_session, codigo="FS-EF-HDR-SRV-001")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    factura = client.post(
        "/api/v1/facturas-servicio",
        headers=HEADERS,
        json=_payload(id_servicio=id_servicio, id_inmueble=id_inmueble, numero_factura="FS-EF-HDR-FAC"),
    )
    assert factura.status_code == 201, factura.text
    id_factura = factura.json()["data"]["id_factura_servicio"]

    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta header faltante")
    headers = {k: v for k, v in HEADERS.items() if k != "X-Op-Id"}
    response = client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=headers,
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 1000.0,
            "medio_pago": "TRANSFERENCIA",
            "referencia_comprobante": "HDR-OP-ID-MISS",
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert body["details"] == {"header": "X-Op-Id"}
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


def test_anular_egreso_proveedor_cambia_estados_en_egreso_y_tesoreria(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-ANU-001"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR ANU 001")
    egreso = client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 25000.00,
            "observaciones": "Carga original",
        },
    ).json()["data"]

    response = client.patch(
        "/api/v1/financiero/egresos-proveedor-factura-servicio/"
        f"{egreso['id_egreso_proveedor_factura_servicio']}/anular",
        headers=HEADERS,
        json={"motivo": "Carga duplicada / error de comprobante"},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["estado_egreso"] == "ANULADO"
    assert data["estado_movimiento_tesoreria"] == "ANULADO"
    assert data["ya_anulado"] is False
    assert data["motivo"] == "Carga duplicada / error de comprobante"
    row = db_session.execute(
        text(
            """
            SELECT e.estado_egreso, mt.estado, e.observaciones
            FROM egreso_proveedor_factura_servicio e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
            WHERE e.id_egreso_proveedor_factura_servicio = :id
            """
        ),
        {"id": egreso["id_egreso_proveedor_factura_servicio"]},
    ).mappings().one()
    assert row["estado_egreso"] == "ANULADO"
    assert row["estado"] == "ANULADO"
    assert "Carga duplicada / error de comprobante" in row["observaciones"]
    assert "Carga original" in row["observaciones"]


def test_anular_egreso_proveedor_consulta_no_suma_y_vuelve_a_sin_pago(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-ANU-002"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR ANU 002")
    url = f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor"
    egreso = client.post(
        url,
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 25000.00,
        },
    ).json()["data"]
    assert client.get(url, headers=HEADERS).json()["data"]["estado_pago_proveedor"] == "PAGADA"

    client.patch(
        "/api/v1/financiero/egresos-proveedor-factura-servicio/"
        f"{egreso['id_egreso_proveedor_factura_servicio']}/anular",
        headers=HEADERS,
        json={"motivo": "Anulacion total"},
    )
    consulta = client.get(url, headers=HEADERS)

    assert consulta.status_code == 200
    data = consulta.json()["data"]
    assert data["total_egresado"] == 0.0
    assert data["saldo_pendiente_pago_proveedor"] == 25000.0
    assert data["estado_pago_proveedor"] == "SIN_PAGO"
    assert data["egresos"][0]["estado_egreso"] == "ANULADO"


def test_anular_egreso_proveedor_consulta_vuelve_a_pago_parcial(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-ANU-003"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR ANU 003")
    url = f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor"
    primero = client.post(
        url,
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 10000.00,
        },
    ).json()["data"]
    segundo = client.post(
        url,
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-21",
            "importe_pagado": 15000.00,
        },
    ).json()["data"]
    assert primero["id_egreso_proveedor_factura_servicio"] > 0

    client.patch(
        "/api/v1/financiero/egresos-proveedor-factura-servicio/"
        f"{segundo['id_egreso_proveedor_factura_servicio']}/anular",
        headers=HEADERS,
        json={"motivo": "Anulacion parcial"},
    )
    data = client.get(url, headers=HEADERS).json()["data"]

    assert data["total_egresado"] == 10000.0
    assert data["saldo_pendiente_pago_proveedor"] == 15000.0
    assert data["estado_pago_proveedor"] == "PAGO_PARCIAL"


def test_anular_egreso_proveedor_repetida_devuelve_ya_anulado(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-ANU-004"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR ANU 004")
    egreso = client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 10000.00,
        },
    ).json()["data"]
    endpoint = (
        "/api/v1/financiero/egresos-proveedor-factura-servicio/"
        f"{egreso['id_egreso_proveedor_factura_servicio']}/anular"
    )
    first = client.patch(endpoint, headers=HEADERS, json={"motivo": "Primer motivo"})
    second = client.patch(endpoint, headers=HEADERS, json={"motivo": "Segundo motivo"})

    assert first.status_code == 200
    assert second.status_code == 200
    data = second.json()["data"]
    assert data["resultado"] == "YA_ANULADO"
    assert data["ya_anulado"] is True
    assert data["motivo"] == "Primer motivo"


def test_anular_egreso_proveedor_inexistente_devuelve_404(client) -> None:
    response = client.patch(
        "/api/v1/financiero/egresos-proveedor-factura-servicio/999999999/anular",
        headers=HEADERS,
        json={"motivo": "No existe"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "EGRESO_PROVEEDOR_NOT_FOUND"


def test_anular_egreso_proveedor_no_crea_movimiento_financiero_ni_obligacion(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="EGR-ANU-005"
    )
    id_cuenta = _crear_cuenta_financiera(db_session, nombre="Cuenta EGR ANU 005")
    egreso = client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/egresos-proveedor",
        headers=_headers_sin_op_id(),
        json={
            "id_cuenta_financiera_origen": id_cuenta,
            "fecha_pago": "2026-05-20",
            "importe_pagado": 10000.00,
        },
    ).json()["data"]
    mov_fin_before = db_session.execute(
        text("SELECT COUNT(*) FROM movimiento_financiero")
    ).scalar_one()
    oblig_before = db_session.execute(
        text("SELECT COUNT(*) FROM obligacion_financiera")
    ).scalar_one()

    response = client.patch(
        "/api/v1/financiero/egresos-proveedor-factura-servicio/"
        f"{egreso['id_egreso_proveedor_factura_servicio']}/anular",
        headers=HEADERS,
        json={"motivo": "No crea financiero"},
    )

    assert response.status_code == 200
    assert (
        db_session.execute(text("SELECT COUNT(*) FROM movimiento_financiero")).scalar_one()
        == mov_fin_before
    )
    assert (
        db_session.execute(text("SELECT COUNT(*) FROM obligacion_financiera")).scalar_one()
        == oblig_before
    )


def test_liquidacion_recupero_requiere_egreso_proveedor_registrado(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-001"
    )

    response = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "EGRESO_PROVEEDOR_REQUERIDO"


def test_liquidacion_recupero_total_crea_financiero_servicio_recuperado(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-002"
    )
    egreso = _registrar_egreso_proveedor(client, db_session, id_factura)
    assert egreso.status_code == 201, egreso.text

    response = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["resultado"] == "EMITIDA"
    assert data["id_factura_servicio"] == id_factura
    assert data["id_relacion_generadora"] > 0
    assert data["id_obligacion_financiera"] > 0
    assert data["importe_total_egresado_base"] == 25000.0
    assert data["importe_total_recuperar"] == 25000.0
    assert data["importe_absorbido_empresa"] == 0.0
    assert data["crea_movimiento_tesoreria"] is False
    assert data["crea_pago_externo_informado"] is False

    row = db_session.execute(
        text(
            """
            SELECT
                rg.tipo_origen,
                rg.id_origen,
                o.estado_obligacion,
                o.importe_total,
                o.saldo_pendiente,
                cf.codigo_concepto_financiero,
                c.importe_componente,
                c.saldo_componente,
                oo.id_persona,
                oo.porcentaje_responsabilidad
            FROM liquidacion_recupero lr
            JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = lr.id_relacion_generadora
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = lr.id_obligacion_financiera
            JOIN composicion_obligacion c
              ON c.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = c.id_concepto_financiero
            JOIN obligacion_obligado oo
              ON oo.id_obligacion_financiera = o.id_obligacion_financiera
            WHERE lr.id_liquidacion_recupero = :id
            """
        ),
        {"id": data["id_liquidacion_recupero"]},
    ).mappings().one()
    assert row["tipo_origen"] == "liquidacion_recupero"
    assert row["id_origen"] == data["id_liquidacion_recupero"]
    assert row["estado_obligacion"] == "EMITIDA"
    assert float(row["importe_total"]) == 25000.0
    assert float(row["saldo_pendiente"]) == 25000.0
    assert row["codigo_concepto_financiero"] == "SERVICIO_RECUPERADO"
    assert float(row["importe_componente"]) == 25000.0
    assert float(row["saldo_componente"]) == 25000.0
    assert row["id_persona"] == id_persona
    assert float(row["porcentaje_responsabilidad"]) == 100.0


def test_liquidacion_recupero_crea_vinculo_egreso_activo(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-LRE-ACT"
    )
    egreso = _registrar_egreso_proveedor(client, db_session, id_factura)
    assert egreso.status_code == 201, egreso.text

    response = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    row = db_session.execute(
        text(
            """
            SELECT
                uid_global,
                version_registro,
                created_at,
                updated_at,
                deleted_at,
                estado_liquidacion_recupero_egreso
            FROM liquidacion_recupero_egreso
            WHERE id_liquidacion_recupero = :id_liquidacion
              AND id_egreso_proveedor_factura_servicio = :id_egreso
            """
        ),
        {
            "id_liquidacion": data["id_liquidacion_recupero"],
            "id_egreso": egreso.json()["data"][
                "id_egreso_proveedor_factura_servicio"
            ],
        },
    ).mappings().one()
    assert row["uid_global"] is not None
    assert row["version_registro"] == 1
    assert row["created_at"] is not None
    assert row["updated_at"] is not None
    assert row["deleted_at"] is None
    assert row["estado_liquidacion_recupero_egreso"] == "ACTIVO"


def test_liquidacion_recupero_no_reutiliza_egreso_con_vinculo_activo(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-LRE-BLOCK"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    responsables = [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}]
    first = _liquidar_recupero(client, id_factura, responsables)
    assert first.status_code == 201, first.text

    second = _liquidar_recupero(
        client,
        id_factura,
        responsables,
        headers={
            **HEADERS,
            "X-Op-Id": "66666666-6666-6666-6666-666666666666",
        },
    )

    assert second.status_code == 409
    assert second.json()["error_code"] == "SIN_MONTO_EGRESADO_DISPONIBLE"


def test_liquidacion_recupero_egreso_anulado_logicamente_vuelve_a_estar_disponible(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-LRE-FREE"
    )
    egreso = _registrar_egreso_proveedor(client, db_session, id_factura)
    assert egreso.status_code == 201, egreso.text
    responsables = [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}]
    first = _liquidar_recupero(client, id_factura, responsables)
    assert first.status_code == 201, first.text

    db_session.execute(
        text(
            """
            UPDATE liquidacion_recupero_egreso
            SET estado_liquidacion_recupero_egreso = 'ANULADO',
                deleted_at = CURRENT_TIMESTAMP
            WHERE id_liquidacion_recupero = :id_liquidacion
              AND id_egreso_proveedor_factura_servicio = :id_egreso
            """
        ),
        {
            "id_liquidacion": first.json()["data"]["id_liquidacion_recupero"],
            "id_egreso": egreso.json()["data"][
                "id_egreso_proveedor_factura_servicio"
            ],
        },
    )
    db_session.flush()

    second = _liquidar_recupero(
        client,
        id_factura,
        responsables,
        headers={
            **HEADERS,
            "X-Op-Id": "77777777-7777-7777-7777-777777777777",
        },
    )

    assert second.status_code == 201, second.text
    assert (
        second.json()["data"]["id_liquidacion_recupero"]
        != first.json()["data"]["id_liquidacion_recupero"]
    )


def test_get_liquidacion_recupero_detalle_emitida(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-DET-001"
    )
    egreso = _registrar_egreso_proveedor(client, db_session, id_factura)
    assert egreso.status_code == 201, egreso.text
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
        importe=20000.00,
    )
    assert liquidacion.status_code == 201, liquidacion.text
    creada = liquidacion.json()["data"]

    response = client.get(
        f"/api/v1/financiero/liquidaciones-recupero/{creada['id_liquidacion_recupero']}"
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id_liquidacion_recupero"] == creada["id_liquidacion_recupero"]
    assert data["estado_liquidacion"] == "EMITIDA"
    assert data["fecha_liquidacion"] == "2026-05-25"
    assert data["fecha_vencimiento"] == "2026-06-10"
    assert data["importe_total_egresado_base"] == 25000.0
    assert data["importe_total_recuperar"] == 20000.0
    assert data["importe_absorbido_empresa"] == 5000.0
    assert data["id_relacion_generadora"] == creada["id_relacion_generadora"]
    assert data["id_obligacion_financiera"] == creada["id_obligacion_financiera"]

    assert data["facturas"] == [
        {
            "id_factura_servicio": id_factura,
            "proveedor": "CALF",
            "numero_factura": "FS-MAT-FAC-REC-DET-001",
            "importe_total": 25000.0,
            "importe_egresado_base": 25000.0,
            "importe_recuperar": 20000.0,
        }
    ]
    assert data["egresos"][0]["id_egreso_proveedor_factura_servicio"] == egreso.json()[
        "data"
    ]["id_egreso_proveedor_factura_servicio"]
    assert data["egresos"][0]["id_movimiento_tesoreria"] == egreso.json()["data"][
        "id_movimiento_tesoreria"
    ]
    assert data["egresos"][0]["fecha_pago"] == "2026-05-20"
    assert data["egresos"][0]["importe_pagado"] == 25000.0
    assert data["egresos"][0]["importe_imputado_base"] == 25000.0
    assert data["egresos"][0]["estado_egreso"] == "REGISTRADO"

    assert data["responsables"] == [
        {
            "id_liquidacion_recupero_responsable": data["responsables"][0][
                "id_liquidacion_recupero_responsable"
            ],
            "id_persona": id_persona,
            "porcentaje_responsabilidad": 100.0,
            "importe_responsable": 20000.0,
            "origen_responsable": "MANUAL",
            "id_asignacion_servicio_responsable": None,
        }
    ]
    assert data["obligacion"]["id_obligacion_financiera"] == creada[
        "id_obligacion_financiera"
    ]
    assert data["obligacion"]["estado_obligacion"] == "EMITIDA"
    assert data["obligacion"]["saldo_pendiente"] == 20000.0
    assert data["obligacion"]["composiciones"] == [
        {
            "codigo_concepto_financiero": "SERVICIO_RECUPERADO",
            "importe_componente": 20000.0,
            "saldo_componente": 20000.0,
        }
    ]
    assert data["obligacion"]["obligados"] == [
        {
            "id_persona": id_persona,
            "rol_obligado": "RESPONSABLE_RECUPERO",
            "porcentaje_responsabilidad": 100.0,
        }
    ]


def test_list_liquidaciones_recupero_por_factura_devuelve_liquidacion(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-LIST-001"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
        importe=20000.00,
    )
    assert liquidacion.status_code == 201, liquidacion.text
    creada = liquidacion.json()["data"]

    response = client.get(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/liquidaciones-recupero"
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id_factura_servicio"] == id_factura
    assert data["total"] == 1
    assert data["items"] == [
        {
            "id_liquidacion_recupero": creada["id_liquidacion_recupero"],
            "codigo_liquidacion_recupero": creada["codigo_liquidacion_recupero"],
            "estado_liquidacion": "EMITIDA",
            "fecha_liquidacion": "2026-05-25",
            "fecha_vencimiento": "2026-06-10",
            "importe_total_recuperar": 20000.0,
            "importe_absorbido_empresa": 5000.0,
            "id_obligacion_financiera": creada["id_obligacion_financiera"],
            "saldo_pendiente": 20000.0,
            "cantidad_responsables": 1,
        }
    ]


def test_list_liquidaciones_recupero_factura_sin_liquidaciones_devuelve_lista_vacia(
    client, db_session
) -> None:
    id_factura, _, _, _ = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-LIST-EMPTY"
    )

    response = client.get(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/liquidaciones-recupero"
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"] == {
        "id_factura_servicio": id_factura,
        "items": [],
        "total": 0,
    }


def test_get_liquidacion_recupero_inexistente_devuelve_404(client) -> None:
    response = client.get("/api/v1/financiero/liquidaciones-recupero/999999999")

    assert response.status_code == 404
    assert response.json()["error_code"] == "LIQUIDACION_RECUPERO_NOT_FOUND"


def test_list_liquidaciones_recupero_factura_inexistente_devuelve_404(client) -> None:
    response = client.get(
        "/api/v1/financiero/facturas-servicio/999999999/liquidaciones-recupero"
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "FACTURA_SERVICIO_NOT_FOUND"


def test_consultar_liquidacion_recupero_no_crea_movimientos_ni_obligaciones(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-READONLY"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    assert liquidacion.status_code == 201, liquidacion.text
    id_liquidacion = liquidacion.json()["data"]["id_liquidacion_recupero"]

    before = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_tesoreria) AS tesoreria,
                (SELECT COUNT(*) FROM movimiento_financiero) AS financiero,
                (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones
            """
        )
    ).mappings().one()

    detail = client.get(f"/api/v1/financiero/liquidaciones-recupero/{id_liquidacion}")
    listing = client.get(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/liquidaciones-recupero"
    )

    assert detail.status_code == 200, detail.text
    assert listing.status_code == 200, listing.text
    after = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM movimiento_tesoreria) AS tesoreria,
                (SELECT COUNT(*) FROM movimiento_financiero) AS financiero,
                (SELECT COUNT(*) FROM obligacion_financiera) AS obligaciones
            """
        )
    ).mappings().one()
    assert dict(after) == dict(before)


def test_liquidacion_recupero_parcial_registra_absorbido_empresa(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-003"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201

    response = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
        importe=20000.00,
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["importe_total_egresado_base"] == 25000.0
    assert data["importe_total_recuperar"] == 20000.0
    assert data["importe_absorbido_empresa"] == 5000.0


def test_liquidacion_recupero_responsables_50_50_genera_obligados_y_snapshot(
    client, db_session
) -> None:
    id_factura, _, _, id_persona_1, id_persona_2 = (
        _crear_factura_servicio_con_responsables_50_50(
            client, db_session, codigo="REC-004"
        )
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201

    response = _liquidar_recupero(
        client,
        id_factura,
        [
            {"id_persona": id_persona_1, "porcentaje_responsabilidad": 50.00},
            {"id_persona": id_persona_2, "porcentaje_responsabilidad": 50.00},
        ],
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert len(data["responsables"]) == 2
    assert [r["importe_responsable"] for r in data["responsables"]] == [
        12500.0,
        12500.0,
    ]
    count_obligados = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM obligacion_obligado
            WHERE id_obligacion_financiera = :id
              AND deleted_at IS NULL
            """
        ),
        {"id": data["id_obligacion_financiera"]},
    ).scalar_one()
    assert count_obligados == 2


def test_liquidacion_recupero_rechaza_porcentajes_que_no_suman_100(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-005"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201

    response = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 80.00}],
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "RESPONSABLES_SUMA_DISTINTA_100"


def test_liquidacion_recupero_rechaza_importe_mayor_al_egresado(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-006"
    )
    assert (
        _registrar_egreso_proveedor(client, db_session, id_factura, importe=10000.00).status_code
        == 201
    )

    response = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
        importe=10000.01,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "IMPORTE_RECUPERO_SUPERA_EGRESADO"


def test_liquidacion_recupero_retry_mismo_op_id_no_duplica(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-007"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    headers = {
        **HEADERS,
        "X-Op-Id": "44444444-4444-4444-4444-444444444444",
    }
    responsables = [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}]

    first = _liquidar_recupero(client, id_factura, responsables, headers=headers)
    second = _liquidar_recupero(client, id_factura, responsables, headers=headers)

    assert first.status_code == 201, first.text
    assert second.status_code == 200, second.text
    assert second.json()["data"]["resultado"] == "YA_EMITIDA"
    assert second.json()["data"]["id_liquidacion_recupero"] == first.json()["data"][
        "id_liquidacion_recupero"
    ]
    count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM liquidacion_recupero
            WHERE op_id_alta = '44444444-4444-4444-4444-444444444444'
              AND deleted_at IS NULL
            """
        )
    ).scalar_one()
    assert count == 1


def test_liquidacion_recupero_mismo_op_id_payload_distinto_conflicto(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-008"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    headers = {
        **HEADERS,
        "X-Op-Id": "55555555-5555-5555-5555-555555555555",
    }
    responsables = [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}]

    first = _liquidar_recupero(client, id_factura, responsables, headers=headers)
    second = _liquidar_recupero(
        client, id_factura, responsables, headers=headers, importe=20000.00
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENCY_PAYLOAD_CONFLICT"


def test_liquidacion_recupero_estado_cuenta_muestra_servicio_recuperado_en_trasladados(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-009"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    assert liquidacion.status_code == 201, liquidacion.text
    id_rg = liquidacion.json()["data"]["id_relacion_generadora"]

    response = client.get(f"/api/v1/financiero/personas/{id_persona}/estado-cuenta")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    trasladados = next(
        g for g in data["grupos_deuda"] if g["grupo_origen_deuda"] == "TRASLADADOS"
    )
    assert data["resumen"]["saldo_trasladados"] >= 25000.0
    relacion = next(r for r in trasladados["relaciones"] if r["id_relacion_generadora"] == id_rg)
    assert relacion["tipo_origen"] == "LIQUIDACION_RECUPERO"
    assert relacion["obligaciones"][0]["composiciones"][0][
        "codigo_concepto_financiero"
    ] == "SERVICIO_RECUPERADO"


def test_liquidacion_recupero_pago_posterior_usa_flujo_normal_pago_persona(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-010"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    id_obligacion = liquidacion.json()["data"]["id_obligacion_financiera"]

    pago = client.post(
        "/api/v1/financiero/pagos",
        headers=_headers_sin_op_id(),
        params={"id_persona": id_persona},
        json={"monto": 25000.00, "fecha_pago": "2026-05-30"},
    )

    assert pago.status_code == 201, pago.text
    assert pago.json()["data"]["obligaciones_pagadas"][0]["id_obligacion_financiera"] == id_obligacion
    saldo = db_session.execute(
        text(
            """
            SELECT saldo_pendiente
            FROM obligacion_financiera
            WHERE id_obligacion_financiera = :id
            """
        ),
        {"id": id_obligacion},
    ).scalar_one()
    assert float(saldo) == 0.0


def test_liquidacion_recupero_pago_normal_cancela_y_no_toca_egreso_base(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-PAGO-NORMAL"
    )
    egreso = _registrar_egreso_proveedor(client, db_session, id_factura)
    assert egreso.status_code == 201, egreso.text
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    assert liquidacion.status_code == 201, liquidacion.text
    data_liq = liquidacion.json()["data"]
    id_obligacion = data_liq["id_obligacion_financiera"]
    id_liquidacion = data_liq["id_liquidacion_recupero"]

    estado_antes = client.get(f"/api/v1/financiero/personas/{id_persona}/estado-cuenta")
    assert estado_antes.status_code == 200, estado_antes.text
    assert estado_antes.json()["data"]["resumen"]["saldo_trasladados"] == 25000.0

    egreso_base_antes = db_session.execute(
        text(
            """
            SELECT
                e.id_egreso_proveedor_factura_servicio,
                e.estado_egreso,
                e.importe_pagado,
                mt.id_movimiento_tesoreria,
                mt.estado AS estado_movimiento_tesoreria,
                lre.estado_liquidacion_recupero_egreso,
                lre.deleted_at
            FROM egreso_proveedor_factura_servicio e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
            JOIN liquidacion_recupero_egreso lre
              ON lre.id_egreso_proveedor_factura_servicio =
                 e.id_egreso_proveedor_factura_servicio
            WHERE lre.id_liquidacion_recupero = :id_liquidacion
            """
        ),
        {"id_liquidacion": id_liquidacion},
    ).mappings().one()

    pago = client.post(
        "/api/v1/financiero/pagos",
        headers={**HEADERS, "X-Op-Id": "aaaaaaaa-0000-4000-8000-000000000101"},
        params={"id_persona": id_persona},
        json={"monto": 25000.00, "fecha_pago": "2026-05-30"},
    )

    assert pago.status_code == 201, pago.text
    assert pago.json()["data"]["obligaciones_pagadas"][0]["id_obligacion_financiera"] == id_obligacion

    row = db_session.execute(
        text(
            """
            SELECT
                o.estado_obligacion,
                o.saldo_pendiente,
                co.saldo_componente,
                cf.codigo_concepto_financiero,
                m.tipo_movimiento,
                a.tipo_aplicacion,
                (SELECT COUNT(*)
                   FROM movimiento_financiero mx
                   JOIN aplicacion_financiera ax
                     ON ax.id_movimiento_financiero = mx.id_movimiento_financiero
                  WHERE ax.id_obligacion_financiera = o.id_obligacion_financiera
                    AND mx.tipo_movimiento = 'PAGO_EXTERNO_INFORMADO'
                    AND mx.deleted_at IS NULL
                    AND ax.deleted_at IS NULL) AS pagos_externos
            FROM obligacion_financiera o
            JOIN composicion_obligacion co
              ON co.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = co.id_concepto_financiero
            JOIN aplicacion_financiera a
              ON a.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN movimiento_financiero m
              ON m.id_movimiento_financiero = a.id_movimiento_financiero
            WHERE o.id_obligacion_financiera = :id_obligacion
              AND m.tipo_movimiento = 'PAGO'
            """
        ),
        {"id_obligacion": id_obligacion},
    ).mappings().one()

    assert row["estado_obligacion"] == "CANCELADA"
    assert float(row["saldo_pendiente"]) == 0.0
    assert float(row["saldo_componente"]) == 0.0
    assert row["codigo_concepto_financiero"] == "SERVICIO_RECUPERADO"
    assert row["tipo_movimiento"] == "PAGO"
    assert row["tipo_aplicacion"] == "PAGO"
    assert row["pagos_externos"] == 0

    estado_despues = client.get(f"/api/v1/financiero/personas/{id_persona}/estado-cuenta")
    assert estado_despues.status_code == 200, estado_despues.text
    assert estado_despues.json()["data"]["resumen"]["saldo_trasladados"] == 0.0

    egreso_base_despues = db_session.execute(
        text(
            """
            SELECT
                e.id_egreso_proveedor_factura_servicio,
                e.estado_egreso,
                e.importe_pagado,
                mt.id_movimiento_tesoreria,
                mt.estado AS estado_movimiento_tesoreria,
                lre.estado_liquidacion_recupero_egreso,
                lre.deleted_at
            FROM egreso_proveedor_factura_servicio e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
            JOIN liquidacion_recupero_egreso lre
              ON lre.id_egreso_proveedor_factura_servicio =
                 e.id_egreso_proveedor_factura_servicio
            WHERE lre.id_liquidacion_recupero = :id_liquidacion
            """
        ),
        {"id_liquidacion": id_liquidacion},
    ).mappings().one()
    assert dict(egreso_base_despues) == dict(egreso_base_antes)


def test_pago_normal_servicio_recuperado_vencido_genera_punitorio_si_aplica(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-PUNIT-APLICA"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    assert liquidacion.status_code == 201, liquidacion.text
    id_obligacion = liquidacion.json()["data"]["id_obligacion_financiera"]
    aplica_antes = db_session.execute(
        text(
            """
            SELECT aplica_punitorio
            FROM concepto_financiero
            WHERE codigo_concepto_financiero = 'SERVICIO_RECUPERADO'
            """
        )
    ).scalar_one()

    pago = client.post(
        "/api/v1/financiero/pagos",
        headers={**HEADERS, "X-Op-Id": "aaaaaaaa-0000-4000-8000-000000000102"},
        params={"id_persona": id_persona},
        json={"monto": 1.00, "fecha_pago": "2026-06-20"},
    )

    assert pago.status_code == 201, pago.text
    row = db_session.execute(
        text(
            """
            SELECT
                co.saldo_componente,
                lp.base_morable,
                lp.importe_liquidado,
                cf.aplica_punitorio
            FROM composicion_obligacion co
            JOIN concepto_financiero cf
              ON cf.id_concepto_financiero = co.id_concepto_financiero
            JOIN liquidacion_punitorio lp
              ON lp.id_composicion_obligacion = co.id_composicion_obligacion
            WHERE co.id_obligacion_financiera = :id_obligacion
              AND cf.codigo_concepto_financiero = 'PUNITORIO'
              AND co.deleted_at IS NULL
              AND lp.deleted_at IS NULL
            """
        ),
        {"id_obligacion": id_obligacion},
    ).mappings().one()
    aplica_despues = db_session.execute(
        text(
            """
            SELECT aplica_punitorio
            FROM concepto_financiero
            WHERE codigo_concepto_financiero = 'SERVICIO_RECUPERADO'
            """
        )
    ).scalar_one()

    assert aplica_antes is True
    assert aplica_despues is True
    assert row["aplica_punitorio"] is False
    assert float(row["base_morable"]) == 25000.0
    assert float(row["importe_liquidado"]) > 0.0


def test_anular_egreso_proveedor_usado_en_liquidacion_recupero_bloquea(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-011"
    )
    egreso = _registrar_egreso_proveedor(client, db_session, id_factura).json()["data"]
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    assert liquidacion.status_code == 201

    response = client.patch(
        "/api/v1/financiero/egresos-proveedor-factura-servicio/"
        f"{egreso['id_egreso_proveedor_factura_servicio']}/anular",
        headers=HEADERS,
        json={"motivo": "Egreso usado"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "EGRESO_PROVEEDOR_CON_LIQUIDACION_RECUPERO"


def test_anular_liquidacion_recupero_sin_pagos_anula_y_libera_egreso(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-ANU-001"
    )
    egreso = _registrar_egreso_proveedor(client, db_session, id_factura)
    assert egreso.status_code == 201, egreso.text
    egreso_data = egreso.json()["data"]
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    assert liquidacion.status_code == 201, liquidacion.text
    creada = liquidacion.json()["data"]

    before = db_session.execute(
        text(
            """
            SELECT
                e.estado_egreso,
                e.id_movimiento_tesoreria,
                mt.estado AS estado_tesoreria,
                mt.importe AS importe_tesoreria
            FROM egreso_proveedor_factura_servicio e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
            WHERE e.id_egreso_proveedor_factura_servicio = :id_egreso
            """
        ),
        {"id_egreso": egreso_data["id_egreso_proveedor_factura_servicio"]},
    ).mappings().one()

    response = _anular_liquidacion_recupero(
        client, creada["id_liquidacion_recupero"]
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["resultado"] == "ANULADA"
    assert data["estado_liquidacion"] == "ANULADA"
    assert data["estado_relacion_generadora"] == "CANCELADA"
    assert data["estado_obligacion"] == "ANULADA"
    assert data["egresos_liberados"] == 1
    assert data["ya_anulada"] is False
    assert data["motivo"] == "Liquidacion cargada por error"

    row = db_session.execute(
        text(
            """
            SELECT
                lr.estado_liquidacion,
                rg.estado_relacion_generadora,
                o.estado_obligacion,
                co.estado_composicion_obligacion,
                lre.estado_liquidacion_recupero_egreso,
                lre.deleted_at
            FROM liquidacion_recupero lr
            JOIN relacion_generadora rg
              ON rg.id_relacion_generadora = lr.id_relacion_generadora
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = lr.id_obligacion_financiera
            JOIN composicion_obligacion co
              ON co.id_obligacion_financiera = o.id_obligacion_financiera
            JOIN liquidacion_recupero_egreso lre
              ON lre.id_liquidacion_recupero = lr.id_liquidacion_recupero
            WHERE lr.id_liquidacion_recupero = :id_liquidacion
            """
        ),
        {"id_liquidacion": creada["id_liquidacion_recupero"]},
    ).mappings().one()
    assert row["estado_liquidacion"] == "ANULADA"
    assert row["estado_relacion_generadora"] == "CANCELADA"
    assert row["estado_obligacion"] == "ANULADA"
    assert row["estado_composicion_obligacion"] == "ANULADA"
    assert row["estado_liquidacion_recupero_egreso"] == "ANULADO"
    assert row["deleted_at"] is not None

    after = db_session.execute(
        text(
            """
            SELECT
                e.estado_egreso,
                e.id_movimiento_tesoreria,
                mt.estado AS estado_tesoreria,
                mt.importe AS importe_tesoreria
            FROM egreso_proveedor_factura_servicio e
            JOIN movimiento_tesoreria mt
              ON mt.id_movimiento_tesoreria = e.id_movimiento_tesoreria
            WHERE e.id_egreso_proveedor_factura_servicio = :id_egreso
            """
        ),
        {"id_egreso": egreso_data["id_egreso_proveedor_factura_servicio"]},
    ).mappings().one()
    assert dict(after) == dict(before)


def test_anular_liquidacion_recupero_estado_cuenta_y_deuda_no_muestran_servicio_recuperado(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-ANU-002"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    creada = liquidacion.json()["data"]

    anular = _anular_liquidacion_recupero(client, creada["id_liquidacion_recupero"])
    assert anular.status_code == 200, anular.text

    estado = client.get(f"/api/v1/financiero/personas/{id_persona}/estado-cuenta")
    deuda = client.get(
        f"/api/v1/financiero/deuda?id_relacion_generadora={creada['id_relacion_generadora']}"
    )

    assert estado.status_code == 200, estado.text
    assert not any(
        item["id_relacion_generadora"] == creada["id_relacion_generadora"]
        for item in estado.json()["data"]["obligaciones"]
    )
    assert deuda.status_code == 200, deuda.text
    assert deuda.json()["data"]["items"] == []


def test_anular_liquidacion_recupero_libera_egreso_para_nueva_liquidacion(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-ANU-003"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    responsables = [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}]
    first = _liquidar_recupero(client, id_factura, responsables)
    assert first.status_code == 201, first.text

    anular = _anular_liquidacion_recupero(
        client, first.json()["data"]["id_liquidacion_recupero"]
    )
    assert anular.status_code == 200, anular.text

    second = _liquidar_recupero(
        client,
        id_factura,
        responsables,
        headers={**HEADERS, "X-Op-Id": "88888888-8888-8888-8888-888888888888"},
    )

    assert second.status_code == 201, second.text
    assert (
        second.json()["data"]["id_liquidacion_recupero"]
        != first.json()["data"]["id_liquidacion_recupero"]
    )


def test_anular_liquidacion_recupero_repetida_devuelve_ya_anulada(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-ANU-004"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    id_liquidacion = liquidacion.json()["data"]["id_liquidacion_recupero"]

    first = _anular_liquidacion_recupero(client, id_liquidacion)
    second = _anular_liquidacion_recupero(
        client,
        id_liquidacion,
        headers={**HEADERS, "X-Op-Id": "99999999-9999-9999-9999-999999999999"},
    )

    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    assert second.json()["data"]["resultado"] == "YA_ANULADA"
    assert second.json()["data"]["ya_anulada"] is True
    assert second.json()["data"]["egresos_liberados"] == 0


def test_anular_liquidacion_recupero_bloquea_si_tiene_pago_normal(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-ANU-005"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    assert liquidacion.status_code == 201, liquidacion.text

    pago = client.post(
        "/api/v1/financiero/pagos",
        headers=_headers_sin_op_id(),
        params={"id_persona": id_persona},
        json={"monto": 25000.00, "fecha_pago": "2026-05-30"},
    )
    assert pago.status_code == 201, pago.text

    response = _anular_liquidacion_recupero(
        client, liquidacion.json()["data"]["id_liquidacion_recupero"]
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "LIQUIDACION_RECUPERO_TIENE_OPERACIONES"


def test_anular_liquidacion_recupero_bloquea_si_tiene_punitorio_activo(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-ANU-006"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    creada = liquidacion.json()["data"]
    comp_id = db_session.execute(
        text(
            """
            SELECT id_composicion_obligacion
            FROM composicion_obligacion
            WHERE id_obligacion_financiera = :id_obligacion
            ORDER BY id_composicion_obligacion ASC
            LIMIT 1
            """
        ),
        {"id_obligacion": creada["id_obligacion_financiera"]},
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO liquidacion_punitorio (
                uid_global, version_registro, created_at, updated_at,
                id_obligacion_financiera, id_composicion_obligacion,
                uid_pago_grupo, codigo_pago_grupo,
                fecha_vencimiento, fecha_inicio_calculo, fecha_fin_calculo,
                base_morable, tasa_diaria, dias_calculados, importe_liquidado,
                estado_liquidacion
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                :id_obligacion, :id_composicion,
                gen_random_uuid(), 'PUNITORIO-BLOCK-ANU-REC',
                '2026-06-10', '2026-06-16', '2026-06-20',
                25000.00, 0.00100000, 4, 100.00,
                'ACTIVA'
            )
            """
        ),
        {
            "id_obligacion": creada["id_obligacion_financiera"],
            "id_composicion": comp_id,
        },
    )
    db_session.flush()

    response = _anular_liquidacion_recupero(client, creada["id_liquidacion_recupero"])

    assert response.status_code == 409
    assert response.json()["error_code"] == "LIQUIDACION_RECUPERO_TIENE_OPERACIONES"


def test_get_liquidacion_recupero_detalle_muestra_anulada(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-ANU-007"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    creada = liquidacion.json()["data"]
    assert _anular_liquidacion_recupero(
        client, creada["id_liquidacion_recupero"]
    ).status_code == 200

    response = client.get(
        f"/api/v1/financiero/liquidaciones-recupero/{creada['id_liquidacion_recupero']}"
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["estado_liquidacion"] == "ANULADA"
    assert data["obligacion"]["estado_obligacion"] == "ANULADA"


def test_list_liquidaciones_recupero_por_factura_muestra_anulada(
    client, db_session
) -> None:
    id_factura, _, _, id_persona = _crear_factura_servicio_con_responsable(
        client, db_session, codigo="REC-ANU-008"
    )
    assert _registrar_egreso_proveedor(client, db_session, id_factura).status_code == 201
    liquidacion = _liquidar_recupero(
        client,
        id_factura,
        [{"id_persona": id_persona, "porcentaje_responsabilidad": 100.00}],
    )
    creada = liquidacion.json()["data"]
    assert _anular_liquidacion_recupero(
        client, creada["id_liquidacion_recupero"]
    ).status_code == 200

    response = client.get(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/liquidaciones-recupero"
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["items"][0]["estado_liquidacion"] == "ANULADA"


def test_anular_liquidacion_recupero_inexistente_devuelve_404(client) -> None:
    response = _anular_liquidacion_recupero(client, 999999999)

    assert response.status_code == 404
    assert response.json()["error_code"] == "LIQUIDACION_RECUPERO_NOT_FOUND"


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
