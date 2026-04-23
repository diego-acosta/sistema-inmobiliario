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


def test_asociar_desarrollo_actualiza_en_postgresql(client, db_session) -> None:
    desarrollo_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-ASOC-001",
            "nombre_desarrollo": "Desarrollo Asociado",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    assert desarrollo_response.status_code == 201
    id_desarrollo = desarrollo_response.json()["data"]["id_desarrollo"]

    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-ASOC-001",
            "nombre_inmueble": "Unidad Asociable",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.patch(
        f"/api/v1/inmuebles/{id_inmueble}/asociar-desarrollo",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={"id_desarrollo": id_desarrollo},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_inmueble": id_inmueble,
            "id_desarrollo": id_desarrollo,
            "version_registro": 2,
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_inmueble,
                id_desarrollo,
                version_registro,
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
    assert row["id_desarrollo"] == id_desarrollo
    assert row["version_registro"] == 2
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_asociar_desarrollo_devuelve_404_si_inmueble_inexistente(client) -> None:
    desarrollo_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-ASOC-404-001",
            "nombre_desarrollo": "Desarrollo 404",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    id_desarrollo = desarrollo_response.json()["data"]["id_desarrollo"]

    response = client.patch(
        "/api/v1/inmuebles/999999/asociar-desarrollo",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={"id_desarrollo": id_desarrollo},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_asociar_desarrollo_devuelve_404_si_inmueble_esta_soft_deleted(
    client, db_session
) -> None:
    desarrollo_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-ASOC-DEL-001",
            "nombre_desarrollo": "Desarrollo Soft Delete",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    id_desarrollo = desarrollo_response.json()["data"]["id_desarrollo"]

    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-ASOC-DEL-001",
            "nombre_inmueble": "Soft Deleted",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

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
        f"/api/v1/inmuebles/{id_inmueble}/asociar-desarrollo",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={"id_desarrollo": id_desarrollo},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = InmuebleRepository(db_session)
    assert repository.get_inmueble_for_update(id_inmueble) is None


def test_asociar_desarrollo_devuelve_404_si_desarrollo_no_existe(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-ASOC-NODEV-001",
            "nombre_inmueble": "Sin Desarrollo",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.patch(
        f"/api/v1/inmuebles/{id_inmueble}/asociar-desarrollo",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={"id_desarrollo": 999999},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_asociar_desarrollo_devuelve_409_si_falta_if_match_version(client) -> None:
    desarrollo_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-ASOC-NOVERSION-001",
            "nombre_desarrollo": "Desarrollo Sin Version",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    id_desarrollo = desarrollo_response.json()["data"]["id_desarrollo"]

    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-ASOC-NOVERSION-001",
            "nombre_inmueble": "Sin Version",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.patch(
        f"/api/v1/inmuebles/{id_inmueble}/asociar-desarrollo",
        headers=HEADERS,
        json={"id_desarrollo": id_desarrollo},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_asociar_desarrollo_devuelve_409_si_if_match_version_es_invalido(client) -> None:
    desarrollo_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-ASOC-BADVERSION-001",
            "nombre_desarrollo": "Desarrollo Version Invalida",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    id_desarrollo = desarrollo_response.json()["data"]["id_desarrollo"]

    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-ASOC-BADVERSION-001",
            "nombre_inmueble": "Version Invalida",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    response = client.patch(
        f"/api/v1/inmuebles/{id_inmueble}/asociar-desarrollo",
        headers={**HEADERS, "If-Match-Version": "abc"},
        json={"id_desarrollo": id_desarrollo},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_asociar_desarrollo_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    desarrollo_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-ASOC-RACE-001",
            "nombre_desarrollo": "Desarrollo Race",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    id_desarrollo = desarrollo_response.json()["data"]["id_desarrollo"]

    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-ASOC-RACE-001",
            "nombre_inmueble": "Race Condition",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

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
        f"/api/v1/inmuebles/{id_inmueble}/asociar-desarrollo",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={"id_desarrollo": id_desarrollo},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
