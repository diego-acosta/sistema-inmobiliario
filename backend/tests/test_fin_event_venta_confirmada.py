from sqlalchemy import text

from app.application.financiero.services.handle_venta_confirmada_event_service import (
    HandleVentaConfirmadaEventService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from tests.test_escrituraciones_create import _confirmar_venta_publica


def _build_service(db_session) -> HandleVentaConfirmadaEventService:
    return HandleVentaConfirmadaEventService(
        repository=FinancieroRepository(db_session),
    )


def _get_venta_confirmada_event(db_session, *, id_venta: int) -> dict:
    return db_session.execute(
        text(
            """
            SELECT id, event_type, aggregate_type, aggregate_id, payload
            FROM outbox_event
            WHERE event_type = 'venta_confirmada'
              AND aggregate_type = 'venta'
              AND aggregate_id = :id_venta
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()


def _count_relaciones_venta(db_session, *, id_venta: int) -> int:
    return db_session.execute(
        text(
            """
            SELECT COUNT(*) AS total
            FROM relacion_generadora
            WHERE tipo_origen = 'venta'
              AND id_origen = :id_venta
              AND deleted_at IS NULL
            """
        ),
        {"id_venta": id_venta},
    ).mappings().one()["total"]


def test_fin_venta_confirmada_crea_relacion_generadora_si_no_existe(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=venta["id_venta"]))

    result = _build_service(db_session).execute(event)

    assert result.success is True
    assert result.data is not None
    assert result.data["id_venta"] == venta["id_venta"]
    assert result.data["created"] is True
    assert isinstance(result.data["id_relacion_generadora"], int)

    row = db_session.execute(
        text(
            """
            SELECT tipo_origen, id_origen, descripcion, estado_relacion_generadora
            FROM relacion_generadora
            WHERE id_relacion_generadora = :id_relacion_generadora
            """
        ),
        {"id_relacion_generadora": result.data["id_relacion_generadora"]},
    ).mappings().one()
    assert row["tipo_origen"] == "venta"
    assert row["id_origen"] == venta["id_venta"]
    assert row["descripcion"] == "Relacion generadora creada desde venta_confirmada"
    assert row["estado_relacion_generadora"] == "BORRADOR"

    obligaciones = db_session.execute(
        text("SELECT COUNT(*) AS total FROM obligacion_financiera")
    ).mappings().one()
    assert obligaciones["total"] == 0


def test_fin_venta_confirmada_no_duplica_si_ya_existe(client, db_session) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=venta["id_venta"]))
    service = _build_service(db_session)

    first_result = service.execute(event)
    second_result = service.execute(event)

    assert first_result.success is True
    assert first_result.data is not None
    assert first_result.data["created"] is True
    assert second_result.success is True
    assert second_result.data is not None
    assert second_result.data["created"] is False
    assert (
        second_result.data["id_relacion_generadora"]
        == first_result.data["id_relacion_generadora"]
    )
    assert _count_relaciones_venta(db_session, id_venta=venta["id_venta"]) == 1


def test_fin_venta_confirmada_ignora_eventos_repetidos_idempotente(
    client, db_session
) -> None:
    venta = _confirmar_venta_publica(client, db_session)
    event = dict(_get_venta_confirmada_event(db_session, id_venta=venta["id_venta"]))
    service = _build_service(db_session)

    results = [service.execute(event) for _ in range(3)]

    assert all(result.success for result in results)
    assert results[0].data is not None
    assert results[0].data["created"] is True
    assert [result.data["created"] for result in results[1:]] == [False, False]
    assert _count_relaciones_venta(db_session, id_venta=venta["id_venta"]) == 1
