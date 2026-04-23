from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_escrituraciones_create import (
    _confirmar_venta_publica,
    _payload_escrituracion,
)


def test_get_venta_escrituraciones_devuelve_items_y_total(client, db_session) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    create_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(),
    )
    assert create_response.status_code == 201
    escrituracion = create_response.json()["data"]

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}/escrituraciones")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["total"] == 1
    assert len(body["data"]["items"]) == 1
    item = body["data"]["items"][0]
    assert item["id_escrituracion"] == escrituracion["id_escrituracion"]
    assert item["id_venta"] == venta["id_venta"]
    assert item["numero_escritura"] == "ESC-2026-001"
    assert item["deleted_at"] is None


def test_get_venta_escrituraciones_filtra_y_excluye_deleted_at(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    old_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(
            fecha_escrituracion="2026-04-22T11:00:00",
            numero_escritura="ESC-2026-OLD",
        ),
    )
    assert old_response.status_code == 201
    id_old = old_response.json()["data"]["id_escrituracion"]

    db_session.execute(
        text(
            """
            UPDATE escrituracion
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_escrituracion = :id_escrituracion
            """
        ),
        {"id_escrituracion": id_old},
    )

    new_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones",
        headers=HEADERS,
        json=_payload_escrituracion(
            fecha_escrituracion="2026-04-24T11:00:00",
            numero_escritura="ESC-2026-NEW",
        ),
    )
    assert new_response.status_code == 201
    id_new = new_response.json()["data"]["id_escrituracion"]

    by_numero = client.get(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones?numero_escritura=ESC-2026-NEW"
    )
    assert by_numero.status_code == 200
    items_numero = by_numero.json()["data"]["items"]
    assert len(items_numero) == 1
    assert items_numero[0]["id_escrituracion"] == id_new

    by_fecha = client.get(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones?fecha_desde=2026-04-24T00:00:00&fecha_hasta=2026-04-25T00:00:00"
    )
    assert by_fecha.status_code == 200
    items_fecha = by_fecha.json()["data"]["items"]
    assert len(items_fecha) == 1
    assert items_fecha[0]["id_escrituracion"] == id_new

    all_response = client.get(
        f"/api/v1/ventas/{venta['id_venta']}/escrituraciones"
    )
    assert all_response.status_code == 200
    all_ids = {
        item["id_escrituracion"] for item in all_response.json()["data"]["items"]
    }
    assert id_new in all_ids
    assert id_old not in all_ids


def test_get_venta_escrituraciones_devuelve_404_si_venta_no_existe(client) -> None:
    response = client.get("/api/v1/ventas/999999/escrituraciones")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "NOT_FOUND"
    assert body["error_message"] == "La venta indicada no existe."
