from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _crear_rol_participacion_activo(db_session, *, id_rol_participacion: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO rol_participacion (
                id_rol_participacion,
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_rol,
                nombre_rol,
                descripcion,
                estado_rol
            )
            VALUES (
                :id_rol_participacion,
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                :op_id,
                :op_id,
                :codigo_rol,
                :nombre_rol,
                NULL,
                'ACTIVO'
            )
            """
        ),
        {
            "id_rol_participacion": id_rol_participacion,
            "op_id": HEADERS["X-Op-Id"],
            "codigo_rol": f"ROL_{id_rol_participacion}",
            "nombre_rol": f"Rol {id_rol_participacion}",
        },
    )


def _crear_reserva_venta(db_session, *, id_reserva_venta: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO reserva_venta (
                id_reserva_venta,
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                observaciones
            )
            VALUES (
                :id_reserva_venta,
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                :op_id,
                :op_id,
                :codigo_reserva,
                DATE '2024-01-01',
                'ACTIVA',
                NULL
            )
            """
        ),
        {
            "id_reserva_venta": id_reserva_venta,
            "op_id": HEADERS["X-Op-Id"],
            "codigo_reserva": f"RES-{id_reserva_venta}",
        },
    )


def test_create_relacion_persona_rol_inserta_en_postgresql(client, db_session) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Grace",
            "apellido": "Hopper",
            "razon_social": None,
            "fecha_nacimiento": "1906-12-09",
            "estado_persona": "ACTIVA",
            "observaciones": "persona creada para test de rol",
        },
    )
    assert persona_response.status_code == 201
    id_persona = persona_response.json()["data"]["id_persona"]

    _crear_rol_participacion_activo(db_session, id_rol_participacion=1001)
    _crear_reserva_venta(db_session, id_reserva_venta=2001)

    response = client.post(
        "/api/v1/roles-participacion",
        headers=HEADERS,
        json={
            "id_persona": id_persona,
            "id_rol_participacion": 1001,
            "tipo_relacion": "reserva_venta",
            "id_relacion": 2001,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": "alta desde test",
        },
    )

    assert response.status_code == 201

    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_relacion_persona_rol"], int)
    assert body["data"] == {
        "id_relacion_persona_rol": body["data"]["id_relacion_persona_rol"],
        "id_persona": id_persona,
        "id_rol_participacion": 1001,
        "tipo_relacion": "reserva_venta",
        "id_relacion": 2001,
        "version_registro": 1,
        "fecha_desde": "2024-01-01",
        "fecha_hasta": None,
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_relacion_persona_rol,
                id_persona,
                id_rol_participacion,
                tipo_relacion,
                id_relacion,
                version_registro,
                fecha_desde,
                fecha_hasta,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion
            FROM relacion_persona_rol
            WHERE id_relacion_persona_rol = :id_relacion_persona_rol
            """
        ),
        {"id_relacion_persona_rol": body["data"]["id_relacion_persona_rol"]},
    ).mappings().one()

    assert row["id_persona"] == id_persona
    assert row["id_rol_participacion"] == 1001
    assert row["tipo_relacion"] == "reserva_venta"
    assert row["id_relacion"] == 2001
    assert row["version_registro"] == 1
    assert str(row["fecha_desde"].date()) == "2024-01-01"
    assert row["fecha_hasta"] is None
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_alta"]) == HEADERS["X-Op-Id"]
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_create_relacion_persona_rol_devuelve_404_si_persona_inexistente(
    client, db_session
) -> None:
    _crear_rol_participacion_activo(db_session, id_rol_participacion=1002)

    response = client.post(
        "/api/v1/roles-participacion",
        headers=HEADERS,
        json={
            "id_persona": 999999,
            "id_rol_participacion": 1002,
            "tipo_relacion": "reserva_venta",
            "id_relacion": 2001,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_create_relacion_persona_rol_devuelve_404_si_persona_esta_soft_deleted(
    client, db_session
) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Barbara",
            "apellido": "Liskov",
            "razon_social": None,
            "fecha_nacimiento": "1939-11-07",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]
    _crear_rol_participacion_activo(db_session, id_rol_participacion=1003)
    _crear_reserva_venta(db_session, id_reserva_venta=2003)

    db_session.execute(
        text(
            """
            UPDATE persona
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_persona = :id_persona
            """
        ),
        {"id_persona": id_persona},
    )

    response = client.post(
        "/api/v1/roles-participacion",
        headers=HEADERS,
        json={
            "id_persona": id_persona,
            "id_rol_participacion": 1003,
            "tipo_relacion": "reserva_venta",
            "id_relacion": 2003,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_create_relacion_persona_rol_devuelve_404_si_rol_inexistente(client) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Ada",
            "apellido": "Lovelace",
            "razon_social": None,
            "fecha_nacimiento": "1815-12-10",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]

    response = client.post(
        "/api/v1/roles-participacion",
        headers=HEADERS,
        json={
            "id_persona": id_persona,
            "id_rol_participacion": 999999,
            "tipo_relacion": "reserva_venta",
            "id_relacion": 2004,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_create_relacion_persona_rol_devuelve_404_si_rol_esta_soft_deleted(
    client, db_session
) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Donald",
            "apellido": "Knuth",
            "razon_social": None,
            "fecha_nacimiento": "1938-01-10",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]
    _crear_rol_participacion_activo(db_session, id_rol_participacion=1004)
    _crear_reserva_venta(db_session, id_reserva_venta=2004)

    db_session.execute(
        text(
            """
            UPDATE rol_participacion
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_rol_participacion = :id_rol_participacion
            """
        ),
        {"id_rol_participacion": 1004},
    )

    response = client.post(
        "/api/v1/roles-participacion",
        headers=HEADERS,
        json={
            "id_persona": id_persona,
            "id_rol_participacion": 1004,
            "tipo_relacion": "reserva_venta",
            "id_relacion": 2004,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_create_relacion_persona_rol_devuelve_400_si_tipo_relacion_esta_vacio(
    client, db_session
) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Alan",
            "apellido": "Turing",
            "razon_social": None,
            "fecha_nacimiento": "1912-06-23",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]
    _crear_rol_participacion_activo(db_session, id_rol_participacion=1005)
    _crear_reserva_venta(db_session, id_reserva_venta=2005)

    response = client.post(
        "/api/v1/roles-participacion",
        headers=HEADERS,
        json={
            "id_persona": id_persona,
            "id_rol_participacion": 1005,
            "tipo_relacion": "   ",
            "id_relacion": 2005,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"


def test_create_relacion_persona_rol_devuelve_400_si_id_relacion_es_invalido(
    client, db_session
) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Katherine",
            "apellido": "Johnson",
            "razon_social": None,
            "fecha_nacimiento": "1918-08-26",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]
    _crear_rol_participacion_activo(db_session, id_rol_participacion=1006)
    _crear_reserva_venta(db_session, id_reserva_venta=2006)

    response = client.post(
        "/api/v1/roles-participacion",
        headers=HEADERS,
        json={
            "id_persona": id_persona,
            "id_rol_participacion": 1006,
            "tipo_relacion": "reserva_venta",
            "id_relacion": 0,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"


def test_create_relacion_persona_rol_devuelve_400_si_faltan_headers(
    client, db_session
) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Linus",
            "apellido": "Torvalds",
            "razon_social": None,
            "fecha_nacimiento": "1969-12-28",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]
    _crear_rol_participacion_activo(db_session, id_rol_participacion=1007)
    _crear_reserva_venta(db_session, id_reserva_venta=2007)

    response = client.post(
        "/api/v1/roles-participacion",
        json={
            "id_persona": id_persona,
            "id_rol_participacion": 1007,
            "tipo_relacion": "reserva_venta",
            "id_relacion": 2007,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    assert response.json()["error_code"] == "APPLICATION_ERROR"
