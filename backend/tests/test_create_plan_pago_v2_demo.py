import pytest
from sqlalchemy import text

from scripts import create_plan_pago_v2_demo as demo
from app.application.comercial.services.generate_plan_pago_venta_v2_por_bloques_service import (
    GeneratePlanPagoVentaV2PorBloquesService,
)
from app.infrastructure.persistence.repositories.plan_pago_venta_v2_repository import (
    PlanPagoVentaV2Repository,
)


@pytest.fixture(autouse=True)
def force_test_environment(monkeypatch):
    monkeypatch.setenv("ENV", "test")


@pytest.mark.parametrize("value", [None, "", "production", "unknown"])
def test_require_safe_environment_rejects_invalid_values(monkeypatch, value, db_session):
    if value is None:
        monkeypatch.delenv("ENV", raising=False)
    else:
        monkeypatch.setenv("ENV", value)
    with pytest.raises(RuntimeError):
        demo.require_safe_environment()


@pytest.mark.parametrize("value", ["dev", "test"])
def test_require_safe_environment_accepts_dev_and_test(monkeypatch, value, db_session):
    monkeypatch.setenv("ENV", value)
    demo.require_safe_environment()


def test_create_rejects_invalid_environment_before_session(monkeypatch, db_session):
    monkeypatch.setenv("ENV", "production")
    with pytest.raises(RuntimeError):
        demo.create()


def test_clean_rejects_invalid_environment_before_session(monkeypatch, db_session):
    monkeypatch.setenv("ENV", "production")
    with pytest.raises(RuntimeError):
        demo.clean()


def test_demo_scenario_is_isolated_idempotent_and_cleanable(monkeypatch, db_session):
    """PostgreSQL integration: preserves seed sale and deletes only demo graph."""
    monkeypatch.setenv("ENV", "test")
    demo.clean(db=db_session)
    # The script itself loads the UI seed; this first run establishes the base.
    demo._seed_ui(db_session)
    base = db_session.execute(text("SELECT id_venta FROM venta WHERE codigo_venta='DEMO-VTA-CUOTAS'")).scalar_one()
    demo.create(db=db_session)
    sale = db_session.execute(text("SELECT id_venta,estado_venta FROM venta WHERE codigo_venta=:code"), {"code": demo.CODIGO_VENTA}).mappings().one()
    plan = db_session.execute(text("SELECT id_plan_pago_venta FROM plan_pago_venta WHERE id_venta=:sale AND deleted_at IS NULL"), {"sale": sale["id_venta"]}).scalar_one()
    assert sale["id_venta"] != base and sale["estado_venta"] == "confirmada"
    assert db_session.execute(text("SELECT id_venta FROM venta WHERE codigo_venta='DEMO-VTA-CUOTAS'")).scalar_one() == base
    assert db_session.execute(text("SELECT count(*) FROM plan_pago_venta_bloque WHERE id_plan_pago_venta=:plan AND deleted_at IS NULL"), {"plan": plan}).scalar_one() == 3
    assert db_session.execute(text("SELECT count(*) FROM obligacion_financiera WHERE id_plan_pago_venta_bloque IN (SELECT id_plan_pago_venta_bloque FROM plan_pago_venta_bloque WHERE id_plan_pago_venta=:plan)"), {"plan": plan}).scalar_one() == 3
    assert db_session.execute(text("SELECT count(*) FROM corrida_indexacion_financiera WHERE id_plan_pago_venta=:plan AND estado_corrida='APLICADA'"), {"plan": plan}).scalar_one() == 1
    demo.create(db=db_session)
    assert db_session.execute(text("SELECT count(*) FROM corrida_indexacion_financiera WHERE id_plan_pago_venta=:plan"), {"plan": plan}).scalar_one() == 3
    assert db_session.execute(text("SELECT count(*) FROM corrida_indexacion_financiera WHERE id_plan_pago_venta=:plan AND estado_corrida='APLICADA'"), {"plan": plan}).scalar_one() == 1
    assert db_session.execute(text("SELECT count(*) FROM obligacion_financiera_indexacion oi JOIN obligacion_financiera o USING(id_obligacion_financiera) JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque) WHERE b.id_plan_pago_venta=:plan AND oi.deleted_at IS NULL"), {"plan": plan}).scalar_one() == 2
    assert db_session.execute(text("SELECT count(*) FROM composicion_obligacion co JOIN concepto_financiero cf USING(id_concepto_financiero) JOIN obligacion_financiera o USING(id_obligacion_financiera) JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque) WHERE b.id_plan_pago_venta=:plan AND cf.codigo_concepto_financiero='AJUSTE_INDEXACION' AND co.deleted_at IS NULL"), {"plan": plan}).scalar_one() == 2
    demo.clean(db=db_session)
    assert db_session.execute(text("SELECT id_venta FROM venta WHERE codigo_venta='DEMO-VTA-CUOTAS' AND deleted_at IS NULL")).scalar_one() == base
    assert db_session.execute(text("SELECT count(*) FROM venta WHERE codigo_venta=:code"), {"code": demo.CODIGO_VENTA}).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM indice_financiero WHERE codigo_indice_financiero='CAC_DEMO' AND deleted_at IS NULL")).scalar_one() == 1
    assert db_session.execute(text("SELECT count(*) FROM persona WHERE codigo_persona='DEMO-PER-COMPRADOR' AND deleted_at IS NULL")).scalar_one() == 1
    demo.clean(db=db_session)


def test_demo_core_ef_context_is_resolved_and_active(monkeypatch, db_session):
    monkeypatch.setenv("ENV", "test")
    context = demo._resolve_demo_core_ef(db_session)
    assert context.x_usuario_id and context.x_sucursal_id and context.x_instalacion_id
    assert db_session.execute(text("SELECT 1 FROM usuario WHERE id_usuario=:id AND estado_usuario='ACTIVO'"), {"id": context.x_usuario_id}).scalar_one() == 1
    assert db_session.execute(text("SELECT 1 FROM sucursal WHERE id_sucursal=:id AND estado_sucursal='ACTIVA'"), {"id": context.x_sucursal_id}).scalar_one() == 1
    assert db_session.execute(text("SELECT 1 FROM instalacion WHERE id_instalacion=:id AND estado_instalacion='ACTIVA'"), {"id": context.x_instalacion_id}).scalar_one() == 1


def test_applied_demo_run_has_financial_consistency_and_version(monkeypatch, db_session):
    monkeypatch.setenv("ENV", "test"); demo.create(db=db_session)
    row = db_session.execute(text("""SELECT o.importe_total,o.saldo_pendiente,o.version_registro,d.version_esperada,d.version_resultante,d.id_obligacion_financiera_indexacion
          FROM obligacion_financiera o JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque) JOIN plan_pago_venta p USING(id_plan_pago_venta)
          JOIN corrida_indexacion_financiera c ON c.id_plan_pago_venta_bloque=b.id_plan_pago_venta_bloque JOIN corrida_indexacion_financiera_detalle d USING(id_corrida_indexacion_financiera)
          WHERE p.id_venta=(SELECT id_venta FROM venta WHERE codigo_venta=:code) AND b.etiqueta_bloque='Demo: corrida posterior' AND c.estado_corrida='APLICADA' AND d.id_obligacion_financiera=o.id_obligacion_financiera"""), {"code": demo.CODIGO_VENTA}).mappings().one()
    comps = db_session.execute(text("""SELECT cf.codigo_concepto_financiero,co.importe_componente FROM composicion_obligacion co JOIN concepto_financiero cf USING(id_concepto_financiero) WHERE co.id_obligacion_financiera=(SELECT d.id_obligacion_financiera FROM corrida_indexacion_financiera_detalle d WHERE d.id_obligacion_financiera_indexacion=:ofi) AND co.deleted_at IS NULL"""), {"ofi": row["id_obligacion_financiera_indexacion"]}).mappings().all()
    values = {x["codigo_concepto_financiero"]: x["importe_componente"] for x in comps}
    assert row["version_registro"] == row["version_resultante"] > row["version_esperada"]
    assert values["AJUSTE_INDEXACION"] > 0 and row["importe_total"] == values["CAPITAL_VENTA"] + values["AJUSTE_INDEXACION"] == row["saldo_pendiente"]
    assert len(comps) == 2 and {x["codigo_concepto_financiero"] for x in comps} == {"CAPITAL_VENTA", "AJUSTE_INDEXACION"}
    indexed = db_session.execute(text("SELECT id_indice_financiero_valor,valor_base_indice,valor_aplicado_indice,coeficiente_indexacion FROM obligacion_financiera_indexacion WHERE id_obligacion_financiera_indexacion=:id AND deleted_at IS NULL"), {"id": row["id_obligacion_financiera_indexacion"]}).mappings().all()
    assert len(indexed) == 1 and indexed[0]["id_indice_financiero_valor"] and indexed[0]["valor_base_indice"] and indexed[0]["valor_aplicado_indice"] and indexed[0]["coeficiente_indexacion"] > 1


def _demo_sale_id(db):
    return db.execute(
        text("SELECT id_venta FROM venta WHERE codigo_venta=:code AND deleted_at IS NULL"),
        {"code": demo.CODIGO_VENTA},
    ).scalar_one()


def _other_plan_snapshot(db, plan):
    """Capture the entire mutable financial graph of a reachable foreign plan."""
    return {
        "blocks": db.execute(text("SELECT id_plan_pago_venta_bloque FROM plan_pago_venta_bloque WHERE id_plan_pago_venta=:plan ORDER BY 1"), {"plan": plan}).scalars().all(),
        "obligations": db.execute(text("SELECT id_obligacion_financiera,version_registro,importe_total,saldo_pendiente FROM obligacion_financiera WHERE id_plan_pago_venta_bloque IN (SELECT id_plan_pago_venta_bloque FROM plan_pago_venta_bloque WHERE id_plan_pago_venta=:plan) ORDER BY 1"), {"plan": plan}).all(),
        "compositions": db.execute(text("SELECT co.id_obligacion_financiera,co.id_concepto_financiero,co.importe_componente,co.saldo_componente FROM composicion_obligacion co JOIN obligacion_financiera o USING(id_obligacion_financiera) JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque) WHERE b.id_plan_pago_venta=:plan ORDER BY 1,2"), {"plan": plan}).all(),
        "indexations": db.execute(text("SELECT oi.id_obligacion_financiera,oi.id_indice_financiero,oi.coeficiente_indexacion FROM obligacion_financiera_indexacion oi JOIN obligacion_financiera o USING(id_obligacion_financiera) JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque) WHERE b.id_plan_pago_venta=:plan ORDER BY 1"), {"plan": plan}).all(),
        "runs": db.execute(text("SELECT id_corrida_indexacion_financiera,estado_corrida,motivo FROM corrida_indexacion_financiera WHERE id_plan_pago_venta=:plan ORDER BY 1"), {"plan": plan}).all(),
    }


def test_create_does_not_modify_other_reachable_plan(monkeypatch, db_session):
    foreign_demo_code = "DEMO-VTA-CUOTAS-PPV2-AJENA-373"
    monkeypatch.setenv("ENV", "test")
    demo.clean(db=db_session)
    try:
        demo._seed_ui(db_session)
        demo._seed_indices_financieros_demo(db_session)
        other_sale = demo._get_or_create_sale(db_session, foreign_demo_code)
        indice = db_session.execute(text("SELECT id_indice_financiero FROM indice_financiero WHERE codigo_indice_financiero='CAC_DEMO' AND deleted_at IS NULL")).scalar_one()
        repo = PlanPagoVentaV2Repository(db_session)
        if repo.get_plan_pago_venta_vivo(other_sale) is None:
            result = GeneratePlanPagoVentaV2PorBloquesService(repo).execute_in_existing_transaction(demo._command(other_sale, indice))
            assert result.success, result.errors
        other_plan = repo.get_plan_pago_venta_vivo(other_sale)["id_plan_pago_venta"]
        before = _other_plan_snapshot(db_session, other_plan)
        assert before["obligations"] and not before["runs"]

        demo.create(db=db_session)
        assert _other_plan_snapshot(db_session, other_plan) == before
        demo_sale = _demo_sale_id(db_session)
        assert db_session.execute(text("SELECT count(*) FROM corrida_indexacion_financiera WHERE motivo='DEMO-373' AND id_plan_pago_venta<>:plan"), {"plan": db_session.execute(text("SELECT id_plan_pago_venta FROM plan_pago_venta WHERE id_venta=:sale"), {"sale": demo_sale}).scalar_one()}).scalar_one() == 0
        applied_blocks = db_session.execute(text("SELECT b.etiqueta_bloque FROM corrida_indexacion_financiera c JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque) WHERE c.estado_corrida='APLICADA' AND c.id_plan_pago_venta=(SELECT id_plan_pago_venta FROM plan_pago_venta WHERE id_venta=:sale)"), {"sale": demo_sale}).scalars().all()
        assert applied_blocks == ["Demo: corrida posterior"]
    finally:
        original_code = demo.CODIGO_VENTA
        demo.CODIGO_VENTA = foreign_demo_code
        try:
            demo.clean(db=db_session)
        finally:
            demo.CODIGO_VENTA = original_code


def test_integral_contract_exposes_complete_demo_scenario(monkeypatch, db_session):
    monkeypatch.setenv("ENV", "test")
    demo.clean(db=db_session)
    demo.create(db=db_session)
    integral = PlanPagoVentaV2Repository(db_session).get_plan_pago_venta_v2_integral(_demo_sale_id(db_session))
    by_label = {block["etiqueta_bloque"]: block["obligaciones"][0] for block in integral["bloques"]}
    born = by_label["Demo: índice al nacimiento"]
    projected = by_label["Demo: proyectada sin índice"]
    later = by_label["Demo: corrida posterior"]
    assert born["estado_obligacion"] == "EMITIDA"
    assert projected["estado_obligacion"] == "PROYECTADA"
    assert later["estado_obligacion"] == "EMITIDA"
    assert born["origen_indexacion"] == "AL_NACIMIENTO"
    assert born["estado_indexacion_presentacion"] == "CON_INDICE_APLICADO"
    assert born["capital_original"] > 0 and born["ajuste_indexacion"] > 0 and born["importe_vigente"] == born["importe_total"]
    assert born["indexacion"] and born["indexacion"]["fecha_base_indice"] and born["indexacion"]["valor_base_indice"] and born["indexacion"]["fecha_aplicacion_indice"] and born["indexacion"]["valor_aplicado_indice"] and born["indexacion"]["coeficiente_indexacion"] > 1
    assert projected["estado_indexacion_presentacion"] == "PROYECTADA_SIN_INDICE"
    assert projected["corrida_aplicada_vigente"] is None and projected["indexacion"] is None
    applied = [run for run in integral["corridas_indexacion"] if run["estado_corrida"] == "APLICADA"]
    assert len(applied) == 1
    assert later["origen_indexacion"] == "CORRIDA_POSTERIOR"
    assert later["corrida_aplicada_vigente"]["id_corrida_indexacion_financiera"] == applied[0]["id_corrida_indexacion_financiera"]
    assert later["capital_original"] > 0 and later["ajuste_indexacion"] > 0 and later["importe_vigente"] == later["importe_total"] == later["saldo_pendiente"]
    assert later["indexacion"]["coeficiente_indexacion"] > 1
    states = [run["estado_corrida"] for run in integral["corridas_indexacion"]]
    assert states.count("PENDIENTE_APLICACION") == states.count("FALLIDA") == states.count("APLICADA") == 1
    pending = next(run for run in integral["corridas_indexacion"] if run["estado_corrida"] == "PENDIENTE_APLICACION")
    failed = next(run for run in integral["corridas_indexacion"] if run["estado_corrida"] == "FALLIDA")
    assert pending["fecha_aplicacion"] is None and pending["obligaciones_afectadas"][0]["estado_elegibilidad"] == "ELEGIBLE" and pending["obligaciones_afectadas"][0]["version_resultante"] is None
    assert failed["codigo_error"] and failed["etapa_error"] and failed["diagnostico_tecnico"] and failed["errores"]
    # The failed presentation fixture is intentionally persisted before the
    # irreversible apply, so it is history only and does not need the later
    # materialized indexation row.


def test_create_rolls_back_all_demo_data_when_internal_step_fails(monkeypatch, db_session):
    monkeypatch.setenv("ENV", "test")
    demo.clean(db=db_session)
    demo._seed_ui(db_session)
    demo._seed_indices_financieros_demo(db_session)
    monkeypatch.setattr(demo, "_fixture_corridas", lambda *_: (_ for _ in ()).throw(RuntimeError("fallo controlado rollback #373")))
    with pytest.raises(RuntimeError, match="fallo controlado rollback #373"):
        demo.create(db=db_session)
    db_session.rollback()
    assert db_session.execute(text("SELECT count(*) FROM venta WHERE codigo_venta=:code"), {"code": demo.CODIGO_VENTA}).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM plan_pago_venta p JOIN venta v USING(id_venta) WHERE v.codigo_venta=:code"), {"code": demo.CODIGO_VENTA}).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM venta WHERE codigo_venta='DEMO-VTA-CUOTAS' AND deleted_at IS NULL")).scalar_one() == 0
    assert db_session.execute(text("SELECT count(*) FROM indice_financiero WHERE codigo_indice_financiero='CAC_DEMO' AND deleted_at IS NULL")).scalar_one() == 0


def _complete_snapshot(db):
    sale = _demo_sale_id(db)
    plan = db.execute(text("SELECT id_plan_pago_venta FROM plan_pago_venta WHERE id_venta=:sale"), {"sale": sale}).scalar_one()
    graph = {
        "venta": "SELECT to_jsonb(v)::text FROM venta v WHERE id_venta=:sale",
        "plan": "SELECT to_jsonb(p)::text FROM plan_pago_venta p WHERE id_plan_pago_venta=:plan",
        "bloques": "SELECT to_jsonb(b)::text FROM plan_pago_venta_bloque b WHERE id_plan_pago_venta=:plan",
        "obligaciones": "SELECT to_jsonb(o)::text FROM obligacion_financiera o JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque) WHERE b.id_plan_pago_venta=:plan",
        "corridas": "SELECT to_jsonb(c)::text FROM corrida_indexacion_financiera c WHERE id_plan_pago_venta=:plan",
        "detalles": "SELECT to_jsonb(d)::text FROM corrida_indexacion_financiera_detalle d JOIN corrida_indexacion_financiera c USING(id_corrida_indexacion_financiera) WHERE c.id_plan_pago_venta=:plan",
        "composiciones": "SELECT to_jsonb(co)::text FROM composicion_obligacion co JOIN obligacion_financiera o USING(id_obligacion_financiera) JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque) WHERE b.id_plan_pago_venta=:plan",
        "indexaciones": "SELECT to_jsonb(oi)::text FROM obligacion_financiera_indexacion oi JOIN obligacion_financiera o USING(id_obligacion_financiera) JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque) WHERE b.id_plan_pago_venta=:plan",
        "outbox": "SELECT to_jsonb(e)::text FROM outbox_event e WHERE e.aggregate_type='corrida_indexacion_financiera' AND e.aggregate_id IN (SELECT id_corrida_indexacion_financiera FROM corrida_indexacion_financiera WHERE id_plan_pago_venta=:plan)",
    }
    return {name: sorted(db.execute(text(sql), {"sale": sale, "plan": plan}).scalars().all()) for name, sql in graph.items()}


def test_second_create_is_a_strict_noop_and_never_applies(monkeypatch, db_session):
    monkeypatch.setenv("ENV", "test")
    demo.clean(db=db_session); demo.create(db=db_session)
    before = _complete_snapshot(db_session)
    assert len(before["outbox"]) == 1
    monkeypatch.setattr(demo, "_create_and_apply_scoped_real_run", lambda *_: pytest.fail("no debe aplicar"))
    demo.create(db=db_session)
    assert _complete_snapshot(db_session) == before


def test_incomplete_existing_scenario_fails_without_repair(monkeypatch, db_session):
    monkeypatch.setenv("ENV", "test")
    demo.clean(db=db_session); demo.create(db=db_session)
    db_session.execute(text("DELETE FROM corrida_indexacion_financiera_detalle WHERE id_corrida_indexacion_financiera=(SELECT id_corrida_indexacion_financiera FROM corrida_indexacion_financiera WHERE estado_corrida='FALLIDA' ORDER BY 1 LIMIT 1)"))
    before = _complete_snapshot(db_session)
    monkeypatch.setattr(demo, "_create_and_apply_scoped_real_run", lambda *_: pytest.fail("no debe aplicar"))
    with pytest.raises(RuntimeError, match="incompleto o inconsistente"):
        demo.create(db=db_session)
    assert _complete_snapshot(db_session) == before


@pytest.mark.parametrize(
    ("state", "wrong_label"),
    [
        ("PENDIENTE_APLICACION", "Demo: índice al nacimiento"),
        ("FALLIDA", "Demo: proyectada sin índice"),
    ],
)
def test_misassociated_fixture_run_is_rejected_without_repair(monkeypatch, state, wrong_label, db_session):
    monkeypatch.setenv("ENV", "test")
    demo.clean(db=db_session); demo.create(db=db_session)
    sale = _demo_sale_id(db_session)
    # The database has a composite FK that requires the block indexation
    # configuration to follow the changed block; the scenario defect under
    # test is exclusively the run-to-block association.
    db_session.execute(text("""UPDATE corrida_indexacion_financiera SET
            id_plan_pago_venta_bloque=(SELECT b.id_plan_pago_venta_bloque FROM plan_pago_venta_bloque b
            JOIN plan_pago_venta p USING(id_plan_pago_venta)
            WHERE p.id_venta=:sale AND b.etiqueta_bloque=:label),
            id_plan_pago_venta_bloque_indexacion=(SELECT i.id_plan_pago_venta_bloque_indexacion
            FROM plan_pago_venta_bloque_indexacion i JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque)
            JOIN plan_pago_venta p USING(id_plan_pago_venta)
            WHERE p.id_venta=:sale AND b.etiqueta_bloque=:label)
            WHERE id_plan_pago_venta=(SELECT id_plan_pago_venta FROM plan_pago_venta WHERE id_venta=:sale)
              AND estado_corrida=:state"""), {"sale": sale, "label": wrong_label, "state": state})
    before = _complete_snapshot(db_session)
    monkeypatch.setattr(demo, "_create_and_apply_scoped_real_run", lambda *_: pytest.fail("no debe reaplicar"))
    with pytest.raises(RuntimeError, match="incompleto o inconsistente"):
        demo.create(db=db_session)
    assert _complete_snapshot(db_session) == before


def test_summary_failure_does_not_undo_committed_application(monkeypatch, db_session):
    monkeypatch.setenv("ENV", "test")
    demo.clean(db=db_session)
    monkeypatch.setattr(demo, "_print_demo_summary", lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("salida caída")))
    demo.create(db=db_session)
    before = _complete_snapshot(db_session)
    assert len(before["outbox"]) == 1
    monkeypatch.setattr(demo, "_create_and_apply_scoped_real_run", lambda *_: pytest.fail("no debe reaplicar"))
    demo.create(db=db_session)
    assert _complete_snapshot(db_session) == before
