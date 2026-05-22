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
