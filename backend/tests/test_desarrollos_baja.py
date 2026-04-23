from sqlalchemy import text

from app.infrastructure.persistence.repositories.desarrollo_repository import (
    DesarrolloRepository,
)


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_baja_desarrollo_actualiza_en_postgresql(client, db_session) -> None:
    create_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-BAJA-001",
            "nombre_desarrollo": "Desarrollo Baja",
            "descripcion": "para baja",
            "estado_desarrollo": "ACTIVO",
            "observaciones": "alta inicial",
        },
    )
    assert create_response.status_code == 201
    id_desarrollo = create_response.json()["data"]["id_desarrollo"]

    response = client.patch(
        f"/api/v1/desarrollos/{id_desarrollo}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_desarrollo": id_desarrollo,
            "version_registro": 2,
            "deleted": True,
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_desarrollo,
                version_registro,
                deleted_at,
                updated_at,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion
            FROM desarrollo
            WHERE id_desarrollo = :id_desarrollo
            """
        ),
        {"id_desarrollo": id_desarrollo},
    ).mappings().one()

    assert row["id_desarrollo"] == id_desarrollo
    assert row["version_registro"] == 2
    assert row["deleted_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_baja_desarrollo_devuelve_404_si_desarrollo_inexistente(client) -> None:
    response = client.patch(
        "/api/v1/desarrollos/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_desarrollo_devuelve_404_si_desarrollo_ya_esta_eliminado(
    client, db_session
) -> None:
    create_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-BAJA-DEL-001",
            "nombre_desarrollo": "Ya Eliminado",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    id_desarrollo = create_response.json()["data"]["id_desarrollo"]

    db_session.execute(
        text(
            """
            UPDATE desarrollo
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_desarrollo = :id_desarrollo
            """
        ),
        {"id_desarrollo": id_desarrollo},
    )

    response = client.patch(
        f"/api/v1/desarrollos/{id_desarrollo}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = DesarrolloRepository(db_session)
    assert repository.get_desarrollo(id_desarrollo) is None


def test_baja_desarrollo_devuelve_409_si_falta_if_match_version(client) -> None:
    create_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-BAJA-NOVERSION-001",
            "nombre_desarrollo": "Sin Version",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    id_desarrollo = create_response.json()["data"]["id_desarrollo"]

    response = client.patch(
        f"/api/v1/desarrollos/{id_desarrollo}/baja",
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_desarrollo_devuelve_409_si_if_match_version_es_invalido(client) -> None:
    create_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-BAJA-BADVERSION-001",
            "nombre_desarrollo": "Version Invalida",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    id_desarrollo = create_response.json()["data"]["id_desarrollo"]

    response = client.patch(
        f"/api/v1/desarrollos/{id_desarrollo}/baja",
        headers={**HEADERS, "If-Match-Version": "abc"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_desarrollo_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    create_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-BAJA-RACE-001",
            "nombre_desarrollo": "Race Condition",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    id_desarrollo = create_response.json()["data"]["id_desarrollo"]

    original_get = DesarrolloRepository.get_desarrollo_for_update
    db_session.execute(
        text(
            """
            UPDATE desarrollo
            SET version_registro = 2
            WHERE id_desarrollo = :id_desarrollo
            """
        ),
        {"id_desarrollo": id_desarrollo},
    )

    def stale_get(self, desarrollo_id: int):
        data = original_get(self, desarrollo_id)
        if data is None:
            return None
        return {
            **data,
            "version_registro": 1,
        }

    monkeypatch.setattr(
        DesarrolloRepository,
        "get_desarrollo_for_update",
        stale_get,
    )

    response = client.patch(
        f"/api/v1/desarrollos/{id_desarrollo}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
