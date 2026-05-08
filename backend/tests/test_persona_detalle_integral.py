from decimal import Decimal

from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _crear_persona(client, *, nombre: str, apellido: str) -> int:
    response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": nombre,
            "apellido": apellido,
            "razon_social": None,
            "fecha_nacimiento": "1990-01-01",
            "estado_persona": "ACTIVA",
            "observaciones": "persona para detalle integral UI",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_persona"]


def _detalle(client, id_persona: int):
    return client.get(f"/api/v1/personas/{id_persona}/detalle-integral")


def _crear_rol(db_session, *, id_rol: int, codigo: str) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO rol_participacion (
                id_rol_participacion, uid_global, version_registro,
                created_at, updated_at, id_instalacion_origen,
                id_instalacion_ultima_modificacion, op_id_alta,
                op_id_ultima_modificacion, codigo_rol, nombre_rol,
                descripcion, estado_rol
            )
            VALUES (
                :id_rol, gen_random_uuid(), 1, CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP, 1, 1, CAST(:op_id AS uuid),
                CAST(:op_id AS uuid), :codigo, :nombre, NULL, 'ACTIVO'
            )
            """
        ),
        {
            "id_rol": id_rol,
            "op_id": HEADERS["X-Op-Id"],
            "codigo": codigo,
            "nombre": f"Rol {codigo}",
        },
    )


def _crear_participacion(
    db_session,
    *,
    id_persona: int,
    id_rol: int,
    tipo_relacion: str,
    id_relacion: int,
) -> int:
    return db_session.execute(
        text(
            """
            INSERT INTO relacion_persona_rol (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, id_persona,
                id_rol_participacion, tipo_relacion, id_relacion,
                fecha_desde, fecha_hasta, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid),
                :id_persona, :id_rol, :tipo_relacion, :id_relacion,
                CURRENT_TIMESTAMP, NULL, NULL
            )
            RETURNING id_relacion_persona_rol
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_persona": id_persona,
            "id_rol": id_rol,
            "tipo_relacion": tipo_relacion,
            "id_relacion": id_relacion,
        },
    ).scalar_one()


def _crear_venta(db_session, *, codigo: str, monto: Decimal = Decimal("100000.00")) -> int:
    return db_session.execute(
        text(
            """
            INSERT INTO venta (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, codigo_venta,
                fecha_venta, estado_venta, monto_total, tipo_plan_financiero,
                moneda, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid),
                :codigo, CURRENT_TIMESTAMP, 'confirmada', :monto,
                'CONTADO', 'ARS', NULL
            )
            RETURNING id_venta
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "codigo": codigo, "monto": monto},
    ).scalar_one()


def _crear_contrato(db_session, *, codigo: str) -> int:
    return db_session.execute(
        text(
            """
            INSERT INTO contrato_alquiler (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, codigo_contrato,
                fecha_inicio, fecha_fin, estado_contrato, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid),
                :codigo, DATE '2026-01-01', DATE '2026-12-31',
                'ACTIVO', NULL
            )
            RETURNING id_contrato_alquiler
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "codigo": codigo},
    ).scalar_one()


def _crear_obligacion(db_session, *, id_persona: int, saldo: Decimal) -> int:
    id_venta = _crear_venta(
        db_session,
        codigo=f"VENTA-OB-PER-{id_persona}",
        monto=Decimal("2000.00"),
    )
    id_rg = db_session.execute(
        text(
            """
            INSERT INTO relacion_generadora (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, tipo_origen,
                id_origen, descripcion, estado_relacion_generadora
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid),
                'venta', :id_venta, 'Detalle integral persona', 'ACTIVA'
            )
            RETURNING id_relacion_generadora
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "id_venta": id_venta},
    ).scalar_one()
    id_obligacion = db_session.execute(
        text(
            """
            INSERT INTO obligacion_financiera (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, id_relacion_generadora,
                fecha_emision, fecha_vencimiento, importe_total, saldo_pendiente,
                moneda, estado_obligacion
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid), :id_rg,
                DATE '2026-05-08', DATE '2026-06-08', :importe, :saldo,
                'ARS', 'EMITIDA'
            )
            RETURNING id_obligacion_financiera
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_rg": id_rg,
            "importe": Decimal("2000.00"),
            "saldo": saldo,
        },
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO obligacion_obligado (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, id_obligacion_financiera,
                id_persona, rol_obligado, porcentaje_responsabilidad
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, CAST(:op_id AS uuid), CAST(:op_id AS uuid),
                :id_obligacion, :id_persona, 'COMPRADOR', 50.00
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_obligacion": id_obligacion,
            "id_persona": id_persona,
        },
    )
    return id_obligacion


def _counts(db_session) -> dict:
    tables = [
        "persona",
        "relacion_persona_rol",
        "obligacion_financiera",
        "obligacion_obligado",
        "movimiento_financiero",
        "aplicacion_financiera",
    ]
    return {
        table: db_session.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar_one()
        for table in tables
    }


def test_detalle_integral_persona_devuelve_subrecursos_completos(client) -> None:
    id_persona = _crear_persona(client, nombre="Detalle", apellido="Completo")
    assert client.post(
        f"/api/v1/personas/{id_persona}/documentos",
        headers=HEADERS,
        json={
            "tipo_documento": "DNI",
            "numero_documento": "12345678",
            "pais_emision": "AR",
            "es_principal": True,
        },
    ).status_code == 201
    assert client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "detalle@example.com",
            "es_principal": True,
        },
    ).status_code == 201
    assert client.post(
        f"/api/v1/personas/{id_persona}/domicilios",
        headers=HEADERS,
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle 123",
            "localidad": "CABA",
            "provincia": "Buenos Aires",
            "pais": "AR",
            "codigo_postal": "1000",
            "es_principal": True,
        },
    ).status_code == 201

    response = _detalle(client, id_persona)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["documentos"][0]["numero_documento"] == "12345678"
    assert data["contactos"][0]["valor_contacto"] == "detalle@example.com"
    assert data["domicilios"][0]["direccion"] == "Calle 123"


def test_detalle_integral_persona_muestra_participaciones_contextuales(
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Participa", apellido="Contextual")
    id_venta = _crear_venta(db_session, codigo="VENTA-DET-PER-PART")
    _crear_rol(db_session, id_rol=7101, codigo="REPRESENTANTE")
    id_relacion = _crear_participacion(
        db_session,
        id_persona=id_persona,
        id_rol=7101,
        tipo_relacion="venta",
        id_relacion=id_venta,
    )

    response = _detalle(client, id_persona)

    assert response.status_code == 200
    participaciones = response.json()["data"]["participaciones"]
    assert participaciones[0]["id_relacion_persona_rol"] == id_relacion
    assert participaciones[0]["codigo_rol"] == "REPRESENTANTE"


def test_detalle_integral_persona_comprador_muestra_uso_venta(client, db_session) -> None:
    id_persona = _crear_persona(client, nombre="Comprador", apellido="Venta")
    id_venta = _crear_venta(db_session, codigo="VENTA-DET-PER-1")
    _crear_rol(db_session, id_rol=7102, codigo="COMPRADOR")
    _crear_participacion(
        db_session,
        id_persona=id_persona,
        id_rol=7102,
        tipo_relacion="venta",
        id_relacion=id_venta,
    )

    response = _detalle(client, id_persona)

    assert response.status_code == 200
    ventas = response.json()["data"]["usos_transversales"]["comprador_ventas"]
    assert ventas == [
        {
            "id_venta": id_venta,
            "codigo_venta": "VENTA-DET-PER-1",
            "estado_venta": "confirmada",
            "monto_total": 100000.0,
            "moneda": "ARS",
            "rol": "COMPRADOR",
        }
    ]


def test_detalle_integral_persona_locatario_muestra_uso_contrato(
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Locatario", apellido="Contrato")
    id_contrato = _crear_contrato(db_session, codigo="CONT-DET-PER-1")
    _crear_rol(db_session, id_rol=7103, codigo="LOCATARIO")
    _crear_participacion(
        db_session,
        id_persona=id_persona,
        id_rol=7103,
        tipo_relacion="contrato_alquiler",
        id_relacion=id_contrato,
    )

    response = _detalle(client, id_persona)

    assert response.status_code == 200
    contratos = response.json()["data"]["usos_transversales"]["contratos_locativos"]
    assert contratos[0]["id_contrato_alquiler"] == id_contrato
    assert contratos[0]["codigo_contrato"] == "CONT-DET-PER-1"
    assert contratos[0]["rol"] == "LOCATARIO"


def test_detalle_integral_persona_con_obligaciones_muestra_resumen(
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Obligado", apellido="Financiero")
    id_obligacion = _crear_obligacion(
        db_session, id_persona=id_persona, saldo=Decimal("1500.00")
    )

    response = _detalle(client, id_persona)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["obligaciones_financieras"][0]["id_obligacion_financiera"] == id_obligacion
    assert data["resumen_financiero"] == {
        "cantidad_obligaciones": 1,
        "importe_total": 2000.0,
        "saldo_pendiente_total": 1500.0,
        "importe_total_responsabilidad": 1000.0,
        "saldo_pendiente_responsabilidad": 750.0,
    }


def test_detalle_integral_persona_sin_participaciones_ni_obligaciones_devuelve_listas(
    client,
) -> None:
    id_persona = _crear_persona(client, nombre="Sin", apellido="Usos")

    response = _detalle(client, id_persona)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["participaciones"] == []
    assert data["obligaciones_financieras"] == []
    assert data["resumen_financiero"]["cantidad_obligaciones"] == 0


def test_detalle_integral_persona_es_read_only(client, db_session) -> None:
    id_persona = _crear_persona(client, nombre="Read", apellido="Only")
    _crear_obligacion(db_session, id_persona=id_persona, saldo=Decimal("500.00"))
    before = _counts(db_session)

    response = _detalle(client, id_persona)

    assert response.status_code == 200
    assert _counts(db_session) == before


def test_detalle_integral_persona_404_si_no_existe(client) -> None:
    response = _detalle(client, 999999999)

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_detalle_integral_persona_404_si_esta_dada_de_baja(
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Baja", apellido="Logica")
    db_session.execute(
        text("UPDATE persona SET deleted_at = created_at WHERE id_persona = :id"),
        {"id": id_persona},
    )

    response = _detalle(client, id_persona)

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
