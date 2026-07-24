from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.application.common.results import AppResult


class IndiceFinancieroQueryRepository(Protocol):
    def list_indices_financieros_activos(self, *, limit: int, offset: int) -> dict[str, Any]: ...
    def get_indice_financiero_por_id(self, id_indice_financiero: int) -> dict[str, Any] | None: ...
    def get_indice_financiero_por_codigo(self, codigo_indice_financiero: str) -> dict[str, Any] | None: ...
    def get_valor_publicado_por_id_y_fecha(self, id_indice_financiero: int, fecha_objetivo: date) -> dict[str, Any] | None: ...
    def get_valor_publicado_por_codigo_y_fecha(self, codigo_indice_financiero: str, fecha_objetivo: date) -> dict[str, Any] | None: ...


class ConsultarIndicesFinancierosService:
    """Queries read-only del catálogo y del valor aplicable de Financiero."""

    def __init__(self, repository: IndiceFinancieroQueryRepository) -> None:
        self.repository = repository

    def listar(self, *, limit: int, offset: int) -> AppResult[dict[str, Any]]:
        return AppResult.ok(self.repository.list_indices_financieros_activos(limit=limit, offset=offset))

    def resolver_valor_aplicable(
        self,
        *,
        id_indice_financiero: int | None,
        codigo_indice_financiero: str | None,
        fecha_objetivo: date,
    ) -> AppResult[dict[str, Any] | None]:
        if (id_indice_financiero is None) == (codigo_indice_financiero is None):
            return AppResult.fail("IDENTIFICADOR_INDICE_XOR_INVALIDO")

        if id_indice_financiero is not None:
            if id_indice_financiero <= 0:
                return AppResult.fail("ID_INDICE_FINANCIERO_INVALIDO")
            indice = self.repository.get_indice_financiero_por_id(id_indice_financiero)
            valor = self.repository.get_valor_publicado_por_id_y_fecha(
                id_indice_financiero, fecha_objetivo
            )
        else:
            codigo = (codigo_indice_financiero or "").strip()
            if not codigo:
                return AppResult.fail("CODIGO_INDICE_FINANCIERO_INVALIDO")
            indice = self.repository.get_indice_financiero_por_codigo(codigo)
            valor = self.repository.get_valor_publicado_por_codigo_y_fecha(codigo, fecha_objetivo)

        if indice is None:
            return AppResult.fail("INDICE_FINANCIERO_NO_ENCONTRADO")
        if indice["deleted_at"] is not None:
            return AppResult.fail("INDICE_FINANCIERO_ELIMINADO")
        if indice["estado_indice_financiero"] != "ACTIVO":
            return AppResult.fail("INDICE_FINANCIERO_INACTIVO")
        if valor is None:
            return AppResult.ok(None)

        return AppResult.ok({**valor, "fecha_objetivo": fecha_objetivo})
