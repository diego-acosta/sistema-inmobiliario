import os


DEFAULT_API_BASE_URL = "http://localhost:8000"


def get_api_base_url() -> str:
    return os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL).rstrip("/")
