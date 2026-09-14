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


def test_setting_ausente_permite_backend_central(monkeypatch):
    assert _settings(monkeypatch).local_installation_code is None


def test_setting_no_acepta_alias_ni_default(monkeypatch):
    monkeypatch.setenv("INSTALLATION_CODE", "INST-ALIAS")
    monkeypatch.setenv("CODIGO_INSTALACION", "INST-ALIAS")
    assert _settings(monkeypatch).local_installation_code is None


def test_database_url_sigue_obligatorio(monkeypatch):
    from app.config.settings import Settings
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="DATABASE_URL"):
        Settings()


def test_setting_no_normaliza_unicode(monkeypatch):
    decomposed = unicodedata.normalize("NFD", "INST-Á")
    assert _settings(monkeypatch, decomposed).local_installation_code == decomposed


def test_main_and_database_import_without_installation(monkeypatch):
    import os
    import subprocess
    import sys
    from pathlib import Path
    env = dict(os.environ)
    env.pop("LOCAL_INSTALLATION_CODE", None)
    env["DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@localhost/inmobiliaria_test"
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1])
    result = subprocess.run([sys.executable, "-c", "import dotenv; dotenv.load_dotenv=lambda *a, **k: None; from app.config.settings import Settings; assert Settings().local_installation_code is None; import app.config.database; import app.main"], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
