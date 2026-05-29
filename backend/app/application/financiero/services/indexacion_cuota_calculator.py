from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol

MODO_INDEXACION_POR_COEFICIENTE = "POR_COEFICIENTE"
BASE_CALCULO_INDEXACION_CAPITAL_INICIAL_BLOQUE = "CAPITAL_INICIAL_BLOQUE"
TIPO_GENERACION_INDEXADA_DEFINITIVA = "DEFINITIVA"
POLITICA_VALOR_NO_DISPONIBLE_ERROR = "ERROR_SI_NO_EXISTE"
ESTADO_INDEXACION_CON_INDICE = "CON_INDICE_APLICADO"
ESTADO_INDEXACION_PROYECTADA = "PROYECTADA_SIN_INDICE"


class IndiceFinancieroPublicadoQuery(Protocol):
    def get_valor_publicado_por_id_y_fecha(
        self,
        id_indice_financiero: int,
        fecha_objetivo: date,
    ) -> dict[str, Any] | None: ...


@dataclass(frozen=True, slots=True)
class ResultadoCalculoCuotaIndexada:
    estado_indexacion: str
    id_indice_financiero: int | None
    id_indice_financiero_valor: int | None
    fecha_valor_indice: date | None
    valor_base_indice: Decimal
    valor_aplicado_indice: Decimal | None
    coeficiente_indexacion: Decimal | None
    capital_cuota: Decimal
    ajuste_indexacion_cuota: Decimal | None
    importe_total: Decimal


class IndexacionCuotaCalculator:
    def __init__(
        self,
        indice_financiero_query: IndiceFinancieroPublicadoQuery | None = None,
    ) -> None:
        self.indice_financiero_query = indice_financiero_query

    def calcular(
        self,
        *,
        id_indice_financiero: int,
        valor_base_indice: Decimal,
        fecha_objetivo: date,
        capital_cuota: Decimal,
        modo_indexacion: str,
        base_calculo_indexacion: str,
        tipo_generacion_indexada: str,
        politica_valor_no_disponible: str,
    ) -> ResultadoCalculoCuotaIndexada:
        self._validar_parametros(
            valor_base_indice=valor_base_indice,
            modo_indexacion=modo_indexacion,
            base_calculo_indexacion=base_calculo_indexacion,
            tipo_generacion_indexada=tipo_generacion_indexada,
            politica_valor_no_disponible=politica_valor_no_disponible,
        )

        valor = None
        if self.indice_financiero_query is not None:
            valor = self.indice_financiero_query.get_valor_publicado_por_id_y_fecha(
                id_indice_financiero,
                fecha_objetivo,
            )

        if valor is None:
            return ResultadoCalculoCuotaIndexada(
                estado_indexacion=ESTADO_INDEXACION_PROYECTADA,
                id_indice_financiero=id_indice_financiero,
                id_indice_financiero_valor=None,
                fecha_valor_indice=None,
                valor_base_indice=valor_base_indice,
                valor_aplicado_indice=None,
                coeficiente_indexacion=None,
                capital_cuota=capital_cuota,
                ajuste_indexacion_cuota=None,
                importe_total=capital_cuota,
            )

        valor_aplicado = self._to_decimal(valor["valor_indice"])
        coeficiente = (valor_aplicado / valor_base_indice).quantize(
            Decimal("0.00000001"), rounding=ROUND_HALF_UP
        )
        ajuste = (capital_cuota * (coeficiente - Decimal("1"))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        importe_total = (capital_cuota + ajuste).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return ResultadoCalculoCuotaIndexada(
            estado_indexacion=ESTADO_INDEXACION_CON_INDICE,
            id_indice_financiero=valor["id_indice_financiero"],
            id_indice_financiero_valor=valor["id_indice_financiero_valor"],
            fecha_valor_indice=valor["fecha_valor"],
            valor_base_indice=valor_base_indice,
            valor_aplicado_indice=valor_aplicado,
            coeficiente_indexacion=coeficiente,
            capital_cuota=capital_cuota,
            ajuste_indexacion_cuota=ajuste,
            importe_total=importe_total,
        )

    @staticmethod
    def _validar_parametros(
        *,
        valor_base_indice: Decimal,
        modo_indexacion: str,
        base_calculo_indexacion: str,
        tipo_generacion_indexada: str,
        politica_valor_no_disponible: str,
    ) -> None:
        if valor_base_indice <= 0:
            raise ValueError("VALOR_BASE_INDICE_INVALIDO")
        if modo_indexacion != MODO_INDEXACION_POR_COEFICIENTE:
            raise ValueError("MODO_INDEXACION_INVALIDO")
        if base_calculo_indexacion != BASE_CALCULO_INDEXACION_CAPITAL_INICIAL_BLOQUE:
            raise ValueError("BASE_CALCULO_INDEXACION_INVALIDA")
        if tipo_generacion_indexada != TIPO_GENERACION_INDEXADA_DEFINITIVA:
            raise ValueError("TIPO_GENERACION_INDEXADA_INVALIDO")
        if politica_valor_no_disponible != POLITICA_VALOR_NO_DISPONIBLE_ERROR:
            raise ValueError("POLITICA_VALOR_NO_DISPONIBLE_INVALIDA")

    @staticmethod
    def _to_decimal(value: Any) -> Decimal:
        if isinstance(value, Decimal):
            return value
        return Decimal(str(value))
