from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.infrastructure.persistence.repositories.comercial_repository import (
    ComercialRepository,
)
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import (
    _crear_disponibilidad,
    _crear_inmueble,
    _crear_persona,
    _crear_rol_participacion_activo,
    _crear_unidad_funcional,
    _insertar_reserva_conflictiva,
)


def _payload_venta_directa(
    *,
    codigo_venta: str,
    monto_total: Decimal | None = Decimal("150000.00"),
) -> dict:
    now = datetime.now(UTC)
    op_id = UUID(HEADERS["X-Op-Id"])
    return {
        "uid_global": str(uuid4()),
        "version_registro": 1,
        "created_at": now,
        "updated_at": now,
        "id_instalacion_origen": 1,
        "id_instalacion_ultima_modificacion": 1,
        "op_id_alta": op_id,
        "op_id_ultima_modificacion": op_id,
        "codigo_venta": codigo_venta,
        "fecha_venta": datetime(2026, 5, 22, 10, 0, tzinfo=UTC),
        "estado_venta": "borrador",
        "monto_total": monto_total,
        "observaciones": "Venta directa tx",
    }


def _payload_objeto(
    *,
    id_inmueble: int | None,
    id_unidad_funcional: int | None = None,
    precio_asignado: Decimal = Decimal("150000.00"),
) -> dict:
    now = datetime.now(UTC)
    op_id = UUID(HEADERS["X-Op-Id"])
    return {
        "uid_global": str(uuid4()),
        "version_registro": 1,
        "created_at": now,
        "updated_at": now,
        "id_instalacion_origen": 1,
        "id_instalacion_ultima_modificacion": 1,
        "op_id_alta": op_id,
        "op_id_ultima_modificacion": op_id,
        "id_inmueble": id_inmueble,
        "id_unidad_funcional": id_unidad_funcional,
        "precio_asignado": precio_asignado,
        "observaciones": "Objeto venta directa tx",
    }


def _payload_comprador(*, id_persona: int, id_rol_participacion: int) -> dict:
    now = datetime.now(UTC)
    op_id = UUID(HEADERS["X-Op-Id"])
    return {
        "uid_global": str(uuid4()),
        "version_registro": 1,
        "created_at": now,
        "updated_at": now,
        "id_instalacion_origen": 1,
        "id_instalacion_ultima_modificacion": 1,
        "op_id_alta": op_id,
        "op_id_ultima_modificacion": op_id,
        "id_persona": id_persona,
        "id_rol_participacion": id_rol_participacion,
        "fecha_desde": date(2026, 5, 22),
        "fecha_hasta": None,
        "observaciones": "Comprador venta directa tx",
    }


def _crear_base_venta_directa(client, db_session, *, codigo_inmueble: str):
    id_persona = _crear_persona(client, nombre="Ada", apellido="Lovelace")
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9701,
        codigo_rol="COMPRADOR",
    )
    id_inmueble = _crear_inmueble(client, codigo=codigo_inmueble)
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )
    return id_inmueble, id_persona, id_rol


def _insertar_venta_conflictiva(
    db_session,
    *,
    codigo_venta: str,
    id_inmueble: int | None = None,
    id_unidad_funcional: int | None = None,
) -> None:
    venta_row = db_session.execute(
        text(
            """
            INSERT INTO venta (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, id_reserva_venta,
                codigo_venta, fecha_venta, estado_venta, monto_total, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id, NULL,
                :codigo_venta, TIMESTAMP '2026-05-20 10:00:00', 'activa', 1000.00, NULL
            )
            RETURNING id_venta
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "codigo_venta": codigo_venta},
    ).mappings().one()
    db_session.execute(
        text(
            """
            INSERT INTO venta_objeto_inmobiliario (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, id_venta,
                id_inmueble, id_unidad_funcional, precio_asignado, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id, :id_venta,
                :id_inmueble, :id_unidad_funcional, 1000.00, NULL
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_venta": venta_row["id_venta"],
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
        },
    )


def _insertar_ocupacion_activa(
    db_session, *, id_inmueble: int | None = None, id_unidad_funcional: int | None = None
) -> None:
    db_session.execute(
        text(
            """
            INSERT INTO ocupacion (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_inmueble, id_unidad_funcional, tipo_ocupacion, fecha_desde, fecha_hasta,
                observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_inmueble, :id_unidad_funcional, 'ALQUILER',
                TIMESTAMP '2026-05-01 00:00:00', NULL, NULL
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
        },
    )


def _insertar_reserva_conflictiva_objeto(
    db_session,
    *,
    codigo_reserva: str,
    id_inmueble: int | None = None,
    id_unidad_funcional: int | None = None,
) -> None:
    reserva_row = db_session.execute(
        text(
            """
            INSERT INTO reserva_venta (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                codigo_reserva, fecha_reserva, estado_reserva, fecha_vencimiento, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :codigo_reserva, TIMESTAMP '2026-05-20 10:00:00', 'activa',
                TIMESTAMP '2026-05-30 10:00:00', NULL
            )
            RETURNING id_reserva_venta
            """
        ),
        {"op_id": HEADERS["X-Op-Id"], "codigo_reserva": codigo_reserva},
    ).mappings().one()
    db_session.execute(
        text(
            """
            INSERT INTO reserva_venta_objeto_inmobiliario (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion, id_reserva_venta,
                id_inmueble, id_unidad_funcional, observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id, :id_reserva_venta,
                :id_inmueble, :id_unidad_funcional, NULL
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_reserva_venta": reserva_row["id_reserva_venta"],
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
        },
    )


@pytest.mark.parametrize(
    ("conflicto", "esperado"),
    [
        ("venta", "CONFLICTING_JERARQUIA_INMOBILIARIA"),
        ("reserva", "CONFLICTING_JERARQUIA_INMOBILIARIA"),
        ("ocupacion", "CONFLICTING_JERARQUIA_INMOBILIARIA"),
    ],
)
def test_create_venta_directa_tx_falla_venta_inmueble_por_conflicto_en_uf_hija(
    client, db_session, conflicto: str, esperado: str
) -> None:
    id_inmueble, id_persona, id_rol = _crear_base_venta_directa(
        client, db_session, codigo_inmueble=f"INM-VD-HIJAS-{conflicto}"
    )
    id_uf = _crear_unidad_funcional(client, id_inmueble=id_inmueble, codigo=f"UF-{conflicto}")
    _crear_disponibilidad(
        client, id_unidad_funcional=id_uf, estado_disponibilidad="DISPONIBLE"
    )

    if conflicto == "venta":
        _insertar_venta_conflictiva(
            db_session,
            codigo_venta="VD-CONFLICT-UF-VENTA",
            id_unidad_funcional=id_uf,
        )
    elif conflicto == "reserva":
        _insertar_reserva_conflictiva_objeto(
            db_session,
            codigo_reserva="RV-CONFLICT-UF-RESERVA",
            id_unidad_funcional=id_uf,
        )
    else:
        _insertar_ocupacion_activa(db_session, id_unidad_funcional=id_uf)

    result = ComercialRepository(db_session)._create_venta_directa_tx(
        _payload_venta_directa(codigo_venta=f"VD-TX-HIJA-{conflicto}"),
        [_payload_objeto(id_inmueble=id_inmueble)],
        [_payload_comprador(id_persona=id_persona, id_rol_participacion=id_rol)],
    )
    assert result == {"status": esperado}


@pytest.mark.parametrize(("conflicto",), [("venta",), ("reserva",), ("ocupacion",)])
def test_create_venta_directa_tx_falla_venta_uf_por_conflicto_en_inmueble_padre(
    client, db_session, conflicto: str
) -> None:
    id_inmueble, id_persona, id_rol = _crear_base_venta_directa(
        client, db_session, codigo_inmueble=f"INM-VD-PADRE-{conflicto}"
    )
    id_uf = _crear_unidad_funcional(client, id_inmueble=id_inmueble, codigo=f"UF-P-{conflicto}")
    _crear_disponibilidad(
        client, id_unidad_funcional=id_uf, estado_disponibilidad="DISPONIBLE"
    )

    if conflicto == "venta":
        _insertar_venta_conflictiva(
            db_session, codigo_venta="VD-CONFLICT-PADRE-VENTA", id_inmueble=id_inmueble
        )
    elif conflicto == "reserva":
        _insertar_reserva_conflictiva(
            db_session, id_inmueble=id_inmueble, codigo_reserva="RV-CONFLICT-PADRE-RES"
        )
    else:
        _insertar_ocupacion_activa(db_session, id_inmueble=id_inmueble)

    result = ComercialRepository(db_session)._create_venta_directa_tx(
        _payload_venta_directa(codigo_venta=f"VD-TX-PADRE-{conflicto}"),
        [_payload_objeto(id_inmueble=None, id_unidad_funcional=id_uf)],
        [_payload_comprador(id_persona=id_persona, id_rol_participacion=id_rol)],
    )
    assert result == {"status": "CONFLICTING_JERARQUIA_INMOBILIARIA"}


def test_create_venta_directa_tx_crea_uf_si_no_hay_conflicto_jerarquico(
    client, db_session
) -> None:
    id_inmueble, id_persona, id_rol = _crear_base_venta_directa(
        client, db_session, codigo_inmueble="INM-VD-UF-SIN-CONFLICTO"
    )
    id_uf = _crear_unidad_funcional(client, id_inmueble=id_inmueble, codigo="UF-OK")
    _crear_disponibilidad(
        client, id_unidad_funcional=id_uf, estado_disponibilidad="DISPONIBLE"
    )

    result = ComercialRepository(db_session)._create_venta_directa_tx(
        _payload_venta_directa(codigo_venta="VD-TX-UF-SIN-CONFLICTO"),
        [_payload_objeto(id_inmueble=None, id_unidad_funcional=id_uf)],
        [_payload_comprador(id_persona=id_persona, id_rol_participacion=id_rol)],
    )
    assert result["status"] == "OK"


def test_create_venta_directa_tx_crea_borrador_objeto_y_comprador(
    client, db_session
) -> None:
    id_inmueble, id_persona, id_rol = _crear_base_venta_directa(
        client,
        db_session,
        codigo_inmueble="INM-VD-TX-001",
    )
    repository = ComercialRepository(db_session)

    result = repository._create_venta_directa_tx(
        _payload_venta_directa(codigo_venta="VD-TX-001"),
        [_payload_objeto(id_inmueble=id_inmueble)],
        [_payload_comprador(id_persona=id_persona, id_rol_participacion=id_rol)],
    )

    assert result["status"] == "OK"
    data = result["data"]
    assert data["codigo_venta"] == "VD-TX-001"
    assert data["estado_venta"] == "borrador"
    assert data["version_registro"] == 1

    venta_row = db_session.execute(
        text(
            """
            SELECT id_reserva_venta, estado_venta
            FROM venta
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": data["id_venta"]},
    ).mappings().one()
    assert venta_row["id_reserva_venta"] is None
    assert venta_row["estado_venta"] == "borrador"

    objeto_row = db_session.execute(
        text(
            """
            SELECT id_venta, id_inmueble, id_unidad_funcional, precio_asignado
            FROM venta_objeto_inmobiliario
            WHERE id_venta = :id_venta
            """
        ),
        {"id_venta": data["id_venta"]},
    ).mappings().one()
    assert objeto_row["id_inmueble"] == id_inmueble
    assert objeto_row["id_unidad_funcional"] is None
    assert objeto_row["precio_asignado"] == Decimal("150000.00")

    comprador_row = db_session.execute(
        text(
            """
            SELECT id_persona, id_rol_participacion, tipo_relacion, id_relacion
            FROM relacion_persona_rol
            WHERE tipo_relacion = 'venta'
              AND id_relacion = :id_venta
            """
        ),
        {"id_venta": data["id_venta"]},
    ).mappings().one()
    assert comprador_row["id_persona"] == id_persona
    assert comprador_row["id_rol_participacion"] == id_rol
    assert comprador_row["tipo_relacion"] == "venta"


def test_create_venta_directa_tx_falla_si_objeto_no_existe(client, db_session) -> None:
    id_persona = _crear_persona(client, nombre="Obj", apellido="Inexistente")
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9702,
        codigo_rol="COMPRADOR",
    )

    result = ComercialRepository(db_session)._create_venta_directa_tx(
        _payload_venta_directa(codigo_venta="VD-TX-NO-OBJ"),
        [_payload_objeto(id_inmueble=999999)],
        [_payload_comprador(id_persona=id_persona, id_rol_participacion=id_rol)],
    )

    assert result == {"status": "NOT_FOUND_INMUEBLE"}


def test_create_venta_directa_tx_falla_si_objeto_esta_reservado(
    client, db_session
) -> None:
    id_inmueble, id_persona, id_rol = _crear_base_venta_directa(
        client,
        db_session,
        codigo_inmueble="INM-VD-TX-RESERVADO",
    )
    db_session.execute(
        text(
            """
            UPDATE disponibilidad
            SET estado_disponibilidad = 'RESERVADA'
            WHERE id_inmueble = :id_inmueble
              AND deleted_at IS NULL
            """
        ),
        {"id_inmueble": id_inmueble},
    )

    result = ComercialRepository(db_session)._create_venta_directa_tx(
        _payload_venta_directa(codigo_venta="VD-TX-RESERVADO"),
        [_payload_objeto(id_inmueble=id_inmueble)],
        [_payload_comprador(id_persona=id_persona, id_rol_participacion=id_rol)],
    )

    assert result == {"status": "INVALID_DISPONIBILIDAD_STATE"}


def test_create_venta_directa_tx_falla_si_objeto_duplicado(client, db_session) -> None:
    id_inmueble, id_persona, id_rol = _crear_base_venta_directa(
        client,
        db_session,
        codigo_inmueble="INM-VD-TX-DUP",
    )

    result = ComercialRepository(db_session)._create_venta_directa_tx(
        _payload_venta_directa(
            codigo_venta="VD-TX-DUP",
            monto_total=Decimal("300000.00"),
        ),
        [
            _payload_objeto(id_inmueble=id_inmueble),
            _payload_objeto(id_inmueble=id_inmueble),
        ],
        [_payload_comprador(id_persona=id_persona, id_rol_participacion=id_rol)],
    )

    assert result == {"status": "DUPLICATE_VENTA_OBJECTS"}


def test_create_venta_directa_tx_falla_si_hay_reserva_vigente(
    client, db_session
) -> None:
    id_inmueble, id_persona, id_rol = _crear_base_venta_directa(
        client,
        db_session,
        codigo_inmueble="INM-VD-TX-RESERVA-CONFLICTO",
    )
    _insertar_reserva_conflictiva(
        db_session,
        id_inmueble=id_inmueble,
        codigo_reserva="RV-VD-TX-CONFLICTO",
    )

    result = ComercialRepository(db_session)._create_venta_directa_tx(
        _payload_venta_directa(codigo_venta="VD-TX-RESERVA-CONFLICTO"),
        [_payload_objeto(id_inmueble=id_inmueble)],
        [_payload_comprador(id_persona=id_persona, id_rol_participacion=id_rol)],
    )

    assert result == {"status": "CONFLICTING_RESERVA"}


def test_create_venta_directa_tx_falla_si_comprador_no_existe(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VD-TX-COMP-NO")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9703,
        codigo_rol="COMPRADOR",
    )

    result = ComercialRepository(db_session)._create_venta_directa_tx(
        _payload_venta_directa(codigo_venta="VD-TX-COMP-NO"),
        [_payload_objeto(id_inmueble=id_inmueble)],
        [_payload_comprador(id_persona=999999, id_rol_participacion=id_rol)],
    )

    assert result == {"status": "NOT_FOUND_PERSONA"}


def test_create_venta_directa_tx_falla_si_rol_no_es_comprador(
    client, db_session
) -> None:
    id_inmueble = _crear_inmueble(client, codigo="INM-VD-TX-ROL")
    _crear_disponibilidad(
        client,
        id_inmueble=id_inmueble,
        estado_disponibilidad="DISPONIBLE",
    )
    id_persona = _crear_persona(client, nombre="Rol", apellido="Incorrecto")
    id_rol = _crear_rol_participacion_activo(
        db_session,
        id_rol_participacion=9704,
        codigo_rol="VENDEDOR-VD-TX",
    )

    result = ComercialRepository(db_session)._create_venta_directa_tx(
        _payload_venta_directa(codigo_venta="VD-TX-ROL"),
        [_payload_objeto(id_inmueble=id_inmueble)],
        [_payload_comprador(id_persona=id_persona, id_rol_participacion=id_rol)],
    )

    assert result == {"status": "INVALID_ROL_COMPRADOR"}


def test_create_venta_directa_tx_respeta_rollback_externo(client, db_session) -> None:
    id_inmueble, id_persona, id_rol = _crear_base_venta_directa(
        client,
        db_session,
        codigo_inmueble="INM-VD-TX-ROLLBACK",
    )
    repository = ComercialRepository(db_session)

    with pytest.raises(RuntimeError):
        with db_session.begin_nested():
            result = repository._create_venta_directa_tx(
                _payload_venta_directa(codigo_venta="VD-TX-ROLLBACK"),
                [_payload_objeto(id_inmueble=id_inmueble)],
                [
                    _payload_comprador(
                        id_persona=id_persona,
                        id_rol_participacion=id_rol,
                    )
                ],
            )
            assert result["status"] == "OK"
            raise RuntimeError("forced rollback")

    total = db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM venta
            WHERE codigo_venta = 'VD-TX-ROLLBACK'
            """
        )
    ).scalar_one()
    assert total == 0
