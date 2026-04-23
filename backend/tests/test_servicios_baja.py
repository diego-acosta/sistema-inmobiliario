from sqlalchemy import text

from app.infrastructure.persistence.repositories.servicio_repository import (
    ServicioRepository,
)


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_baja_servicio_actualiza_en_postgresql(client, db_session) -> None:
    create_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-BAJA-001",
            "nombre_servicio": "Agua",
            "descripcion": "alta inicial",
            "estado_servicio": "ACTIVO",
        },
    )
    assert create_response.status_code == 201
    id_servicio = create_response.json()["data"]["id_servicio"]

    response = client.patch(
        f"/api/v1/servicios/{id_servicio}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_servicio": id_servicio,
            "version_registro": 2,
            "deleted": True,
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_servicio,
                version_registro,
                deleted_at,
                updated_at,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion
            FROM servicio
            WHERE id_servicio = :id_servicio
            """
        ),
        {"id_servicio": id_servicio},
    ).mappings().one()

    assert row["id_servicio"] == id_servicio
    assert row["version_registro"] == 2
    assert row["deleted_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_baja_servicio_devuelve_404_si_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/servicios/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_servicio_devuelve_404_si_ya_esta_eliminado(client, db_session) -> None:
    create_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-BAJA-DEL-001",
            "nombre_servicio": "Gas",
            "descripcion": None,
            "estado_servicio": "ACTIVO",
        },
    )
    id_servicio = create_response.json()["data"]["id_servicio"]

    db_session.execute(
        text(
            """
            UPDATE servicio
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_servicio = :id_servicio
            """
        ),
        {"id_servicio": id_servicio},
    )

    response = client.patch(
        f"/api/v1/servicios/{id_servicio}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = ServicioRepository(db_session)
    assert repository.get_servicio(id_servicio) is None


def test_baja_servicio_devuelve_409_si_falta_if_match_version(client) -> None:
    create_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-BAJA-NOVERSION-001",
            "nombre_servicio": "Internet",
            "descripcion": None,
            "estado_servicio": "ACTIVO",
        },
    )
    id_servicio = create_response.json()["data"]["id_servicio"]

    response = client.patch(
        f"/api/v1/servicios/{id_servicio}/baja",
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_servicio_devuelve_409_si_if_match_version_es_invalido(client) -> None:
    create_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-BAJA-BADVERSION-001",
            "nombre_servicio": "Luz",
            "descripcion": None,
            "estado_servicio": "ACTIVO",
        },
    )
    id_servicio = create_response.json()["data"]["id_servicio"]

    response = client.patch(
        f"/api/v1/servicios/{id_servicio}/baja",
        headers={**HEADERS, "If-Match-Version": "abc"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_servicio_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    create_response = client.post(
        "/api/v1/servicios",
        headers=HEADERS,
        json={
            "codigo_servicio": "SERV-BAJA-RACE-001",
            "nombre_servicio": "Race Condition",
            "descripcion": None,
            "estado_servicio": "ACTIVO",
        },
    )
    id_servicio = create_response.json()["data"]["id_servicio"]

    original_get = ServicioRepository.get_servicio_for_update
    db_session.execute(
        text(
            """
            UPDATE servicio
            SET version_registro = 2
            WHERE id_servicio = :id_servicio
            """
        ),
        {"id_servicio": id_servicio},
    )

    def stale_get(self, servicio_id: int):
        data = original_get(self, servicio_id)
        if data is None:
            return None
        return {
            **data,
            "version_registro": 1,
        }

    monkeypatch.setattr(
        ServicioRepository,
        "get_servicio_for_update",
        stale_get,
    )

    response = client.patch(
        f"/api/v1/servicios/{id_servicio}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
