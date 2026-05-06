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


def _materializar(client, id_factura: int):
    return client.post(
        f"/api/v1/financiero/facturas-servicio/{id_factura}/materializar",
        headers=HEADERS,
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
