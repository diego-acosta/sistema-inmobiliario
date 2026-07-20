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
    demo.clean()
    demo.clean()
    with SessionLocal() as db:
        assert db.execute(text("SELECT id_venta FROM venta WHERE codigo_venta=:code"), {"code": demo.CODIGO_VENTA}).scalar_one_or_none() is None
        assert db.execute(text("SELECT id_venta FROM venta WHERE codigo_venta='DEMO-VTA-CUOTAS'")).scalar_one() == base
