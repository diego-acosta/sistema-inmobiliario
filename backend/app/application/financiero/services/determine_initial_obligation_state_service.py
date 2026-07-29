"""Financial policy for issuing obligations from materialized amounts."""

from datetime import date

ESTADO_OBLIGACION_PROYECTADA = "PROYECTADA"
ESTADO_OBLIGACION_EMITIDA = "EMITIDA"


def determine_initial_obligation_state(
    *,
    definitive_amount_materialized: bool,
    fecha_aplicacion_indice: date | None = None,
    fecha_referencia: date | None = None,
) -> str:
    """Resolve the financial lifecycle state from the supplied business fact."""
    if (
        fecha_aplicacion_indice is not None
        and fecha_aplicacion_indice > (fecha_referencia or date.today())
    ):
        return ESTADO_OBLIGACION_PROYECTADA
    return (
        ESTADO_OBLIGACION_EMITIDA
        if definitive_amount_materialized
        else ESTADO_OBLIGACION_PROYECTADA
    )
