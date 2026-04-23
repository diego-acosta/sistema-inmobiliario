from sqlalchemy import text

from app.infrastructure.persistence.repositories.inmueble_repository import (
    InmuebleRepository,
)


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_baja_inmueble_actualiza_en_postgresql(client, db_session) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-BAJA-001",
            "nombre_inmueble": "Inmueble Baja",
            "superficie": "45.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": "alta inicial",
        },
    )
    assert create_response.status_code == 201
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    response = client.patch(
        f"/api/v1/inmuebles/{id_inmueble}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_inmueble": id_inmueble,
            "version_registro": 2,
            "deleted": True,
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_inmueble,
                version_registro,
                deleted_at,
                updated_at,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion
            FROM inmueble
            WHERE id_inmueble = :id_inmueble
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().one()

    assert row["id_inmueble"] == id_inmueble
    assert row["version_registro"] == 2
    assert row["deleted_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_baja_inmueble_devuelve_404_si_inmueble_inexistente(client) -> None:
    response = client.patch(
        "/api/v1/inmuebles/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_inmueble_devuelve_404_si_inmueble_ya_esta_eliminado(
    client, db_session
) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-BAJA-DEL-001",
            "nombre_inmueble": "Ya Eliminado",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    db_session.execute(
        text(
            """
            UPDATE inmueble
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_inmueble = :id_inmueble
            """
        ),
        {"id_inmueble": id_inmueble},
    )

    response = client.patch(
        f"/api/v1/inmuebles/{id_inmueble}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = InmuebleRepository(db_session)
    assert repository.get_inmueble(id_inmueble) is None


def test_baja_inmueble_devuelve_409_si_falta_if_match_version(client) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-BAJA-NOVERSION-001",
            "nombre_inmueble": "Sin Version",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    response = client.patch(
        f"/api/v1/inmuebles/{id_inmueble}/baja",
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_inmueble_devuelve_409_si_if_match_version_es_invalido(client) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-BAJA-BADVERSION-001",
            "nombre_inmueble": "Version Invalida",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    response = client.patch(
        f"/api/v1/inmuebles/{id_inmueble}/baja",
        headers={**HEADERS, "If-Match-Version": "abc"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_inmueble_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-BAJA-RACE-001",
            "nombre_inmueble": "Race Condition",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    original_get = InmuebleRepository.get_inmueble_for_update
    db_session.execute(
        text(
            """
            UPDATE inmueble
            SET version_registro = 2
            WHERE id_inmueble = :id_inmueble
            """
        ),
        {"id_inmueble": id_inmueble},
    )

    def stale_get(self, inmueble_id: int):
        data = original_get(self, inmueble_id)
        if data is None:
            return None
        return {
            **data,
            "version_registro": 1,
        }

    monkeypatch.setattr(
        InmuebleRepository,
        "get_inmueble_for_update",
        stale_get,
    )

    response = client.patch(
        f"/api/v1/inmuebles/{id_inmueble}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
