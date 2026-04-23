from sqlalchemy import text


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_get_persona_devuelve_persona_y_subrecursos(client, db_session) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Juan",
            "apellido": "Perez",
            "razon_social": None,
            "fecha_nacimiento": "1985-04-12",
            "estado_persona": "ACTIVA",
            "observaciones": "Alta inicial",
        },
    )

    assert persona_response.status_code == 201
    id_persona = persona_response.json()["data"]["id_persona"]

    documento_response = client.post(
        f"/api/v1/personas/{id_persona}/documentos",
        headers=HEADERS,
        json={
            "tipo_documento": "DNI",
            "numero_documento": f"{id_persona:08d}",
            "pais_emision": "Argentina",
            "es_principal": True,
            "fecha_desde": "2020-01-01",
            "fecha_hasta": None,
            "observaciones": "documento principal",
        },
    )
    assert documento_response.status_code == 201
    id_persona_documento = documento_response.json()["data"]["id_persona_documento"]

    domicilio_response = client.post(
        f"/api/v1/personas/{id_persona}/domicilios",
        headers=HEADERS,
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle 123",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": "domicilio principal",
        },
    )
    assert domicilio_response.status_code == 201
    id_persona_domicilio = domicilio_response.json()["data"]["id_persona_domicilio"]

    contacto_response = client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "juan@mail.com",
            "es_principal": True,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": "contacto principal",
        },
    )
    assert contacto_response.status_code == 201
    id_persona_contacto = contacto_response.json()["data"]["id_persona_contacto"]

    persona_relacionada_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Maria",
            "apellido": "Gomez",
            "razon_social": None,
            "fecha_nacimiento": "1988-01-01",
            "estado_persona": "ACTIVA",
            "observaciones": "persona relacionada",
        },
    )
    assert persona_relacionada_response.status_code == 201
    id_persona_relacionada = persona_relacionada_response.json()["data"]["id_persona"]

    relacion_response = client.post(
        f"/api/v1/personas/{id_persona}/relaciones",
        headers=HEADERS,
        json={
            "id_persona_destino": id_persona_relacionada,
            "tipo_relacion": "FAMILIAR",
            "fecha_desde": "2024-01-01T00:00:00",
            "fecha_hasta": None,
            "observaciones": "relacion principal",
        },
    )
    assert relacion_response.status_code == 201
    id_persona_relacion = relacion_response.json()["data"]["id_persona_relacion"]

    persona_representante_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Carlos",
            "apellido": "Lopez",
            "razon_social": None,
            "fecha_nacimiento": "1970-06-15",
            "estado_persona": "ACTIVA",
            "observaciones": "persona representante",
        },
    )
    assert persona_representante_response.status_code == 201
    id_persona_representante = persona_representante_response.json()["data"][
        "id_persona"
    ]

    representacion_response = client.post(
        f"/api/v1/personas/{id_persona}/representaciones-poder",
        headers=HEADERS,
        json={
            "id_persona_representante": id_persona_representante,
            "tipo_poder": "GENERAL",
            "estado_representacion": "ACTIVA",
            "fecha_desde": "2024-01-01T00:00:00",
            "fecha_hasta": None,
            "descripcion": "representacion principal",
        },
    )
    assert representacion_response.status_code == 201
    id_representacion_poder = representacion_response.json()["data"][
        "id_representacion_poder"
    ]

    db_session.execute(
        text(
            """
            UPDATE persona_documento
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_persona = :id_persona
              AND id_persona_documento <> :id_persona_documento
            """
        ),
        {
            "id_persona": id_persona,
            "id_persona_documento": id_persona_documento,
        },
    )
    db_session.execute(
        text(
            """
            UPDATE persona_domicilio
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_persona = :id_persona
              AND id_persona_domicilio <> :id_persona_domicilio
            """
        ),
        {
            "id_persona": id_persona,
            "id_persona_domicilio": id_persona_domicilio,
        },
    )
    db_session.execute(
        text(
            """
            UPDATE persona_contacto
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_persona = :id_persona
              AND id_persona_contacto <> :id_persona_contacto
            """
        ),
        {
            "id_persona": id_persona,
            "id_persona_contacto": id_persona_contacto,
        },
    )
    db_session.execute(
        text(
            """
            UPDATE persona_relacion
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_persona_origen = :id_persona
              AND id_persona_relacion <> :id_persona_relacion
            """
        ),
        {
            "id_persona": id_persona,
            "id_persona_relacion": id_persona_relacion,
        },
    )
    db_session.execute(
        text(
            """
            UPDATE representacion_poder
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_persona_representado = :id_persona
              AND id_representacion_poder <> :id_representacion_poder
            """
        ),
        {
            "id_persona": id_persona,
            "id_representacion_poder": id_representacion_poder,
        },
    )

    response = client.get(f"/api/v1/personas/{id_persona}")

    assert response.status_code == 200

    body = response.json()

    assert body["ok"] is True
    assert body["data"] == {
        "id_persona": id_persona,
        "tipo_persona": "FISICA",
        "nombre": "Juan",
        "apellido": "Perez",
        "razon_social": None,
        "fecha_nacimiento": "1985-04-12",
        "estado_persona": "ACTIVA",
        "observaciones": "Alta inicial",
        "documentos": [
            {
                "id_persona_documento": id_persona_documento,
                "tipo_documento": "DNI",
                "numero_documento": f"{id_persona:08d}",
                "pais_emision": "Argentina",
                "es_principal": True,
            }
        ],
        "domicilios": [
            {
                "id_persona_domicilio": id_persona_domicilio,
                "tipo_domicilio": "REAL",
                "direccion": "Calle 123",
                "localidad": "Neuquen",
                "provincia": "Neuquen",
                "pais": "Argentina",
                "codigo_postal": "8300",
                "es_principal": True,
            }
        ],
        "contactos": [
            {
                "id_persona_contacto": id_persona_contacto,
                "tipo_contacto": "EMAIL",
                "valor_contacto": "juan@mail.com",
                "es_principal": True,
            }
        ],
        "relaciones": [
            {
                "id_persona_relacion": id_persona_relacion,
                "id_persona_origen": id_persona,
                "id_persona_destino": id_persona_relacionada,
                "tipo_relacion": "FAMILIAR",
                "fecha_desde": "2024-01-01T00:00:00",
                "fecha_hasta": None,
            }
        ],
        "representaciones_poder": [
            {
                "id_representacion_poder": id_representacion_poder,
                "id_persona_representado": id_persona,
                "id_persona_representante": id_persona_representante,
                "tipo_poder": "GENERAL",
                "estado_representacion": "ACTIVA",
                "fecha_desde": "2024-01-01T00:00:00",
                "fecha_hasta": None,
            }
        ],
    }


def test_get_persona_inexistente_devuelve_404(client) -> None:
    response = client.get("/api/v1/personas/999999")

    assert response.status_code == 404
    assert response.json() == {
        "ok": False,
        "error_code": "NOT_FOUND",
        "error_message": "La persona indicada no existe.",
        "details": {"errors": ["NOT_FOUND"]},
    }
