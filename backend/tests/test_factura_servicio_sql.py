import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

from app.config.database import engine
from tests.test_disponibilidades_create import HEADERS


OP_ID = HEADERS["X-Op-Id"]


# ─── helpers ────────────────────────────────────────────────────────────────


def _crear_inmueble(db_session, *, codigo: str) -> int:
    row = db_session.execute(
        text("""
            INSERT INTO inmueble (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                codigo_inmueble, nombre_inmueble,
                estado_administrativo, estado_juridico
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :codigo, :nombre,
                'ACTIVO', 'REGULAR'
            )
            RETURNING id_inmueble
        """),
        {"op_id": OP_ID, "codigo": codigo, "nombre": f"Inmueble {codigo}"},
    ).mappings().one()
    return row["id_inmueble"]


def _crear_unidad_funcional(db_session, *, id_inmueble: int, codigo: str) -> int:
    row = db_session.execute(
        text("""
            INSERT INTO unidad_funcional (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_inmueble, codigo_unidad, nombre_unidad,
                estado_administrativo, estado_operativo
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_inmueble, :codigo, :nombre,
                'ACTIVA', 'DISPONIBLE'
            )
            RETURNING id_unidad_funcional
        """),
        {"op_id": OP_ID, "id_inmueble": id_inmueble, "codigo": codigo, "nombre": f"Unidad {codigo}"},
    ).mappings().one()
    return row["id_unidad_funcional"]


def _crear_servicio(db_session, *, codigo: str) -> int:
    row = db_session.execute(
        text("""
            INSERT INTO servicio (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                codigo_servicio, nombre_servicio, estado_servicio
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :codigo, :nombre, 'ACTIVO'
            )
            RETURNING id_servicio
        """),
        {"op_id": OP_ID, "codigo": codigo, "nombre": f"Servicio {codigo}"},
    ).mappings().one()
    return row["id_servicio"]


def _asociar_inmueble_servicio(db_session, *, id_inmueble: int, id_servicio: int) -> None:
    db_session.execute(
        text("""
            INSERT INTO inmueble_servicio (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_inmueble, id_servicio, estado
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_inmueble, :id_servicio, 'ACTIVO'
            )
        """),
        {"op_id": OP_ID, "id_inmueble": id_inmueble, "id_servicio": id_servicio},
    )


def _asociar_unidad_funcional_servicio(
    db_session, *, id_unidad_funcional: int, id_servicio: int
) -> None:
    db_session.execute(
        text("""
            INSERT INTO unidad_funcional_servicio (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_unidad_funcional, id_servicio, estado
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_unidad_funcional, :id_servicio, 'ACTIVO'
            )
        """),
        {"op_id": OP_ID, "id_unidad_funcional": id_unidad_funcional, "id_servicio": id_servicio},
    )


def _insert_factura_servicio(
    db_session,
    *,
    id_servicio: int,
    id_inmueble: int | None,
    id_unidad_funcional: int | None,
    proveedor: str = "Proveedor Test SA",
    numero_factura: str,
    fecha_emision: str = "2026-01-15",
    fecha_vencimiento: str | None = "2026-02-15",
    periodo_desde: str | None = "2026-01-01",
    periodo_hasta: str | None = "2026-01-31",
    importe_total: str = "1500.00",
) -> int:
    row = db_session.execute(
        text("""
            INSERT INTO factura_servicio (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_servicio, id_inmueble, id_unidad_funcional,
                proveedor, numero_factura,
                fecha_emision, fecha_vencimiento,
                periodo_desde, periodo_hasta,
                importe_total
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_servicio, :id_inmueble, :id_unidad_funcional,
                :proveedor, :numero_factura,
                :fecha_emision, :fecha_vencimiento,
                :periodo_desde, :periodo_hasta,
                :importe_total
            )
            RETURNING id_factura_servicio
        """),
        {
            "op_id": OP_ID,
            "id_servicio": id_servicio,
            "id_inmueble": id_inmueble,
            "id_unidad_funcional": id_unidad_funcional,
            "proveedor": proveedor,
            "numero_factura": numero_factura,
            "fecha_emision": fecha_emision,
            "fecha_vencimiento": fecha_vencimiento,
            "periodo_desde": periodo_desde,
            "periodo_hasta": periodo_hasta,
            "importe_total": importe_total,
        },
    ).mappings().one()
    return row["id_factura_servicio"]


# ─── tests de inserción válida ───────────────────────────────────────────────


def test_insert_valido_por_inmueble(db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-INM-001")
    id_servicio = _crear_servicio(db_session, codigo="FS-SRV-001")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    id_fs = _insert_factura_servicio(
        db_session,
        id_servicio=id_servicio,
        id_inmueble=id_inmueble,
        id_unidad_funcional=None,
        numero_factura="FAC-INM-001",
    )

    row = db_session.execute(
        text("""
            SELECT estado_factura_servicio, id_inmueble, id_unidad_funcional
            FROM factura_servicio
            WHERE id_factura_servicio = :id
        """),
        {"id": id_fs},
    ).mappings().one()
    assert row["estado_factura_servicio"] == "REGISTRADA"
    assert row["id_inmueble"] == id_inmueble
    assert row["id_unidad_funcional"] is None


def test_insert_valido_por_unidad_funcional(db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-INM-002")
    id_uf = _crear_unidad_funcional(db_session, id_inmueble=id_inmueble, codigo="FS-UF-002")
    id_servicio = _crear_servicio(db_session, codigo="FS-SRV-002")
    _asociar_unidad_funcional_servicio(
        db_session, id_unidad_funcional=id_uf, id_servicio=id_servicio
    )

    id_fs = _insert_factura_servicio(
        db_session,
        id_servicio=id_servicio,
        id_inmueble=None,
        id_unidad_funcional=id_uf,
        numero_factura="FAC-UF-002",
    )

    row = db_session.execute(
        text("""
            SELECT estado_factura_servicio, id_inmueble, id_unidad_funcional
            FROM factura_servicio
            WHERE id_factura_servicio = :id
        """),
        {"id": id_fs},
    ).mappings().one()
    assert row["estado_factura_servicio"] == "REGISTRADA"
    assert row["id_inmueble"] is None
    assert row["id_unidad_funcional"] == id_uf


# ─── tests de XOR ────────────────────────────────────────────────────────────


def test_xor_ambos_null_falla(db_session) -> None:
    id_servicio = _crear_servicio(db_session, codigo="FS-SRV-003")

    # El trigger BEFORE INSERT valida XOR antes que el CHECK constraint
    with pytest.raises(ProgrammingError):
        db_session.execute(
            text("""
                INSERT INTO factura_servicio (
                    uid_global, version_registro, created_at, updated_at,
                    id_instalacion_origen, id_instalacion_ultima_modificacion,
                    op_id_alta, op_id_ultima_modificacion,
                    id_servicio, id_inmueble, id_unidad_funcional,
                    proveedor, numero_factura, fecha_emision, importe_total
                )
                VALUES (
                    gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                    1, 1, :op_id, :op_id,
                    :id_servicio, NULL, NULL,
                    'Proveedor Test', 'FAC-NULL-003', '2026-01-15', 100
                )
            """),
            {"op_id": OP_ID, "id_servicio": id_servicio},
        )
        db_session.flush()


def test_xor_ambos_informados_falla(db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-INM-004")
    id_uf = _crear_unidad_funcional(db_session, id_inmueble=id_inmueble, codigo="FS-UF-004")
    id_servicio = _crear_servicio(db_session, codigo="FS-SRV-004")

    # El trigger BEFORE INSERT valida XOR antes que el CHECK constraint
    with pytest.raises(ProgrammingError):
        db_session.execute(
            text("""
                INSERT INTO factura_servicio (
                    uid_global, version_registro, created_at, updated_at,
                    id_instalacion_origen, id_instalacion_ultima_modificacion,
                    op_id_alta, op_id_ultima_modificacion,
                    id_servicio, id_inmueble, id_unidad_funcional,
                    proveedor, numero_factura, fecha_emision, importe_total
                )
                VALUES (
                    gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                    1, 1, :op_id, :op_id,
                    :id_servicio, :id_inmueble, :id_uf,
                    'Proveedor Test', 'FAC-BOTH-004', '2026-01-15', 100
                )
            """),
            {
                "op_id": OP_ID,
                "id_servicio": id_servicio,
                "id_inmueble": id_inmueble,
                "id_uf": id_uf,
            },
        )
        db_session.flush()


# ─── test de trigger: asociación servicio ────────────────────────────────────


def test_servicio_no_asociado_a_inmueble_falla(db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-INM-005")
    id_servicio = _crear_servicio(db_session, codigo="FS-SRV-005")
    # Sin crear la asociación en inmueble_servicio deliberadamente

    with pytest.raises(ProgrammingError):
        db_session.execute(
            text("""
                INSERT INTO factura_servicio (
                    uid_global, version_registro, created_at, updated_at,
                    id_instalacion_origen, id_instalacion_ultima_modificacion,
                    op_id_alta, op_id_ultima_modificacion,
                    id_servicio, id_inmueble, id_unidad_funcional,
                    proveedor, numero_factura, fecha_emision, importe_total
                )
                VALUES (
                    gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                    1, 1, :op_id, :op_id,
                    :id_servicio, :id_inmueble, NULL,
                    'Proveedor Test', 'FAC-NOASSOC-005', '2026-01-15', 100
                )
            """),
            {"op_id": OP_ID, "id_servicio": id_servicio, "id_inmueble": id_inmueble},
        )
        db_session.flush()


# ─── tests de unicidad parcial ───────────────────────────────────────────────


def test_duplicado_proveedor_numero_activo_falla(db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-INM-006")
    id_servicio = _crear_servicio(db_session, codigo="FS-SRV-006")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    _insert_factura_servicio(
        db_session,
        id_servicio=id_servicio,
        id_inmueble=id_inmueble,
        id_unidad_funcional=None,
        proveedor="Prov-DUP-006",
        numero_factura="FAC-DUP-006",
    )

    with pytest.raises(IntegrityError):
        _insert_factura_servicio(
            db_session,
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_unidad_funcional=None,
            proveedor="Prov-DUP-006",
            numero_factura="FAC-DUP-006",
        )
        db_session.flush()


def test_duplicado_proveedor_numero_con_soft_delete_permite_reinsercion(db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-INM-007")
    id_servicio = _crear_servicio(db_session, codigo="FS-SRV-007")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    id_original = _insert_factura_servicio(
        db_session,
        id_servicio=id_servicio,
        id_inmueble=id_inmueble,
        id_unidad_funcional=None,
        proveedor="Prov-SD-007",
        numero_factura="FAC-SD-007",
    )

    db_session.execute(
        text("""
            UPDATE factura_servicio
            SET deleted_at = CURRENT_TIMESTAMP
            WHERE id_factura_servicio = :id
        """),
        {"id": id_original},
    )

    # El índice parcial excluye deleted_at IS NOT NULL, por lo que se puede reinsertar
    id_nuevo = _insert_factura_servicio(
        db_session,
        id_servicio=id_servicio,
        id_inmueble=id_inmueble,
        id_unidad_funcional=None,
        proveedor="Prov-SD-007",
        numero_factura="FAC-SD-007",
    )

    assert isinstance(id_nuevo, int)
    assert id_nuevo != id_original


# ─── tests de constraints de valores ─────────────────────────────────────────


def test_importe_negativo_falla(db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-INM-008")
    id_servicio = _crear_servicio(db_session, codigo="FS-SRV-008")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    with pytest.raises(IntegrityError):
        _insert_factura_servicio(
            db_session,
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_unidad_funcional=None,
            numero_factura="FAC-NEG-008",
            importe_total="-0.01",
        )
        db_session.flush()


def test_periodo_invalido_hasta_anterior_a_desde_falla(db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-INM-009")
    id_servicio = _crear_servicio(db_session, codigo="FS-SRV-009")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    with pytest.raises(IntegrityError):
        _insert_factura_servicio(
            db_session,
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_unidad_funcional=None,
            numero_factura="FAC-PERIOD-009",
            periodo_desde="2026-01-31",
            periodo_hasta="2026-01-01",
        )
        db_session.flush()


def test_vencimiento_anterior_a_emision_falla(db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-INM-010")
    id_servicio = _crear_servicio(db_session, codigo="FS-SRV-010")
    _asociar_inmueble_servicio(db_session, id_inmueble=id_inmueble, id_servicio=id_servicio)

    with pytest.raises(IntegrityError):
        _insert_factura_servicio(
            db_session,
            id_servicio=id_servicio,
            id_inmueble=id_inmueble,
            id_unidad_funcional=None,
            numero_factura="FAC-VENC-010",
            fecha_emision="2026-02-15",
            fecha_vencimiento="2026-01-01",
        )
        db_session.flush()


# ─── test de FK inválida ─────────────────────────────────────────────────────


def test_fk_servicio_inexistente_falla(db_session) -> None:
    id_inmueble = _crear_inmueble(db_session, codigo="FS-INM-011")
    # El trigger BEFORE INSERT detecta la ausencia de asociación antes que el FK constraint
    with pytest.raises(ProgrammingError):
        db_session.execute(
            text("""
                INSERT INTO factura_servicio (
                    uid_global, version_registro, created_at, updated_at,
                    id_instalacion_origen, id_instalacion_ultima_modificacion,
                    op_id_alta, op_id_ultima_modificacion,
                    id_servicio, id_inmueble, id_unidad_funcional,
                    proveedor, numero_factura, fecha_emision, importe_total
                )
                VALUES (
                    gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                    1, 1, :op_id, :op_id,
                    999999999, :id_inmueble, NULL,
                    'Proveedor Test', 'FAC-FK-011', '2026-01-15', 100
                )
            """),
            {"op_id": OP_ID, "id_inmueble": id_inmueble},
        )
        db_session.flush()
