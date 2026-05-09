from typing import Any, Protocol

from app.application.common.results import AppResult


class InmuebleRepository(Protocol):
    def get_unidades_funcionales_global(
        self,
        *,
        q: str | None = None,
        id_inmueble: int | None = None,
        estado_administrativo: str | None = None,
        estado_operativo: str | None = None,
        disponibilidad_actual: str | None = None,
        ocupacion_actual: str | None = None,
        id_servicio: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        ...


class GetUnidadesFuncionalesGlobalService:
    def __init__(self, repository: InmuebleRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        q: str | None = None,
        id_inmueble: int | None = None,
        estado_administrativo: str | None = None,
        estado_operativo: str | None = None,
        disponibilidad_actual: str | None = None,
        ocupacion_actual: str | None = None,
        id_servicio: int | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> AppResult[dict[str, Any]]:
        unidades = self.repository.get_unidades_funcionales_global(
            q=q,
            id_inmueble=id_inmueble,
            estado_administrativo=estado_administrativo,
            estado_operativo=estado_operativo,
            disponibilidad_actual=disponibilidad_actual,
            ocupacion_actual=ocupacion_actual,
            id_servicio=id_servicio,
            limit=limit,
            offset=offset,
        )
        return AppResult.ok(unidades)
