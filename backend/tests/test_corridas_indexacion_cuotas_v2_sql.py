from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

PATCH = Path("backend/database/patch_corridas_indexacion_cuotas_v2_20260710.sql")


def _apply_patch(db_session):
    db_session.execute(text(PATCH.read_text()))
    db_session.flush()


def _scalar(db_session, sql, **params):
    return db_session.execute(text(sql), params).scalar()


def _constraint_names(db_session, table):
    rows = db_session.execute(
        text(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = (:table)::regclass
            """
        ),
        {"table": f"public.{table}"},
    ).scalars()
    return set(rows)


def _index_names(db_session, table):
    rows = db_session.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public' AND tablename = :table
            """
        ),
        {"table": table},
    ).scalars()
    return set(rows)


def _exec_raises_integrity(db_session, sql, **params):
    with pytest.raises(IntegrityError):
        db_session.execute(text(sql), params)
        db_session.flush()
    db_session.rollback()
    _apply_patch(db_session)


@pytest.fixture
def corrida_schema(db_session):
    _apply_patch(db_session)
    return db_session


def test_corridas_indexacion_v2_existen_tablas_constraints_indices_core_ef(corrida_schema):
    db = corrida_schema
    assert _scalar(db, "SELECT to_regclass('public.corrida_indexacion_financiera')") == "corrida_indexacion_financiera"
    assert _scalar(db, "SELECT to_regclass('public.corrida_indexacion_financiera_detalle')") == "corrida_indexacion_financiera_detalle"

    for table in ("corrida_indexacion_financiera", "corrida_indexacion_financiera_detalle"):
        columns = set(
            db.execute(
                text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = :table
                    """
                ),
                {"table": table},
            ).scalars()
        )
        assert {
            "uid_global",
            "version_registro",
            "created_at",
            "updated_at",
            "deleted_at",
            "id_instalacion_origen",
            "id_instalacion_ultima_modificacion",
            "op_id_alta",
            "op_id_ultima_modificacion",
        }.issubset(columns)

    constraints = _constraint_names(db, "corrida_indexacion_financiera")
    assert {
        "corrida_indexacion_financiera_pkey",
        "uq_cif_uid_global",
        "fk_cif_bloque_mismo_plan",
        "fk_cif_bloque_indexacion_mismo_bloque",
        "fk_cif_valor_aplicado_mismo_indice",
        "ck_cif_estado",
        "ck_cif_origen",
        "ck_cif_cantidades_no_negativas",
        "ck_cif_importes_no_negativos",
        "ck_cif_reemplazo_no_autoref",
    }.issubset(constraints)

    detail_constraints = _constraint_names(db, "corrida_indexacion_financiera_detalle")
    assert {
        "corrida_indexacion_financiera_detalle_pkey",
        "uq_cifd_uid_global",
        "fk_cifd_corrida",
        "fk_cifd_obligacion",
        "ck_cifd_versiones",
        "ck_cifd_elegibilidad",
        "ck_cifd_importes_no_negativos",
    }.issubset(detail_constraints)

    assert {
        "ux_cif_idempotencia_funcional_activa",
        "idx_cif_plan_bloque",
        "idx_cif_estado",
        "idx_cif_origen",
        "idx_cif_fecha_corte",
        "idx_cif_hash_corrida",
        "idx_cif_pendientes",
        "idx_cif_activas",
    }.issubset(_index_names(db, "corrida_indexacion_financiera"))
    assert {
        "ux_cifd_corrida_obligacion",
        "idx_cifd_obligacion",
        "idx_cifd_elegibilidad",
        "idx_cifd_codigo_error",
        "idx_cifd_elegibles",
    }.issubset(_index_names(db, "corrida_indexacion_financiera_detalle"))


def test_corridas_indexacion_v2_checks_no_persisten_estados_operativos(corrida_schema):
    db = corrida_schema
    definition = _scalar(
        db,
        """
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'ck_cif_estado'
          AND conrelid = 'public.corrida_indexacion_financiera'::regclass
        """,
    )
    assert "PREVISUALIZADA" in definition
    assert "PENDIENTE_APLICACION" in definition
    assert "APLICANDO" not in definition
    assert "APLICADA_PARCIAL" not in definition
    assert "REVERSADA" not in definition

    origin_definition = _scalar(
        db,
        """
        SELECT pg_get_constraintdef(oid)
        FROM pg_constraint
        WHERE conname = 'ck_cif_origen'
          AND conrelid = 'public.corrida_indexacion_financiera'::regclass
        """,
    )
    assert "IMPORTACION_VENTA_HISTORICA" in origin_definition
    assert "REPROCESO_CONTROLADO" in origin_definition


def test_corridas_indexacion_v2_constraints_basicas_sin_fks(corrida_schema):
    db = corrida_schema
    _exec_raises_integrity(
        db,
        """
        INSERT INTO corrida_indexacion_financiera (
            id_plan_pago_venta, id_plan_pago_venta_bloque, id_indice_financiero,
            id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte,
            origen_corrida, estado_corrida, op_id, hash_corrida, cantidad_analizada
        ) VALUES (999999, 999999, 999999, 999999, DATE '2026-06-01', DATE '2026-06-30',
                  'PUBLICACION_INDICE', 'APLICANDO', gen_random_uuid(), 'hash-x', 0)
        """,
    )
    _exec_raises_integrity(
        db,
        """
        INSERT INTO corrida_indexacion_financiera (
            id_plan_pago_venta, id_plan_pago_venta_bloque, id_indice_financiero,
            id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte,
            origen_corrida, estado_corrida, op_id, hash_corrida, cantidad_analizada
        ) VALUES (999999, 999999, 999999, 999999, DATE '2026-06-01', DATE '2026-06-30',
                  'ORIGEN_INVALIDO', 'BORRADOR', gen_random_uuid(), 'hash-x', 0)
        """,
    )
    _exec_raises_integrity(
        db,
        """
        INSERT INTO corrida_indexacion_financiera (
            id_plan_pago_venta, id_plan_pago_venta_bloque, id_indice_financiero,
            id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte,
            origen_corrida, estado_corrida, op_id, hash_corrida, cantidad_analizada
        ) VALUES (999999, 999999, 999999, 999999, DATE '2026-06-01', DATE '2026-06-30',
                  'PUBLICACION_INDICE', 'BORRADOR', gen_random_uuid(), 'hash-x', -1)
        """,
    )
    _exec_raises_integrity(
        db,
        """
        INSERT INTO corrida_indexacion_financiera_detalle (
            id_corrida_indexacion_financiera, id_obligacion_financiera, version_esperada,
            valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad
        ) VALUES (999999, 999999, 0, 1, 1, 1, 'ELEGIBLE')
        """,
    )
    _exec_raises_integrity(
        db,
        """
        INSERT INTO corrida_indexacion_financiera_detalle (
            id_corrida_indexacion_financiera, id_obligacion_financiera, version_esperada,
            capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion,
            ajuste_nuevo, estado_elegibilidad
        ) VALUES (999999, 999999, 1, 100, 1, 1, 1, -0.01, 'ELEGIBLE')
        """,
    )
    _exec_raises_integrity(
        db,
        """
        INSERT INTO corrida_indexacion_financiera_detalle (
            id_corrida_indexacion_financiera, id_obligacion_financiera, version_esperada,
            valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad
        ) VALUES (999999, 999999, 1, 1, 1, 1, 'DESCONOCIDA')
        """,
    )
