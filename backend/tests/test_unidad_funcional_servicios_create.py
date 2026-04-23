from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_create_unidad_funcional_servicio_inserta_en_postgresql(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UFS-001",
            "nombre_inmueble": "Inmueble Base UFS",
            "superficie": "100.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    unidad_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-SERV-001",
            "nombre_unidad": "Unidad Servicio",
            "superficie": "44.50",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert unidad_response.status_code == 201
    id_unidad_funcional = unidad_response.json()["data"]["id_unidad_funcional"]

    servicio_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-UFS-001",
            "nombre_servicio": "Servicio UF",
            "descripcion": "servicio asociado a unidad funcional",
            "estado_servicio": "ACTIVO",
        },
    )
    assert servicio_response.status_code == 201
    id_servicio = servicio_response.json()["data"]["id_servicio"]

    response = client.post(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios",
        headers=HEADERS,
        json={
            "id_servicio": id_servicio,
            "estado": "ACTIVO",
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_unidad_funcional_servicio"], int)
    assert body["data"]["id_unidad_funcional"] == id_unidad_funcional
    assert body["data"]["id_servicio"] == id_servicio
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["estado"] == "ACTIVO"

    row = db_session.execute(
        text(
            """
            SELECT
                id_unidad_funcional_servicio,
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_unidad_funcional,
                id_servicio,
                estado,
                fecha_alta
            FROM unidad_funcional_servicio
            WHERE id_unidad_funcional_servicio = :id_unidad_funcional_servicio
            """
        ),
        {"id_unidad_funcional_servicio": body["data"]["id_unidad_funcional_servicio"]},
    ).mappings().one()

    assert row["id_unidad_funcional_servicio"] == body["data"]["id_unidad_funcional_servicio"]
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["created_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_alta"]) == HEADERS["X-Op-Id"]
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]
    assert row["id_unidad_funcional"] == id_unidad_funcional
    assert row["id_servicio"] == id_servicio
    assert row["estado"] == "ACTIVO"
    assert row["fecha_alta"] is not None


def test_create_unidad_funcional_servicio_rechaza_duplicado_activo(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UFS-DUP",
            "nombre_inmueble": "Inmueble UF Duplicado",
            "superficie": "75.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    unidad_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-SERV-DUP",
            "nombre_unidad": "Unidad Duplicada",
            "superficie": "41.00",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert unidad_response.status_code == 201
    id_unidad_funcional = unidad_response.json()["data"]["id_unidad_funcional"]

    servicio_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-UFS-DUP",
            "nombre_servicio": "Servicio Duplicado",
            "descripcion": "servicio para duplicado",
            "estado_servicio": "ACTIVO",
        },
    )
    assert servicio_response.status_code == 201
    id_servicio = servicio_response.json()["data"]["id_servicio"]

    primera_response = client.post(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios",
        headers=HEADERS,
        json={
            "id_servicio": id_servicio,
            "estado": "ACTIVO",
        },
    )
    assert primera_response.status_code == 201

    duplicada_response = client.post(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios",
        headers=HEADERS,
        json={
            "id_servicio": id_servicio,
            "estado": "ACTIVO",
        },
    )

    assert duplicada_response.status_code == 400
    body = duplicada_response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "Ya existe una asociacion activa entre la unidad funcional y el servicio."
    )

    count = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM unidad_funcional_servicio
            WHERE id_unidad_funcional = :id_unidad_funcional
              AND id_servicio = :id_servicio
              AND deleted_at IS NULL
            """
        ),
        {
            "id_unidad_funcional": id_unidad_funcional,
            "id_servicio": id_servicio,
        },
    ).scalar_one()

    assert count == 1


def test_create_unidad_funcional_servicio_devuelve_404_si_unidad_funcional_no_existe(
    client,
) -> None:
    servicio_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-UFS-404-UF",
            "nombre_servicio": "Servicio 404 UF",
            "descripcion": None,
            "estado_servicio": "ACTIVO",
        },
    )
    assert servicio_response.status_code == 201
    id_servicio = servicio_response.json()["data"]["id_servicio"]

    response = client.post(
        "/api/v1/unidades-funcionales/999999/servicios",
        headers=HEADERS,
        json={
            "id_servicio": id_servicio,
            "estado": "ACTIVO",
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_create_unidad_funcional_servicio_devuelve_404_si_servicio_no_existe(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UFS-404",
            "nombre_inmueble": "Inmueble UF 404",
            "superficie": "60.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    unidad_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-SERV-404",
            "nombre_unidad": "Unidad sin servicio",
            "superficie": "33.00",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert unidad_response.status_code == 201
    id_unidad_funcional = unidad_response.json()["data"]["id_unidad_funcional"]

    response = client.post(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios",
        headers=HEADERS,
        json={
            "id_servicio": 999999,
            "estado": "ACTIVO",
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
