from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.infrastructure.persistence.repositories.inmueble_repository import (
    InmuebleRepository,
)
from tests.test_ocupaciones_create import HEADERS


def test_close_ocupacion_actualiza_fecha_hasta_y_version(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-CLOSE-001",
            "nombre_inmueble": "Inmueble Cierre Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": "ocupacion abierta",
            "observaciones": "cierre exitoso",
        },
    )
    assert create_response.status_code == 201
    ocupacion = create_response.json()["data"]

    response = client.patch(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}/cerrar",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={"fecha_hasta": "2026-04-25T10:00:00"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_ocupacion"] == ocupacion["id_ocupacion"]
    assert body["data"]["version_registro"] == 2
    assert body["data"]["id_inmueble"] == id_inmueble
    assert body["data"]["id_unidad_funcional"] is None
    assert body["data"]["tipo_ocupacion"] == "PROPIA"
    assert body["data"]["fecha_desde"] == "2026-04-21T10:00:00"
    assert body["data"]["fecha_hasta"] == "2026-04-25T10:00:00"
    assert body["data"]["descripcion"] == "ocupacion abierta"
    assert body["data"]["observaciones"] == "cierre exitoso"

    row = db_session.execute(
        text(
            """
            SELECT version_registro, fecha_hasta, deleted_at
            FROM ocupacion
            WHERE id_ocupacion = :id_ocupacion
            """
        ),
        {"id_ocupacion": ocupacion["id_ocupacion"]},
    ).mappings().one()

    assert row["version_registro"] == 2
    assert row["fecha_hasta"].isoformat() == "2026-04-25T10:00:00"
    assert row["deleted_at"] is None


def test_close_ocupacion_devuelve_error_si_fecha_hasta_es_menor(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-CLOSE-002",
            "nombre_inmueble": "Inmueble Fecha Invalida Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )
    assert create_response.status_code == 201
    ocupacion = create_response.json()["data"]

    response = client.patch(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}/cerrar",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={"fecha_hasta": "2026-04-20T10:00:00"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["error_message"] == "fecha_hasta no puede ser menor que fecha_desde."


def test_close_ocupacion_devuelve_error_de_concurrencia(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-CLOSE-003",
            "nombre_inmueble": "Inmueble Concurrencia Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )
    assert create_response.status_code == 201
    ocupacion = create_response.json()["data"]

    response = client.patch(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}/cerrar",
        headers={**HEADERS, "If-Match-Version": "999"},
        json={"fecha_hasta": "2026-04-22T10:00:00"},
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error_code"] == "CONCURRENCY_ERROR"
    assert (
        body["error_message"]
        == "If-Match-Version es requerido y debe coincidir con version_registro."
    )


def test_close_ocupacion_devuelve_error_si_no_existe(client) -> None:
    response = client.patch(
        "/api/v1/ocupaciones/999999/cerrar",
        headers={**HEADERS, "If-Match-Version": "1"},
        json={"fecha_hasta": "2026-04-22T10:00:00"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "NOT_FOUND"
    assert body["error_message"] == "La ocupacion indicada no existe."


def test_close_ocupacion_devuelve_error_si_esta_eliminada(client, db_session) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-CLOSE-004",
            "nombre_inmueble": "Inmueble Eliminado Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )
    assert create_response.status_code == 201
    ocupacion = create_response.json()["data"]

    db_session.execute(
        text(
            """
            UPDATE ocupacion
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_ocupacion = :id_ocupacion
            """
        ),
        {"id_ocupacion": ocupacion["id_ocupacion"]},
    )

    response = client.patch(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}/cerrar",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={"fecha_hasta": "2026-04-22T10:00:00"},
    )

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "NOT_FOUND"
    assert body["error_message"] == "La ocupacion indicada no existe."


def test_close_ocupacion_devuelve_error_si_ya_estaba_cerrada(client) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-CLOSE-005",
            "nombre_inmueble": "Inmueble Ocupacion Cerrada",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": "2026-04-22T10:00:00",
            "descripcion": None,
            "observaciones": None,
        },
    )
    assert create_response.status_code == 201
    ocupacion = create_response.json()["data"]

    response = client.patch(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}/cerrar",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={"fecha_hasta": "2026-04-23T10:00:00"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["error_message"] == "La ocupacion ya se encuentra cerrada."


def test_close_ocupacion_traduce_error_publico_de_solapamiento(
    client, monkeypatch
) -> None:
    inmueble_response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": "INM-OC-CLOSE-006",
            "nombre_inmueble": "Inmueble Solapamiento Ocupacion",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert inmueble_response.status_code == 201
    id_inmueble = inmueble_response.json()["data"]["id_inmueble"]

    create_response = client.post(
        "/api/v1/ocupaciones",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "tipo_ocupacion": "PROPIA",
            "fecha_desde": "2026-04-21T10:00:00",
            "fecha_hasta": None,
            "descripcion": None,
            "observaciones": None,
        },
    )
    assert create_response.status_code == 201
    ocupacion = create_response.json()["data"]

    def _raise_overlap(*args, **kwargs):
        raise DBAPIError(
            statement="UPDATE ocupacion ...",
            params={},
            orig=Exception(
                "Solapamiento de vigencia en ocupacion para inmueble 1, unidad_funcional None, tipo PROPIA"
            ),
        )

    monkeypatch.setattr(InmuebleRepository, "close_ocupacion", _raise_overlap)

    response = client.patch(
        f"/api/v1/ocupaciones/{ocupacion['id_ocupacion']}/cerrar",
        headers={**HEADERS, "If-Match-Version": str(ocupacion["version_registro"])},
        json={"fecha_hasta": "2026-04-22T10:00:00"},
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "El cierre de ocupacion viola las reglas vigentes de solapamiento."
    )
