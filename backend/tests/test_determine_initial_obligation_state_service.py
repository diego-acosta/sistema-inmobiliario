from datetime import date

import pytest

from app.application.financiero.services.determine_initial_obligation_state_service import (
    determine_initial_obligation_state,
)


@pytest.mark.parametrize(
    ("definitive_amount_materialized", "expected"),
    [(True, "EMITIDA"), (False, "PROYECTADA")],
)
def test_determine_initial_obligation_state(
    definitive_amount_materialized: bool, expected: str
) -> None:
    assert (
        determine_initial_obligation_state(
            definitive_amount_materialized=definitive_amount_materialized
        )
        == expected
    )


@pytest.mark.parametrize(
    ("fecha_aplicacion_indice", "expected"),
    [
        (date(2026, 7, 28), "EMITIDA"),
        (date(2026, 7, 29), "EMITIDA"),
        (date(2026, 7, 30), "PROYECTADA"),
    ],
)
def test_determine_initial_obligation_state_respects_index_application_date(
    fecha_aplicacion_indice: date, expected: str
) -> None:
    assert (
        determine_initial_obligation_state(
            definitive_amount_materialized=True,
            fecha_aplicacion_indice=fecha_aplicacion_indice,
            fecha_referencia=date(2026, 7, 29),
        )
        == expected
    )
