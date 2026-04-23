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


def test_baja_unidad_funcional_actualiza_en_postgresql(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-BAJA-001",
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
            "codigo_unidad": "UF-BAJA-001",
            "nombre_unidad": "Unidad Baja",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": "alta inicial",
        },
    )
    assert create_response.status_code == 201
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    response = client.patch(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {
            "id_unidad_funcional": id_unidad_funcional,
            "version_registro": 2,
            "deleted": True,
        },
    }

    row = db_session.execute(
        text(
            """
            SELECT
                id_unidad_funcional,
                version_registro,
                deleted_at,
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
    assert row["version_registro"] == 2
    assert row["deleted_at"] is not None
    assert row["updated_at"] is not None
    assert row["id_instalacion_ultima_modificacion"] == 1
    assert str(row["op_id_ultima_modificacion"]) == HEADERS["X-Op-Id"]


def test_baja_unidad_funcional_devuelve_404_si_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/unidades-funcionales/999999/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_baja_unidad_funcional_devuelve_404_si_ya_esta_eliminada(
    client, db_session
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-BAJA-DEL-001",
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
            "codigo_unidad": "UF-BAJA-DEL-001",
            "nombre_unidad": "Ya Eliminada",
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

    response = client.patch(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"

    repository = InmuebleRepository(db_session)
    assert repository.get_unidad_funcional(id_unidad_funcional) is None


def test_baja_unidad_funcional_devuelve_409_si_falta_if_match_version(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-BAJA-NOVERSION-001",
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
            "codigo_unidad": "UF-BAJA-NOVERSION-001",
            "nombre_unidad": "Sin Version",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    response = client.patch(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/baja",
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_unidad_funcional_devuelve_409_si_if_match_version_es_invalido(
    client,
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-BAJA-BADVERSION-001",
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
            "codigo_unidad": "UF-BAJA-BADVERSION-001",
            "nombre_unidad": "Version Invalida",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    id_unidad_funcional = create_response.json()["data"]["id_unidad_funcional"]

    response = client.patch(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/baja",
        headers={**HEADERS, "If-Match-Version": "abc"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"


def test_baja_unidad_funcional_devuelve_409_si_update_no_afecta_filas_por_version(
    client, db_session, monkeypatch
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-UF-BAJA-RACE-001",
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
            "codigo_unidad": "UF-BAJA-RACE-001",
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

    response = client.patch(
        f"/api/v1/unidades-funcionales/{id_unidad_funcional}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"
