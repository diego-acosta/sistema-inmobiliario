"""
Tests de integración para POST /api/v1/financiero/inbox.
Cubre: evento válido, evento desconocido e idempotencia.
"""
from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_escrituraciones_create import _confirmar_venta_publica


URL = "/api/v1/financiero/inbox"


# ─── helpers ─────────────────────────────────────────────────────────────────


def _count_relaciones_venta(db_session, *, id_venta: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM relacion_generadora
            WHERE tipo_origen = 'venta'
              AND id_origen = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()["total"]


def _count_obligaciones_relacion(db_session, *, id_relacion_generadora: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM obligacion_financiera
            WHERE id_relacion_generadora = :id
              AND deleted_at IS NULL
            """
        ),
        {"id": id_relacion_generadora},
    ).mappings().one()["total"]


def _get_relacion_venta(db_session, *, id_venta: int) -> dict:
    return db_session.execute(
        text(
            """
            SELECT id_relacion_generadora, tipo_origen, id_origen, estado_relacion_generadora
            FROM relacion_generadora
            WHERE tipo_origen = 'venta'
              AND id_origen = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()


# ─── caso 1: evento válido ────────────────────────────────────────────────────


def test_inbox_venta_confirmada_crea_relacion_generadora_y_obligacion(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    id_venta = venta["id_venta"]

    response = client.post(
        URL,
        headers=HEADERS,
        json={
            "event_type": "venta_confirmada",
            "payload": {"id_venta": id_venta},
        },
    )

    assert response.status_code == 204
    assert response.content == b""

    assert _count_relaciones_venta(db_session, id_venta=id_venta) == 1

    relacion = _get_relacion_venta(db_session, id_venta=id_venta)
    assert relacion["tipo_origen"] == "venta"
    assert relacion["id_origen"] == id_venta

    assert (
        _count_obligaciones_relacion(
            db_session,
            id_relacion_generadora=relacion["id_relacion_generadora"],
        )
        == 1
    )


# ─── caso 2: evento desconocido ──────────────────────────────────────────────


def test_inbox_evento_desconocido_no_rompe_y_no_crea_datos(
    client, db_session
) -> None:
    response = client.post(
        URL,
        headers=HEADERS,
        json={
            "event_type": "evento_inexistente_xyz",
            "payload": {"foo": "bar"},
        },
    )

    assert response.status_code == 204

    total_relaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM relacion_generadora WHERE deleted_at IS NULL")
    ).mappings().one()["total"]
    assert total_relaciones == 0

    total_obligaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM obligacion_financiera WHERE deleted_at IS NULL")
    ).mappings().one()["total"]
    assert total_obligaciones == 0


# ─── caso 3: idempotencia ─────────────────────────────────────────────────────


def test_inbox_venta_confirmada_idempotente_no_duplica(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    id_venta = venta["id_venta"]
    body = {
        "event_type": "venta_confirmada",
        "payload": {"id_venta": id_venta},
    }

    response1 = client.post(URL, headers=HEADERS, json=body)
    response2 = client.post(URL, headers=HEADERS, json=body)

    assert response1.status_code == 204
    assert response2.status_code == 204

    assert _count_relaciones_venta(db_session, id_venta=id_venta) == 1

    relacion = _get_relacion_venta(db_session, id_venta=id_venta)
    assert (
        _count_obligaciones_relacion(
            db_session,
            id_relacion_generadora=relacion["id_relacion_generadora"],
        )
        == 1
    )
