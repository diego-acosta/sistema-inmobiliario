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


def test_update_edificacion_actualiza_en_postgresql(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-UPD-001",
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
            "descripcion": "Edificacion Inicial",
            "tipo_edificacion": "CASA",
            "superficie": "111.10",
            "observaciones": "inicial",
        },
    )
    assert create_response.status_code == 201
    id_edificacion = create_response.json()["data"]["id_edificacion"]

    response = client.put(
        f"/api/v1/edificaciones/{id_edificacion}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "descripcion": "Edificacion Actualizada",
            "tipo_edificacion": "LOCAL",
            "superficie": "222.20",
            "observaciones": "actualizada",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_edificacion": id_edificacion,
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "version_registro": 2,
            "descripcion": "Edificacion Actualizada",
            "tipo_edificacion": "LOCAL",
            "superficie": "222.20",
            "observaciones": "actualizada",
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_edificacion,
                id_inmueble,
                id_unidad_funcional,
                version_registro,
                descripcion,
                tipo_edificacion,
                superficie,
                observaciones,
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
    assert row["id_inmueble"] == id_inmueble
    assert row["id_unidad_funcional"] is None
    assert row["version_registro"] == 2
    assert row["descripcion"] == "Edificacion Actualizada"
    assert row["tipo_edificacion"] == "LOCAL"
    assert str(row["superficie"]) == "222.20"
    assert row["observaciones"] == "actualizada"
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_update_edificacion_devuelve_404_si_no_existe(client) -> None:
    response = client.put(
        "/api/v1/edificaciones/999999",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "descripcion": "No Existe",
            "tipo_edificacion": None,
            "superficie": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_edificacion_devuelve_404_si_esta_soft_deleted(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-DEL-UPD-001",
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
            "descripcion": "Soft Deleted",
            "tipo_edificacion": "CASA",
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

    response = client.put(
        f"/api/v1/edificaciones/{id_edificacion}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "descripcion": "Soft Deleted",
            "tipo_edificacion": "CASA",
            "superficie": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = EdificacionRepository(db_session)
    assert repository.get_edificacion_for_update(id_edificacion) is None


def test_update_edificacion_devuelve_409_si_falta_if_match_version(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-NOVERSION-001",
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

    response = client.put(
        f"/api/v1/edificaciones/{id_edificacion}",
        headers=HEADERS,
        json={
            "descripcion": "Sin Version",
            "tipo_edificacion": None,
            "superficie": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_edificacion_devuelve_409_si_if_match_version_es_invalido(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-BADVERSION-001",
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

    response = client.put(
        f"/api/v1/edificaciones/{id_edificacion}",
        headers={**HEADERS, "If-Match-Version": "abc"},
        json={
            "descripcion": "Version Invalida",
            "tipo_edificacion": None,
            "superficie": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_edificacion_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-EDIF-RACE-001",
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

    response = client.put(
        f"/api/v1/edificaciones/{id_edificacion}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "descripcion": "Race Condition",
            "tipo_edificacion": None,
            "superficie": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
