from sqlalchemy import text
from sqlalchemy.orm import Session


PLAN_PAGO_VENTA_COLUMNS = {
    "id_plan_pago_venta",
    "uid_global",
    "version_registro",
    "created_at",
    "updated_at",
    "deleted_at",
    "id_instalacion_origen",
    "id_instalacion_ultima_modificacion",
    "op_id_alta",
    "op_id_ultima_modificacion",
    "id_venta",
    "metodo_plan_pago",
    "estado_plan_pago",
    "moneda",
    "monto_total_plan",
    "cantidad_cuotas",
    "periodicidad",
    "fecha_primer_vencimiento",
    "importe_anticipo",
    "fecha_vencimiento_anticipo",
    "regla_redondeo",
    "observaciones",
}


GENERACION_CRONOGRAMA_COLUMNS = {
    "id_generacion_cronograma_financiero",
    "uid_global",
    "version_registro",
    "created_at",
    "updated_at",
    "deleted_at",
    "id_instalacion_origen",
    "id_instalacion_ultima_modificacion",
    "op_id_alta",
    "op_id_ultima_modificacion",
    "id_relacion_generadora",
    "id_plan_pago_venta",
    "tipo_generacion",
    "clave_generacion",
    "estado_generacion",
    "fecha_generacion",
    "observaciones",
}


PLAN_PAGO_VENTA_BLOQUE_COLUMNS = {
    "id_plan_pago_venta_bloque",
    "uid_global",
    "version_registro",
    "created_at",
    "updated_at",
    "deleted_at",
    "id_instalacion_origen",
    "id_instalacion_ultima_modificacion",
    "op_id_alta",
    "op_id_ultima_modificacion",
    "id_plan_pago_venta",
    "numero_bloque",
    "tipo_bloque",
    "etiqueta_bloque",
    "clave_bloque",
    "cantidad_cuotas",
    "importe_total_bloque",
    "importe_cuota",
    "fecha_vencimiento",
    "fecha_primer_vencimiento",
    "periodicidad",
    "regla_redondeo",
    "concepto_financiero_codigo",
    "observaciones",
}


OBLIGACION_FINANCIERA_V2_COLUMNS = {
    "id_generacion_cronograma_financiero",
    "id_plan_pago_venta_bloque",
    "numero_obligacion",
    "tipo_item_cronograma",
    "etiqueta_obligacion",
    "clave_funcional_origen",
}


EXPECTED_CONSTRAINTS_BY_TABLE = {
    "plan_pago_venta": {
        "fk_plan_pago_venta_venta",
        "chk_plan_pago_venta_deleted_at",
        "chk_plan_pago_venta_metodo",
        "chk_plan_pago_venta_estado",
        "chk_plan_pago_venta_monto",
        "chk_plan_pago_venta_cantidad",
        "chk_plan_pago_venta_importe_anticipo",
    },
    "generacion_cronograma_financiero": {
        "fk_gcf_relacion_generadora",
        "fk_gcf_plan_pago_venta",
        "chk_gcf_deleted_at",
        "chk_gcf_tipo",
        "chk_gcf_estado",
    },
    "plan_pago_venta_bloque": {
        "fk_ppvb_plan_pago_venta",
        "chk_ppvb_deleted_at",
        "chk_ppvb_numero_bloque",
        "chk_ppvb_tipo_bloque",
        "chk_ppvb_cantidad_cuotas",
        "chk_ppvb_importe_total_bloque",
        "chk_ppvb_importe_cuota",
        "chk_ppvb_tramo_cuotas_requeridos",
        "chk_ppvb_pago_unico_requeridos",
    },
    "obligacion_financiera": {
        "fk_obl_generacion_cronograma",
        "fk_obl_plan_pago_venta_bloque",
        "chk_obl_numero_obligacion",
        "chk_obl_tipo_item_cronograma",
    },
}


EXPECTED_INDEXES = {
    "idx_plan_pago_venta_uid_global",
    "idx_plan_pago_venta_venta",
    "uq_plan_pago_venta_activo",
    "idx_gcf_uid_global",
    "idx_gcf_relacion_generadora",
    "idx_gcf_plan_pago_venta",
    "uq_gcf_clave_activa",
    "idx_ppvb_uid_global",
    "idx_ppvb_plan_pago_venta",
    "uq_ppvb_plan_numero",
    "uq_ppvb_plan_clave",
    "idx_obl_generacion_cronograma",
    "idx_obl_plan_pago_venta_bloque",
    "idx_obl_cronograma_orden",
    "uq_obl_cronograma_item_activo",
}


EXPECTED_TRIGGERS_BY_TABLE = {
    "plan_pago_venta": {
        "trg_bi_plan_pago_venta_core_ef",
        "trg_bu_plan_pago_venta_core_ef",
    },
    "generacion_cronograma_financiero": {
        "trg_bi_gcf_core_ef",
        "trg_bu_gcf_core_ef",
    },
    "plan_pago_venta_bloque": {
        "trg_bi_ppvb_core_ef",
        "trg_bu_ppvb_core_ef",
    },
}


def _table_exists(db_session: Session, table_name: str) -> bool:
    return (
        db_session.execute(
            text("SELECT to_regclass(:qualified_name)"),
            {"qualified_name": f"public.{table_name}"},
        ).scalar()
        == table_name
    )


def _columns(db_session: Session, table_name: str) -> set[str]:
    rows = db_session.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = :table_name
            """
        ),
        {"table_name": table_name},
    ).scalars()
    return set(rows)


def _constraints(db_session: Session, table_name: str) -> set[str]:
    rows = db_session.execute(
        text(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = (:qualified_name)::regclass
            """
        ),
        {"qualified_name": f"public.{table_name}"},
    ).scalars()
    return set(rows)


def _constraint_definitions(db_session: Session, table_name: str) -> dict[str, str]:
    rows = db_session.execute(
        text(
            """
            SELECT conname, pg_get_constraintdef(oid) AS definition
            FROM pg_constraint
            WHERE conrelid = (:qualified_name)::regclass
            """
        ),
        {"qualified_name": f"public.{table_name}"},
    ).mappings()
    return {row["conname"]: row["definition"] for row in rows}


def _indexes(db_session: Session) -> set[str]:
    rows = db_session.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            """
        )
    ).scalars()
    return set(rows)


def _index_definitions(db_session: Session) -> dict[str, str]:
    rows = db_session.execute(
        text(
            """
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            """
        )
    ).mappings()
    return {row["indexname"]: row["indexdef"] for row in rows}


def _comments(db_session: Session) -> dict[str, str]:
    row = db_session.execute(
        text(
            """
            SELECT
                obj_description(
                    'public.plan_pago_venta_bloque'::regclass
                ) AS table_comment,
                col_description(
                    'public.plan_pago_venta_bloque'::regclass,
                    (
                        SELECT ordinal_position
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'plan_pago_venta_bloque'
                          AND column_name = 'tipo_bloque'
                    )::integer
                ) AS tipo_bloque_comment,
                col_description(
                    'public.plan_pago_venta_bloque'::regclass,
                    (
                        SELECT ordinal_position
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'plan_pago_venta_bloque'
                          AND column_name = 'clave_bloque'
                    )::integer
                ) AS clave_bloque_comment,
                col_description(
                    'public.plan_pago_venta_bloque'::regclass,
                    (
                        SELECT ordinal_position
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'plan_pago_venta_bloque'
                          AND column_name = 'concepto_financiero_codigo'
                    )::integer
                ) AS concepto_financiero_codigo_comment,
                col_description(
                    'public.obligacion_financiera'::regclass,
                    (
                        SELECT ordinal_position
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'obligacion_financiera'
                          AND column_name = 'id_plan_pago_venta_bloque'
                    )::integer
                ) AS id_plan_pago_venta_bloque_comment
            """
        )
    ).mappings().one()
    return dict(row)


def _triggers(db_session: Session, table_name: str) -> set[str]:
    rows = db_session.execute(
        text(
            """
            SELECT tgname
            FROM pg_trigger
            WHERE tgrelid = (:qualified_name)::regclass
              AND NOT tgisinternal
            """
        ),
        {"qualified_name": f"public.{table_name}"},
    ).scalars()
    return set(rows)


def test_schema_cronograma_v2_planes_venta(db_session: Session) -> None:
    assert _table_exists(db_session, "plan_pago_venta")
    assert _table_exists(db_session, "generacion_cronograma_financiero")
    assert _table_exists(db_session, "plan_pago_venta_bloque")
    assert _table_exists(db_session, "venta_plan_cuota")

    assert not _table_exists(db_session, "plan_pago_venta_cuota")
    assert not _table_exists(db_session, "plan_pago_venta_tramo")

    assert PLAN_PAGO_VENTA_COLUMNS <= _columns(db_session, "plan_pago_venta")
    assert GENERACION_CRONOGRAMA_COLUMNS <= _columns(
        db_session, "generacion_cronograma_financiero"
    )
    assert PLAN_PAGO_VENTA_BLOQUE_COLUMNS <= _columns(
        db_session, "plan_pago_venta_bloque"
    )
    assert OBLIGACION_FINANCIERA_V2_COLUMNS <= _columns(
        db_session, "obligacion_financiera"
    )

    for table_name, expected_constraints in EXPECTED_CONSTRAINTS_BY_TABLE.items():
        assert expected_constraints <= _constraints(db_session, table_name)

    assert EXPECTED_INDEXES <= _indexes(db_session)

    for table_name, expected_triggers in EXPECTED_TRIGGERS_BY_TABLE.items():
        assert expected_triggers <= _triggers(db_session, table_name)

    ppvb_constraints = _constraint_definitions(db_session, "plan_pago_venta_bloque")
    assert "importe_total_bloque >" in ppvb_constraints[
        "chk_ppvb_importe_total_bloque"
    ]

    index_definitions = _index_definitions(db_session)
    assert "UNIQUE" in index_definitions["uq_ppvb_plan_numero"]
    assert "WHERE (deleted_at IS NULL)" in index_definitions["uq_ppvb_plan_numero"]
    assert "UNIQUE" in index_definitions["uq_ppvb_plan_clave"]
    assert "WHERE (deleted_at IS NULL)" in index_definitions["uq_ppvb_plan_clave"]
    assert "WHERE (deleted_at IS NULL)" in index_definitions[
        "idx_obl_plan_pago_venta_bloque"
    ]

    comments = _comments(db_session)
    assert "No representa deuda" in comments["table_comment"]
    assert "Tipo estructural" in comments["tipo_bloque_comment"]
    assert "Clave estable" in comments["clave_bloque_comment"]
    concepto_comment = comments["concepto_financiero_codigo_comment"]
    assert concepto_comment is None or "sin FK" in concepto_comment
    assert "no es la clave de idempotencia" in comments[
        "id_plan_pago_venta_bloque_comment"
    ]
