from sqlalchemy import text

from app.infrastructure.persistence.repositories.persona_repository import PersonaRepository


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_baja_persona_contacto_actualiza_en_postgresql(client, db_session) -> None:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Marie",
            "apellido": "Curie",
            "razon_social": None,
            "fecha_nacimiento": "1867-11-07",
            "estado_persona": "ACTIVA",
            "observaciones": "persona creada para test baja contacto",
        },
    )
    assert persona_response.status_code == 201
    id_persona = persona_response.json()["data"]["id_persona"]

    contacto_response = client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "marie@mail.com",
            "es_principal": True,
            "fecha_desde": "2024-01-01",
            "fecha_hasta": None,
            "observaciones": "contacto inicial",
        },
    )
    assert contacto_response.status_code == 201
    id_persona_contacto = contacto_response.json()["data"]["id_persona_contacto"]

    response = client.patch(
        f"/api/v1/personas/{id_persona}/contactos/{id_persona_contacto}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 200

    body = response.json()

    assert body["ok"] is True
    assert body["data"] == {
        "id_persona_contacto": id_persona_contacto,
        "id_persona": id_persona,
        "version_registro": 2,
        "deleted": True,
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_persona_contacto,
                id_persona,
                version_registro,
                deleted_at,
                updated_at,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion
            FROM persona_contacto
            WHERE id_persona_contacto = :id_persona_contacto
            """
        ),
        {"id_persona_contacto": id_persona_contacto},
    ).mappings().one()

    assert row["id_persona_contacto"] == id_persona_contacto
    assert row["id_persona"] == id_persona
    assert row["version_registro"] == 2
    assert row["deleted_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_baja_persona_contacto_devuelve_404_si_persona_inexistente(client) -> None:
    response = client.patch(
        "/api/v1/personas/999999/contactos/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_persona_contacto_devuelve_404_si_persona_esta_soft_deleted(
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

    contacto_response = client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "barbara@mail.com",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    id_persona_contacto = contacto_response.json()["data"]["id_persona_contacto"]

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

    response = client.patch(
        f"/api/v1/personas/{id_persona}/contactos/{id_persona_contacto}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = PersonaRepository(db_session)
    assert repository.persona_exists(id_persona) is False


def test_baja_persona_contacto_devuelve_404_si_contacto_inexistente(client) -> None:
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

    response = client.patch(
        f"/api/v1/personas/{id_persona}/contactos/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_persona_contacto_devuelve_404_si_contacto_ya_esta_eliminado(
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

    contacto_response = client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "donald@mail.com",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    id_persona_contacto = contacto_response.json()["data"]["id_persona_contacto"]

    db_session.execute(
        text(
            """
            UPDATE persona_contacto
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_persona_contacto = :id_persona_contacto
            """
        ),
        {"id_persona_contacto": id_persona_contacto},
    )

    response = client.patch(
        f"/api/v1/personas/{id_persona}/contactos/{id_persona_contacto}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_persona_contacto_devuelve_404_si_contacto_no_pertenece_a_persona(
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

    contacto = client.post(
        f"/api/v1/personas/{persona_1}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "alan@mail.com",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    ).json()["data"]["id_persona_contacto"]

    response = client.patch(
        f"/api/v1/personas/{persona_2}/contactos/{contacto}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_persona_contacto_devuelve_409_si_falta_if_match_version(client) -> None:
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

    contacto_response = client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "hedy@mail.com",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    id_persona_contacto = contacto_response.json()["data"]["id_persona_contacto"]

    response = client.patch(
        f"/api/v1/personas/{id_persona}/contactos/{id_persona_contacto}/baja",
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_persona_contacto_devuelve_409_si_if_match_version_es_invalido(
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

    contacto_response = client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "grace@mail.com",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    id_persona_contacto = contacto_response.json()["data"]["id_persona_contacto"]

    response = client.patch(
        f"/api/v1/personas/{id_persona}/contactos/{id_persona_contacto}/baja",
        headers={**HEADERS, "If-Match-Version": "abc"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_persona_contacto_devuelve_409_si_update_no_afecta_filas_por_version(
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

    contacto_response = client.post(
        f"/api/v1/personas/{id_persona}/contactos",
        headers=HEADERS,
        json={
            "tipo_contacto": "EMAIL",
            "valor_contacto": "edsger@mail.com",
            "es_principal": True,
            "fecha_desde": None,
            "fecha_hasta": None,
            "observaciones": None,
        },
    )
    id_persona_contacto = contacto_response.json()["data"]["id_persona_contacto"]

    original_get = PersonaRepository.get_persona_contacto_for_update
    db_session.execute(
        text(
            """
            UPDATE persona_contacto
            SET version_registro = 2
            WHERE id_persona_contacto = :id_persona_contacto
            """
        ),
        {"id_persona_contacto": id_persona_contacto},
    )

    def stale_get(self, contacto_id: int):
        data = original_get(self, contacto_id)
        if data is None:
            return None
        return {
            **data,
            "version_registro": 1,
        }

    monkeypatch.setattr(
        PersonaRepository,
        "get_persona_contacto_for_update",
        stale_get,
    )

    response = client.patch(
        f"/api/v1/personas/{id_persona}/contactos/{id_persona_contacto}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
