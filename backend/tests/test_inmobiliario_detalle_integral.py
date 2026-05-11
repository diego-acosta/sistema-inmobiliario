from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _crear_inmueble(client, codigo: str, **overrides) -> int:
    payload = {
        "id_desarrollo": None,
        "codigo_inmueble": codigo,
        "nombre_inmueble": f"Nombre {codigo}",
        "superficie": "100.00",
        "estado_administrativo": "ACTIVO",
        "estado_juridico": "REGULAR",
        "observaciones": f"Obs {codigo}",
    }
    payload.update(overrides)
    response = client.post("/api/v1/inmuebles", headers=HEADERS, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]["id_inmueble"]


def _crear_unidad(client, id_inmueble: int, codigo: str) -> int:
    response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": codigo,
            "nombre_unidad": f"Nombre {codigo}",
            "superficie": "40.00",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": f"Obs {codigo}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id_unidad_funcional"]


def _crear_servicio(client, codigo: str) -> int:
    response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": codigo,
            "nombre_servicio": f"Servicio {codigo}",
            "descripcion": None,
            "estado_servicio": "ACTIVO",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id_servicio"]


def _crear_persona(client, codigo: str) -> int:
    response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": f"Persona {codigo}",
            "apellido": "Responsable",
            "razon_social": None,
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["id_persona"]


def _insertar_disponibilidad(
    db_session,
    *,
    id_inmueble: int | None = None,
    id_unidad_funcional: int | None = None,
    estado: str,
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO disponibilidad (
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta
            )
            VALUES (
                :id_inmueble,
                :id_unidad_funcional,
                :estado,
                CURRENT_TIMESTAMP,
                NULL
            )
            """
        ),
        {
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
            "estado": estado,
        },
    )


def _insertar_ocupacion(
    db_session,
    *,
    id_inmueble: int | None = None,
    id_unidad_funcional: int | None = None,
    tipo: str,
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO ocupacion (
                id_inmueble,
                id_unidad_funcional,
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta
            )
            VALUES (
                :id_inmueble,
                :id_unidad_funcional,
                :tipo,
                CURRENT_TIMESTAMP,
                NULL
            )
            """
        ),
        {
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
            "tipo": tipo,
        },
    )


def _insertar_relaciones_simples(
    db_session,
    *,
    id_inmueble: int | None = None,
    id_unidad_funcional: int | None = None,
) -> None:
    reserva_venta = db_session.execute(
        text(
            """
            INSERT INTO reserva_venta (codigo_reserva, fecha_reserva, estado_reserva)
            VALUES (:codigo, CURRENT_TIMESTAMP, 'activa')
            RETURNING id_reserva_venta
            """
        ),
        {"codigo": f"RV-DI-{id_inmueble or id_unidad_funcional}"},
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO reserva_venta_objeto_inmobiliario (
                id_reserva_venta, id_inmueble, id_unidad_funcional
            )
            VALUES (:id_reserva, :id_inmueble, :id_unidad_funcional)
            """
        ),
        {
            "id_reserva": reserva_venta,
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
        },
    )
    venta = db_session.execute(
        text(
            """
            INSERT INTO venta (
                id_reserva_venta, codigo_venta, fecha_venta, estado_venta
            )
            VALUES (:id_reserva, :codigo, CURRENT_TIMESTAMP, 'confirmada')
            RETURNING id_venta
            """
        ),
        {
            "id_reserva": reserva_venta,
            "codigo": f"V-DI-{id_inmueble or id_unidad_funcional}",
        },
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO venta_objeto_inmobiliario (
                id_venta, id_inmueble, id_unidad_funcional
            )
            VALUES (:id_venta, :id_inmueble, :id_unidad_funcional)
            """
        ),
        {
            "id_venta": venta,
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
        },
    )
    reserva_locativa = db_session.execute(
        text(
            """
            INSERT INTO reserva_locativa (
                codigo_reserva, fecha_reserva, estado_reserva
            )
            VALUES (:codigo, CURRENT_TIMESTAMP, 'confirmada')
            RETURNING id_reserva_locativa
            """
        ),
        {"codigo": f"RL-DI-{id_inmueble or id_unidad_funcional}"},
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO reserva_locativa_objeto (
                id_reserva_locativa, id_inmueble, id_unidad_funcional
            )
            VALUES (:id_reserva, :id_inmueble, :id_unidad_funcional)
            """
        ),
        {
            "id_reserva": reserva_locativa,
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
        },
    )
    contrato = db_session.execute(
        text(
            """
            INSERT INTO contrato_alquiler (
                id_reserva_locativa,
                codigo_contrato,
                fecha_inicio,
                fecha_fin,
                estado_contrato
            )
            VALUES (:id_reserva, :codigo, DATE '2026-05-01', NULL, 'ACTIVO')
            RETURNING id_contrato_alquiler
            """
        ),
        {
            "id_reserva": reserva_locativa,
            "codigo": f"CA-DI-{id_inmueble or id_unidad_funcional}",
        },
    ).scalar_one()
    db_session.execute(
        text(
            """
            INSERT INTO contrato_objeto_locativo (
                id_contrato_alquiler, id_inmueble, id_unidad_funcional
            )
            VALUES (:id_contrato, :id_inmueble, :id_unidad_funcional)
            """
        ),
        {
            "id_contrato": contrato,
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
        },
    )


def _contadores_read_only(db_session) -> dict[str, int]:
    return {
        "disponibilidad": db_session.execute(
            text("SELECT COUNT(*) FROM disponibilidad")
        ).scalar_one(),
        "ocupacion": db_session.execute(text("SELECT COUNT(*) FROM ocupacion")).scalar_one(),
        "outbox": db_session.execute(text("SELECT COUNT(*) FROM outbox_event")).scalar_one(),
    }


def test_detalle_integral_inmueble_read_only_y_no_mezcla_unidad(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, "INM-DI-001")
    id_unidad = _crear_unidad(client, id_inmueble, "UF-DI-001")
    id_servicio = _crear_servicio(client, "SERV-DI-INM")
    id_persona = _crear_persona(client, "DI-INM")
    assert client.post(
        f"/api/v1/inmuebles/{id_inmueble}/servicios",
        headers=HEADERS,
        json={"id_servicio": id_servicio, "estado": "ACTIVO"},
    ).status_code == 201
    db_session.execute(
        text(
            """
            INSERT INTO asignacion_servicio_responsable (
                id_servicio, id_inmueble, id_persona,
                porcentaje_responsabilidad, fecha_desde, estado_asignacion
            )
            VALUES (:id_servicio, :id_inmueble, :id_persona, 100.00, DATE '2026-05-01', 'ACTIVA')
            """
        ),
        {
            "id_servicio": id_servicio,
            "id_inmueble": id_inmueble,
            "id_persona": id_persona,
        },
    )
    _insertar_disponibilidad(db_session, id_inmueble=id_inmueble, estado="INMUEBLE")
    _insertar_ocupacion(db_session, id_inmueble=id_inmueble, tipo="INMUEBLE")
    _insertar_disponibilidad(db_session, id_unidad_funcional=id_unidad, estado="UNIDAD")
    _insertar_ocupacion(db_session, id_unidad_funcional=id_unidad, tipo="UNIDAD")
    _insertar_relaciones_simples(db_session, id_inmueble=id_inmueble)

    before = _contadores_read_only(db_session)
    response = client.get(f"/api/v1/inmuebles/{id_inmueble}/detalle-integral")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["inmueble"]["id_inmueble"] == id_inmueble
    assert [uf["id_unidad_funcional"] for uf in data["unidades_funcionales"]] == [
        id_unidad
    ]
    assert data["servicios"][0]["id_servicio"] == id_servicio
    assert data["responsables_servicio"][0]["id_persona"] == id_persona
    assert data["disponibilidad_actual"]["estado_disponibilidad"] == "INMUEBLE"
    assert data["ocupacion_actual"]["tipo_ocupacion"] == "INMUEBLE"
    assert data["disponibilidad_ambigua"] is False
    assert data["ocupacion_ambigua"] is False
    assert {d["estado_disponibilidad"] for d in data["disponibilidades"]} == {
        "INMUEBLE"
    }
    assert {o["tipo_ocupacion"] for o in data["ocupaciones"]} == {"INMUEBLE"}
    assert len(data["reservas_venta"]) == 1
    assert len(data["ventas"]) == 1
    assert len(data["reservas_locativas"]) == 1
    assert len(data["contratos_alquiler"]) == 1
    assert data["resumen_operativo"] == {
        "cantidad_unidades": 1,
        "cantidad_servicios": 1,
        "tiene_ocupacion_actual": True,
        "tiene_disponibilidad_actual": True,
        "disponibilidad_ambigua": False,
        "ocupacion_ambigua": False,
    }
    assert _contadores_read_only(db_session) == before


def test_detalle_integral_inmueble_ambiguo_y_404(client, db_session) -> None:
    id_inmueble = _crear_inmueble(client, "INM-DI-AMB")
    db_session.execute(text("ALTER TABLE disponibilidad DISABLE TRIGGER trg_biu_disponibilidad_no_solapada"))
    db_session.execute(text("ALTER TABLE ocupacion DISABLE TRIGGER trg_biu_ocupacion_no_solapada"))
    try:
        _insertar_disponibilidad(db_session, id_inmueble=id_inmueble, estado="UNO")
        _insertar_disponibilidad(db_session, id_inmueble=id_inmueble, estado="DOS")
        _insertar_ocupacion(db_session, id_inmueble=id_inmueble, tipo="UNO")
        _insertar_ocupacion(db_session, id_inmueble=id_inmueble, tipo="DOS")
    finally:
        db_session.execute(text("ALTER TABLE disponibilidad ENABLE TRIGGER trg_biu_disponibilidad_no_solapada"))
        db_session.execute(text("ALTER TABLE ocupacion ENABLE TRIGGER trg_biu_ocupacion_no_solapada"))

    response = client.get(f"/api/v1/inmuebles/{id_inmueble}/detalle-integral")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["disponibilidad_actual"] is None
    assert data["disponibilidad_ambigua"] is True
    assert data["ocupacion_actual"] is None
    assert data["ocupacion_ambigua"] is True

    db_session.execute(
        text("UPDATE inmueble SET deleted_at = CURRENT_TIMESTAMP WHERE id_inmueble = :id"),
        {"id": id_inmueble},
    )
    assert client.get(f"/api/v1/inmuebles/{id_inmueble}/detalle-integral").status_code == 404
    assert client.get("/api/v1/inmuebles/999999999/detalle-integral").status_code == 404


def test_detalle_integral_unidad_read_only_y_no_mezcla_inmueble(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, "INM-DI-UF")
    id_unidad = _crear_unidad(client, id_inmueble, "UF-DI-002")
    id_servicio = _crear_servicio(client, "SERV-DI-UF")
    id_persona = _crear_persona(client, "DI-UF")
    assert client.post(
        f"/api/v1/unidades-funcionales/{id_unidad}/servicios",
        headers=HEADERS,
        json={"id_servicio": id_servicio, "estado": "ACTIVO"},
    ).status_code == 201
    db_session.execute(
        text(
            """
            INSERT INTO asignacion_servicio_responsable (
                id_servicio, id_unidad_funcional, id_persona,
                porcentaje_responsabilidad, fecha_desde, estado_asignacion
            )
            VALUES (:id_servicio, :id_unidad, :id_persona, 100.00, DATE '2026-05-01', 'ACTIVA')
            """
        ),
        {
            "id_servicio": id_servicio,
            "id_unidad": id_unidad,
            "id_persona": id_persona,
        },
    )
    _insertar_disponibilidad(db_session, id_inmueble=id_inmueble, estado="INMUEBLE")
    _insertar_ocupacion(db_session, id_inmueble=id_inmueble, tipo="INMUEBLE")
    _insertar_disponibilidad(db_session, id_unidad_funcional=id_unidad, estado="UNIDAD")
    _insertar_ocupacion(db_session, id_unidad_funcional=id_unidad, tipo="UNIDAD")
    _insertar_relaciones_simples(db_session, id_unidad_funcional=id_unidad)

    before = _contadores_read_only(db_session)
    response = client.get(
        f"/api/v1/unidades-funcionales/{id_unidad}/detalle-integral"
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["unidad_funcional"]["id_unidad_funcional"] == id_unidad
    assert data["inmueble"]["id_inmueble"] == id_inmueble
    assert data["servicios"][0]["id_servicio"] == id_servicio
    assert data["responsables_servicio"][0]["id_persona"] == id_persona
    assert data["disponibilidad_actual"]["estado_disponibilidad"] == "UNIDAD"
    assert data["ocupacion_actual"]["tipo_ocupacion"] == "UNIDAD"
    assert {d["estado_disponibilidad"] for d in data["disponibilidades"]} == {"UNIDAD"}
    assert {o["tipo_ocupacion"] for o in data["ocupaciones"]} == {"UNIDAD"}
    assert len(data["reservas_venta"]) == 1
    assert len(data["ventas"]) == 1
    assert len(data["reservas_locativas"]) == 1
    assert len(data["contratos_alquiler"]) == 1
    assert data["resumen_operativo"] == {
        "cantidad_servicios": 1,
        "tiene_ocupacion_actual": True,
        "tiene_disponibilidad_actual": True,
        "disponibilidad_ambigua": False,
        "ocupacion_ambigua": False,
    }
    assert _contadores_read_only(db_session) == before


def test_detalle_integral_unidad_ambigua_y_404(client, db_session) -> None:
    id_inmueble = _crear_inmueble(client, "INM-DI-UF-AMB")
    id_unidad = _crear_unidad(client, id_inmueble, "UF-DI-AMB")
    db_session.execute(text("ALTER TABLE disponibilidad DISABLE TRIGGER trg_biu_disponibilidad_no_solapada"))
    db_session.execute(text("ALTER TABLE ocupacion DISABLE TRIGGER trg_biu_ocupacion_no_solapada"))
    try:
        _insertar_disponibilidad(db_session, id_unidad_funcional=id_unidad, estado="UNO")
        _insertar_disponibilidad(db_session, id_unidad_funcional=id_unidad, estado="DOS")
        _insertar_ocupacion(db_session, id_unidad_funcional=id_unidad, tipo="UNO")
        _insertar_ocupacion(db_session, id_unidad_funcional=id_unidad, tipo="DOS")
    finally:
        db_session.execute(text("ALTER TABLE disponibilidad ENABLE TRIGGER trg_biu_disponibilidad_no_solapada"))
        db_session.execute(text("ALTER TABLE ocupacion ENABLE TRIGGER trg_biu_ocupacion_no_solapada"))

    response = client.get(
        f"/api/v1/unidades-funcionales/{id_unidad}/detalle-integral"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["disponibilidad_actual"] is None
    assert data["disponibilidad_ambigua"] is True
    assert data["ocupacion_actual"] is None
    assert data["ocupacion_ambigua"] is True

    db_session.execute(
        text(
            "UPDATE unidad_funcional SET deleted_at = CURRENT_TIMESTAMP WHERE id_unidad_funcional = :id"
        ),
        {"id": id_unidad},
    )
    assert (
        client.get(
            f"/api/v1/unidades-funcionales/{id_unidad}/detalle-integral"
        ).status_code
        == 404
    )
    assert (
        client.get(
            "/api/v1/unidades-funcionales/999999999/detalle-integral"
        ).status_code
        == 404
    )
