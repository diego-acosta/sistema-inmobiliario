from datetime import date
from typing import Any, Protocol

from app.application.common.results import AppResult


class LocativoRepository(Protocol):
    def list_contratos_alquiler(
        self,
        *,
        q: str | None,
        codigo_contrato: str | None,
        estado_contrato: str | None,
        id_persona: int | None,
        rol_codigo: str | None,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        fecha_inicio_desde: date | None,
        fecha_inicio_hasta: date | None,
        fecha_fin_desde: date | None,
        fecha_fin_hasta: date | None,
        con_saldo: bool | None,
        limit: int,
        offset: int,
    ) -> dict[str, Any]: ...


class ListContratosAlquilerService:
    def __init__(self, repository: LocativoRepository) -> None:
        self.repository = repository

    def execute(
        self,
        *,
        q: str | None,
        codigo_contrato: str | None,
        estado_contrato: str | None,
        id_persona: int | None,
        rol_codigo: str | None,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        fecha_inicio_desde: date | None,
        fecha_inicio_hasta: date | None,
        fecha_fin_desde: date | None,
        fecha_fin_hasta: date | None,
        con_saldo: bool | None,
        limit: int,
        offset: int,
    ) -> AppResult[dict[str, Any]]:
        if limit < 0 or offset < 0:
            return AppResult.fail("INVALID_PAGINATION")

        result = self.repository.list_contratos_alquiler(
            q=q,
            codigo_contrato=codigo_contrato,
            estado_contrato=estado_contrato,
            id_persona=id_persona,
            rol_codigo=rol_codigo,
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
            fecha_inicio_desde=fecha_inicio_desde,
            fecha_inicio_hasta=fecha_inicio_hasta,
            fecha_fin_desde=fecha_fin_desde,
            fecha_fin_hasta=fecha_fin_hasta,
            con_saldo=con_saldo,
            limit=limit,
            offset=offset,
        )
        return AppResult.ok(result)
