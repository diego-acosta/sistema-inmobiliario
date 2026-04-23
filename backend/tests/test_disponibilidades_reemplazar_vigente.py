from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS


def _crear_inmueble(client, codigo: str, nombre: str) -> int:
    response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": codigo,
            "nombre_inmueble": nombre,
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_inmueble"]


def _crear_disponibilidad_abierta(
    client,
    id_inmueble: int,
    *,
    estado_disponibilidad: str = "DISPONIBLE",
    fecha_desde: str = "2026-04-21T10:00:00",
    motivo: str | None = "Alta inicial",
    observaciones: str | None = "disponibilidad vigente",
) -> dict:
    response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": estado_disponibilidad,
            "fecha_desde": fecha_desde,
            "fecha_hasta": None,
            "motivo": motivo,
            "observaciones": observaciones,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def test_replace_disponibilidad_vigente_reemplaza_registro_abierto(client, db_session) -> None:
    id_inmueble = _crear_inmueble(
        client,
        "INM-DISP-REEMP-001",
        "Inmueble Reemplazo Exitoso",
    )
    disponibilidad_actual = _crear_disponibilidad_abierta(client, id_inmueble)

    response = client.post(
        "/api/v1/disponibilidades/reemplazar-vigente",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-25T10:00:00",
            "motivo": "Cambio de estado",
            "observaciones": "nueva disponibilidad vigente",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_disponibilidad"] != disponibilidad_actual["id_disponibilidad"]
    assert body["data"]["id_inmueble"] == id_inmueble
    assert body["data"]["id_unidad_funcional"] is None
    assert body["data"]["estado_disponibilidad"] == "RESERVADA"
    assert body["data"]["fecha_desde"] == "2026-04-25T10:00:00"
    assert body["data"]["fecha_hasta"] is None
    assert body["data"]["version_registro"] == 1

    rows = db_session.execute(
        text(
            """
            SELECT
                id_disponibilidad,
                version_registro,
                fecha_desde,
                fecha_hasta,
                estado_disponibilidad
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().all()

    assert len(rows) == 2

    anterior = next(
        row
        for row in rows
        if row["id_disponibilidad"] == disponibilidad_actual["id_disponibilidad"]
    )
    nueva = next(
        row for row in rows if row["id_disponibilidad"] == body["data"]["id_disponibilidad"]
    )

    assert anterior["version_registro"] == 2
    assert anterior["fecha_desde"].isoformat() == "2026-04-21T10:00:00"
    assert anterior["fecha_hasta"].isoformat() == "2026-04-25T10:00:00"
    assert anterior["estado_disponibilidad"] == "DISPONIBLE"

    assert nueva["version_registro"] == 1
    assert nueva["fecha_desde"].isoformat() == "2026-04-25T10:00:00"
    assert nueva["fecha_hasta"] is None
    assert nueva["estado_disponibilidad"] == "RESERVADA"

    abiertas = [row for row in rows if row["fecha_hasta"] is None]
    assert len(abiertas) == 1
    assert abiertas[0]["id_disponibilidad"] == body["data"]["id_disponibilidad"]


def test_replace_disponibilidad_vigente_devuelve_error_si_no_hay_vigente(client) -> None:
    id_inmueble = _crear_inmueble(
        client,
        "INM-DISP-REEMP-002",
        "Inmueble Sin Vigente",
    )

    response = client.post(
        "/api/v1/disponibilidades/reemplazar-vigente",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-25T10:00:00",
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert body["error_message"] == "No existe una disponibilidad vigente para la entidad indicada."


def test_replace_disponibilidad_vigente_devuelve_error_si_hay_mas_de_una_vigente(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(
        client,
        "INM-DISP-REEMP-003",
        "Inmueble Multiple Vigente",
    )

    db_session.execute(
        text(
            """
            INSERT INTO disponibilidad (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_inmueble,
                id_unidad_funcional,
                estado_disponibilidad,
                fecha_desde,
                fecha_hasta,
                motivo,
                observaciones
            )
            VALUES
            (
                '11111111-1111-1111-1111-111111111111',
                1,
                '2026-04-21T10:00:00',
                '2026-04-21T10:00:00',
                1,
                1,
                CAST(:op_id AS uuid),
                CAST(:op_id AS uuid),
                :id_inmueble,
                NULL,
                'DISPONIBLE',
                '2026-04-21T10:00:00',
                NULL,
                'Alta 1',
                NULL
            ),
            (
                '22222222-2222-2222-2222-222222222222',
                1,
                '2026-04-21T11:00:00',
                '2026-04-21T11:00:00',
                1,
                1,
                CAST(:op_id AS uuid),
                CAST(:op_id AS uuid),
                :id_inmueble,
                NULL,
                'RESERVADA',
                '2026-04-21T11:00:00',
                NULL,
                'Alta 2',
                NULL
            )
            """
        ),
        {"id_inmueble": id_inmueble, "op_id": HEADERS["X-Op-Id"]},
    )
    db_session.commit()

    response = client.post(
        "/api/v1/disponibilidades/reemplazar-vigente",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "BLOQUEADA",
            "fecha_desde": "2026-04-25T10:00:00",
            "motivo": "Normalizacion",
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "La entidad indicada tiene mas de una disponibilidad vigente. Estado inconsistente."
    )

    abiertas = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND fecha_hasta IS NULL
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().one()
    assert abiertas["total"] == 2


def test_replace_disponibilidad_vigente_traduce_solapamiento_y_hace_rollback(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(
        client,
        "INM-DISP-REEMP-004",
        "Inmueble Solapamiento Reemplazo",
    )
    disponibilidad_actual = _crear_disponibilidad_abierta(
        client,
        id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )

    response = client.post(
        "/api/v1/disponibilidades/reemplazar-vigente",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "DISPONIBLE",
            "fecha_desde": "2026-04-25T10:00:00",
            "motivo": "Intento con mismo estado",
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "El reemplazo de disponibilidad viola las reglas vigentes de solapamiento."
    )

    rows = db_session.execute(
        text(
            """
            SELECT
                id_disponibilidad,
                version_registro,
                fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().all()

    assert len(rows) == 1
    assert rows[0]["id_disponibilidad"] == disponibilidad_actual["id_disponibilidad"]
    assert rows[0]["version_registro"] == 1
    assert rows[0]["fecha_hasta"] is None


def test_replace_disponibilidad_vigente_hace_rollback_si_falla_creacion_despues_del_cierre(
    client, db_session, monkeypatch
) -> None:
    id_inmueble = _crear_inmueble(
        client,
        "INM-DISP-REEMP-005",
        "Inmueble Rollback Reemplazo",
    )
    disponibilidad_actual = _crear_disponibilidad_abierta(client, id_inmueble)

    original_execute = db_session.execute

    def failing_execute(statement, *args, **kwargs):
        sql = str(statement)
        if "INSERT INTO disponibilidad" in sql and "RETURNING" in sql:
            raise RuntimeError("forced insert failure after close")
        return original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db_session, "execute", failing_execute)

    response = client.post(
        "/api/v1/disponibilidades/reemplazar-vigente",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-25T10:00:00",
            "motivo": "Fallo forzado",
            "observaciones": None,
        },
    )

    monkeypatch.undo()

    assert response.status_code == 500
    body = response.json()
    assert body["error_code"] == "INTERNAL_ERROR"
    assert "forced insert failure after close" in body["error_message"]

    rows = db_session.execute(
        text(
            """
            SELECT
                id_disponibilidad,
                version_registro,
                fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND id_unidad_funcional IS NULL
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().all()

    assert len(rows) == 1
    assert rows[0]["id_disponibilidad"] == disponibilidad_actual["id_disponibilidad"]
    assert rows[0]["version_registro"] == 1
    assert rows[0]["fecha_hasta"] is None


def test_replace_disponibilidad_vigente_devuelve_error_si_xor_es_invalido(client) -> None:
    response = client.post(
        "/api/v1/disponibilidades/reemplazar-vigente",
        headers=HEADERS,
        json={
            "id_inmueble": 1,
            "id_unidad_funcional": 1,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-25T10:00:00",
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional."
    )


def test_replace_disponibilidad_vigente_devuelve_error_si_no_viene_parent(client) -> None:
    response = client.post(
        "/api/v1/disponibilidades/reemplazar-vigente",
        headers=HEADERS,
        json={
            "id_inmueble": None,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-25T10:00:00",
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional."
    )


def test_replace_disponibilidad_vigente_devuelve_error_si_fecha_desde_es_anterior(
    client,
) -> None:
    id_inmueble = _crear_inmueble(
        client,
        "INM-DISP-REEMP-006",
        "Inmueble Fecha Reemplazo",
    )
    _crear_disponibilidad_abierta(
        client,
        id_inmueble,
        fecha_desde="2026-04-21T10:00:00",
    )

    response = client.post(
        "/api/v1/disponibilidades/reemplazar-vigente",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": None,
            "estado_disponibilidad": "RESERVADA",
            "fecha_desde": "2026-04-20T10:00:00",
            "motivo": None,
            "observaciones": None,
        },
    )

    assert response.status_code == 400
    body = response.json()
    assert body["error_code"] == "APPLICATION_ERROR"
    assert (
        body["error_message"]
        == "La nueva disponibilidad no puede comenzar antes que la disponibilidad vigente actual."
    )
