import importlib
import unicodedata

import pytest


def _settings(monkeypatch, value=...):
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret-user:secret-pass@db/secret")
    if value is ...:
        monkeypatch.delenv("LOCAL_INSTALLATION_CODE", raising=False)
    else:
        monkeypatch.setenv("LOCAL_INSTALLATION_CODE", value)
    import app.config.settings as module

    module = importlib.reload(module)
    if value is ...:
        original_getenv = module.getenv
        monkeypatch.setattr(
            module,
            "getenv",
            lambda key, default=None: (
                None if key == "LOCAL_INSTALLATION_CODE" else original_getenv(key, default)
            ),
        )
    return module.Settings()


def test_setting_preserva_codigo_exacto_y_case(monkeypatch):
    settings = _settings(monkeypatch, "Inst-Á-001")
    assert settings.local_installation_code == "Inst-Á-001"


@pytest.mark.parametrize("value", ["", "   ", " INST-001", "INST-001 "])
def test_setting_rechaza_codigo_invalido(monkeypatch, value):
    from app.application.common.local_installation import InvalidLocalInstallationCode

    with pytest.raises(InvalidLocalInstallationCode) as exc_info:
        _settings(monkeypatch, value)
    assert "secret" not in str(exc_info.value)
    assert "postgresql" not in str(exc_info.value)


def test_setting_acepta_codigo_exclusivamente_numerico(monkeypatch):
    settings = _settings(monkeypatch, "123")
    assert settings.local_installation_code == "123"


def test_setting_ausente_es_default_deny_y_sanitizado(monkeypatch):
    from app.application.common.local_installation import LocalInstallationNotConfigured

    with pytest.raises(LocalInstallationNotConfigured) as exc_info:
        _settings(monkeypatch)
    assert "secret" not in str(exc_info.value)
    assert "DATABASE_URL" not in str(exc_info.value)


def test_setting_no_acepta_alias_ni_default(monkeypatch):
    monkeypatch.setenv("INSTALLATION_CODE", "INST-ALIAS")
    monkeypatch.setenv("CODIGO_INSTALACION", "INST-ALIAS")
    from app.application.common.local_installation import LocalInstallationNotConfigured

    with pytest.raises(LocalInstallationNotConfigured):
        _settings(monkeypatch)


def test_setting_no_normaliza_unicode(monkeypatch):
    decomposed = unicodedata.normalize("NFD", "INST-Á")
    assert _settings(monkeypatch, decomposed).local_installation_code == decomposed
