import importlib


def _reload_settings(monkeypatch, *, env: str, database_url: str | None):
    monkeypatch.setenv("ENV", env)
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)

    import app.config.settings as settings_module

    reloaded = importlib.reload(settings_module)
    reloaded.get_settings.cache_clear()
    return reloaded


def test_database_url_del_entorno_prevalece_sobre_env_test(monkeypatch) -> None:
    database_url = "postgresql+psycopg://env_user:env_pass@localhost:5432/env_db"
    settings_module = _reload_settings(
        monkeypatch,
        env="test",
        database_url=database_url,
    )

    assert settings_module.get_settings().database_url == database_url


def test_env_test_funciona_como_fallback_si_no_hay_database_url(monkeypatch) -> None:
    settings_module = _reload_settings(
        monkeypatch,
        env="test",
        database_url=None,
    )

    assert settings_module.get_settings().database_url.endswith(
        "postgres:gc001@localhost:5432/inmobiliaria_test"
    )
