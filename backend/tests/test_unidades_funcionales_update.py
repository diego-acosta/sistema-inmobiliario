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


def test_update_unidad_funcional_actualiza_en_postgresql(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-UPD-001",
            "nombre_inmueble": "Inmueble Base",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-UPD-001",
            "nombre_unidad": "Unidad Inicial",
            "superficie": "66.60",
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": "inicial",
        },
    )
    assert create_response.status_code == 201
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    response = client.put(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "codigo_unidad": "UF-UPD-999",
            "nombre_unidad": "Unidad Actualizada",
            "superficie": "88.80",
            "estado_administrativo": "INACTIVA",
            "estado_operativo": "RESERVADA",
            "observaciones": "actualizada",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_unidad_funcional": id_unidad_funcional,
            "id_inmueble": id_inmueble,
            "version_registro": 2,
            "codigo_unidad": "UF-UPD-999",
            "nombre_unidad": "Unidad Actualizada",
            "superficie": "88.80",
            "estado_administrativo": "INACTIVA",
            "estado_operativo": "RESERVADA",
            "observaciones": "actualizada",
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_unidad_funcional,
                id_inmueble,
                version_registro,
                codigo_unidad,
                nombre_unidad,
                superficie,
                estado_administrativo,
                estado_operativo,
                observaciones,
                updated_at,
                id_instalacion_ultima_modificacion,
                op_id_ultima_modificacion
            FROM unidad_funcional
            WHERE id_unidad_funcional = :id_unidad_funcional
            """
        ),
        {"id_unidad_funcional": id_unidad_funcional},
    ).mappings().one()

    assert row["id_unidad_funcional"] == id_unidad_funcional
    assert row["id_inmueble"] == id_inmueble
    assert row["version_registro"] == 2
    assert row["codigo_unidad"] == "UF-UPD-999"
    assert row["nombre_unidad"] == "Unidad Actualizada"
    assert str(row["superficie"]) == "88.80"
    assert row["estado_administrativo"] == "INACTIVA"
    assert row["estado_operativo"] == "RESERVADA"
    assert row["observaciones"] == "actualizada"
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_update_unidad_funcional_devuelve_404_si_no_existe(client) -> None:
    response = client.put(
        "/api/v1/unidades-funcionales/999999",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "codigo_unidad": "UF-NOPE-001",
            "nombre_unidad": "No Existe",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_update_unidad_funcional_devuelve_404_si_esta_soft_deleted(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-DEL-UPD-001",
            "nombre_inmueble": "Inmueble Base",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-DEL-UPD-001",
            "nombre_unidad": "Soft Deleted",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    db_session.execute(
        text(
            """
            UPDATE unidad_funcional
            SET deleted_at = created_at + INTERVAL '1 second'
            WHERE id_unidad_funcional = :id_unidad_funcional
            """
        ),
        {"id_unidad_funcional": id_unidad_funcional},
    )

    response = client.put(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "codigo_unidad": "UF-DEL-UPD-001",
            "nombre_unidad": "Soft Deleted",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = InmuebleRepository(db_session)
    assert repository.get_unidad_funcional_for_update(id_unidad_funcional) is None


def test_update_unidad_funcional_devuelve_409_si_falta_if_match_version(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-NOVERSION-001",
            "nombre_inmueble": "Inmueble Base",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-NOVERSION-001",
            "nombre_unidad": "Sin Version",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    response = client.put(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-NOVERSION-001",
            "nombre_unidad": "Sin Version",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_unidad_funcional_devuelve_409_si_if_match_version_es_invalido(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-BADVERSION-001",
            "nombre_inmueble": "Inmueble Base",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-BADVERSION-001",
            "nombre_unidad": "Version Invalida",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    response = client.put(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}",
        headers={**HEADERS, "If-Match-Version": "abc"},
        json={
            "codigo_unidad": "UF-BADVERSION-001",
            "nombre_unidad": "Version Invalida",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_unidad_funcional_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-RACE-001",
            "nombre_inmueble": "Inmueble Base",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-RACE-001",
            "nombre_unidad": "Race Condition",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    original_get = InmuebleRepository.get_unidad_funcional_for_update
    db_session.execute(
        text(
            """
            UPDATE unidad_funcional
            SET version_registro = 2
            WHERE id_unidad_funcional = :id_unidad_funcional
            """
        ),
        {"id_unidad_funcional": id_unidad_funcional},
    )

    def stale_get(self, unidad_id: int):
        data = original_get(self, unidad_id)
        if data is None:
            return None
        return {
            **data,
            "version_registro": 1,
        }

    monkeypatch.setattr(
        InmuebleRepository,
        "get_unidad_funcional_for_update",
        stale_get,
    )

    response = client.put(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "codigo_unidad": "UF-RACE-001",
            "nombre_unidad": "Race Condition",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_update_unidad_funcional_devuelve_422_si_campos_obligatorios_son_null(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-UPD-422-001",
            "nombre_inmueble": "Inmueble Base",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": "UF-UPD-422-001",
            "nombre_unidad": "Unidad Valida",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert create_response.status_code == 201
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    response = client.put(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={
            "codigo_unidad": None,
            "nombre_unidad": "Unidad Invalida",
            "superficie": None,
            "estado_administrativo": None,
            "estado_operativo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 422
