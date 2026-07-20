import pytest

from scripts.create_plan_pago_v2_demo import require_safe_environment


@pytest.mark.parametrize("value", [None, "", "production", "unknown"])
def test_require_safe_environment_rejects_invalid_values(monkeypatch, value):
    if value is None:
        monkeypatch.delenv("ENV", raising=False)
    else:
        monkeypatch.setenv("ENV", value)
    with pytest.raises(RuntimeError):
        require_safe_environment()


@pytest.mark.parametrize("value", ["dev", "test"])
def test_require_safe_environment_accepts_dev_and_test(monkeypatch, value):
    monkeypatch.setenv("ENV", value)
    require_safe_environment()
