from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, ProgrammingError

PATCH = Path("backend/database/patch_corridas_indexacion_cuotas_v2_20260710.sql")
PATCH_PREPARACION = Path("backend/database/patch_preparar_corridas_indexacion_cuotas_v2_20260714.sql")

ESTADOS = (
    "BORRADOR",
    "PREVISUALIZADA",
    "PENDIENTE_APLICACION",
    "APLICADA",
    "FALLIDA",
    "ANULADA",
    "REEMPLAZADA",
)
ORIGENES = (
    "IMPORTACION_VENTA_HISTORICA",
    "ALTA_MANUAL_VENTA_HISTORICA",
    "PUBLICACION_INDICE",
    "REINDEXACION_MANUAL",
    "CORRECCION_INDICE",
    "REPROCESO_CONTROLADO",
)


def _apply_patch(db_session) -> None:
    db_session.execute(text(PATCH.read_text()))
    db_session.flush()


def _scalar(db_session, sql: str, **params):
    return db_session.execute(text(sql), params).scalar()


def _one(db_session, sql: str, **params):
    return db_session.execute(text(sql), params).mappings().one()


def _integrity_error(db_session, sql: str, **params) -> None:
    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(text(sql), params)
            db_session.flush()


def _trigger_rejection(
    db_session,
    sql: str,
    expected_message: str,
    **params,
) -> None:
    with pytest.raises(ProgrammingError) as exc_info:
        with db_session.begin_nested():
            db_session.execute(text(sql), params)
            db_session.flush()
    assert expected_message in str(exc_info.value)


@pytest.fixture
def corrida_schema(db_session):
    _apply_patch(db_session)
    _apply_patch(db_session)
    db_session.execute(text(PATCH_PREPARACION.read_text(encoding="utf-8")))
    db_session.flush()
    return db_session


def _ensure_concept(
    db,
    codigo: str,
    tipo: str = "CAPITAL",
    naturaleza: str = "DEBITO",
) -> int:
    return _scalar(
        db,
        """
        INSERT INTO public.concepto_financiero (
            codigo_concepto_financiero,
            nombre_concepto_financiero,
            tipo_concepto_financiero,
            naturaleza_concepto,
            estado_concepto_financiero
        ) VALUES (
            :codigo,
            :codigo,
            :tipo,
            :naturaleza,
            'ACTIVO'
        )
        ON CONFLICT (codigo_concepto_financiero) DO UPDATE SET
            nombre_concepto_financiero = EXCLUDED.nombre_concepto_financiero
        RETURNING id_concepto_financiero
        """,
        codigo=codigo,
        tipo=tipo,
        naturaleza=naturaleza,
    )


def _create_indice(db, codigo: str):
    indice = _scalar(
        db,
        """
        INSERT INTO public.indice_financiero (
            codigo_indice_financiero, nombre_indice_financiero, tipo_indice,
            unidad_medida, frecuencia_publicacion, estado_indice_financiero
        ) VALUES (:codigo, :codigo, 'PRECIO', 'PUNTOS', 'MENSUAL', 'ACTIVO')
        RETURNING id_indice_financiero
        """,
        codigo=codigo,
    )
    base = _scalar(
        db,
        """
        INSERT INTO public.indice_financiero_valor (
            id_indice_financiero, fecha_valor, valor_indice,
            fecha_publicacion, estado_valor_indice
        ) VALUES (:indice, DATE '2026-01-01', 100.00000000, DATE '2026-01-02', 'PUBLICADO')
        RETURNING id_indice_financiero_valor
        """,
        indice=indice,
    )
    aplicado = _scalar(
        db,
        """
        INSERT INTO public.indice_financiero_valor (
            id_indice_financiero, fecha_valor, valor_indice,
            fecha_publicacion, estado_valor_indice
        ) VALUES (:indice, DATE '2026-06-01', 125.00000000, DATE '2026-06-02', 'PUBLICADO')
        RETURNING id_indice_financiero_valor
        """,
        indice=indice,
    )
    return {"id": indice, "base": base, "aplicado": aplicado}


def _create_plan_bloque(db, codigo: str):
    venta = _scalar(
        db,
        """
        INSERT INTO public.venta (codigo_venta, fecha_venta, estado_venta, monto_total, tipo_plan_financiero, moneda)
        VALUES (:codigo, CURRENT_TIMESTAMP, 'BORRADOR', 1000.00, 'CUOTAS_FIJAS', 'ARS')
        RETURNING id_venta
        """,
        codigo=f"VENTA-{codigo}",
    )
    plan = _scalar(
        db,
        """
        INSERT INTO public.plan_pago_venta (id_venta, metodo_plan_pago, estado_plan_pago, moneda, monto_total_plan)
        VALUES (:venta, 'CRONOGRAMA_DEFINIDO', 'BORRADOR', 'ARS', 1000.00)
        RETURNING id_plan_pago_venta
        """,
        venta=venta,
    )
    bloque = _scalar(
        db,
        """
        INSERT INTO public.plan_pago_venta_bloque (
            id_plan_pago_venta, numero_bloque, tipo_bloque, clave_bloque,
            cantidad_cuotas, importe_total_bloque, importe_cuota,
            fecha_primer_vencimiento, periodicidad
        ) VALUES (:plan, 1, 'TRAMO_CUOTAS', :clave, 1, 1000.00, 1000.00, DATE '2026-07-10', 'MENSUAL')
        RETURNING id_plan_pago_venta_bloque
        """,
        plan=plan,
        clave=f"BLOQUE-{codigo}",
    )
    return {"venta": venta, "plan": plan, "bloque": bloque}


def _create_context(db):
    capital = _ensure_concept(db, "CAPITAL_VENTA", "CAPITAL")
    ajuste = _ensure_concept(db, "AJUSTE_INDEXACION", "AJUSTE")
    otro = _ensure_concept(db, "OTRO_TEST_INDEXACION", "AJUSTE")

    indice = _create_indice(db, "IDX-CIF-1")
    otro_indice = _create_indice(db, "IDX-CIF-2")
    plan = _create_plan_bloque(db, "A")
    otro_plan = _create_plan_bloque(db, "B")

    config = _scalar(
        db,
        """
        INSERT INTO public.plan_pago_venta_bloque_indexacion (
            id_plan_pago_venta_bloque, id_indice_financiero, fecha_base_indice,
            valor_base_indice, modo_indexacion, base_calculo_indexacion,
            tipo_generacion_indexada, politica_valor_no_disponible
        ) VALUES (:bloque, :indice, DATE '2026-01-01', 100.00000000,
                  'POR_COEFICIENTE', 'CAPITAL_INICIAL_BLOQUE', 'DEFINITIVA', 'ERROR_SI_NO_EXISTE')
        RETURNING id_plan_pago_venta_bloque_indexacion
        """,
        bloque=plan["bloque"],
        indice=indice["id"],
    )
    config_otro_indice = _scalar(
        db,
        """
        INSERT INTO public.plan_pago_venta_bloque_indexacion (
            id_plan_pago_venta_bloque, id_indice_financiero, fecha_base_indice,
            valor_base_indice, modo_indexacion, base_calculo_indexacion,
            tipo_generacion_indexada, politica_valor_no_disponible
        ) VALUES (:bloque, :indice, DATE '2026-01-01', 200.00000000,
                  'POR_COEFICIENTE', 'CAPITAL_INICIAL_BLOQUE', 'DEFINITIVA', 'ERROR_SI_NO_EXISTE')
        RETURNING id_plan_pago_venta_bloque_indexacion
        """,
        bloque=otro_plan["bloque"],
        indice=otro_indice["id"],
    )

    relacion = _scalar(
        db,
        """
        INSERT INTO public.relacion_generadora (tipo_origen, id_origen, estado_relacion_generadora)
        VALUES ('venta', :venta, 'ACTIVA')
        RETURNING id_relacion_generadora
        """,
        venta=plan["venta"],
    )
    generacion = _scalar(
        db,
        """
        INSERT INTO public.generacion_cronograma_financiero (
            id_relacion_generadora, id_plan_pago_venta, tipo_generacion, clave_generacion, estado_generacion
        ) VALUES (:relacion, :plan, 'PLAN_PAGO_VENTA_V2', :clave, 'GENERADA')
        RETURNING id_generacion_cronograma_financiero
        """,
        relacion=relacion,
        plan=plan["plan"],
        clave=f"GCF-{plan['plan']}",
    )
    generacion_otro_plan = _scalar(
        db,
        """
        INSERT INTO public.generacion_cronograma_financiero (
            id_relacion_generadora, id_plan_pago_venta, tipo_generacion, clave_generacion, estado_generacion
        ) VALUES (:relacion, :plan, 'PLAN_PAGO_VENTA_V2', :clave, 'GENERADA')
        RETURNING id_generacion_cronograma_financiero
        """,
        relacion=relacion,
        plan=otro_plan["plan"],
        clave=f"GCF-{otro_plan['plan']}",
    )

    obligacion = _scalar(
        db,
        """
        INSERT INTO public.obligacion_financiera (
            id_relacion_generadora, fecha_emision, fecha_vencimiento, importe_total,
            saldo_pendiente, moneda, estado_obligacion, es_proyectada,
            id_generacion_cronograma_financiero, id_plan_pago_venta_bloque,
            numero_obligacion, tipo_item_cronograma, clave_funcional_origen
        ) VALUES (:relacion, DATE '2026-07-01', DATE '2026-07-10', 1000.00,
                  1000.00, 'ARS', 'PROYECTADA', true, :generacion, :bloque,
                  1, 'CUOTA', :clave)
        RETURNING id_obligacion_financiera
        """,
        relacion=relacion,
        generacion=generacion,
        bloque=plan["bloque"],
        clave="OBL-CIF-1",
    )
    otra_obligacion = _scalar(
        db,
        """
        INSERT INTO public.obligacion_financiera (
            id_relacion_generadora, fecha_emision, fecha_vencimiento, importe_total,
            saldo_pendiente, moneda, estado_obligacion, es_proyectada,
            id_generacion_cronograma_financiero, id_plan_pago_venta_bloque,
            numero_obligacion, tipo_item_cronograma, clave_funcional_origen
        ) VALUES (:relacion, DATE '2026-07-01', DATE '2026-07-10', 500.00,
                  500.00, 'ARS', 'PROYECTADA', true, :generacion, :bloque,
                  2, 'CUOTA', :clave)
        RETURNING id_obligacion_financiera
        """,
        relacion=relacion,
        generacion=generacion,
        bloque=plan["bloque"],
        clave="OBL-CIF-2",
    )

    comp_capital = _insert_composicion(db, obligacion, capital, 1000)
    comp_ajuste = _insert_composicion(db, obligacion, ajuste, 250)
    comp_otro_concepto = _insert_composicion(db, obligacion, otro, 10)
    comp_capital_otra_obl = _insert_composicion(db, otra_obligacion, capital, 500)
    comp_ajuste_otra_obl = _insert_composicion(db, otra_obligacion, ajuste, 100)

    ofi = _insert_ofi(db, obligacion, config, indice)
    ofi_otra = _insert_ofi(db, otra_obligacion, config, indice)

    return {
        "capital": capital,
        "ajuste": ajuste,
        "otro_concepto": otro,
        "indice": indice,
        "otro_indice": otro_indice,
        "plan": plan,
        "otro_plan": otro_plan,
        "config": config,
        "config_otro_indice": config_otro_indice,
        "relacion": relacion,
        "generacion": generacion,
        "generacion_otro_plan": generacion_otro_plan,
        "obligacion": obligacion,
        "otra_obligacion": otra_obligacion,
        "comp_capital": comp_capital,
        "comp_ajuste": comp_ajuste,
        "comp_otro_concepto": comp_otro_concepto,
        "comp_capital_otra_obl": comp_capital_otra_obl,
        "comp_ajuste_otra_obl": comp_ajuste_otra_obl,
        "ofi": ofi,
        "ofi_otra": ofi_otra,
    }


def _insert_composicion(db, obligacion: int, concepto: int, importe: float) -> int:
    return _scalar(
        db,
        """
        INSERT INTO public.composicion_obligacion (
            id_obligacion_financiera, id_concepto_financiero, orden_composicion,
            estado_composicion_obligacion, importe_componente, saldo_componente, moneda_componente
        ) VALUES (:obligacion, :concepto, 1, 'ACTIVA', :importe, :importe, 'ARS')
        RETURNING id_composicion_obligacion
        """,
        obligacion=obligacion,
        concepto=concepto,
        importe=importe,
    )


def _insert_ofi(db, obligacion: int, config: int, indice: dict) -> int:
    return _scalar(
        db,
        """
        INSERT INTO public.obligacion_financiera_indexacion (
            id_obligacion_financiera, id_plan_pago_venta_bloque_indexacion,
            id_indice_financiero, id_indice_financiero_valor, fecha_base_indice,
            valor_base_indice, fecha_aplicacion_indice, valor_aplicado_indice,
            coeficiente_indexacion, modo_indexacion, base_calculo_indexacion,
            tipo_generacion_indexada
        ) VALUES (:obligacion, :config, :indice, :valor, DATE '2026-01-01',
                  100.00000000, DATE '2026-06-01', 125.00000000,
                  1.25000000, 'POR_COEFICIENTE', 'CAPITAL_INICIAL_BLOQUE', 'DEFINITIVA')
        RETURNING id_obligacion_financiera_indexacion
        """,
        obligacion=obligacion,
        config=config,
        indice=indice["id"],
        valor=indice["aplicado"],
    )


def _insert_corrida(db, ctx, **overrides) -> int:
    data = {
        "plan": ctx["plan"]["plan"],
        "bloque": ctx["plan"]["bloque"],
        "config": ctx["config"],
        "generacion": ctx["generacion"],
        "indice": ctx["indice"]["id"],
        "valor_base": ctx["indice"]["base"],
        "valor_aplicado": ctx["indice"]["aplicado"],
        "periodo_aplicado": "2026-06-01",
        "fecha_corte": "2026-06-30",
        "origen": "REINDEXACION_MANUAL",
        "estado": "BORRADOR",
        "hash": "hash-cif-1",
        "aplicacion": None,
        "anterior": None,
        "reemplazante": None,
    }
    data.update(overrides)
    return _scalar(
        db,
        """
        INSERT INTO public.corrida_indexacion_financiera (
            id_plan_pago_venta, id_plan_pago_venta_bloque,
            id_plan_pago_venta_bloque_indexacion, id_generacion_cronograma_financiero,
            id_indice_financiero, id_indice_financiero_valor_base,
            id_indice_financiero_valor_aplicado, periodo_base, periodo_aplicado,
            fecha_corte, origen_corrida, estado_corrida, op_id, hash_corrida,
            fecha_aplicacion, cantidad_analizada, cantidad_elegible,
            id_corrida_anterior, id_corrida_reemplazante
        ) VALUES (:plan, :bloque, :config, :generacion, :indice, :valor_base,
                  :valor_aplicado, DATE '2026-01-01', :periodo_aplicado,
                  :fecha_corte, :origen, :estado, gen_random_uuid(), :hash,
                  :aplicacion, 1, 1, :anterior, :reemplazante)
        RETURNING id_corrida_indexacion_financiera
        """,
        **data,
    )


def _insert_detalle(db, ctx, corrida: int, **overrides) -> int:
    data = {
        "corrida": corrida,
        "obligacion": ctx["obligacion"],
        "capital": ctx["comp_capital"],
        "ajuste": ctx["comp_ajuste"],
        "ofi": ctx["ofi"],
        "version_esperada": 1,
        "version_resultante": None,
        "ajuste_nuevo": 250,
        "estado": "ELEGIBLE",
        "motivo": None,
    }
    data.update(overrides)
    return _scalar(
        db,
        """
        INSERT INTO public.corrida_indexacion_financiera_detalle (
            id_corrida_indexacion_financiera, id_obligacion_financiera,
            id_composicion_capital_venta, id_composicion_ajuste_indexacion,
            id_obligacion_financiera_indexacion, version_esperada, version_resultante,
            capital_base, valor_indice_base, valor_indice_aplicado,
            coeficiente_indexacion, ajuste_anterior, ajuste_nuevo,
            diferencia_neta, importe_anterior, importe_nuevo,
            saldo_anterior, saldo_nuevo, estado_elegibilidad, motivo_exclusion
        ) VALUES (:corrida, :obligacion, :capital, :ajuste, :ofi,
                  :version_esperada, :version_resultante, 1000.00,
                  100.00000000, 125.00000000, 1.25000000, 0.00,
                  :ajuste_nuevo, 250.00, 1000.00, 1250.00,
                  1000.00, 1250.00, :estado, :motivo)
        RETURNING id_corrida_indexacion_financiera_detalle
        """,
        **data,
    )


def test_patch_es_idempotente_y_crea_tablas_constraints_indices(corrida_schema):
    db = corrida_schema
    assert _scalar(db, "SELECT to_regclass('public.corrida_indexacion_financiera')") == "corrida_indexacion_financiera"
    assert _scalar(db, "SELECT to_regclass('public.corrida_indexacion_financiera_detalle')") == "corrida_indexacion_financiera_detalle"

    for constraint in (
        "uq_ifv_id_indice_pair",
        "uq_ppvbi_id_bloque_indice_pair",
        "uq_composicion_obligacion_id_obligacion_pair",
        "uq_ofi_id_obligacion_pair",
        "fk_cif_bloque_indexacion_mismo_bloque_indice",
        "fk_cif_valor_base_mismo_indice",
        "fk_cif_valor_aplicado_mismo_indice",
        "fk_cifd_composicion_capital_obligacion",
        "fk_cifd_composicion_ajuste_obligacion",
        "fk_cifd_obligacion_indexacion_obligacion",
    ):
        assert _scalar(db, "SELECT COUNT(*) FROM pg_constraint WHERE conname = :name", name=constraint) == 1

    assert _scalar(db, "SELECT COUNT(*) FROM pg_trigger WHERE tgname = 'trg_biu_cifd_validar_composiciones'") == 1
    assert _scalar(db, "SELECT COUNT(*) FROM pg_indexes WHERE indexname = 'ux_cif_idempotencia_funcional_activa'") == 1
    assert _scalar(db, "SELECT COUNT(*) FROM pg_indexes WHERE indexname = 'idx_cifd_elegibles'") == 0


def test_insercion_valida_y_core_ef(corrida_schema):
    db = corrida_schema
    ctx = _create_context(db)
    corrida = _insert_corrida(db, ctx)
    detalle = _insert_detalle(db, ctx, corrida)

    cab = _one(db, "SELECT uid_global, version_registro, created_at, updated_at FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera = :id", id=corrida)
    det = _one(db, "SELECT uid_global, version_registro FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera_detalle = :id", id=detalle)
    assert cab["uid_global"] is not None
    assert cab["version_registro"] == 1
    assert cab["created_at"] <= cab["updated_at"]
    assert det["uid_global"] is not None
    assert det["version_registro"] == 1

    old_uid = cab["uid_global"]
    db.execute(text("UPDATE corrida_indexacion_financiera SET observaciones = 'actualizada' WHERE id_corrida_indexacion_financiera = :id"), {"id": corrida})
    db.flush()
    updated = _one(db, "SELECT uid_global, version_registro, updated_at FROM corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera = :id", id=corrida)
    assert updated["uid_global"] == old_uid
    assert updated["version_registro"] == 2
    assert updated["updated_at"] >= cab["updated_at"]

    db.execute(text("UPDATE corrida_indexacion_financiera_detalle SET detalle_controlado = 'ok' WHERE id_corrida_indexacion_financiera_detalle = :id"), {"id": detalle})
    db.flush()
    assert _scalar(db, "SELECT version_registro FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera_detalle = :id", id=detalle) == 2


def test_consistencia_plan_bloque_configuracion_indice_valores_y_generacion(corrida_schema):
    db = corrida_schema
    ctx = _create_context(db)
    _insert_corrida(db, ctx)

    _integrity_error(db, """
        INSERT INTO public.corrida_indexacion_financiera (
            id_plan_pago_venta, id_plan_pago_venta_bloque, id_plan_pago_venta_bloque_indexacion,
            id_generacion_cronograma_financiero, id_indice_financiero, id_indice_financiero_valor_base,
            id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte, origen_corrida,
            estado_corrida, op_id, hash_corrida
        ) VALUES (:otro_plan, :bloque, :config, :generacion, :indice, :valor_base, :valor_aplicado,
                  DATE '2026-06-01', DATE '2026-06-30', 'PUBLICACION_INDICE', 'BORRADOR', gen_random_uuid(), 'bloque-plan')
    """, otro_plan=ctx["otro_plan"]["plan"], bloque=ctx["plan"]["bloque"], config=ctx["config"], generacion=ctx["generacion"], indice=ctx["indice"]["id"], valor_base=ctx["indice"]["base"], valor_aplicado=ctx["indice"]["aplicado"])

    _integrity_error(db, """
        INSERT INTO public.corrida_indexacion_financiera (
            id_plan_pago_venta, id_plan_pago_venta_bloque, id_plan_pago_venta_bloque_indexacion,
            id_generacion_cronograma_financiero, id_indice_financiero, id_indice_financiero_valor_base,
            id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte, origen_corrida,
            estado_corrida, op_id, hash_corrida
        ) VALUES (:plan, :bloque, :config_otro_indice, :generacion, :indice, :valor_base, :valor_aplicado,
                  DATE '2026-06-01', DATE '2026-06-30', 'PUBLICACION_INDICE', 'BORRADOR', gen_random_uuid(), 'config-indice')
    """, plan=ctx["plan"]["plan"], bloque=ctx["plan"]["bloque"], config_otro_indice=ctx["config_otro_indice"], generacion=ctx["generacion"], indice=ctx["indice"]["id"], valor_base=ctx["indice"]["base"], valor_aplicado=ctx["indice"]["aplicado"])

    _integrity_error(db, """
        INSERT INTO public.corrida_indexacion_financiera (
            id_plan_pago_venta, id_plan_pago_venta_bloque, id_plan_pago_venta_bloque_indexacion,
            id_generacion_cronograma_financiero, id_indice_financiero, id_indice_financiero_valor_base,
            id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte, origen_corrida,
            estado_corrida, op_id, hash_corrida
        ) VALUES (:plan, :bloque, :config, :generacion_otro_plan, :indice, :valor_base, :valor_aplicado,
                  DATE '2026-06-01', DATE '2026-06-30', 'PUBLICACION_INDICE', 'BORRADOR', gen_random_uuid(), 'generacion-plan')
    """, plan=ctx["plan"]["plan"], bloque=ctx["plan"]["bloque"], config=ctx["config"], generacion_otro_plan=ctx["generacion_otro_plan"], indice=ctx["indice"]["id"], valor_base=ctx["indice"]["base"], valor_aplicado=ctx["indice"]["aplicado"])

    _integrity_error(db, """
        INSERT INTO public.corrida_indexacion_financiera (
            id_plan_pago_venta, id_plan_pago_venta_bloque, id_plan_pago_venta_bloque_indexacion,
            id_generacion_cronograma_financiero, id_indice_financiero, id_indice_financiero_valor_base,
            id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte, origen_corrida,
            estado_corrida, op_id, hash_corrida
        ) VALUES (:plan, :bloque, :config, :generacion, :indice, :valor_base_otro, :valor_aplicado,
                  DATE '2026-06-01', DATE '2026-06-30', 'PUBLICACION_INDICE', 'BORRADOR', gen_random_uuid(), 'valor-base')
    """, plan=ctx["plan"]["plan"], bloque=ctx["plan"]["bloque"], config=ctx["config"], generacion=ctx["generacion"], indice=ctx["indice"]["id"], valor_base_otro=ctx["otro_indice"]["base"], valor_aplicado=ctx["indice"]["aplicado"])


def test_composiciones_y_trazabilidad_pertenecen_a_la_obligacion_y_concepto(corrida_schema):
    db = corrida_schema
    ctx = _create_context(db)
    corrida = _insert_corrida(db, ctx)
    _insert_detalle(db, ctx, corrida)

    corrida_2 = _insert_corrida(db, ctx, hash="hash-cif-comp-2")
    _trigger_rejection(db, "INSERT INTO public.corrida_indexacion_financiera_detalle (id_corrida_indexacion_financiera, id_obligacion_financiera, id_composicion_capital_venta, version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad) VALUES (:corrida, :obligacion, :capital_otra, 1, 100, 100, 125, 1.25, 'ELEGIBLE')", "id_composicion_capital_venta debe pertenecer a la obligacion y usar concepto CAPITAL_VENTA", corrida=corrida_2, obligacion=ctx["obligacion"], capital_otra=ctx["comp_capital_otra_obl"])

    _trigger_rejection(db, "INSERT INTO public.corrida_indexacion_financiera_detalle (id_corrida_indexacion_financiera, id_obligacion_financiera, id_composicion_capital_venta, version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad) VALUES (:corrida, :obligacion, :otro_concepto, 1, 100, 100, 125, 1.25, 'ELEGIBLE')", "id_composicion_capital_venta debe pertenecer a la obligacion y usar concepto CAPITAL_VENTA", corrida=corrida_2, obligacion=ctx["obligacion"], otro_concepto=ctx["comp_otro_concepto"])

    _trigger_rejection(db, "INSERT INTO public.corrida_indexacion_financiera_detalle (id_corrida_indexacion_financiera, id_obligacion_financiera, id_composicion_ajuste_indexacion, version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad) VALUES (:corrida, :obligacion, :ajuste_otra, 1, 100, 100, 125, 1.25, 'ELEGIBLE')", "id_composicion_ajuste_indexacion debe pertenecer a la obligacion y usar concepto AJUSTE_INDEXACION", corrida=corrida_2, obligacion=ctx["obligacion"], ajuste_otra=ctx["comp_ajuste_otra_obl"])

    _trigger_rejection(db, "INSERT INTO public.corrida_indexacion_financiera_detalle (id_corrida_indexacion_financiera, id_obligacion_financiera, id_composicion_ajuste_indexacion, version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad) VALUES (:corrida, :obligacion, :capital, 1, 100, 100, 125, 1.25, 'ELEGIBLE')", "id_composicion_ajuste_indexacion debe pertenecer a la obligacion y usar concepto AJUSTE_INDEXACION", corrida=corrida_2, obligacion=ctx["obligacion"], capital=ctx["comp_capital"])

    _integrity_error(db, "INSERT INTO public.corrida_indexacion_financiera_detalle (id_corrida_indexacion_financiera, id_obligacion_financiera, id_obligacion_financiera_indexacion, version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad) VALUES (:corrida, :obligacion, :ofi_otra, 1, 100, 100, 125, 1.25, 'ELEGIBLE')", corrida=corrida_2, obligacion=ctx["obligacion"], ofi_otra=ctx["ofi_otra"])


def test_estados_origenes_e_idempotencia(corrida_schema):
    db = corrida_schema
    ctx = _create_context(db)
    for idx, estado in enumerate(ESTADOS):
        _insert_corrida(db, ctx, estado=estado, hash=f"hash-estado-{idx}", aplicacion="2026-07-01" if estado == "APLICADA" else None)
    for idx, origen in enumerate(ORIGENES):
        _insert_corrida(db, ctx, origen=origen, hash=f"hash-origen-{idx}")

    for estado in ("APLICANDO", "APLICADA_PARCIAL", "REVERSADA", "DESCONOCIDO"):
        _integrity_error(db, "INSERT INTO public.corrida_indexacion_financiera (id_plan_pago_venta, id_plan_pago_venta_bloque, id_plan_pago_venta_bloque_indexacion, id_indice_financiero, id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte, origen_corrida, estado_corrida, op_id, hash_corrida) VALUES (:plan, :bloque, :config, :indice, :valor, DATE '2026-06-01', DATE '2026-06-30', 'PUBLICACION_INDICE', :estado, gen_random_uuid(), :hash)", plan=ctx["plan"]["plan"], bloque=ctx["plan"]["bloque"], config=ctx["config"], indice=ctx["indice"]["id"], valor=ctx["indice"]["aplicado"], estado=estado, hash=f"bad-{estado}")

    _integrity_error(db, "INSERT INTO public.corrida_indexacion_financiera (id_plan_pago_venta, id_plan_pago_venta_bloque, id_plan_pago_venta_bloque_indexacion, id_indice_financiero, id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte, origen_corrida, estado_corrida, op_id, hash_corrida) VALUES (:plan, :bloque, :config, :indice, :valor, DATE '2026-06-01', DATE '2026-06-30', 'ORIGEN_INVALIDO', 'BORRADOR', gen_random_uuid(), 'bad-origin')", plan=ctx["plan"]["plan"], bloque=ctx["plan"]["bloque"], config=ctx["config"], indice=ctx["indice"]["id"], valor=ctx["indice"]["aplicado"])

    _insert_corrida(db, ctx, hash="hash-idem")
    _integrity_error(db, "INSERT INTO public.corrida_indexacion_financiera (id_plan_pago_venta, id_plan_pago_venta_bloque, id_plan_pago_venta_bloque_indexacion, id_indice_financiero, id_indice_financiero_valor_aplicado, periodo_aplicado, fecha_corte, origen_corrida, estado_corrida, op_id, hash_corrida) VALUES (:plan, :bloque, :config, :indice, :valor, DATE '2026-06-01', DATE '2026-06-30', 'PUBLICACION_INDICE', 'BORRADOR', gen_random_uuid(), 'hash-idem')", plan=ctx["plan"]["plan"], bloque=ctx["plan"]["bloque"], config=ctx["config"], indice=ctx["indice"]["id"], valor=ctx["indice"]["aplicado"])
    _insert_corrida(db, ctx, hash="hash-idem-distinto")
    _insert_corrida(db, ctx, hash="hash-idem", fecha_corte="2026-07-13", periodo_aplicado="2026-07-01")
    _insert_corrida(db, ctx, hash="hash-idem", origen="CORRECCION_INDICE")
    _insert_corrida(db, ctx, hash="hash-idem-anulada", estado="ANULADA")
    _insert_corrida(db, ctx, hash="hash-idem-anulada", estado="BORRADOR")
    _insert_corrida(db, ctx, hash="hash-idem-reemplazada", estado="REEMPLAZADA")
    _insert_corrida(db, ctx, hash="hash-idem-reemplazada", estado="BORRADOR")


def test_identidad_publicacion_indice_es_mensual_y_no_incluye_valor(corrida_schema):
    db = corrida_schema
    ctx = _create_context(db)
    otro_valor = _scalar(db, """
        INSERT INTO indice_financiero_valor (
            id_indice_financiero, fecha_valor, valor_indice,
            fecha_publicacion, estado_valor_indice
        ) VALUES (:indice, DATE '2026-06-15', 130, DATE '2026-06-16', 'PUBLICADO')
        RETURNING id_indice_financiero_valor
    """, indice=ctx["indice"]["id"])
    _insert_corrida(db, ctx, origen="PUBLICACION_INDICE", estado="APLICADA", aplicacion="2026-07-01", hash="mensual-a")
    with pytest.raises(IntegrityError) as exc_info:
        with db.begin_nested():
            _insert_corrida(db, ctx, valor_aplicado=otro_valor, periodo_aplicado="2026-06-15", origen="PUBLICACION_INDICE", estado="PREVISUALIZADA", hash="mensual-b")
    assert "ux_cif_publicacion_indice_grupo_activo" in str(exc_info.value)
    _insert_corrida(db, ctx, valor_aplicado=otro_valor, periodo_aplicado="2026-07-01", fecha_corte="2026-07-14", origen="PUBLICACION_INDICE", estado="PREVISUALIZADA", hash="mes-siguiente")
    _insert_corrida(db, ctx, valor_aplicado=otro_valor, origen="REINDEXACION_MANUAL", estado="PREVISUALIZADA", hash="manual")


def test_detalle_constraints_y_reemplazo(corrida_schema):
    db = corrida_schema
    ctx = _create_context(db)
    corrida = _insert_corrida(db, ctx)
    _insert_detalle(db, ctx, corrida)
    _integrity_error(db, "INSERT INTO public.corrida_indexacion_financiera_detalle (id_corrida_indexacion_financiera, id_obligacion_financiera, version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad) VALUES (:corrida, :obligacion, 1, 100, 100, 125, 1.25, 'ELEGIBLE')", corrida=corrida, obligacion=ctx["obligacion"])

    otra_corrida = _insert_corrida(db, ctx, hash="hash-det-otra")
    _insert_detalle(db, ctx, otra_corrida, capital=None, ajuste=None, ofi=None)

    for fragment in (
        "version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad) VALUES (:corrida, :obligacion, 0, 100, 100, 125, 1.25, 'ELEGIBLE')",
        "version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, ajuste_nuevo, estado_elegibilidad) VALUES (:corrida, :obligacion, 1, 100, 100, 125, 1.25, -1, 'ELEGIBLE')",
        "version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad) VALUES (:corrida, :obligacion, 1, -100, 100, 125, 1.25, 'ELEGIBLE')",
        "version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad) VALUES (:corrida, :obligacion, 1, 100, 100, 125, 1.25, 'DESCONOCIDA')",
        "version_esperada, capital_base, valor_indice_base, valor_indice_aplicado, coeficiente_indexacion, estado_elegibilidad) VALUES (:corrida, :obligacion, 1, 100, 100, 125, 1.25, 'EXCLUIDA')",
    ):
        c = _insert_corrida(db, ctx, hash=f"hash-det-{abs(hash(fragment))}")
        _integrity_error(db, f"INSERT INTO public.corrida_indexacion_financiera_detalle (id_corrida_indexacion_financiera, id_obligacion_financiera, {fragment}", corrida=c, obligacion=ctx["obligacion"])

    excluida = _insert_corrida(db, ctx, hash="hash-excluida")
    _insert_detalle(db, ctx, excluida, capital=None, ajuste=None, ofi=None, estado="EXCLUIDA", motivo="sin indice aplicable")

    _integrity_error(db, "UPDATE public.corrida_indexacion_financiera SET id_corrida_anterior = id_corrida_indexacion_financiera WHERE id_corrida_indexacion_financiera = :id", id=corrida)
    anterior = _insert_corrida(db, ctx, hash="hash-anterior")
    reemplazante = _insert_corrida(db, ctx, hash="hash-reemplazante", anterior=anterior)
    db.execute(text("UPDATE public.corrida_indexacion_financiera SET id_corrida_reemplazante = :reemplazante WHERE id_corrida_indexacion_financiera = :anterior"), {"reemplazante": reemplazante, "anterior": anterior})
    db.flush()
    _integrity_error(db, "UPDATE public.corrida_indexacion_financiera SET id_corrida_anterior = :x, id_corrida_reemplazante = :x WHERE id_corrida_indexacion_financiera = :id", x=anterior, id=corrida)


def test_idempotencia_publicacion_indice_ordinaria_por_periodo(corrida_schema):
    db = corrida_schema
    ctx = _create_context(db)
    corrida = _insert_corrida(db, ctx, origen="PUBLICACION_INDICE", estado="PREVISUALIZADA", hash="hash-pub-1")
    db.execute(text("UPDATE corrida_indexacion_financiera SET payload_hash='payload-1' WHERE id_corrida_indexacion_financiera=:id"), {"id": corrida})
    db.flush()
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            otra = _insert_corrida(db, ctx, origen="PUBLICACION_INDICE", estado="PREVISUALIZADA", hash="hash-pub-2")
            db.execute(text("UPDATE corrida_indexacion_financiera SET payload_hash='payload-2' WHERE id_corrida_indexacion_financiera=:id"), {"id": otra})
            db.flush()

    db.execute(text("UPDATE corrida_indexacion_financiera SET estado_corrida='ANULADA' WHERE id_corrida_indexacion_financiera=:id"), {"id": corrida})
    db.flush()
    anulada_recreada = _insert_corrida(db, ctx, origen="PUBLICACION_INDICE", estado="PREVISUALIZADA", hash="hash-pub-anulada")
    db.execute(text("UPDATE corrida_indexacion_financiera SET payload_hash='payload-anulada' WHERE id_corrida_indexacion_financiera=:id"), {"id": anulada_recreada})
    db.flush()

    manual_1 = _insert_corrida(db, ctx, origen="REINDEXACION_MANUAL", hash="hash-manual-1")
    manual_2 = _insert_corrida(db, ctx, origen="REINDEXACION_MANUAL", hash="hash-manual-2")
    assert manual_1 != manual_2
