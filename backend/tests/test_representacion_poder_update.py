from sqlalchemy import text

from app.infrastructure.persistence.repositories.persona_repository import PersonaRepository


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _crear_persona(client, nombre: str, apellido: str) -> int:
    response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": nombre,
            "apellido": apellido,
            "razon_social": None,
            "fecha_nacimiento": "1990-01-01",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_persona"]


def _crear_representacion(
    client, *, id_persona_representado: int, id_persona_representante: int
) -> int:
    response = client.post(
        f"/api/v1/personas/{id_persona_representado}/representaciones-poder",
        headers=HEADERS,
        json={
            "id_persona_representante": id_persona_representante,
            "tipo_poder": "GENERAL",
            "estado_representacion": "ACTIVA",
            "fecha_desde": "2024-01-01T00:00:00",
            "fecha_hasta": None,
            "descripcion": "representacion inicial",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_representacion_poder"]


def test_update_representacion_poder_actualiza_en_postgresql(client, db_session) -> None:
    id_persona_representado = _crear_persona(client, "Marie", "Curie")
    id_persona_representante = _crear_persona(client, "Pierre", "Curie")
    id_persona_representante_nuevo = _crear_persona(client, "Irene", "Joliot-Curie")
    id_representacion_poder = _crear_representacion(
        client,
        id_persona_representado=id_persona_representado,
        id_persona_representante=id_persona_representante,
    )

    response = client.put(
        f"/api/v1/personas/{id_persona_representado}/representaciones-poder/{id_representacion_poder}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_persona_representante": id_persona_representante_nuevo,
            "tipo_poder": "ESPECIAL",
            "estado_representacion": "REVOCADA",
            "fecha_desde": "2024-02-01T10:30:00",
            "fecha_hasta": None,
            "descripcion": "representacion actualizada",
        },
    )

    assert response.status_code == 200

    body = response.json()
    assert body["ok"] is True
    assert body["data"] == {
        "id_representacion_poder": id_representacion_poder,
        "id_persona_representado": id_persona_representado,
        "id_persona_representante": id_persona_representante_nuevo,
        "version_registro": 2,
        "tipo_poder": "ESPECIAL",
        "estado_representacion": "REVOCADA",
        "fecha_desde": "2024-02-01T10:30:00",
        "fecha_hasta": None,
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_representacion_poder,
                id_persona_representado,
                id_persona_representante,
                version_registro,
                tipo_poder,
                estado_representacion,
                descripcion,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion,
                updated_at
            FROM representacion_poder
            WHERE id_representacion_poder = :id_representacion_poder
            """
        ),
        {"id_representacion_poder": id_representacion_poder},
    ).mappings().one()

    assert row["id_representacion_poder"] == id_representacion_poder
    assert row["id_persona_representado"] == id_persona_representado
    assert row["id_persona_representante"] == id_persona_representante_nuevo
    assert row["version_registro"] == 2
    assert row["tipo_poder"] == "ESPECIAL"
    assert row["estado_representacion"] == "REVOCADA"
    assert row["descripcion"] == "representacion actualizada"
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]
    assert row["updated_at"] is not None


def test_update_representacion_poder_devuelve_409_si_falta_if_match_version(client) -> None:
    id_persona_representado = _crear_persona(client, "Ada", "Lovelace")
    id_persona_representante = _crear_persona(client, "Charles", "Babbage")
    id_representacion_poder = _crear_representacion(
        client,
        id_persona_representado=id_persona_representado,
        id_persona_representante=id_persona_representante,
    )

    response = client.put(
        f"/api/v1/personas/{id_persona_representado}/representaciones-poder/{id_representacion_poder}",
        headers=HEADERS,
        json={
            "id_persona_representante": id_persona_representante,
            "tipo_poder": "GENERAL",
            "estado_representacion": "ACTIVA",
            "fecha_desde": None,
            "fecha_hasta": None,
            "descripcion": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_representacion_poder_devuelve_404_si_no_pertenece_a_persona(
    client,
) -> None:
    persona_1 = _crear_persona(client, "Alan", "Turing")
    persona_2 = _crear_persona(client, "Katherine", "Johnson")
    persona_3 = _crear_persona(client, "Joan", "Clarke")
    representacion = _crear_representacion(
        client,
        id_persona_representado=persona_1,
        id_persona_representante=persona_2,
    )

    response = client.put(
        f"/api/v1/personas/{persona_3}/representaciones-poder/{representacion}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_persona_representante": persona_2,
            "tipo_poder": "GENERAL",
            "estado_representacion": "ACTIVA",
            "fecha_desde": None,
            "fecha_hasta": None,
            "descripcion": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_representacion_poder_devuelve_404_si_esta_soft_deleted(
    client, db_session
) -> None:
    id_persona_representado = _crear_persona(client, "Donald", "Knuth")
    id_persona_representante = _crear_persona(client, "Leslie", "Lamport")
    id_representacion_poder = _crear_representacion(
        client,
        id_persona_representado=id_persona_representado,
        id_persona_representante=id_persona_representante,
    )

    db_session.execute(
        text(
            """
            UPDATE representacion_poder
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_representacion_poder = :id_representacion_poder
            """
        ),
        {"id_representacion_poder": id_representacion_poder},
    )

    response = client.put(
        f"/api/v1/personas/{id_persona_representado}/representaciones-poder/{id_representacion_poder}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_persona_representante": id_persona_representante,
            "tipo_poder": "GENERAL",
            "estado_representacion": "ACTIVA",
            "fecha_desde": None,
            "fecha_hasta": None,
            "descripcion": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_representacion_poder_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    id_persona_representado = _crear_persona(client, "Edsger", "Dijkstra")
    id_persona_representante = _crear_persona(client, "Niklaus", "Wirth")
    id_representacion_poder = _crear_representacion(
        client,
        id_persona_representado=id_persona_representado,
        id_persona_representante=id_persona_representante,
    )

    original_get = PersonaRepository.get_representacion_poder_for_update
    db_session.execute(
        text(
            """
            UPDATE representacion_poder
            SET version_registro = 2
            WHERE id_representacion_poder = :id_representacion_poder
            """
        ),
        {"id_representacion_poder": id_representacion_poder},
    )

    def stale_get(self, representacion_id: int):
        data = original_get(self, representacion_id)
        if data is None:
            return None
        return {
            **data,
            "version_registro": 1,
        }

    monkeypatch.setattr(
        PersonaRepository,
        "get_representacion_poder_for_update",
        stale_get,
    )

    response = client.put(
        f"/api/v1/personas/{id_persona_representado}/representaciones-poder/{id_representacion_poder}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_persona_representante": id_persona_representante,
            "tipo_poder": "GENERAL",
            "estado_representacion": "ACTIVA",
            "fecha_desde": None,
            "fecha_hasta": None,
            "descripcion": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
