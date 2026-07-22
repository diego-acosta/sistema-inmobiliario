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
