from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.application.financiero.services.indexacion_cuota_calculator import (
    ESTADO_INDEXACION_CON_INDICE,
    ESTADO_INDEXACION_PROYECTADA,
    IndexacionCuotaCalculator,
)


class _IndicePublicadoFake:
    def __init__(self, valor: dict[str, Any] | None) -> None:
        self.valor = valor
        self.calls: list[tuple[int, date]] = []

    def get_valor_publicado_por_id_y_fecha(
        self,
        id_indice_financiero: int,
        fecha_objetivo: date,
    ) -> dict[str, Any] | None:
        self.calls.append((id_indice_financiero, fecha_objetivo))
        return self.valor


def _calcular(
    query: _IndicePublicadoFake,
    *,
    valor_base_indice: Decimal = Decimal("100.00000000"),
    capital_cuota: Decimal = Decimal("1000.00"),
):
    return IndexacionCuotaCalculator(query).calcular(
        id_indice_financiero=7,
        valor_base_indice=valor_base_indice,
        fecha_objetivo=date(2026, 6, 10),
        capital_cuota=capital_cuota,
        modo_indexacion="POR_COEFICIENTE",
        base_calculo_indexacion="CAPITAL_INICIAL_BLOQUE",
        tipo_generacion_indexada="DEFINITIVA",
        politica_valor_no_disponible="ERROR_SI_NO_EXISTE",
    )


def test_calcula_cuota_indexada_con_indice_disponible() -> None:
    query = _IndicePublicadoFake(
        {
            "id_indice_financiero": 7,
            "id_indice_financiero_valor": 70,
            "fecha_valor": date(2026, 6, 10),
            "valor_indice": Decimal("125.00000000"),
        }
    )

    result = _calcular(query)

    assert query.calls == [(7, date(2026, 6, 10))]
    assert result.estado_indexacion == ESTADO_INDEXACION_CON_INDICE
    assert result.id_indice_financiero == 7
    assert result.id_indice_financiero_valor == 70
    assert result.fecha_valor_indice == date(2026, 6, 10)
    assert result.valor_base_indice == Decimal("100.00000000")
    assert result.valor_aplicado_indice == Decimal("125.00000000")
    assert result.coeficiente_indexacion == Decimal("1.25000000")
    assert result.capital_cuota == Decimal("1000.00")
    assert result.ajuste_indexacion_cuota == Decimal("250.00")
    assert result.importe_total == Decimal("1250.00")


def test_calcula_cuota_indexada_sin_indice_disponible_proyecta() -> None:
    query = _IndicePublicadoFake(None)

    result = _calcular(query)

    assert query.calls == [(7, date(2026, 6, 10))]
    assert result.estado_indexacion == ESTADO_INDEXACION_PROYECTADA
    assert result.id_indice_financiero == 7
    assert result.id_indice_financiero_valor is None
    assert result.fecha_valor_indice is None
    assert result.valor_base_indice == Decimal("100.00000000")
    assert result.valor_aplicado_indice is None
    assert result.coeficiente_indexacion is None
    assert result.capital_cuota == Decimal("1000.00")
    assert result.ajuste_indexacion_cuota is None
    assert result.importe_total == Decimal("1000.00")


def test_requiere_valor_base_indice_positivo() -> None:
    query = _IndicePublicadoFake(None)

    with pytest.raises(ValueError, match="VALOR_BASE_INDICE_INVALIDO"):
        _calcular(query, valor_base_indice=Decimal("0.00000000"))

    assert query.calls == []


def test_redondea_coeficiente_a_8_decimales_y_montos_a_2_decimales() -> None:
    query = _IndicePublicadoFake(
        {
            "id_indice_financiero": 7,
            "id_indice_financiero_valor": 71,
            "fecha_valor": date(2026, 6, 10),
            "valor_indice": Decimal("133.33333333"),
        }
    )

    result = _calcular(
        query,
        valor_base_indice=Decimal("100.00000000"),
        capital_cuota=Decimal("1000.01"),
    )

    assert result.coeficiente_indexacion == Decimal("1.33333333")
    assert result.ajuste_indexacion_cuota == Decimal("333.34")
    assert result.importe_total == Decimal("1333.35")
