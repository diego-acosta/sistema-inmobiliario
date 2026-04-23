from pathlib import Path

from sqlalchemy import text

from tests.test_disponibilidades_create import HEADERS


PATCH_SQL_PATH = (
    Path(__file__).resolve().parents[1]
    / "database"
    / "patch_reserva_venta_multiobjeto_20260421.sql"
)


def _apply_reserva_multiobjeto_patch(db_session) -> None:
    raw_connection = db_session.connection().connection
    with raw_connection.cursor() as cursor:
        cursor.execute(PATCH_SQL_PATH.read_text(encoding="utf-8"))


def _crear_rol_participacion_activo(db_session, *, id_rol_participacion: int) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO rol_participacion (
                id_rol_participacion,
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                codigo_rol,
                nombre_rol,
                descripcion,
                estado_rol
            )
            VALUES (
                :id_rol_participacion,
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                :op_id,
                :op_id,
                :codigo_rol,
                :nombre_rol,
                NULL,
                'ACTIVO'
            )
            """
        ),
        {
            "id_rol_participacion": id_rol_participacion,
            "op_id": HEADERS["X-Op-Id"],
            "codigo_rol": f"ROL-COM-{id_rol_participacion}",
            "nombre_rol": f"Rol Comercial {id_rol_participacion}",
        },
    )


def _crear_persona(client, *, nombre: str, apellido: str) -> int:
    response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": nombre,
            "apellido": apellido,
            "razon_social": None,
            "fecha_nacimiento": "1990-01-01",
            "estado_persona": "ACTIVA",
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_persona"]


def _crear_inmueble(client, *, codigo: str) -> int:
    response = client.post(
        "/api/v1/inmuebles",
        headers=HEADERS,
        json={
            "id_desarrollo": None,
            "codigo_inmueble": codigo,
            "nombre_inmueble": f"Inmueble {codigo}",
            "superficie": None,
            "estado_administrativo": "ACTIVO",
            "estado_juridico": "REGULAR",
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_inmueble"]


def _crear_unidad_funcional(client, *, id_inmueble: int, codigo: str) -> int:
    response = client.post(
        f"/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
        headers=HEADERS,
        json={
            "codigo_unidad": codigo,
            "nombre_unidad": f"Unidad {codigo}",
            "superficie": None,
            "estado_administrativo": "ACTIVA",
            "estado_operativo": "DISPONIBLE",
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_unidad_funcional"]


def _crear_disponibilidad(
    client,
    *,
    id_inmueble: int | None = None,
    id_unidad_funcional: int | None = None,
    estado_disponibilidad: str,
    fecha_desde: str = "2026-04-01T00:00:00",
    fecha_hasta: str | None = None,
) -> int:
    response = client.post(
        "/api/v1/disponibilidades",
        headers=HEADERS,
        json={
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
            "estado_disponibilidad": estado_disponibilidad,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "motivo": "Test comercial",
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id_disponibilidad"]


def _insertar_venta_conflictiva(db_session, *, id_inmueble: int, codigo_venta: str) -> None:
    venta_row = db_session.execute(
        text(
            """
            INSERT INTO venta (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_reserva_venta,
                codigo_venta,
                fecha_venta,
                estado_venta,
                monto_total,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                :op_id,
                :op_id,
                NULL,
                :codigo_venta,
                TIMESTAMP '2026-04-10 10:00:00',
                'activa',
                1000.00,
                NULL
            )
            RETURNING id_venta
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "codigo_venta": codigo_venta,
        },
    ).mappings().one()

    db_session.execute(
        text(
            """
            INSERT INTO venta_objeto_inmobiliario (
                uid_global,
                version_registro,
                created_at,
                updated_at,
                id_instalacion_origen,
                id_instalacion_ultima_modificacion,
                op_id_alta,
                op_id_ultima_modificacion,
                id_venta,
                id_inmueble,
                id_unidad_funcional,
                precio_asignado,
                observaciones
            )
            VALUES (
                gen_random_uuid(),
                1,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP,
                1,
                1,
                :op_id,
                :op_id,
                :id_venta,
                :id_inmueble,
                NULL,
                1000.00,
                NULL
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_venta": venta_row["id_venta"],
            "id_inmueble": id_inmueble,
        },
    )


def _insertar_reserva_conflictiva(db_session, *, id_inmueble: int, codigo_reserva: str) -> None:
    reserva_row = db_session.execute(
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
                :op_id,
                :op_id,
                :codigo_reserva,
                TIMESTAMP '2026-04-10 10:00:00',
                'activa',
                TIMESTAMP '2026-04-30 10:00:00',
                NULL
            )
            RETURNING id_reserva_venta
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "codigo_reserva": codigo_reserva,
        },
    ).mappings().one()

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
                :op_id,
                :op_id,
                :id_reserva_venta,
                :id_inmueble,
                NULL,
                NULL
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_reserva_venta": reserva_row["id_reserva_venta"],
            "id_inmueble": id_inmueble,
        },
    )


def _crear_trigger_falla_relacion(db_session) -> None:
    db_session.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION trg_test_fail_reserva_objeto()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF NEW.observaciones = 'FORCE_FAIL' THEN
                    RAISE EXCEPTION 'forced failure on reserva_venta_objeto_inmobiliario';
                END IF;
                RETURN NEW;
            END;
            $$;
            """
        )
    )
    db_session.execute(text("DROP TRIGGER IF EXISTS trg_test_fail_reserva_objeto ON reserva_venta_objeto_inmobiliario"))
    db_session.execute(
        text(
            """
            CREATE TRIGGER trg_test_fail_reserva_objeto
            BEFORE INSERT ON reserva_venta_objeto_inmobiliario
            FOR EACH ROW
            EXECUTE FUNCTION trg_test_fail_reserva_objeto()
            """
        )
    )


def _payload_base(*, codigo_reserva: str, objetos: list[dict], id_persona: int, id_rol: int) -> dict:
    return {
        "codigo_reserva": codigo_reserva,
        "fecha_reserva": "2026-04-21T10:00:00",
        "fecha_vencimiento": "2026-04-30T10:00:00",
        "observaciones": "Reserva de prueba",
        "objetos": objetos,
        "participaciones": [
            {
                "id_persona": id_persona,
                "id_rol_participacion": id_rol,
                "fecha_desde": "2026-04-21",
                "fecha_hasta": None,
                "observaciones": "Participacion principal",
            }
        ],
    }


def test_create_reserva_venta_alta_exitosa_un_objeto(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Grace", apellido="Hopper")
    id_inmueble = _crear_inmueble(client, codigo="INM-RES-OK-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9101)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-OK-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": "Objeto principal"}],
            id_persona=id_persona,
            id_rol=9101,
        ),
    )

    assert response.status_code == 201
    body = response.json()

    assert body["ok"] is True
    assert isinstance(body["data"]["id_reserva_venta"], int)
    assert body["data"]["estado_reserva"] == "borrador"
    assert len(body["data"]["objetos"]) == 1
    assert body["data"]["objetos"][0]["id_inmueble"] == id_inmueble
    assert body["data"]["objetos"][0]["id_unidad_funcional"] is None

    objeto_row = db_session.execute(
        text(
            """
            SELECT id_reserva_venta, id_inmueble, id_unidad_funcional
            FROM reserva_venta_objeto_inmobiliario
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": body["data"]["id_reserva_venta"]},
    ).mappings().one()

    assert objeto_row["id_inmueble"] == id_inmueble
    assert objeto_row["id_unidad_funcional"] is None


def test_create_reserva_venta_alta_exitosa_multiobjeto(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Hedy", apellido="Lamarr")
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-RES-MULTI-001")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-RES-MULTI-002")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_1, estado_disponibilidad="DISPONIBLE")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_2, estado_disponibilidad="DISPONIBLE")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9102)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-MULTI-001",
            objetos=[
                {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None, "observaciones": "Objeto A"},
                {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None, "observaciones": "Objeto B"},
            ],
            id_persona=id_persona,
            id_rol=9102,
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert len(body["data"]["objetos"]) == 2

    count_objetos = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM reserva_venta_objeto_inmobiliario
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": body["data"]["id_reserva_venta"]},
    ).scalar_one()

    assert count_objetos == 2


def test_create_reserva_venta_devuelve_error_si_objetos_esta_vacio(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Niklaus", apellido="Wirth")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9111)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-EMPTY-001",
            objetos=[],
            id_persona=id_persona,
            id_rol=9111,
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["OBJETOS_REQUIRED"]


def test_create_reserva_venta_devuelve_error_si_repite_mismo_inmueble(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Leslie", apellido="Lamport")
    id_inmueble = _crear_inmueble(client, codigo="INM-RES-DUP-001")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9112)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-DUP-INM-001",
            objetos=[
                {"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": "A"},
                {"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": "B"},
            ],
            id_persona=id_persona,
            id_rol=9112,
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["DUPLICATE_OBJECT"]


def test_create_reserva_venta_devuelve_error_si_repite_misma_unidad_funcional(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Tony", apellido="Hoare")
    id_inmueble = _crear_inmueble(client, codigo="INM-RES-DUP-UF-001")
    id_unidad_funcional = _crear_unidad_funcional(
        client,
        id_inmueble=id_inmueble,
        codigo="UF-RES-DUP-001",
    )
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9113)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-DUP-UF-001",
            objetos=[
                {
                    "id_inmueble": None,
                    "id_unidad_funcional": id_unidad_funcional,
                    "observaciones": "A",
                },
                {
                    "id_inmueble": None,
                    "id_unidad_funcional": id_unidad_funcional,
                    "observaciones": "B",
                },
            ],
            id_persona=id_persona,
            id_rol=9113,
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["DUPLICATE_OBJECT"]


def test_create_reserva_venta_devuelve_error_si_un_item_tiene_xor_invalido(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Ada", apellido="Lovelace")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9103)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-XOR-001",
            objetos=[{"id_inmueble": 1, "id_unidad_funcional": 1, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9103,
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["EXACTLY_ONE_OBJECT_PARENT_REQUIRED"]


def test_create_reserva_venta_devuelve_error_si_objeto_no_existe(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Barbara", apellido="Liskov")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9104)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-NF-001",
            objetos=[{"id_inmueble": 999999, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9104,
        ),
    )

    assert response.status_code == 404
    assert response.json()["details"]["errors"] == ["NOT_FOUND_INMUEBLE"]


def test_create_reserva_venta_devuelve_error_si_persona_no_existe(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_inmueble = _crear_inmueble(client, codigo="INM-RES-NOPER-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9105)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-NOPER-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=999999,
            id_rol=9105,
        ),
    )

    assert response.status_code == 404
    assert response.json()["details"]["errors"] == ["NOT_FOUND_PERSONA"]


def test_create_reserva_venta_devuelve_error_si_un_objeto_no_esta_disponible(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Edsger", apellido="Dijkstra")
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-RES-DISP-001")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-RES-DISP-002")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_1, estado_disponibilidad="DISPONIBLE")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_2, estado_disponibilidad="NO_DISPONIBLE")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9106)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-DISP-001",
            objetos=[
                {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None, "observaciones": None},
                {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None, "observaciones": None},
            ],
            id_persona=id_persona,
            id_rol=9106,
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["OBJECT_NOT_AVAILABLE"]


def test_create_reserva_venta_devuelve_error_si_hay_conflicto_con_venta_activa(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Alan", apellido="Turing")
    id_inmueble = _crear_inmueble(client, codigo="INM-RES-CONFLICT-VENTA-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9107)
    _insertar_venta_conflictiva(
        db_session,
        id_inmueble=id_inmueble,
        codigo_venta="V-CONFLICT-001",
    )

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-CONFLICT-VENTA-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9107,
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["CONFLICTING_VENTA"]


def test_create_reserva_venta_devuelve_error_si_hay_conflicto_con_reserva_activa(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Donald", apellido="Knuth")
    id_inmueble = _crear_inmueble(client, codigo="INM-RES-CONFLICT-RES-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9108)
    _insertar_reserva_conflictiva(
        db_session,
        id_inmueble=id_inmueble,
        codigo_reserva="RV-ACTIVA-001",
    )

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-CONFLICT-RES-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9108,
        ),
    )

    assert response.status_code == 400
    assert response.json()["details"]["errors"] == ["CONFLICTING_RESERVA"]


def test_create_reserva_venta_hace_rollback_completo_si_falla_relacion(
    client, db_session
) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    _crear_trigger_falla_relacion(db_session)
    id_persona = _crear_persona(client, nombre="John", apellido="Backus")
    id_inmueble_1 = _crear_inmueble(client, codigo="INM-RES-ROLLBACK-001")
    id_inmueble_2 = _crear_inmueble(client, codigo="INM-RES-ROLLBACK-002")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_1, estado_disponibilidad="DISPONIBLE")
    _crear_disponibilidad(client, id_inmueble=id_inmueble_2, estado_disponibilidad="DISPONIBLE")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9109)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-ROLLBACK-001",
            objetos=[
                {"id_inmueble": id_inmueble_1, "id_unidad_funcional": None, "observaciones": "OK"},
                {"id_inmueble": id_inmueble_2, "id_unidad_funcional": None, "observaciones": "FORCE_FAIL"},
            ],
            id_persona=id_persona,
            id_rol=9109,
        ),
    )

    assert response.status_code == 500

    reserva_count = db_session.execute(
        text("SELECT COUNT(*) FROM reserva_venta WHERE codigo_reserva = 'RV-ROLLBACK-001'")
    ).scalar_one()
    objeto_count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM reserva_venta_objeto_inmobiliario
            WHERE observaciones IN ('OK', 'FORCE_FAIL')
            """
        )
    ).scalar_one()
    participacion_count = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'reserva_venta'
            """
        )
    ).scalar_one()

    assert reserva_count == 0
    assert objeto_count == 0
    assert participacion_count == 0


def test_create_reserva_venta_asigna_estado_inicial_valido(client, db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)
    id_persona = _crear_persona(client, nombre="Margaret", apellido="Hamilton")
    id_inmueble = _crear_inmueble(client, codigo="INM-RES-STATE-001")
    _crear_disponibilidad(client, id_inmueble=id_inmueble, estado_disponibilidad="DISPONIBLE")
    _crear_rol_participacion_activo(db_session, id_rol_participacion=9110)

    response = client.post(
        "/api/v1/reservas-venta",
        headers=HEADERS,
        json=_payload_base(
            codigo_reserva="RV-STATE-001",
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            id_persona=id_persona,
            id_rol=9110,
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["estado_reserva"] == "borrador"

    reserva_row = db_session.execute(
        text(
            """
            SELECT estado_reserva
            FROM reserva_venta
            WHERE id_reserva_venta = :id_reserva_venta
            """
        ),
        {"id_reserva_venta": body["data"]["id_reserva_venta"]},
    ).mappings().one()

    assert reserva_row["estado_reserva"] == "borrador"


def test_patch_multiobjeto_crea_indices_minimos_en_tabla_relacion(db_session) -> None:
    _apply_reserva_multiobjeto_patch(db_session)

    rows = db_session.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND tablename = 'reserva_venta_objeto_inmobiliario'
              AND indexname IN (
                  'idx_rvo_reserva',
                  'idx_rvo_inmueble',
                  'idx_rvo_unidad'
              )
            ORDER BY indexname
            """
        )
    ).scalars().all()

    assert rows == [
        "idx_rvo_inmueble",
        "idx_rvo_reserva",
        "idx_rvo_unidad",
    ]
