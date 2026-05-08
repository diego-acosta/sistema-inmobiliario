from typing import Any, Protocol

from app.application.common.results import AppResult


class PersonaRepository(Protocol):
    def list_personas(
        self,
        *,
        q: str | None,
        tipo_persona: str | None,
        estado_persona: str | None,
        numero_documento: str | None,
        cuit_cuil: str | None,
        tipo_documento: str | None,
        contacto: str | None,
        rol_codigo: str | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]:
        ...


class ListPersonasService:
    def __init__(self, repository: PersonaRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        q: str | None,
        tipo_persona: str | None,
        estado_persona: str | None,
        numero_documento: str | None,
        cuit_cuil: str | None,
        tipo_documento: str | None,
        contacto: str | None,
        rol_codigo: str | None,
        limit: int,
        offset: int,
    ) -> AppResult[dict[str, Any]]:
        return AppResult.ok(
            self.repository.list_personas(
                q=_clean(q),
                tipo_persona=_clean(tipo_persona),
                estado_persona=_clean(estado_persona),
                numero_documento=_clean(numero_documento),
                cuit_cuil=_clean(cuit_cuil),
                tipo_documento=_clean(tipo_documento),
                contacto=_clean(contacto),
                rol_codigo=_clean(rol_codigo),
                limit=limit,
                offset=offset,
            )
        )


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None
