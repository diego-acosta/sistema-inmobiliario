"""Financial policy for issuing obligations from materialized amounts."""

ESTADO_OBLIGACION_PROYECTADA = "PROYECTADA"
ESTADO_OBLIGACION_EMITIDA = "EMITIDA"


def determine_initial_obligation_state(
    *, definitive_amount_materialized: bool
) -> str:
    """Resolve the financial lifecycle state from the supplied business fact."""
    return (
        ESTADO_OBLIGACION_EMITIDA
        if definitive_amount_materialized
        else ESTADO_OBLIGACION_PROYECTADA
    )
