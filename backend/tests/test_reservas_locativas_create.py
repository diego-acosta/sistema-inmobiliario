from pathlib import Path

from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_disponibilidad, _crear_inmueble


PATCH_SQL_PATH = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "patch_reserva_locativa_objeto_20260426.sql"
)


def _apply_patch(db_session) -> None:
    raw_connection = db_session.connection().connection
    with raw_connection.cursor() as cursor:
        cursor.execute(PATCH_SQL_PATH.read_text(encoding="utf-8"))


def _crear_inmueble_disponible(client, db_session, *, codigo: str) -> int:
    id_inmueble = _crear_inmueble(client, codigo=codigo)
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )
    return id_inmueble


def _payload_reserva(*, codigo: str, id_inmueble: int) -> dict:
    return {
        "codigo_reserva": codigo,
        "fecha_reserva": "2026-05-01T10:00:00",
        "fecha_vencimiento": "2026-05-10T10:00:00",
        "observaciones": "Reserva de prueba",
        "objetos": [
            {"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}
        ],
    }


def test_create_reserva_locativa_exitosa(client, db_session) -> None:
    _apply_patch(db_session)
    id_inmueble = _crear_inmueble_disponible(client, db_session, codigo="INM-RL-CRE-001")

    response = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CRE-001", id_inmueble=id_inmueble),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    data = body["data"]
    assert isinstance(data["id_reserva_locativa"], int)
    assert data["estado_reserva"] == "pendiente"
    assert data["codigo_reserva"] == "RL-CRE-001"
    assert len(data["objetos"]) == 1
    assert data["objetos"][0]["id_inmueble"] == id_inmueble
    assert isinstance(data["objetos"][0]["id_reserva_locativa_objeto"], int)
    assert data["deleted_at"] is None

    row = db_session.execute(
        text(
            "SELECT estado_reserva FROM reserva_locativa WHERE id_reserva_locativa = :id"
        ),
        {"id": data["id_reserva_locativa"]},
    ).mappings().one()
    assert row["estado_reserva"] == "pendiente"

    obj_row = db_session.execute(
        text(
            "SELECT id_inmueble FROM reserva_locativa_objeto WHERE id_reserva_locativa = :id"
        ),
        {"id": data["id_reserva_locativa"]},
    ).mappings().one()
    assert obj_row["id_inmueble"] == id_inmueble


def test_create_reserva_locativa_sin_disponibilidad_devuelve_400(client, db_session) -> None:
    _apply_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RL-NODISP-001")

    response = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-NODISP-001", id_inmueble=id_inmueble),
    )

    assert response.status_code == 400
    body = response.json()
    assert body["ok"] is False
    assert body["details"]["errors"] == ["OBJECT_NOT_AVAILABLE"]


def test_create_reserva_locativa_conflicto_reserva_existente_devuelve_400(
    client, db_session
) -> None:
    _apply_patch(db_session)
    id_inmueble = _crear_inmueble_disponible(client, db_session, codigo="INM-RL-CONF-001")

    first = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONF-001A", id_inmueble=id_inmueble),
    )
    assert first.status_code == 201

    response = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-CONF-001B", id_inmueble=id_inmueble),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["CONFLICTING_RESERVA_LOCATIVA"]


def test_create_reserva_locativa_sin_objetos_devuelve_400(client, db_session) -> None:
    _apply_patch(db_session)

    response = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json={
            "codigo_reserva": "RL-NOOBJ-001",
            "fecha_reserva": "2026-05-01T10:00:00",
            "objetos": [],
        },
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["OBJETOS_REQUIRED"]


def test_create_reserva_locativa_inmueble_no_existe_devuelve_404(client, db_session) -> None:
    _apply_patch(db_session)

    response = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json=_payload_reserva(codigo="RL-NF-001", id_inmueble=999999),
    )

    assert response.status_code == 404
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "NOT_FOUND"


def test_create_reserva_locativa_fecha_vencimiento_invalida_devuelve_400(
    client, db_session
) -> None:
    _apply_patch(db_session)
    id_inmueble = _crear_inmueble_disponible(client, db_session, codigo="INM-RL-FECH-001")

    response = client.post(
        "/api/v1/reservas-locativas",
        headers=HEADERS,
        json={
            "codigo_reserva": "RL-FECH-001",
            "fecha_reserva": "2026-05-10T10:00:00",
            "fecha_vencimiento": "2026-05-01T10:00:00",
            "objetos": [
                {"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}
            ],
        },
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_DATE_RANGE"]
