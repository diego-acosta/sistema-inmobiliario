from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def find_existing_by_codes(self, codigos: list[str]) -> list[dict[str, Any]]:
        ...

    def get_inmuebles(
        self,
        *,
        q: str | None = None,
        estado_administrativo: str | None = None,
        estado_juridico: str | None = None,
        id_desarrollo: int | None = None,
        disponibilidad_actual: str | None = None,
        ocupacion_actual: str | None = None,
        id_servicio: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        ...


class GetInmueblesService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        q: str | None = None,
        estado_administrativo: str | None = None,
        estado_juridico: str | None = None,
        id_desarrollo: int | None = None,
        disponibilidad_actual: str | None = None,
        ocupacion_actual: str | None = None,
        id_servicio: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> AppResult[dict[str, Any]]:
        inmuebles = self.repository.get_inmuebles(
            q=q,
            estado_administrativo=estado_administrativo,
            estado_juridico=estado_juridico,
            id_desarrollo=id_desarrollo,
            disponibilidad_actual=disponibilidad_actual,
            ocupacion_actual=ocupacion_actual,
            id_servicio=id_servicio,
            limit=limit,
            offset=offset,
        )
        return AppResult.ok(inmuebles)


class BuscarInmueblesExistentesImportacionService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(self, *, codigos: list[str]) -> AppResult[list[dict[str, Any]]]:
        codigos_normalizados = sorted(
            {str(codigo).strip().casefold() for codigo in codigos if str(codigo).strip()}
        )
        if not codigos_normalizados:
            return AppResult.ok([])
        return AppResult.ok(self.repository.find_existing_by_codes(codigos_normalizados))
