from sqlalchemy import text

from tests.test_cesiones_create import _confirmar_venta_publica, _payload_cesion
from tests.test_disponibilidades_create import HEADERS


def test_get_venta_cesiones_devuelve_items_y_total(client, db_session) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    create_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(),
    )
    assert create_response.status_code == 201
    cesion = create_response.json()["data"]

    response = client.get(f"/api/v1/ventas/{venta['id_venta']}/cesiones")

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["total"] == 1
    assert len(body["data"]["items"]) == 1
    item = body["data"]["items"][0]
    assert item["id_cesion"] == cesion["id_cesion"]
    assert item["id_venta"] == venta["id_venta"]
    assert item["tipo_cesion"] == "total"
    assert item["deleted_at"] is None


def test_get_venta_cesiones_filtra_y_excluye_deleted_at(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)

    total_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(
            fecha_cesion="2026-04-22T14:00:00",
            tipo_cesion="total",
        ),
    )
    assert total_response.status_code == 201
    id_total = total_response.json()["data"]["id_cesion"]

    db_session.execute(
        text(
            """
            UPDATE cesion
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_cesion = :id_cesion
            """
        ),
        {"id_cesion": id_total},
    )

    parcial_response = client.post(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones",
        headers=HEADERS,
        json=_payload_cesion(
            fecha_cesion="2026-04-24T14:00:00",
            tipo_cesion="parcial",
        ),
    )
    assert parcial_response.status_code == 201
    id_parcial = parcial_response.json()["data"]["id_cesion"]

    by_tipo = client.get(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones?tipo_cesion=parcial"
    )
    assert by_tipo.status_code == 200
    items_tipo = by_tipo.json()["data"]["items"]
    assert len(items_tipo) == 1
    assert items_tipo[0]["id_cesion"] == id_parcial

    by_fecha = client.get(
        f"/api/v1/ventas/{venta['id_venta']}/cesiones?fecha_desde=2026-04-24T00:00:00&fecha_hasta=2026-04-25T00:00:00"
    )
    assert by_fecha.status_code == 200
    items_fecha = by_fecha.json()["data"]["items"]
    assert len(items_fecha) == 1
    assert items_fecha[0]["id_cesion"] == id_parcial

    all_response = client.get(f"/api/v1/ventas/{venta['id_venta']}/cesiones")
    assert all_response.status_code == 200
    all_ids = {item["id_cesion"] for item in all_response.json()["data"]["items"]}
    assert id_parcial in all_ids
    assert id_total not in all_ids


def test_get_venta_cesiones_devuelve_404_si_venta_no_existe(client) -> None:
    response = client.get("/api/v1/ventas/999999/cesiones")

    assert response.status_code == 404
    body = response.json()
    assert body["error_code"] == "NOT_FOUND"
    assert body["error_message"] == "La venta indicada no existe."
