from sqlalchemy import text


def _seed_roles_permisos(db_session) -> dict[str, int]:
    rol_id = db_session.execute(text("""
            INSERT INTO rol_seguridad (codigo_rol, nombre_rol, descripcion, estado_rol)
            VALUES ('ADM_TEST', 'Administrador test', 'Rol de seguridad para pruebas', 'ACTIVO')
            RETURNING id_rol_seguridad
            """)).scalar_one()
    permiso_id = db_session.execute(text("""
            INSERT INTO permiso (codigo_permiso, nombre_permiso, descripcion, estado_permiso)
            VALUES ('ADM_TEST_LEER', 'Leer administrativo test', 'Permiso de lectura para pruebas', 'ACTIVO')
            RETURNING id_permiso
            """)).scalar_one()
    db_session.execute(
        text("""
            INSERT INTO rol_seguridad_permiso (id_rol_seguridad, id_permiso)
            VALUES (:rol_id, :permiso_id)
            """),
        {"rol_id": rol_id, "permiso_id": permiso_id},
    )
    db_session.flush()
    return {"rol_id": rol_id, "permiso_id": permiso_id}


def test_list_roles_seguridad(client, db_session):
    ids = _seed_roles_permisos(db_session)

    response = client.get("/api/v1/administrativo/roles-seguridad")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert any(item["id_rol_seguridad"] == ids["rol_id"] for item in body["data"])


def test_get_rol_seguridad(client, db_session):
    ids = _seed_roles_permisos(db_session)

    response = client.get(f"/api/v1/administrativo/roles-seguridad/{ids['rol_id']}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id_rol_seguridad"] == ids["rol_id"]
    assert data["codigo_rol"] == "ADM_TEST"
    assert data["nombre_rol"] == "Administrador test"


def test_list_permisos(client, db_session):
    ids = _seed_roles_permisos(db_session)

    response = client.get("/api/v1/administrativo/permisos")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert any(item["id_permiso"] == ids["permiso_id"] for item in body["data"])


def test_list_permisos_by_rol_seguridad(client, db_session):
    ids = _seed_roles_permisos(db_session)

    response = client.get(
        f"/api/v1/administrativo/roles-seguridad/{ids['rol_id']}/permisos"
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["id_permiso"] == ids["permiso_id"]
    assert data[0]["codigo_permiso"] == "ADM_TEST_LEER"


def test_get_rol_seguridad_inexistente_devuelve_404(client):
    response = client.get("/api/v1/administrativo/roles-seguridad/999999999")

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"
