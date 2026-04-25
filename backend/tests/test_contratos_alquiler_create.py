from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
)


def _payload_base(
    *,
    codigo_contrato: str,
    objetos: list[dict],
    id_persona: int,
    id_rol: int,
    fecha_inicio: str = "2026-05-01",
    fecha_fin: str | None = "2026-10-31",
) -> dict:
    return {
        "codigo_contrato": codigo_contrato,
        "fecha_contrato": "2026-04-24",
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "canon_inicial": "1500.00",
        "moneda": "ARS",
        "observaciones": "Contrato de prueba",
        "objetos": objetos,
        "participaciones": [
            {
                "id_persona": id_persona,
                "id_rol_participacion": id_rol,
                "fecha_desde": fecha_inicio,
                "fecha_hasta": None,
                "observaciones": "Participante principal",
            }
        ],
    }


def test_create_contrato_alquiler_exitoso(client, db_session) -> None:
    id_persona = _crear_persona(client, nombre="Elena", apellido="Poniatowska")
    id_inmueble = _crear_inmueble(client, codigo="INM-CA-OK-001")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9201)

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-OK-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": "Objeto A"}],
            id_persona=id_persona,
            id_rol=9201,
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert isinstance(body["data"]["id_contrato_alquiler"], int)
    assert body["data"]["estado_contrato"] == "borrador"
    assert body["data"]["codigo_contrato"] == "CA-OK-001"
    assert len(body["data"]["objetos"]) == 1
    assert body["data"]["objetos"][0]["id_inmueble"] == id_inmueble
    assert isinstance(body["data"]["objetos"][0]["id_contrato_objeto"], int)

    id_contrato = body["data"]["id_contrato_alquiler"]

    contrato_row = db_session.execute(
        text(
            """
            SELECT estado_contrato, codigo_contrato
            FROM contrato_alquiler
            WHERE id_contrato_alquiler = :id
            """
        ),
        {"id": id_contrato},
    ).mappings().one()
    assert contrato_row["estado_contrato"] == "borrador"
    assert contrato_row["codigo_contrato"] == "CA-OK-001"

    objeto_row = db_session.execute(
        text(
            """
            SELECT id_inmueble
            FROM contrato_objeto_locativo
            WHERE id_contrato_alquiler = :id
            """
        ),
        {"id": id_contrato},
    ).mappings().one()
    assert objeto_row["id_inmueble"] == id_inmueble

    participacion_row = db_session.execute(
        text(
            """
            SELECT tipo_relacion, id_relacion
            FROM relacion_persona_rol
            WHERE id_relacion = :id_contrato
              AND id_persona = :id_persona
            """
        ),
        {"id_contrato": id_contrato, "id_persona": id_persona},
    ).mappings().one()
    assert participacion_row["tipo_relacion"] == "contrato_alquiler"
    assert participacion_row["id_relacion"] == id_contrato


def test_create_contrato_alquiler_objeto_inexistente_devuelve_404(client, db_session) -> None:
    id_persona = _crear_persona(client, nombre="Simone", apellido="de Beauvoir")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9202)

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-NF-INM-001",
            objetos=[{"id_inmueble": 999999, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9202,
        ),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
    assert response.json()["details"]["errors"] == ["NOT_FOUND_INMUEBLE"]


def test_create_contrato_alquiler_persona_inexistente_devuelve_404(client, db_session) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-CA-NOPER-001")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9203)

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-NF-PER-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=999999,
            id_rol=9203,
        ),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"
    assert response.json()["details"]["errors"] == ["NOT_FOUND_PERSONA"]


def test_create_contrato_alquiler_sin_objetos_devuelve_400(client, db_session) -> None:
    id_persona = _crear_persona(client, nombre="Virginia", apellido="Woolf")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9204)

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-NOOBJ-001",
            objetos=[],
            id_persona=id_persona,
            id_rol=9204,
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["OBJETOS_REQUIRED"]


def test_create_contrato_alquiler_sin_participaciones_devuelve_400(client, db_session) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-CA-NPAR-001")

    payload = _payload_base(
        codigo_contrato="CA-NPAR-001",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
        id_persona=0,
        id_rol=0,
    )
    payload["participaciones"] = []

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["PARTICIPACIONES_REQUIRED"]


def test_create_contrato_alquiler_fecha_fin_menor_a_fecha_inicio_devuelve_400(
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Hannah", apellido="Arendt")
    id_inmueble = _crear_inmueble(client, codigo="INM-CA-FECH-001")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9205)

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-FECH-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9205,
            fecha_inicio="2026-05-01",
            fecha_fin="2026-04-01",
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["INVALID_DATE_RANGE"]


def test_create_contrato_alquiler_tipo_relacion_persiste_como_contrato_alquiler(
    client, db_session
) -> None:
    id_persona = _crear_persona(client, nombre="Frida", apellido="Kahlo")
    id_inmueble = _crear_inmueble(client, codigo="INM-CA-TR-001")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9206)

    response = client.post(
        "/api/v1/contratos-alquiler",
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato="CA-TR-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9206,
        ),
    )

    assert response.status_code == 201
    id_contrato = response.json()["data"]["id_contrato_alquiler"]

    row = db_session.execute(
        text(
            """
            SELECT tipo_relacion
            FROM relacion_persona_rol
            WHERE id_relacion = :id_contrato
              AND id_persona = :id_persona
            """
        ),
        {"id_contrato": id_contrato, "id_persona": id_persona},
    ).mappings().one_or_none()

    assert row is not None, "No se encontró fila en relacion_persona_rol para el contrato"
    assert row["tipo_relacion"] == "contrato_alquiler"
