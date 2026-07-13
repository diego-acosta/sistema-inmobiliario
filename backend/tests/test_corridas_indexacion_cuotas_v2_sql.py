from sqlalchemy import text


def _columns(db_session, table_name: str) -> set[str]:
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


def _constraints(db_session, table_name: str) -> set[str]:
    rows = db_session.execute(
        text(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = (:table_name)::regclass
            """
        ),
        {"table_name": f"public.{table_name}"},
    ).scalars()
    return set(rows)


def test_tablas_corridas_indexacion_existen(db_session) -> None:
    tablas = set(
        db_session.execute(
            text(
                """
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                  AND tablename LIKE 'corrida_indexacion_financiera%'
                """
            )
        ).scalars()
    )

    assert "corrida_indexacion_financiera" in tablas
    assert "corrida_indexacion_financiera_detalle" in tablas


def test_cabecera_corrida_tiene_columnas_de_identidad_alcance_y_estado(db_session) -> None:
    columnas = _columns(db_session, "corrida_indexacion_financiera")

    assert {
        "id_corrida_indexacion_financiera",
        "uid_global",
        "version_registro",
        "id_plan_pago_venta",
        "id_plan_pago_venta_bloque",
        "id_plan_pago_venta_bloque_indexacion",
        "origen_corrida",
        "estado_corrida",
        "hash_corrida",
        "op_id",
        "payload_hash",
    }.issubset(columnas)


def test_cabecera_corrida_tiene_columnas_de_indices_y_totales(db_session) -> None:
    columnas = _columns(db_session, "corrida_indexacion_financiera")

    assert {
        "id_indice_financiero",
        "id_indice_financiero_valor_base",
        "id_indice_financiero_valor_aplicado",
        "fecha_base",
        "fecha_corte",
        "valor_base_indice",
        "valor_aplicado_indice",
        "total_analizadas",
        "total_elegibles",
        "total_excluidas",
        "total_aplicadas",
    }.issubset(columnas)


def test_detalle_corrida_tiene_columnas_de_obligacion_y_resultado(db_session) -> None:
    columnas = _columns(db_session, "corrida_indexacion_financiera_detalle")

    assert {
        "id_corrida_indexacion_financiera_detalle",
        "id_corrida_indexacion_financiera",
        "id_obligacion_financiera",
        "version_esperada",
        "version_resultante",
        "capital_base",
        "coeficiente_indexacion",
        "ajuste_anterior",
        "ajuste_nuevo",
        "importe_anterior",
        "importe_nuevo",
        "saldo_anterior",
        "saldo_nuevo",
        "elegibilidad",
    }.issubset(columnas)


def test_corridas_indexacion_tienen_constraints_principales(db_session) -> None:
    cabecera = _constraints(db_session, "corrida_indexacion_financiera")
    detalle = _constraints(db_session, "corrida_indexacion_financiera_detalle")

    assert {
        "corrida_indexacion_financiera_pkey",
        "uq_cif_uid_global",
        "chk_cif_estado",
        "chk_cif_origen",
        "chk_cif_totales_no_negativos",
    }.issubset(cabecera)
    assert {
        "corrida_indexacion_financiera_detalle_pkey",
        "uq_cifd_uid_global",
        "chk_cifd_elegibilidad",
        "fk_cifd_corrida",
        "fk_cifd_obligacion_financiera",
    }.issubset(detalle)


def test_patch_corridas_indexacion_es_idempotente(db_session) -> None:
    db_session.execute(
        text("SELECT to_regclass('public.corrida_indexacion_financiera')")
    ).scalar_one()
    db_session.execute(
        text("SELECT to_regclass('public.corrida_indexacion_financiera_detalle')")
    ).scalar_one()

    assert db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname IN (
                'idx_cif_estado_corrida',
                'idx_cif_plan_bloque',
                'idx_cif_op_id',
                'idx_cifd_corrida',
                'idx_cifd_obligacion'
              )
            """
        )
    ).scalar_one() == 5
