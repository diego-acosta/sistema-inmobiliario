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


def test_update_inmueble_actualiza_en_postgresql(client, db_session) -> None:
    desarrollo_response = client.post(
        "/api/v1/desarrollos",
        headers=HEADERS,
        json={
            "codigo_desarrollo": "DESA-INM-UPD-001",
            "nombre_desarrollo": "Desarrollo Inicial",
            "descripcion": None,
            "estado_desarrollo": "ACTIVO",
            "observaciones": None,
        },
    )
    assert desarrollo_response.status_code == 201
    id_desarrollo = desarrollo_response.json()["data"]["id_desarrollo"]

    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UPD-001",
            "nombre_inmueble": "Unidad Inicial",
            "superficie": "60.00",
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": "inicial",
        },
    )
    assert create_response.status_code == 201
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    response = client.put(
        f"/api/v1/inmuebles/{id_inmueble}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_desarrollo": id_desarrollo,
            "codigo_inmueble": "INM-UPD-999",
            "nombre_inmueble": "Unidad Actualizada",
            "superficie": "88.40",
            "estado_administrativo": "INACTIVO",
            "estado_juridico": "OBSERVADO",
            "observaciones": "actualizado",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_inmueble": id_inmueble,
            "version_registro": 2,
            "id_desarrollo": id_desarrollo,
            "codigo_inmueble": "INM-UPD-999",
            "nombre_inmueble": "Unidad Actualizada",
            "superficie": "88.40",
            "estado_administrativo": "INACTIVO",
            "estado_juridico": "OBSERVADO",
            "observaciones": "actualizado",
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_inmueble,
                version_registro,
                id_desarrollo,
                codigo_inmueble,
                nombre_inmueble,
                superficie,
                estado_administrativo,
                estado_juridico,
                observaciones,
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
    assert row["id_desarrollo"] == id_desarrollo
    assert row["codigo_inmueble"] == "INM-UPD-999"
    assert row["nombre_inmueble"] == "Unidad Actualizada"
    assert str(row["superficie"]) == "88.40"
    assert row["estado_administrativo"] == "INACTIVO"
    assert row["estado_juridico"] == "OBSERVADO"
    assert row["observaciones"] == "actualizado"
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_update_inmueble_devuelve_404_si_inmueble_inexistente(client) -> None:
    response = client.put(
        "/api/v1/inmuebles/999999",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-NOPE-001",
            "nombre_inmueble": "No Existe",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_inmueble_devuelve_404_si_inmueble_esta_soft_deleted(
    client, db_session
) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DEL-UPD-001",
            "nombre_inmueble": "Soft Deleted",
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

    response = client.put(
        f"/api/v1/inmuebles/{id_inmueble}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-DEL-UPD-001",
            "nombre_inmueble": "Soft Deleted",
            "superficie": None,
            "estado_administrativo": "INACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = InmuebleRepository(db_session)
    assert repository.get_inmueble_for_update(id_inmueble) is None


def test_update_inmueble_devuelve_404_si_desarrollo_no_existe(client) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-NODEV-001",
            "nombre_inmueble": "Sin Desarrollo",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    response = client.put(
        f"/api/v1/inmuebles/{id_inmueble}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_desarrollo": 999999,
            "codigo_inmueble": "INM-NODEV-001",
            "nombre_inmueble": "Sin Desarrollo",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_inmueble_devuelve_409_si_falta_if_match_version(client) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-NOVERSION-001",
            "nombre_inmueble": "Sin Version",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    response = client.put(
        f"/api/v1/inmuebles/{id_inmueble}",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-NOVERSION-001",
            "nombre_inmueble": "Sin Version",
            "superficie": None,
            "estado_administrativo": "INACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_inmueble_devuelve_409_si_if_match_version_es_invalido(client) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-BADVERSION-001",
            "nombre_inmueble": "Version Invalida",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = create_response.json()["data"]["id_inmueble"]

    response = client.put(
        f"/api/v1/inmuebles/{id_inmueble}",
        headers={**HEADERS, "If-Match-Version": "abc"},
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-BADVERSION-001",
            "nombre_inmueble": "Version Invalida",
            "superficie": None,
            "estado_administrativo": "INACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_inmueble_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    create_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-RACE-001",
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

    response = client.put(
        f"/api/v1/inmuebles/{id_inmueble}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-RACE-001",
            "nombre_inmueble": "Race Condition",
            "superficie": None,
            "estado_administrativo": "INACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
