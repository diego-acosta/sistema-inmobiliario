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
        "observaciones": f"Ubicacion {codigo}",
    }
    payload.update(overrides)
    response = client.post("/api/v1/inmuebles", headers=HEADERS, json=payload)
    assert response.status_code == 201
    return response.json()["data"]["id_inmueble"]


def _crear_unidad(client, id_inmueble: int, codigo: str, **overrides) -> int:
    payload = {
        "codigo_unidad": codigo,
        "nombre_unidad": f"Nombre {codigo}",
        "superficie": "45.00",
        "estado_administrativo": "ACTIVA",
        "estado_operativo": "DISPONIBLE",
        "observaciones": f"Descripcion {codigo}",
    }
    payload.update(overrides)
    response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json=payload,
    )
    assert response.status_code == 201
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
    assert response.status_code == 201
    return response.json()["data"]["id_servicio"]


def _insertar_disponibilidad(
    db_session,
    *,
    id_inmueble: int | None = None,
    id_unidad_funcional: int | None = None,
    estado: str = "DISPONIBLE",
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
    tipo: str = "OCUPADO",
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


def test_selector_inmuebles_filtros_estado_desarrollo_servicio_y_paginacion(
    client, db_session
) -> None:
    desarrollo = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DES-SEL-001",
            "nombre_desarrollo": "Desarrollo Selector",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    assert desarrollo.status_code == 201
    id_desarrollo = desarrollo.json()["data"]["id_desarrollo"]

    id_servicio = _crear_servicio(client, "SERV-SEL-INM")
    id_1 = _crear_inmueble(
        client,
        "INM-SEL-001",
        id_desarrollo=id_desarrollo,
        nombre_inmueble="Torre Buscada",
        estado_administrativo="ACTIVO",
        estado_juridico="REGULAR",
        observaciones="Direccion Norte",
    )
    id_2 = _crear_inmueble(
        client,
        "INM-SEL-002",
        estado_administrativo="INACTIVO",
        estado_juridico="OBSERVADO",
    )
    servicio_response = client.post(
        f"/api/v1/inmuebles/{id_1}/servicios",
        headers=HEADERS,
        json={"id_servicio": id_servicio, "estado": "ACTIVO"},
    )
    assert servicio_response.status_code == 201

    db_session.execute(
        text("UPDATE inmueble SET deleted_at = CURRENT_TIMESTAMP WHERE id_inmueble = :id"),
        {"id": id_2},
    )

    response = client.get(
        "/api/v1/inmuebles",
        params={
            "q": "buscada",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "id_desarrollo": id_desarrollo,
            "id_servicio": id_servicio,
            "limit": 1,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["limit"] == 1
    assert body["offset"] == 0
    assert [item["id_inmueble"] for item in body["items"]] == [id_1]
    assert body["items"] == body["data"]
    assert body["items"][0]["disponibilidad_actual"] is None
    assert body["items"][0]["ocupacion_actual"] is None


def test_selector_inmuebles_disponibilidad_ocupacion_actual_y_ambigua(
    client, db_session
) -> None:
    id_unico = _crear_inmueble(client, "INM-SEL-ACTUAL")
    _insertar_disponibilidad(db_session, id_inmueble=id_unico, estado="DISPONIBLE")
    _insertar_ocupacion(db_session, id_inmueble=id_unico, tipo="PROPIETARIO")

    response = client.get(
        "/api/v1/inmuebles",
        params={
            "q": "INM-SEL-ACTUAL",
            "disponibilidad_actual": "DISPONIBLE",
            "ocupacion_actual": "PROPIETARIO",
        },
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["disponibilidad_actual"]["estado_disponibilidad"] == "DISPONIBLE"
    assert item["disponibilidad_ambigua"] is False
    assert item["ocupacion_actual"]["tipo_ocupacion"] == "PROPIETARIO"
    assert item["ocupacion_ambigua"] is False

    id_ambiguo = _crear_inmueble(client, "INM-SEL-AMB")
    db_session.execute(text("ALTER TABLE disponibilidad DISABLE TRIGGER trg_biu_disponibilidad_no_solapada"))
    db_session.execute(text("ALTER TABLE ocupacion DISABLE TRIGGER trg_biu_ocupacion_no_solapada"))
    try:
        _insertar_disponibilidad(db_session, id_inmueble=id_ambiguo, estado="UNO")
        _insertar_disponibilidad(db_session, id_inmueble=id_ambiguo, estado="DOS")
        _insertar_ocupacion(db_session, id_inmueble=id_ambiguo, tipo="UNO")
        _insertar_ocupacion(db_session, id_inmueble=id_ambiguo, tipo="DOS")
    finally:
        db_session.execute(text("ALTER TABLE disponibilidad ENABLE TRIGGER trg_biu_disponibilidad_no_solapada"))
        db_session.execute(text("ALTER TABLE ocupacion ENABLE TRIGGER trg_biu_ocupacion_no_solapada"))

    response_ambiguo = client.get("/api/v1/inmuebles", params={"q": "INM-SEL-AMB"})
    assert response_ambiguo.status_code == 200
    item_ambiguo = response_ambiguo.json()["items"][0]
    assert item_ambiguo["disponibilidad_actual"] is None
    assert item_ambiguo["disponibilidad_ambigua"] is True
    assert item_ambiguo["ocupacion_actual"] is None
    assert item_ambiguo["ocupacion_ambigua"] is True


def test_selector_unidades_filtros_actuales_y_no_mezcla_con_inmueble(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, "INM-SEL-UF-PADRE")
    id_unidad = _crear_unidad(client, id_inmueble, "UF-SEL-ACTUAL")
    id_servicio = _crear_servicio(client, "SERV-SEL-UF")
    servicio_response = client.post(
        f"/api/v1/unidades-funcionales/{id_unidad}/servicios",
        headers=HEADERS,
        json={"id_servicio": id_servicio, "estado": "ACTIVO"},
    )
    assert servicio_response.status_code == 201

    _insertar_disponibilidad(db_session, id_inmueble=id_inmueble, estado="INMUEBLE")
    _insertar_ocupacion(db_session, id_inmueble=id_inmueble, tipo="INMUEBLE")
    _insertar_disponibilidad(
        db_session, id_unidad_funcional=id_unidad, estado="UNIDAD"
    )
    _insertar_ocupacion(db_session, id_unidad_funcional=id_unidad, tipo="UNIDAD")

    response = client.get(
        "/api/v1/unidades-funcionales",
        params={
            "q": "UF-SEL-ACTUAL",
            "id_inmueble": id_inmueble,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "disponibilidad_actual": "UNIDAD",
            "ocupacion_actual": "UNIDAD",
            "id_servicio": id_servicio,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id_unidad_funcional"] == id_unidad
    assert item["disponibilidad_actual"]["estado_disponibilidad"] == "UNIDAD"
    assert item["ocupacion_actual"]["tipo_ocupacion"] == "UNIDAD"
    assert item["inmueble"]["id_inmueble"] == id_inmueble
    assert item["inmueble"]["codigo_inmueble"] == "INM-SEL-UF-PADRE"

    sin_mezcla = client.get(
        "/api/v1/unidades-funcionales",
        params={"q": "UF-SEL-ACTUAL", "disponibilidad_actual": "INMUEBLE"},
    )
    assert sin_mezcla.status_code == 200
    assert sin_mezcla.json()["items"] == []
    assert sin_mezcla.json()["total"] == 0


def test_selector_unidades_ambigua_y_consulta_no_modifica_vigencias(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, "INM-SEL-UF-AMB")
    id_unidad = _crear_unidad(client, id_inmueble, "UF-SEL-AMB")

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

    before = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM disponibilidad WHERE id_unidad_funcional = :id_unidad AND fecha_hasta IS NULL) AS disp,
                (SELECT COUNT(*) FROM ocupacion WHERE id_unidad_funcional = :id_unidad AND fecha_hasta IS NULL) AS ocup
            """
        ),
        {"id_unidad": id_unidad},
    ).mappings().one()

    response = client.get("/api/v1/unidades-funcionales", params={"q": "UF-SEL-AMB"})

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["disponibilidad_actual"] is None
    assert item["disponibilidad_ambigua"] is True
    assert item["ocupacion_actual"] is None
    assert item["ocupacion_ambigua"] is True

    after = db_session.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM disponibilidad WHERE id_unidad_funcional = :id_unidad AND fecha_hasta IS NULL) AS disp,
                (SELECT COUNT(*) FROM ocupacion WHERE id_unidad_funcional = :id_unidad AND fecha_hasta IS NULL) AS ocup
            """
        ),
        {"id_unidad": id_unidad},
    ).mappings().one()
    assert after == before


def test_selector_sin_resultados_devuelve_items_y_total(client) -> None:
    response = client.get("/api/v1/inmuebles", params={"q": "NO-EXISTE-SEL"})

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["data"] == []
    assert response.json()["total"] == 0
