from sqlalchemy import text

from app.infrastructure.persistence.repositories.persona_repository import PersonaRepository


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_update_persona_domicilio_actualiza_en_postgresql(client, db_session) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Nikola",
            "apellido": "Tesla",
            "razon_social": None,
            "fecha_nacimiento": "1856-07-10",
            "estado_persona": "ACTIVA",
            "observaciones": "persona creada para test update domicilio",
        },
    )
    assert persona_response.status_code == 201
    id_persona = persona_response.json()["data"]["id_persona"]

    domicilio_response = client.post(
        f"/api/v1/personas/{id_persona}/domicilios",
        headers=HEADERS,
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle Vieja 123",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": False,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": "domicilio inicial",
        },
    )
    assert domicilio_response.status_code == 201
    domicilio_data = domicilio_response.json()["data"]
    id_persona_domicilio = domicilio_data["id_persona_domicilio"]

    response = client.put(
        f"/api/v1/personas/{id_persona}/domicilios/{id_persona_domicilio}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle Nueva 456",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": "2024-02-01",
            "fecha_hasta": None,
            "observaciones": "domicilio actualizado",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["ok"] is True
    assert body["data"] == {
        "id_persona_domicilio": id_persona_domicilio,
        "id_persona": id_persona,
        "version_registro": 2,
        "tipo_domicilio": "REAL",
        "direccion": "Calle Nueva 456",
        "localidad": "Neuquen",
        "provincia": "Neuquen",
        "pais": "Argentina",
        "codigo_postal": "8300",
        "es_principal": True,
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_persona_domicilio,
                id_persona,
                version_registro,
                tipo_domicilio,
                direccion,
                localidad,
                provincia,
                pais,
                codigo_postal,
                es_principal,
                observaciones,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion,
                updated_at
            FROM persona_domicilio
            WHERE id_persona_domicilio = :id_persona_domicilio
            """
        ),
        {"id_persona_domicilio": id_persona_domicilio},
    ).mappings().one()

    assert row["id_persona_domicilio"] == id_persona_domicilio
    assert row["id_persona"] == id_persona
    assert row["version_registro"] == 2
    assert row["tipo_domicilio"] == "REAL"
    assert row["direccion"] == "Calle Nueva 456"
    assert row["localidad"] == "Neuquen"
    assert row["provincia"] == "Neuquen"
    assert row["pais"] == "Argentina"
    assert row["codigo_postal"] == "8300"
    assert row["es_principal"] is True
    assert row["observaciones"] == "domicilio actualizado"
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]
    assert row["updated_at"] is not None


def test_update_persona_domicilio_devuelve_404_si_persona_inexistente(client) -> None:
    response = client.put(
        "/api/v1/personas/999999/domicilios/999999",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle Nueva 456",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_persona_domicilio_devuelve_404_si_persona_esta_soft_deleted(
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

    domicilio_response = client.post(
        f"/api/v1/personas/{id_persona}/domicilios",
        headers=HEADERS,
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Siempre Viva 742",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    id_persona_domicilio = domicilio_response.json()["data"]["id_persona_domicilio"]

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

    response = client.put(
        f"/api/v1/personas/{id_persona}/domicilios/{id_persona_domicilio}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle Nueva 456",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = PersonaRepository(db_session)
    assert repository.persona_exists(id_persona) is False


def test_update_persona_domicilio_devuelve_404_si_domicilio_inexistente(client) -> None:
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

    response = client.put(
        f"/api/v1/personas/{id_persona}/domicilios/999999",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle Nueva 456",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_persona_domicilio_devuelve_404_si_domicilio_esta_soft_deleted(
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
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    id_persona_domicilio = domicilio_response.json()["data"]["id_persona_domicilio"]

    db_session.execute(
        text(
            """
            UPDATE persona_domicilio
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_persona_domicilio = :id_persona_domicilio
            """
        ),
        {"id_persona_domicilio": id_persona_domicilio},
    )

    response = client.put(
        f"/api/v1/personas/{id_persona}/domicilios/{id_persona_domicilio}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle Nueva 456",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_persona_domicilio_devuelve_404_si_domicilio_no_pertenece_a_persona(
    client,
) -> None:
    persona_1 = client.post(
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
    ).json()["data"]["id_persona"]

    persona_2 = client.post(
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
    ).json()["data"]["id_persona"]

    domicilio = client.post(
        f"/api/v1/personas/{persona_1}/domicilios",
        headers=HEADERS,
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle 123",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    ).json()["data"]["id_persona_domicilio"]

    response = client.put(
        f"/api/v1/personas/{persona_2}/domicilios/{domicilio}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Otra Calle 999",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_persona_domicilio_devuelve_409_si_falta_if_match_version(client) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Hedy",
            "apellido": "Lamarr",
            "razon_social": None,
            "fecha_nacimiento": "1914-11-09",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]

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
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    id_persona_domicilio = domicilio_response.json()["data"]["id_persona_domicilio"]

    response = client.put(
        f"/api/v1/personas/{id_persona}/domicilios/{id_persona_domicilio}",
        headers=HEADERS,
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle Nueva 456",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_persona_domicilio_devuelve_409_si_if_match_version_es_invalido(
    client,
) -> None:
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
            "observaciones": None,
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]

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
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    id_persona_domicilio = domicilio_response.json()["data"]["id_persona_domicilio"]

    response = client.put(
        f"/api/v1/personas/{id_persona}/domicilios/{id_persona_domicilio}",
        headers={**HEADERS, "If-Match-Version": "abc"},
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle Nueva 456",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_persona_domicilio_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Edsger",
            "apellido": "Dijkstra",
            "razon_social": None,
            "fecha_nacimiento": "1930-05-11",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    id_persona = persona_response.json()["data"]["id_persona"]

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
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    id_persona_domicilio = domicilio_response.json()["data"]["id_persona_domicilio"]

    original_get = PersonaRepository.get_persona_domicilio_for_update
    db_session.execute(
        text(
            """
            UPDATE persona_domicilio
            SET version_registro = 2
            WHERE id_persona_domicilio = :id_persona_domicilio
            """
        ),
        {"id_persona_domicilio": id_persona_domicilio},
    )

    def stale_get(self, domicilio_id: int):
        data = original_get(self, domicilio_id)
        if data is None:
            return None
        return {
            **data,
            "version_registro": 1,
        }

    monkeypatch.setattr(
        PersonaRepository,
        "get_persona_domicilio_for_update",
        stale_get,
    )

    response = client.put(
        f"/api/v1/personas/{id_persona}/domicilios/{id_persona_domicilio}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "tipo_domicilio": "REAL",
            "direccion": "Calle Nueva 456",
            "localidad": "Neuquen",
            "provincia": "Neuquen",
            "pais": "Argentina",
            "codigo_postal": "8300",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
