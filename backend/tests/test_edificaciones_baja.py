from sqlalchemy import text

from app.infrastructure.persistence.repositories.edificacion_repository import (
    EdificacionRepository,
)


HEADERS = {
    "X-Op-Id": "550e8400-e29b-41d4-a716-446655440000",
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def test_baja_edificacion_actualiza_en_postgresql(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-BAJA-001",
            "nombre_inmueble": "Inmueble Base Edif",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "Edificacion Baja",
            "tipo_edificacion": "CASA",
            "superficie": None,
            "observaciones": "alta inicial",
        },
    )
    assert create_response.status_code == 201
    id_edificacion = create_response.json()["data"]["id_edificacion"]

    response = client.patch(
        f"/api/v1/edificaciones/{id_edificacion}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_edificacion": id_edificacion,
            "version_registro": 2,
            "deleted": True,
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_edificacion,
                version_registro,
                deleted_at,
                updated_at,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion
            FROM edificacion
            WHERE id_edificacion = :id_edificacion
            """
        ),
        {"id_edificacion": id_edificacion},
    ).mappings().one()

    assert row["id_edificacion"] == id_edificacion
    assert row["version_registro"] == 2
    assert row["deleted_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_baja_edificacion_devuelve_404_si_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/edificaciones/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_edificacion_devuelve_404_si_ya_esta_eliminada(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-BAJA-DEL-001",
            "nombre_inmueble": "Inmueble Base Edif",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "Ya Eliminada",
            "tipo_edificacion": None,
            "superficie": None,
            "observaciones": None,
        },
    )
    id_edificacion = create_response.json()["data"]["id_edificacion"]

    db_session.execute(
        text(
            """
            UPDATE edificacion
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_edificacion = :id_edificacion
            """
        ),
        {"id_edificacion": id_edificacion},
    )

    response = client.patch(
        f"/api/v1/edificaciones/{id_edificacion}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = EdificacionRepository(db_session)
    assert repository.get_edificacion(id_edificacion) is None


def test_baja_edificacion_devuelve_409_si_falta_if_match_version(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-BAJA-NOVERSION-001",
            "nombre_inmueble": "Inmueble Base Edif",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "Sin Version",
            "tipo_edificacion": None,
            "superficie": None,
            "observaciones": None,
        },
    )
    id_edificacion = create_response.json()["data"]["id_edificacion"]

    response = client.patch(
        f"/api/v1/edificaciones/{id_edificacion}/baja",
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_edificacion_devuelve_409_si_if_match_version_es_invalido(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-BAJA-BADVERSION-001",
            "nombre_inmueble": "Inmueble Base Edif",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "Version Invalida",
            "tipo_edificacion": None,
            "superficie": None,
            "observaciones": None,
        },
    )
    id_edificacion = create_response.json()["data"]["id_edificacion"]

    response = client.patch(
        f"/api/v1/edificaciones/{id_edificacion}/baja",
        headers={**HEADERS, "If-Match-Version": "abc"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_edificacion_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-BAJA-RACE-001",
            "nombre_inmueble": "Inmueble Base Edif",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/edificaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "descripcion": "Race Condition",
            "tipo_edificacion": None,
            "superficie": None,
            "observaciones": None,
        },
    )
    id_edificacion = create_response.json()["data"]["id_edificacion"]

    original_get = EdificacionRepository.get_edificacion_for_update
    db_session.execute(
        text(
            """
            UPDATE edificacion
            SET version_registro = 2
            WHERE id_edificacion = :id_edificacion
            """
        ),
        {"id_edificacion": id_edificacion},
    )

    def stale_get(self, edificacion_id: int):
        data = original_get(self, edificacion_id)
        if data is None:
            return None
        return {
            **data,
            "version_registro": 1,
        }

    monkeypatch.setattr(
        EdificacionRepository,
        "get_edificacion_for_update",
        stale_get,
    )

    response = client.patch(
        f"/api/v1/edificaciones/{id_edificacion}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
