from functools import lru_cache
from os import getenv
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]


def _get_env_file() -> Path:
    env = getenv("ENV", "dev").strip().lower()
    if env == "test":
        return BASE_DIR / ".env.test"
    return BASE_DIR / ".env"


load_dotenv(_get_env_file(), override=True)


class Settings:
    def __init__(self) -> None:
        self.app_name = getenv("APP_NAME", "Sistema Inmobiliario API")
        self.app_version = getenv("APP_VERSION", "0.1.0")
        self.env = getenv("ENV", "dev")
        self.database_url = self._get_database_url()

    @staticmethod
    def _get_database_url() -> str:
        database_url = getenv("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "DATABASE_URL is not set. Define it in your environment file."
            )
        return database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
