import pytest
from sqlalchemy import text

from scripts import create_plan_pago_v2_demo as demo
from app.config.database import SessionLocal


@pytest.mark.parametrize("value", [None, "", "production", "unknown"])
def test_require_safe_environment_rejects_invalid_values(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("ENV", raising=False)
    else:
        monkeypatch.setenv("ENV", value)
    with pytest.raises(RuntimeError):
        demo.require_safe_environment()


@pytest.mark.parametrize("value", ["dev", "test"])
def test_require_safe_environment_accepts_dev_and_test(monkeypatch, value):
    monkeypatch.setenv("ENV", value)
    demo.require_safe_environment()


def test_create_rejects_invalid_environment_before_session(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.setattr(demo, "SessionLocal", lambda: pytest.fail("DB abierta"))
    with pytest.raises(RuntimeError):
        demo.create()


def test_demo_scenario_is_isolated_idempotent_and_cleanable(monkeypatch):
    """PostgreSQL integration: preserves seed sale and deletes only demo graph."""
    monkeypatch.setenv("ENV", "test")
    demo.clean()
    with SessionLocal() as db:
        # The script itself loads the UI seed; this first run establishes the base.
        demo._seed_ui(db)
        db.commit()
        base = db.execute(text("SELECT id_venta FROM venta WHERE codigo_venta='DEMO-VTA-CUOTAS'")).scalar_one()
    demo.create()
    with SessionLocal() as db:
        sale = db.execute(text("SELECT id_venta,estado_venta FROM venta WHERE codigo_venta=:code"), {"code": demo.CODIGO_VENTA}).mappings().one()
        assert sale["id_venta"] != base and sale["estado_venta"] == "confirmada"
        assert db.execute(text("SELECT id_venta FROM venta WHERE codigo_venta='DEMO-VTA-CUOTAS'")).scalar_one() == base
        plan = db.execute(text("SELECT id_plan_pago_venta FROM plan_pago_venta WHERE id_venta=:sale AND deleted_at IS NULL"), {"sale": sale["id_venta"]}).scalar_one()
        assert db.execute(text("SELECT count(*) FROM plan_pago_venta_bloque WHERE id_plan_pago_venta=:plan AND deleted_at IS NULL"), {"plan": plan}).scalar_one() == 3
        assert db.execute(text("SELECT count(*) FROM obligacion_financiera WHERE id_plan_pago_venta_bloque IN (SELECT id_plan_pago_venta_bloque FROM plan_pago_venta_bloque WHERE id_plan_pago_venta=:plan)"), {"plan": plan}).scalar_one() == 3
        assert db.execute(text("SELECT count(*) FROM corrida_indexacion_financiera WHERE id_plan_pago_venta=:plan AND estado_corrida='APLICADA'"), {"plan": plan}).scalar_one() == 1
    demo.create()
    with SessionLocal() as db:
        assert db.execute(text("SELECT count(*) FROM corrida_indexacion_financiera WHERE id_plan_pago_venta=:plan"), {"plan": plan}).scalar_one() == 3
    demo.clean(); demo.clean()


def test_demo_core_ef_context_is_resolved_and_active(monkeypatch):
    monkeypatch.setenv("ENV", "test")
    with SessionLocal() as db:
        context = demo._resolve_demo_core_ef(db)
        assert context.x_usuario_id and context.x_sucursal_id and context.x_instalacion_id
        assert db.execute(text("SELECT 1 FROM usuario WHERE id_usuario=:id AND estado_usuario='ACTIVO'"), {"id": context.x_usuario_id}).scalar_one() == 1
        assert db.execute(text("SELECT 1 FROM sucursal WHERE id_sucursal=:id AND estado_sucursal='ACTIVA'"), {"id": context.x_sucursal_id}).scalar_one() == 1
        assert db.execute(text("SELECT 1 FROM instalacion WHERE id_instalacion=:id AND estado_instalacion='ACTIVA'"), {"id": context.x_instalacion_id}).scalar_one() == 1


def test_applied_demo_run_has_consistent_financial_graph(monkeypatch):
    monkeypatch.setenv("ENV", "test"); demo.create()
    with SessionLocal() as db:
        row = db.execute(text("""SELECT o.importe_total,o.saldo_pendiente,o.version_registro,d.version_esperada,d.version_resultante,d.id_obligacion_financiera_indexacion
          FROM obligacion_financiera o JOIN plan_pago_venta_bloque b USING(id_plan_pago_venta_bloque) JOIN plan_pago_venta p USING(id_plan_pago_venta)
          JOIN corrida_indexacion_financiera c ON c.id_plan_pago_venta_bloque=b.id_plan_pago_venta_bloque JOIN corrida_indexacion_financiera_detalle d USING(id_corrida_indexacion_financiera)
          WHERE p.id_venta=(SELECT id_venta FROM venta WHERE codigo_venta=:code) AND b.etiqueta_bloque='Demo: corrida posterior' AND c.estado_corrida='APLICADA' AND d.id_obligacion_financiera=o.id_obligacion_financiera"""), {"code": demo.CODIGO_VENTA}).mappings().one()
        comps = db.execute(text("""SELECT cf.codigo_concepto_financiero,co.importe_componente FROM composicion_obligacion co JOIN concepto_financiero cf USING(id_concepto_financiero) WHERE co.id_obligacion_financiera=(SELECT d.id_obligacion_financiera FROM corrida_indexacion_financiera_detalle d WHERE d.id_obligacion_financiera_indexacion=:ofi) AND co.deleted_at IS NULL"""), {"ofi": row["id_obligacion_financiera_indexacion"]}).mappings().all()
        values = {x["codigo_concepto_financiero"]: x["importe_componente"] for x in comps}
        assert row["version_registro"] == row["version_resultante"] > row["version_esperada"]
        assert values["AJUSTE_INDEXACION"] > 0 and row["importe_total"] == values["CAPITAL_VENTA"] + values["AJUSTE_INDEXACION"] == row["saldo_pendiente"]
