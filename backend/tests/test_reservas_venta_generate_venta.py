from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import text

from app.application.comercial.commands.generate_venta_from_reserva_venta import (
    GenerateVentaFromReservaVentaCommand,
)
from app.application.comercial.services.generate_venta_from_reserva_venta_service import (
    GenerateVentaFromReservaVentaService,
)
from app.application.common.commands import CommandContext
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _apply_reserva_multiobjeto_patch,
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
    _insertar_venta_conflictiva,
)


def _insertar_reserva_para_generar_venta(
    db_session,
    *,
    codigo_reserva: str,
    estado_reserva: str,
    objetos: list[dict[str, int | None]],
    participaciones: list[dict[str, object]] | None = None,
) -> dict[str, int]:
    reserva = db_session.execute(
        text(
            """
            INSERT INTO reserva_venta (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_reserva,
                fecha_reserva,
                estado_reserva,
                fecha_vencimiento,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                CAST(:op_id AS uuid),
                CAST(:op_id AS uuid),
                :codigo_reserva,
                TIMESTAMP '2026-04-21 10:00:00',
                :estado_reserva,
                TIMESTAMP '2026-04-30 10:00:00',
                'Reserva para generar venta'
            )
            RETURNING id_reserva_venta, version_registro
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "codigo_reserva": codigo_reserva,
            "estado_reserva": estado_reserva,
        },
    ).mappings().one()

    for objeto in objetos:
        db_session.execute(
            text(
                """
                INSERT INTO reserva_venta_objeto_inmobiliario (
                    uid_global,
                    version_registro,
                    created_at,
                    updated_at,
                    id_instalacion_origen,
                    id_instalacion_ultima_modificacion,
                    op_id_alta,
                    op_id_ultima_modificacion,
                    id_reserva_venta,
                    id_inmueble,
                    id_unidad_funcional,
                    observaciones
                )
                VALUES (
                    gen_random_uuid(),
                    1,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    1,
                    1,
                    CAST(:op_id AS uuid),
                    CAST(:op_id AS uuid),
                    :id_reserva_venta,
                    :id_inmueble,
                    :id_unidad_funcional,
                    :observaciones
                )
                """
            ),
            {
                "op_id": HEADERS["X-Op-Id"],
                "id_reserva_venta": reserva["id_reserva_venta"],
                "id_inmueble": objeto["id_inmueble"],
                "id_unidad_funcional": objeto["id_unidad_funcional"],
                "observaciones": objeto.get("observaciones"),
            },
        )

    for participacion in participaciones or []:
        db_session.execute(
            text(
                """
                INSERT INTO relacion_persona_rol (
                    uid_global,
                    version_registro,
                    created_at,
                    updated_at,
                    id_instalacion_origen,
                    id_instalacion_ultima_modificacion,
                    op_id_alta,
                    op_id_ultima_modificacion,
                    id_persona,
                    id_rol_participacion,
                    tipo_relacion,
                    id_relacion,
                    fecha_desde,
                    fecha_hasta,
                    observaciones
                )
                VALUES (
                    gen_random_uuid(),
                    1,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP,
                    1,
                    1,
                    CAST(:op_id AS uuid),
                    CAST(:op_id AS uuid),
                    :id_persona,
                    :id_rol_participacion,
                    'reserva_venta',
                    :id_relacion,
                    :fecha_desde,
                    :fecha_hasta,
                    :observaciones
                )
                """
            ),
            {
                "op_id": HEADERS["X-Op-Id"],
                "id_persona": participacion["id_persona"],
                "id_rol_participacion": participacion["id_rol_participacion"],
                "id_relacion": reserva["id_reserva_venta"],
                "fecha_desde": participacion["fecha_desde"],
                "fecha_hasta": participacion.get("fecha_hasta"),
                "observaciones": participacion.get("observaciones"),
            },
        )

    return {
        "id_reserva_venta": reserva["id_reserva_venta"],
        "version_registro": reserva["version_registro"],
    }


def _crear_trigger_falla_venta_objeto(db_session, *, id_inmueble: int) -> None:
    db_session.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION trg_test_fail_venta_objeto()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.id_inmueble = :id_inmueble_fail THEN
                    RAISE EXCEPTION 'forced failure on venta_objeto_inmobiliario';
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        ).bindparams(id_inmueble_fail=id_inmueble)
    )
    db_session.execute(
        text(
            "DROP TRIGGER IF EXISTS trg_test_fail_venta_objeto ON venta_objeto_inmobiliario"
        )
    )
    db_session.execute(
        text(
            """
            CREATE TRIGGER trg_test_fail_venta_objeto
            BEFORE INSERT ON venta_objeto_inmobiliario
            FOR EACH ROW
            EXECUTE FUNCTION trg_test_fail_venta_objeto()
            """
        )
    )


def _payload_generar_venta(*, codigo_venta: str) -> dict[str, object]:
    return {
        "codigo_venta": codigo_venta,
        "fecha_venta": "2026-04-22T11:00:00",
        "monto_total": 150000.00,
        "observaciones": "Venta generada desde reserva",
    }


def test_generate_venta_from_reserva_confirmada_crea_venta_finaliza_reserva_y_copia_objetos(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Ada", apellido="Lovelace")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9201)
    id_inmueble = _crear_inmueble(client, codigo="INM-GEN-VTA-001")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva="RV-GEN-001",
        estado_reserva="confirmada",
        objetos=[
            {
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": None,
                "observaciones": "Objeto reservado",
            }
        ],
        participaciones=[
            {
                "id_persona": id_persona,
                "id_rol_participacion": 9201,
                "fecha_desde": datetime(2026, 4, 21, 0, 0, 0),
                "fecha_hasta": None,
                "observaciones": "Comprador principal",
            }
        ],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/generar-venta",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload_generar_venta(codigo_venta="V-GEN-001"),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["ok"] is True
    assert body["data"]["id_reserva_venta"] == reserva["id_reserva_venta"]
    assert body["data"]["codigo_venta"] == "V-GEN-001"
    assert body["data"]["estado_venta"] == "borrador"
    assert Decimal(body["data"]["monto_total"]) == Decimal("150000.00")
    assert len(body["data"]["objetos"]) == 1
    assert body["data"]["objetos"][0]["id_inmueble"] == id_inmueble
    assert body["data"]["objetos"][0]["precio_asignado"] is None

    reserva_row = db_session.execute(
        text(
            """
            SELECT estado_reserva, version_registro
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert reserva_row["estado_reserva"] == "finalizada"
    assert reserva_row["version_registro"] == 2

    venta_row = db_session.execute(
        text(
            """
            SELECT
                id_venta,
                id_reserva_venta,
                codigo_venta,
                estado_venta,
                monto_total,
                observaciones,
                deleted_at
            FROM venta
            WHERE codigo_venta = :codigo_venta
            """
        ),
        {"codigo_venta": "V-GEN-001"},
    ).mappings().one()
    assert venta_row["id_reserva_venta"] == reserva["id_reserva_venta"]
    assert venta_row["estado_venta"] == "borrador"
    assert venta_row["monto_total"] == Decimal("150000.00")
    assert venta_row["observaciones"] == "Venta generada desde reserva"
    assert venta_row["deleted_at"] is None

    venta_objeto_row = db_session.execute(
        text(
            """
            SELECT
                id_venta,
                id_inmueble,
                id_unidad_funcional,
                precio_asignado,
                observaciones
            FROM venta_objeto_inmobiliario
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": venta_row["id_venta"]},
    ).mappings().one()
    assert venta_objeto_row["id_inmueble"] == id_inmueble
    assert venta_objeto_row["id_unidad_funcional"] is None
    assert venta_objeto_row["precio_asignado"] is None
    assert venta_objeto_row["observaciones"] == "Objeto reservado"

    disponibilidades = db_session.execute(
        text(
            """
            SELECT estado_disponibilidad, fecha_hasta
            FROM disponibilidad
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            ORDER BY id_disponibilidad
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().all()
    assert len(disponibilidades) == 1
    assert disponibilidades[0]["estado_disponibilidad"] == "RESERVADA"
    assert disponibilidades[0]["fecha_hasta"] is None

    relacion_venta = db_session.execute(
        text(
            """
            SELECT id_persona, id_rol_participacion, tipo_relacion, id_relacion
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'venta'
              AND id_relacion = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": venta_row["id_venta"]},
    ).mappings().one()
    assert relacion_venta["id_persona"] == id_persona
    assert relacion_venta["id_rol_participacion"] == 9201
    assert relacion_venta["tipo_relacion"] == "venta"

    ocupaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM ocupacion
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": id_inmueble},
    ).mappings().one()
    assert ocupaciones["total"] == 0

    relacion_generadora = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM relacion_generadora
            WHERE tipo_origen = 'venta'
              AND id_origen = :id_venta
            """
        ),
        {"id_venta": venta_row["id_venta"]},
    ).mappings().one()
    assert relacion_generadora["total"] == 0

    obligaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM obligacion_financiera
            """
        )
    ).mappings().one()
    assert obligaciones["total"] == 0


def test_generate_venta_from_reserva_devuelve_404_si_no_existe(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)

    response = client.post(
        "/api/v1/reservas-venta/999999/generar-venta",
        headers={**HEADERS, "If-Match-Version": "1"},
        json=_payload_generar_venta(codigo_venta="V-GEN-404"),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_generate_venta_from_reserva_devuelve_404_si_esta_eliminada(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-GEN-VTA-002")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva="RV-GEN-002",
        estado_reserva="confirmada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )
    db_session.execute(
        text(
            """
            UPDATE reserva_venta
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/generar-venta",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload_generar_venta(codigo_venta="V-GEN-002"),
    )

    assert response.status_code == 404
    assert response.json()["error_code"] == "NOT_FOUND"


def test_generate_venta_from_reserva_devuelve_error_si_estado_no_es_confirmada(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-GEN-VTA-003")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva="RV-GEN-003",
        estado_reserva="activa",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/generar-venta",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload_generar_venta(codigo_venta="V-GEN-003"),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "Solo una reserva en estado confirmada puede generar una venta."
    )


def test_generate_venta_from_reserva_devuelve_error_de_concurrencia_si_version_no_coincide(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-GEN-VTA-003B")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva="RV-GEN-003B",
        estado_reserva="confirmada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/generar-venta",
        headers={**HEADERS, "If-Match-Version": "999"},
        json=_payload_generar_venta(codigo_venta="V-GEN-003B"),
    )

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONCURRENCY_ERROR"

    reserva_row = db_session.execute(
        text(
            """
            SELECT estado_reserva, version_registro
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert reserva_row["estado_reserva"] == "confirmada"
    assert reserva_row["version_registro"] == reserva["version_registro"]

    ventas = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM venta
            WHERE id_reserva_venta = :id_reserva_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert ventas["total"] == 0


def test_generate_venta_from_reserva_devuelve_error_si_ya_fue_convertida(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-GEN-VTA-004")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva="RV-GEN-004",
        estado_reserva="confirmada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    first_response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/generar-venta",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload_generar_venta(codigo_venta="V-GEN-004"),
    )
    assert first_response.status_code == 201

    version_actual = db_session.execute(
        text(
            """
            SELECT version_registro
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).scalar_one()

    second_response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/generar-venta",
        headers={**HEADERS, "If-Match-Version": str(version_actual)},
        json=_payload_generar_venta(codigo_venta="V-GEN-004-BIS"),
    )

    assert second_response.status_code == 400
    assert second_response.json()["error_message"] == "La reserva ya fue convertida en una venta."


def test_generate_venta_from_reserva_devuelve_error_si_hay_conflicto_con_venta_activa(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-GEN-VTA-005")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="RESERVADA",
    )
    _insertar_venta_conflictiva(
        db_session,
        id_inmueble=id_inmueble,
        codigo_venta="V-CONFLICT-GEN-005",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva="RV-GEN-005",
        estado_reserva="confirmada",
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None}],
    )

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/generar-venta",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload_generar_venta(codigo_venta="V-GEN-005"),
    )

    assert response.status_code == 400
    assert (
        response.json()["error_message"]
        == "El objeto inmobiliario indicado ya participa en una venta activa incompatible."
    )


def test_generate_venta_from_reserva_hace_rollback_completo_si_falla_un_objeto(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Katherine", apellido="Johnson")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9202)
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-GEN-VTA-006A")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-GEN-VTA-006B")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble_1,
        estado_disponibilidad="RESERVADA",
    )
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble_2,
        estado_disponibilidad="RESERVADA",
    )
    reserva = _insertar_reserva_para_generar_venta(
        db_session,
        codigo_reserva="RV-GEN-006",
        estado_reserva="confirmada",
        objetos=[
            {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None},
            {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None},
        ],
        participaciones=[
            {
                "id_persona": id_persona,
                "id_rol_participacion": 9202,
                "fecha_desde": datetime(2026, 4, 21, 0, 0, 0),
                "fecha_hasta": None,
                "observaciones": "Participacion persistida",
            }
        ],
    )
    _crear_trigger_falla_venta_objeto(db_session, id_inmueble=id_inmueble_2)
    db_session.commit()

    response = client.post(
        f"/api/v1/reservas-venta/{reserva['id_reserva_venta']}/generar-venta",
        headers={**HEADERS, "If-Match-Version": str(reserva["version_registro"])},
        json=_payload_generar_venta(codigo_venta="V-GEN-006"),
    )

    assert response.status_code == 500
    assert response.json()["error_code"] == "INTERNAL_ERROR"

    reserva_row = db_session.execute(
        text(
            """
            SELECT estado_reserva, version_registro
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": reserva["id_reserva_venta"]},
    ).mappings().one()
    assert reserva_row["estado_reserva"] == "confirmada"
    assert reserva_row["version_registro"] == 1

    ventas = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM venta
            WHERE codigo_venta = 'V-GEN-006'
            """
        )
    ).mappings().one()
    assert ventas["total"] == 0

    venta_objetos = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM venta_objeto_inmobiliario
            """
        )
    ).mappings().one()
    assert venta_objetos["total"] == 0

    participaciones_venta = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'venta'
            """
        )
    ).mappings().one()
    assert participaciones_venta["total"] == 0


class _FakeGenerateVentaRepository:
    def get_reserva_venta(self, id_reserva_venta: int) -> dict[str, object] | None:
        return {
            "id_reserva_venta": id_reserva_venta,
            "uid_global": "uid",
            "version_registro": 1,
            "codigo_reserva": "RV-FAKE-001",
            "fecha_reserva": datetime(2026, 4, 21, 10, 0, 0, tzinfo=UTC),
            "estado_reserva": "confirmada",
            "fecha_vencimiento": None,
            "observaciones": None,
            "deleted_at": None,
            "objetos": [
                {
                    "id_reserva_venta_objeto": 1,
                    "id_inmueble": None,
                    "id_unidad_funcional": None,
                    "observaciones": None,
                }
            ],
            "participaciones": [],
        }

    def inmueble_exists(self, id_inmueble: int) -> bool:
        return True

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        return True

    def has_conflicting_active_venta(self, **kwargs) -> bool:
        return False

    def has_conflicting_active_reserva(self, **kwargs) -> bool:
        return False

    def venta_exists_for_reserva(self, id_reserva_venta: int) -> bool:
        return False

    def venta_codigo_exists(self, codigo_venta: str) -> bool:
        return False

    def get_current_disponibilidad_state(self, **kwargs) -> str | None:
        return "RESERVADA"

    def generate_venta_from_reserva(self, payload, objetos, participaciones, reserva_payload):
        raise AssertionError("No debe intentar persistir si los objetos de la reserva son inconsistentes.")


def test_generate_venta_from_reserva_service_devuelve_error_si_objetos_son_inconsistentes() -> None:
    service = GenerateVentaFromReservaVentaService(_FakeGenerateVentaRepository())
    command = GenerateVentaFromReservaVentaCommand(
        context=CommandContext(actor_id="1", metadata={}),
        id_reserva_venta=1,
        if_match_version=1,
        codigo_venta="V-FAKE-001",
        fecha_venta=datetime(2026, 4, 22, 11, 0, 0, tzinfo=UTC),
        monto_total=None,
        observaciones=None,
    )

    result = service.execute(command)

    assert result.success is False
    assert result.errors == ["INVALID_RESERVA_OBJECTS"]
