from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_unidad_funcional_devuelve_unidad_activa(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-DET-001",
            "nombre_inmueble": "Inmueble Detalle UF",
            "superficie": "120.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": "inmueble para detalle UF",
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-DET-001",
            "nombre_unidad": "Unidad Detalle",
            "superficie": "65.55",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": "unidad para consulta",
        },
    )
    assert create_response.status_code == 201
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    response = client.get(f"/api/v1/unidades-funcionales/{id_unidad_funcional}")

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_unidad_funcional": id_unidad_funcional,
            "id_inmueble": id_inmueble,
            "codigo_unidad": "UF-DET-001",
            "nombre_unidad": "Unidad Detalle",
            "superficie": "65.55",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": "unidad para consulta",
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_unidad_funcional,
                id_inmueble,
                codigo_unidad,
                nombre_unidad,
                superficie,
                estado_administrativo,
                estado_operativo,
                observaciones
            FROM unidad_funcional
            WHERE id_unidad_funcional = :id_unidad_funcional
            """
        ),
        {"id_unidad_funcional": id_unidad_funcional},
    ).mappings().one()

    assert row["id_unidad_funcional"] == id_unidad_funcional
    assert row["id_inmueble"] == id_inmueble
    assert row["codigo_unidad"] == "UF-DET-001"
    assert row["nombre_unidad"] == "Unidad Detalle"
    assert str(row["superficie"]) == "65.55"
    assert row["estado_administrativo"] == "ACTIVA"
    assert row["estado_operativo"] == "DISPONIBLE"
    assert row["observaciones"] == "unidad para consulta"


def test_get_unidad_funcional_inexistente_devuelve_404(client) -> None:
    response = client.get("/api/v1/unidades-funcionales/999999")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "La unidad funcional indicada no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }


def test_get_unidad_funcional_filtra_soft_delete(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-DEL-001",
            "nombre_inmueble": "Inmueble Delete UF",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-DEL-001",
            "nombre_unidad": "Unidad Eliminada",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": "no debe leerse",
        },
    )
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    db_session.execute(
        text(
            """
            UPDATE unidad_funcional
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_unidad_funcional = :id_unidad_funcional
            """
        ),
        {"id_unidad_funcional": id_unidad_funcional},
    )

    response = client.get(f"/api/v1/unidades-funcionales/{id_unidad_funcional}")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "La unidad funcional indicada no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }
