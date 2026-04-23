from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_create_servicio_inserta_en_postgresql(client, db_session) -> None:
    response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-001",
            "nombre_servicio": "Agua Corriente",
            "descripcion": "servicio basico",
            "estado_servicio": "ACTIVO",
        },
    )

    assert response.status_code == 201
    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_servicio"], int)
    assert body["data"]["uid_global"]
    assert body["data"]["version_registro"] == 1
    assert body["data"]["codigo_servicio"] == "SERV-001"
    assert body["data"]["nombre_servicio"] == "Agua Corriente"
    assert body["data"]["estado_servicio"] == "ACTIVO"

    row = db_session.execute(
        text(
            """
            SELECT
                id_servicio,
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_servicio,
                nombre_servicio,
                descripcion,
                estado_servicio
            FROM servicio
            WHERE id_servicio = :id_servicio
            """
        ),
        {"id_servicio": body["data"]["id_servicio"]},
    ).mappings().one()

    assert row["id_servicio"] == body["data"]["id_servicio"]
    assert str(row["uid_global"]) == body["data"]["uid_global"]
    assert row["version_registro"] == 1
    assert row["created_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_alta"]) == HEADERS["X-Op-Id"]
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]
    assert row["codigo_servicio"] == "SERV-001"
    assert row["nombre_servicio"] == "Agua Corriente"
    assert row["descripcion"] == "servicio basico"
    assert row["estado_servicio"] == "ACTIVO"
