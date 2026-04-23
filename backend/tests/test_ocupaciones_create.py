from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS


def test_create_ocupacion_inserta_en_postgresql_para_inmueble(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-001",
            "nombre_inmueble": "Inmueble Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-30T10:00:00",
            "descripcion": "ocupacion por inmueble",
            "observaciones": "alta ocupacion inmueble",
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_ocupacion"], int)
    assert body["data"]["id_inmueble"] == id_inmueble
    assert body["data"]["id_unidad_funcional"] is None
    assert body["data"]["tipo_ocupacion"] == "PROPIA"
    assert body["data"]["fecha_desde"] == "2026-04-21T10:00:00"
    assert body["data"]["fecha_hasta"] == "2026-04-30T10:00:00"
    assert body["data"]["descripcion"] == "ocupacion por inmueble"
    assert body["data"]["observaciones"] == "alta ocupacion inmueble"
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1

    row = db_session.execute(
        text(
            """
            SELECT
                id_ocupacion,
                uid_global,
                version_registro,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_inmueble,
                id_unidad_funcional,
                tipo_ocupacion,
                fecha_desde,
                fecha_hasta,
                descripcion,
                observaciones
            FROM ocupacion
            WHERE id_ocupacion = :id_ocupacion
            """
        ),
        {"id_ocupacion": body["data"]["id_ocupacion"]},
    ).mappings().one()

    assert row["id_ocupacion"] == body["data"]["id_ocupacion"]
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_alta"]) == HEADERS["X-Op-Id"]
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]
    assert row["id_inmueble"] == id_inmueble
    assert row["id_unidad_funcional"] is None
    assert row["tipo_ocupacion"] == "PROPIA"
    assert row["descripcion"] == "ocupacion por inmueble"
    assert row["observaciones"] == "alta ocupacion inmueble"


def test_create_ocupacion_inserta_en_postgresql_para_unidad_funcional(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-UF-001",
            "nombre_inmueble": "Inmueble Base UF Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    uf_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-OC-001",
            "nombre_unidad": "Unidad con Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert uf_response.status_code == 201
    id_unidad_funcional = uf_response.json()["data"]["id_unidad_funcional"]

    response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": None,
            "id_unidad_funcional": id_unidad_funcional,
            "tipo_ocupacion": "TERCEROS",
            "fecha_desde": "2026-04-22T09:30:00",
            "fecha_hasta": None,
            "descripcion": "ocupacion por unidad",
            "observaciones": "alta ocupacion unidad",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["id_inmueble"] is None
    assert body["data"]["id_unidad_funcional"] == id_unidad_funcional
    assert body["data"]["tipo_ocupacion"] == "TERCEROS"
    assert body["data"]["fecha_desde"] == "2026-04-22T09:30:00"
    assert body["data"]["fecha_hasta"] is None


def test_create_ocupacion_devuelve_error_si_vienen_ambos_padres(client) -> None:
    response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": 1,
            "id_unidad_funcional": 1,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional."
    )


def test_create_ocupacion_devuelve_error_si_no_viene_ningun_padre(
    client,
) -> None:
    response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": None,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional."
    )


def test_create_ocupacion_devuelve_error_si_fecha_hasta_es_menor(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-FECHA-001",
            "nombre_inmueble": "Inmueble Fecha Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-20T10:00:00",
            "descripcion": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["error_message"] == "fecha_hasta no puede ser menor que fecha_desde."
