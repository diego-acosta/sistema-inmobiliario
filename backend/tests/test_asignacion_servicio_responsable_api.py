from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS
from tests.test_factura_servicio_sql import (
    _asociar_inmueble_servicio,
    _asociar_unidad_funcional_servicio,
    _crear_inmueble,
    _crear_servicio,
    _crear_unidad_funcional,
)


def _crear_persona(db_session, *, codigo: str, estado: str = "ACTIVA") -> int:
    row = db_session.execute(
        text(
            """
            INSERT INTO persona (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                tipo_persona, codigo_persona, nombre, apellido, estado_persona
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                'FISICA', :codigo, :nombre, 'Responsable', :estado
            )
            RETURNING id_persona
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "codigo": codigo,
            "nombre": f"Persona {codigo}",
            "estado": estado,
        },
    ).mappings().one()
    return row["id_persona"]


def _payload(
    *,
    id_servicio: int,
    id_persona: int,
    id_inmueble: int | None = None,
    id_unidad_funcional: int | None = None,
    porcentaje: float = 100.0,
    fecha_desde: str = "2026-05-01",
    fecha_hasta: str | None = None,
) -> dict:
    return {
        "id_servicio": id_servicio,
        "id_inmueble": id_inmueble,
        "id_unidad_funcional": id_unidad_funcional,
        "id_persona": id_persona,
        "porcentaje_responsabilidad": porcentaje,
        "fecha_desde": fecha_desde,
        "fecha_hasta": fecha_hasta,
        "estado_asignacion": "ACTIVA",
        "observaciones": "Responsable de servicio trasladado",
    }


def test_crear_asignacion_100_para_inmueble_con_servicio_asociado(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="ASR-INM-001")
    id_servicio = _crear_servicio(db_session, codigo="ASR-SRV-001")
    id_persona = _crear_persona(db_session, codigo="ASR-PER-001")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    response = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=id_persona,
        ),
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["id_asignacion_servicio_responsable"] > 0
    assert data["id_inmueble"] == id_inmueble
    assert data["id_unidad_funcional"] is None
    assert data["porcentaje_responsabilidad"] == 100.0
    assert data["estado_asignacion"] == "ACTIVA"


def test_crear_asignacion_100_para_uf_con_servicio_asociado(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="ASR-INM-002")
    id_uf = _crear_unidad_funcional(db_session, id_inmueble=id_inmueble, codigo="ASR-UF-002")
    id_servicio = _crear_servicio(db_session, codigo="ASR-SRV-002")
    id_persona = _crear_persona(db_session, codigo="ASR-PER-002")
    _asociar_unidad_funcional_servicio(db_session, id_unidad_funcional=id_uf, id_servicio=id_servicio)

    response = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_unidad_funcional=id_uf,
            id_persona=id_persona,
        ),
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id_inmueble"] is None
    assert data["id_unidad_funcional"] == id_uf


def test_rechaza_xor_invalido(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="ASR-INM-003")
    id_uf = _crear_unidad_funcional(db_session, id_inmueble=id_inmueble, codigo="ASR-UF-003")
    id_servicio = _crear_servicio(db_session, codigo="ASR-SRV-003")
    id_persona = _crear_persona(db_session, codigo="ASR-PER-003")

    response = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_uf,
            id_persona=id_persona,
        ),
    )

    assert response.status_code == 422


def test_rechaza_servicio_no_asociado_al_objeto(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="ASR-INM-004")
    id_servicio = _crear_servicio(db_session, codigo="ASR-SRV-004")
    id_persona = _crear_persona(db_session, codigo="ASR-PER-004")

    response = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=id_persona,
        ),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "SERVICIO_NO_ASOCIADO"


def test_rechaza_persona_inexistente_o_inactiva(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="ASR-INM-005")
    id_servicio = _crear_servicio(db_session, codigo="ASR-SRV-005")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)
    id_persona_inactiva = _crear_persona(
        db_session, codigo="ASR-PER-005", estado="INACTIVA"
    )

    inexistente = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=999999999,
        ),
    )
    inactiva = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=id_persona_inactiva,
        ),
    )

    assert inexistente.status_code == 404
    assert inactiva.status_code == 404


def test_rechaza_porcentaje_fuera_de_rango(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="ASR-INM-006")
    id_servicio = _crear_servicio(db_session, codigo="ASR-SRV-006")
    id_persona = _crear_persona(db_session, codigo="ASR-PER-006")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    response = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=id_persona,
            porcentaje=0,
        ),
    )

    assert response.status_code == 422


def test_rechaza_configuracion_activa_con_suma_distinta_de_100(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="ASR-INM-007")
    id_servicio = _crear_servicio(db_session, codigo="ASR-SRV-007")
    id_persona_1 = _crear_persona(db_session, codigo="ASR-PER-007-A")
    id_persona_2 = _crear_persona(db_session, codigo="ASR-PER-007-B")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    first = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=id_persona_1,
            porcentaje=50,
        ),
    )
    second = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=id_persona_2,
            porcentaje=40,
        ),
    )

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "RESPONSABLE_SERVICIO_AMBIGUO"


def test_permite_dos_responsables_50_50_si_suma_100(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="ASR-INM-008")
    id_servicio = _crear_servicio(db_session, codigo="ASR-SRV-008")
    id_persona_1 = _crear_persona(db_session, codigo="ASR-PER-008-A")
    id_persona_2 = _crear_persona(db_session, codigo="ASR-PER-008-B")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    first = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=id_persona_1,
            porcentaje=50,
        ),
    )
    second = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=id_persona_2,
            porcentaje=50,
        ),
    )

    assert first.status_code == 201
    assert second.status_code == 201


def test_get_listado_y_baja_logica(client, db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="ASR-INM-009")
    id_servicio = _crear_servicio(db_session, codigo="ASR-SRV-009")
    id_persona = _crear_persona(db_session, codigo="ASR-PER-009")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)
    created = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=id_persona,
        ),
    )
    id_asignacion = created.json()["data"]["id_asignacion_servicio_responsable"]

    detail = client.get(f"/api/v1/asignaciones-servicio-responsable/{id_asignacion}")
    listing = client.get("/api/v1/asignaciones-servicio-responsable")
    deleted = client.patch(
        f"/api/v1/asignaciones-servicio-responsable/{id_asignacion}/baja",
        headers={**HEADERS, "If-Match-Version": "1"},
    )
    row = db_session.execute(
        text(
            """
            SELECT deleted_at
            FROM asignacion_servicio_responsable
            WHERE id_asignacion_servicio_responsable = :id
            """
        ),
        {"id": id_asignacion},
    ).mappings().one()

    assert detail.status_code == 200
    assert listing.status_code == 200
    assert id_asignacion in {
        item["id_asignacion_servicio_responsable"] for item in listing.json()["data"]
    }
    assert deleted.status_code == 200
    assert deleted.json()["data"]["deleted"] is True
    assert row["deleted_at"] is not None


def test_asignacion_no_crea_factura_relacion_generadora_ni_obligacion(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="ASR-INM-010")
    id_servicio = _crear_servicio(db_session, codigo="ASR-SRV-010")
    id_persona = _crear_persona(db_session, codigo="ASR-PER-010")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)
    facturas_antes = db_session.execute(text("SELECT COUNT(*) FROM factura_servicio")).scalar_one()
    relaciones_antes = db_session.execute(text("SELECT COUNT(*) FROM relacion_generadora")).scalar_one()
    obligaciones_antes = db_session.execute(text("SELECT COUNT(*) FROM obligacion_financiera")).scalar_one()

    response = client.post(
        "/api/v1/asignaciones-servicio-responsable",
        headers=HEADERS,
        json=_payload(
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_persona=id_persona,
        ),
    )

    facturas_despues = db_session.execute(text("SELECT COUNT(*) FROM factura_servicio")).scalar_one()
    relaciones_despues = db_session.execute(text("SELECT COUNT(*) FROM relacion_generadora")).scalar_one()
    obligaciones_despues = db_session.execute(text("SELECT COUNT(*) FROM obligacion_financiera")).scalar_one()

    assert response.status_code == 201
    assert facturas_despues == facturas_antes
    assert relaciones_despues == relaciones_antes
    assert obligaciones_despues == obligaciones_antes
