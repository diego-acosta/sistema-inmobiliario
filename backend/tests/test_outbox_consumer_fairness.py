import pytest

from app.application.inmuebles.services.consume_entrega_locativa_service import (
    EVENT_TYPE as ENTREGA_EVENT_TYPE,
    ConsumeEntregaLocativaService,
)
from app.application.inmuebles.services.consume_escrituracion_registrada_service import (
    EVENT_TYPE_ESCRITURACION_REGISTRADA,
    ConsumeEscrituracionRegistradaService,
)
from app.application.inmuebles.services.consume_restitucion_locativa_service import (
    EVENT_TYPE as RESTITUCION_EVENT_TYPE,
    ConsumeRestitucionLocativaService,
)
from app.application.inmuebles.services.consume_venta_confirmada_service import (
    EVENT_TYPE_VENTA_CONFIRMADA,
    ConsumeVentaConfirmadaService,
)


class RecordingOutboxRepository:
    def __init__(self) -> None:
        self.calls = []

    def get_pending_events(self, *, limit=100, event_types=None):
        self.calls.append({"limit": limit, "event_types": tuple(event_types or ())})
        return []


@pytest.mark.parametrize(
    ("service_factory", "expected_event_type"),
    [
        (
            lambda outbox: ConsumeVentaConfirmadaService(None, None, outbox),
            EVENT_TYPE_VENTA_CONFIRMADA,
        ),
        (
            lambda outbox: ConsumeEntregaLocativaService(None, None, outbox, None),
            ENTREGA_EVENT_TYPE,
        ),
        (
            lambda outbox: ConsumeRestitucionLocativaService(None, None, outbox, None),
            RESTITUCION_EVENT_TYPE,
        ),
        (
            lambda outbox: ConsumeEscrituracionRegistradaService(None, None, outbox),
            EVENT_TYPE_ESCRITURACION_REGISTRADA,
        ),
    ],
)
def test_consumers_especializados_declaran_filtro_sql(
    service_factory, expected_event_type
):
    outbox = RecordingOutboxRepository()

    result = service_factory(outbox).execute(limit=37)

    assert result.success is True
    assert outbox.calls == [
        {"limit": 37, "event_types": (expected_event_type,)},
    ]
