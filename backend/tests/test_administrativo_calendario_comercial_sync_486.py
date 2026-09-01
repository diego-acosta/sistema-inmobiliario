from copy import deepcopy
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.core_ef_headers import AuthenticatedCoreEFHeaders, TechnicalCoreEFHeaders
from app.application.administrativo.services.bootstrap_calendario_comercial_service import (
    BootstrapCalendarioComercialService,
)
from app.application.administrativo.services.calendario_comercial_sync_service import (
    CALENDARIO_SYNC_CONSUMER,
    CalendarioComercialSyncPayloadError,
    _is_reconciliable_integrity_error,
    parse_calendario_outbox_envelope,
    register_calendario_outbox_delivery,
    run_calendario_inbox_once,
    transport_calendario_outbox_once,
)
from app.application.administrativo.services.programar_calendario_comercial_service import (
    ProgramarCalendarioComercialService,
)
from app.application.common.idempotency import canonical_payload_hash
from app.application.integration.inbox_retry import InboxOutcomeKind
from app.infrastructure.persistence.repositories.inbox_repository import InboxRepository
from app.infrastructure.persistence.repositories.outbox_repository import (
    OutboxRepository,
)


class _NullSession:
    """Adapta la sesión transaccional del fixture al lifecycle de #512."""

    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, *_):
        return False


def _run_inbox(db_session, **kwargs):
    return run_calendario_inbox_once(
        db_session,
        lifecycle_session_factory=lambda: _NullSession(db_session),
        **kwargs,
    )


def _headers(op_id=None, version=None):
    cls = AuthenticatedCoreEFHeaders if version is not None else TechnicalCoreEFHeaders
    values = {
        "x_op_id": op_id or uuid4(),
        "x_sucursal_id": 1,
        "x_instalacion_id": 1,
    }
    if version is not None:
        values["if_match_version"] = version
    return cls(**values)


def _outbox(db_session, event_type):
    return dict(
        db_session.execute(
            text("""
            SELECT id, event_id, event_type, aggregate_type, aggregate_id,
                   payload, occurred_at, published_at, processed_at, status,
                   retry_count, last_error, processing_reason,
                   processing_metadata
              FROM outbox_event
             WHERE event_type=:event_type
             ORDER BY id DESC LIMIT 1
            """),
            {"event_type": event_type},
        )
        .mappings()
        .one()
    )


def _bootstrap_origin(db_session, op_id=None):
    BootstrapCalendarioComercialService(db_session).execute(
        dia_cierre_comercial=20,
        dia_vencimiento_predeterminado_cuotas=10,
        vigente_desde=date(2026, 9, 1),
        headers=_headers(op_id),
        id_usuario=1,
    )
    db_session.commit()
    return _outbox(db_session, "calendario_comercial_creado")


def _program_origin(db_session, op_id=None):
    ProgramarCalendarioComercialService(db_session).execute(
        dia_cierre_comercial=21,
        dia_vencimiento_predeterminado_cuotas=11,
        vigente_desde=date(2026, 10, 1),
        headers=_headers(op_id, 1),
        id_usuario=1,
    )
    db_session.commit()
    return _outbox(db_session, "calendario_comercial_programado")


def _program_origin_v3(db_session, op_id=None):
    ProgramarCalendarioComercialService(db_session).execute(
        dia_cierre_comercial=22,
        dia_vencimiento_predeterminado_cuotas=12,
        vigente_desde=date(2026, 11, 1),
        headers=_headers(op_id, 2),
        id_usuario=1,
    )
    db_session.commit()
    return _outbox(db_session, "calendario_comercial_programado")


def _clear_calendar(db_session):
    db_session.execute(
        text("""
        DELETE FROM valor_parametro v USING parametro_sistema p
         WHERE v.id_parametro_sistema=p.id_parametro_sistema
           AND p.codigo_parametro IN
             ('DIA_CIERRE_COMERCIAL',
              'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
        """)
    )
    db_session.execute(text("DELETE FROM configuracion_calendario_comercial"))
    db_session.commit()


def _rehash(payload):
    payload["metadata"]["payload_hash"] = canonical_payload_hash(
        {
            "metadata": {
                "uid_instalacion_origen": payload["metadata"][
                    "uid_instalacion_origen"
                ]
            },
            "data": payload["data"],
        }
    )
    return payload


@pytest.mark.parametrize(
    "event_type",
    ["calendario_comercial_creado", "calendario_comercial_programado"],
)
def test_parser_acepta_ambos_envelopes_reales(db_session, event_type):
    created = _bootstrap_origin(db_session)
    event = created if event_type.endswith("creado") else _program_origin(db_session)

    parsed = parse_calendario_outbox_envelope(
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        value=event["payload"],
    )

    assert parsed["aggregate_uid"] == event["payload"]["data"]["uid_global"]
    assert parsed["op_id"] == event["payload"]["data"]["op_id"]
    assert parsed["provenance"]["producer_payload_hash"] == event["payload"][
        "metadata"
    ]["payload_hash"]


@pytest.mark.parametrize(
    ("mutation", "rehash"),
    [
        (lambda value: value["data"].pop("op_id"), False),
        (lambda value: value["data"].__setitem__("campo_extra", 1), True),
        (lambda value: value["data"].__setitem__("uid_global", "no-uuid"), True),
        (lambda value: value["data"].__setitem__("vigente_desde", "2026-02-30"), True),
        (lambda value: value["data"].__setitem__("version_agregada", 0), True),
        (lambda value: value["data"].__setitem__("dia_cierre_comercial", 32), True),
        (lambda value: value["data"].__setitem__("id_valor_parametro", 99), True),
        (lambda value: value["metadata"].__setitem__("payload_hash", "0" * 64), False),
    ],
)
def test_parser_default_deny_rechaza_envelope_invalido(db_session, mutation, rehash):
    payload = deepcopy(_bootstrap_origin(db_session)["payload"])
    mutation(payload)
    if rehash:
        _rehash(payload)

    with pytest.raises(CalendarioComercialSyncPayloadError):
        parse_calendario_outbox_envelope(
            event_type="calendario_comercial_creado",
            aggregate_type="calendario_comercial",
            value=payload,
        )


def test_parser_rechaza_tipo_y_aggregate_incorrectos(db_session):
    event = _bootstrap_origin(db_session)
    with pytest.raises(CalendarioComercialSyncPayloadError):
        parse_calendario_outbox_envelope(
            event_type="valor_parametro_modificado",
            aggregate_type="calendario_comercial",
            value=event["payload"],
        )
    with pytest.raises(CalendarioComercialSyncPayloadError):
        parse_calendario_outbox_envelope(
            event_type=event["event_type"],
            aggregate_type="valor_parametro",
            value=event["payload"],
        )


def test_registro_separa_hash_productor_de_fingerprint_tecnico(db_session):
    event = _bootstrap_origin(db_session)
    assert register_calendario_outbox_delivery(db_session, outbox_event=event)
    assert not register_calendario_outbox_delivery(db_session, outbox_event=event)
    delivery = InboxRepository(db_session).get(
        event_id=str(event["event_id"]), consumer=CALENDARIO_SYNC_CONSUMER
    )
    assert delivery["payload_fingerprint"] != event["payload"]["metadata"][
        "payload_hash"
    ]
    assert delivery["provenance"]["producer_payload_hash"] == event["payload"][
        "metadata"
    ]["payload_hash"]


def test_creacion_remota_preserva_uids_y_es_replayable(db_session):
    event = _bootstrap_origin(db_session)
    expected = event["payload"]["data"]
    _clear_calendar(db_session)
    assert register_calendario_outbox_delivery(db_session, outbox_event=event)
    db_session.commit()

    outcome = _run_inbox(
        db_session, worker_id="calendar", event_id=str(event["event_id"]), manual=True
    )

    assert outcome.kind is InboxOutcomeKind.PROCESSED
    root = db_session.execute(
        text("SELECT uid_global, version_registro FROM configuracion_calendario_comercial")
    ).one()
    assert str(root.uid_global) == expected["uid_global"]
    assert root.version_registro == 1
    children = dict(
        db_session.execute(
            text("""
            SELECT p.codigo_parametro, v.uid_global
              FROM valor_parametro v
              JOIN parametro_sistema p USING(id_parametro_sistema)
             WHERE p.codigo_parametro IN
               ('DIA_CIERRE_COMERCIAL',
                'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
            """)
        ).all()
    )
    assert str(children["DIA_CIERRE_COMERCIAL"]) == expected[
        "valor_dia_cierre_comercial"
    ]["uid_global"]
    assert str(children["DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS"]) == expected[
        "valor_dia_vencimiento_predeterminado_cuotas"
    ]["uid_global"]

    duplicate = deepcopy(event)
    duplicate["event_id"] = uuid4()
    assert register_calendario_outbox_delivery(db_session, outbox_event=duplicate)
    db_session.commit()
    replay = _run_inbox(
        db_session,
        worker_id="calendar-replay",
        event_id=str(duplicate["event_id"]),
        manual=True,
    )
    assert replay.kind is InboxOutcomeKind.PROCESSED
    assert db_session.execute(
        text("SELECT count(*) FROM configuracion_calendario_comercial")
    ).scalar_one() == 1


def test_mismo_op_id_payload_distinto_es_conflicto(db_session):
    event = _bootstrap_origin(db_session)
    _clear_calendar(db_session)
    assert register_calendario_outbox_delivery(db_session, outbox_event=event)
    db_session.commit()
    assert _run_inbox(
        db_session,
        worker_id="calendar-first",
        event_id=str(event["event_id"]),
        manual=True,
    ).kind is InboxOutcomeKind.PROCESSED

    incompatible = deepcopy(event)
    incompatible["event_id"] = uuid4()
    incompatible["payload"]["data"]["dia_cierre_comercial"] = 22
    _rehash(incompatible["payload"])
    assert register_calendario_outbox_delivery(
        db_session, outbox_event=incompatible
    )
    db_session.commit()
    assert _run_inbox(
        db_session,
        worker_id="calendar-conflict",
        event_id=str(incompatible["event_id"]),
        manual=True,
    ).kind is InboxOutcomeKind.CONFLICTO


def test_op_distinto_mismo_snapshot_converge_sin_segundo_efecto(db_session):
    event = _bootstrap_origin(db_session)
    _clear_calendar(db_session)
    assert register_calendario_outbox_delivery(db_session, outbox_event=event)
    db_session.commit()
    assert _run_inbox(
        db_session,
        worker_id="calendar-first",
        event_id=str(event["event_id"]),
        manual=True,
    ).kind is InboxOutcomeKind.PROCESSED

    convergent = deepcopy(event)
    convergent["event_id"] = uuid4()
    convergent["payload"]["data"]["op_id"] = str(uuid4())
    _rehash(convergent["payload"])
    assert register_calendario_outbox_delivery(db_session, outbox_event=convergent)
    db_session.commit()
    assert _run_inbox(
        db_session,
        worker_id="calendar-convergent",
        event_id=str(convergent["event_id"]),
        manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    assert db_session.execute(
        text("SELECT count(*) FROM configuracion_calendario_comercial")
    ).scalar_one() == 1
    assert db_session.execute(
        text(
            "SELECT count(*) FROM inbox_operation_scope "
            "WHERE consumer=:consumer"
        ),
        {"consumer": CALENDARIO_SYNC_CONSUMER},
    ).scalar_one() == 2


def test_programacion_remota_y_consultas_historicas(db_session):
    created = _bootstrap_origin(db_session)
    programmed = _program_origin(db_session)
    _clear_calendar(db_session)
    for event in (created, programmed):
        assert register_calendario_outbox_delivery(db_session, outbox_event=event)
        db_session.commit()
        outcome = _run_inbox(
            db_session,
            worker_id="calendar",
            event_id=str(event["event_id"]),
            manual=True,
        )
        assert outcome.kind is InboxOutcomeKind.PROCESSED

    root_version = db_session.execute(
        text("SELECT version_registro FROM configuracion_calendario_comercial")
    ).scalar_one()
    intervals = db_session.execute(
        text("""
        SELECT fecha_desde::date, fecha_hasta::date, count(*)
          FROM valor_parametro v JOIN parametro_sistema p USING(id_parametro_sistema)
         WHERE p.codigo_parametro IN
           ('DIA_CIERRE_COMERCIAL',
            'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
         GROUP BY fecha_desde, fecha_hasta ORDER BY fecha_desde
        """)
    ).all()
    assert root_version == 2
    assert intervals == [
        (date(2026, 9, 1), date(2026, 10, 1), 2),
        (date(2026, 10, 1), None, 2),
    ]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (False, InboxOutcomeKind.PROCESSED),
        (True, InboxOutcomeKind.CONFLICTO),
    ],
)
def test_v2_mismo_version_con_op_distinto_clasifica_snapshot(
    db_session, mutate, expected
):
    created = _bootstrap_origin(db_session)
    programmed = _program_origin(db_session)
    _clear_calendar(db_session)
    for event in (created, programmed):
        assert register_calendario_outbox_delivery(db_session, outbox_event=event)
        db_session.commit()
        assert _run_inbox(
            db_session,
            worker_id="calendar",
            event_id=str(event["event_id"]),
            manual=True,
        ).kind is InboxOutcomeKind.PROCESSED

    candidate = deepcopy(programmed)
    candidate["event_id"] = uuid4()
    candidate["payload"]["data"]["op_id"] = str(uuid4())
    if mutate:
        candidate["payload"]["data"]["dia_cierre_comercial"] = 31
    _rehash(candidate["payload"])
    assert register_calendario_outbox_delivery(db_session, outbox_event=candidate)
    db_session.commit()
    assert _run_inbox(
        db_session,
        worker_id="calendar-equal-version",
        event_id=str(candidate["event_id"]),
        manual=True,
    ).kind is expected
    assert db_session.execute(
        text("SELECT version_registro FROM configuracion_calendario_comercial")
    ).scalar_one() == 2


def test_version_inferior_es_obsoleta_sin_mutacion(db_session):
    created = _bootstrap_origin(db_session)
    v2 = _program_origin(db_session)
    v3 = _program_origin_v3(db_session)
    _clear_calendar(db_session)
    for event in (created, v2, v3):
        assert register_calendario_outbox_delivery(db_session, outbox_event=event)
        db_session.commit()
        assert _run_inbox(
            db_session,
            worker_id="calendar",
            event_id=str(event["event_id"]),
            manual=True,
        ).kind is InboxOutcomeKind.PROCESSED

    obsolete = deepcopy(v2)
    obsolete["event_id"] = uuid4()
    obsolete["payload"]["data"]["op_id"] = str(uuid4())
    _rehash(obsolete["payload"])
    assert register_calendario_outbox_delivery(db_session, outbox_event=obsolete)
    db_session.commit()
    assert _run_inbox(
        db_session,
        worker_id="calendar-obsolete",
        event_id=str(obsolete["event_id"]),
        manual=True,
    ).kind is InboxOutcomeKind.PROCESSED
    assert db_session.execute(
        text("SELECT version_registro FROM configuracion_calendario_comercial")
    ).scalar_one() == 3


def test_v3_antes_de_v2_pending_y_converge_despues(db_session):
    created = _bootstrap_origin(db_session)
    v2 = _program_origin(db_session)
    v2_data = deepcopy(v2["payload"]["data"])
    v3 = deepcopy(v2)
    v3["event_id"] = uuid4()
    v3["payload"]["data"].update(
        {
            "version_agregada": 3,
            "version_agregada_anterior": 2,
            "vigente_desde": "2026-11-01",
            "fecha_desde_vigencia_anterior": "2026-10-01",
            "fecha_hasta_vigencia_anterior": "2026-11-01",
            "op_id": str(uuid4()),
        }
    )
    v3["payload"]["data"]["valor_anterior_dia_cierre_comercial"] = deepcopy(
        v2_data["valor_dia_cierre_comercial"]
    )
    v3["payload"]["data"]["valor_anterior_dia_cierre_comercial"][
        "version_registro"
    ] = 2
    v3["payload"]["data"][
        "valor_anterior_dia_vencimiento_predeterminado_cuotas"
    ] = deepcopy(v2_data["valor_dia_vencimiento_predeterminado_cuotas"])
    v3["payload"]["data"][
        "valor_anterior_dia_vencimiento_predeterminado_cuotas"
    ]["version_registro"] = 2
    v3["payload"]["data"]["valor_dia_cierre_comercial"] = {
        "uid_global": str(uuid4()),
        "version_registro": 1,
    }
    v3["payload"]["data"]["valor_dia_vencimiento_predeterminado_cuotas"] = {
        "uid_global": str(uuid4()),
        "version_registro": 1,
    }
    _rehash(v3["payload"])
    _clear_calendar(db_session)

    for event in (created, v3):
        assert register_calendario_outbox_delivery(db_session, outbox_event=event)
        db_session.commit()
        outcome = _run_inbox(
            db_session, worker_id="calendar", event_id=str(event["event_id"]), manual=True
        )
    assert outcome.kind is InboxOutcomeKind.PENDING_DEPENDENCY

    assert register_calendario_outbox_delivery(db_session, outbox_event=v2)
    db_session.commit()
    assert _run_inbox(
        db_session, worker_id="calendar", event_id=str(v2["event_id"]), manual=True
    ).kind is InboxOutcomeKind.PROCESSED
    assert _run_inbox(
        db_session, worker_id="calendar", event_id=str(v3["event_id"]), manual=True
    ).kind is InboxOutcomeKind.PROCESSED
    assert db_session.execute(
        text("SELECT version_registro FROM configuracion_calendario_comercial")
    ).scalar_one() == 3


def test_transporte_filtra_calendario_antes_del_limit(db_session):
    calendar = _bootstrap_origin(db_session)
    foreign = deepcopy(calendar)
    foreign["id"] = calendar["id"] - 1
    foreign["event_type"] = "usuario_creado"
    calls = []

    class RecordingOutbox:
        def __init__(self, _session):
            pass

        def get_pending_events(self, *, limit, event_types):
            calls.append((limit, frozenset(event_types)))
            return []

    with patch(
        (
            "app.application.administrativo.services."
            "calendario_comercial_sync_service.OutboxRepository"
        ),
        RecordingOutbox,
    ), patch(
        "app.application.administrativo.services."
        "calendario_comercial_sync_service._postgres_database_identity",
        side_effect=lambda session: (id(session),),
    ):
        assert transport_calendario_outbox_once(db_session, object(), limit=1) == (0, 0)
    assert calls == [
        (
            1,
            frozenset(
                {"calendario_comercial_creado", "calendario_comercial_programado"}
            ),
        )
    ]
    assert foreign["event_type"] == "usuario_creado"


def test_fairness_sql_eventos_ajenos_no_consumen_limit_calendario(db_session):
    db_session.execute(
        text("""
        INSERT INTO outbox_event(
            event_type, aggregate_type, aggregate_id, payload, occurred_at, status)
        SELECT 'usuario_creado', 'usuario', value, '{}'::jsonb,
               timestamp '2026-01-01' + value * interval '1 second', 'PENDING'
          FROM generate_series(1, 101) AS value
        """)
    )
    calendar = _bootstrap_origin(db_session)
    selected = OutboxRepository(db_session).get_pending_events(
        limit=1,
        event_types={"calendario_comercial_creado", "calendario_comercial_programado"},
    )
    assert [str(event["event_id"]) for event in selected] == [
        str(calendar["event_id"])
    ]


def test_transporte_rechaza_self_delivery(db_session):
    with pytest.raises(
        ValueError, match="CALENDARIO_SYNC_SOURCE_DESTINATION_MUST_DIFFER"
    ):
        transport_calendario_outbox_once(db_session, db_session)


def test_transporte_rechaza_sessions_distintas_sobre_misma_base(db_session):
    event = _bootstrap_origin(db_session)
    inbox_before = db_session.execute(
        text("SELECT count(*) FROM inbox_event")
    ).scalar_one()
    bind = db_session.get_bind()
    with Session(getattr(bind, "engine", bind)) as destination:
        assert destination is not db_session
        with pytest.raises(
            ValueError, match="CALENDARIO_SYNC_SOURCE_DESTINATION_MUST_DIFFER"
        ):
            transport_calendario_outbox_once(db_session, destination)
    assert _outbox(db_session, event["event_type"])["status"] == "PENDING"
    assert (
        db_session.execute(text("SELECT count(*) FROM inbox_event")).scalar_one()
        == inbox_before
    )


def test_transporte_confirma_destino_antes_del_ack_origen():
    calls = []
    event = {"id": 7}

    class Source:
        def commit(self):
            calls.append("source.commit")

        def rollback(self):
            calls.append("source.rollback")

    class Destination:
        def commit(self):
            calls.append("destination.commit")

        def rollback(self):
            calls.append("destination.rollback")

    class Outbox:
        def __init__(self, _session):
            pass

        def get_pending_events(self, *, limit, event_types):
            return [event]

        def mark_as_published(self, event_id):
            assert event_id == 7
            calls.append("source.ack")

    with (
        patch(
            "app.application.administrativo.services."
            "calendario_comercial_sync_service.OutboxRepository",
            Outbox,
        ),
        patch(
            "app.application.administrativo.services."
            "calendario_comercial_sync_service.register_calendario_outbox_delivery",
            side_effect=lambda session, outbox_event: calls.append(
                "destination.register"
            )
            or True,
        ),
        patch(
            "app.application.administrativo.services."
            "calendario_comercial_sync_service._postgres_database_identity",
            side_effect=lambda session: (id(session),),
        ),
    ):
        assert transport_calendario_outbox_once(Source(), Destination()) == (1, 1)
    assert calls == [
        "destination.register",
        "destination.commit",
        "source.ack",
        "source.commit",
    ]


def test_transporte_no_ackea_si_destino_falla():
    calls = []

    class Source:
        def rollback(self):
            calls.append("source.rollback")

    class Destination:
        def commit(self):
            raise RuntimeError("destination unavailable")

        def rollback(self):
            calls.append("destination.rollback")

    class Outbox:
        def __init__(self, _session):
            pass

        def get_pending_events(self, *, limit, event_types):
            return [{"id": 8}]

        def mark_as_published(self, event_id):
            calls.append("source.ack")

    with (
        patch(
            "app.application.administrativo.services."
            "calendario_comercial_sync_service.OutboxRepository",
            Outbox,
        ),
        patch(
            "app.application.administrativo.services."
            "calendario_comercial_sync_service.register_calendario_outbox_delivery",
            return_value=True,
        ),
        patch(
            "app.application.administrativo.services."
            "calendario_comercial_sync_service._postgres_database_identity",
            side_effect=lambda session: (id(session),),
        ),
        pytest.raises(RuntimeError, match="destination unavailable"),
    ):
        transport_calendario_outbox_once(Source(), Destination())
    assert calls == ["destination.rollback", "source.rollback"]


def test_integrity_error_solo_reconcilia_unique_conocida():
    class Diagnostic:
        constraint_name = "uq_valor_parametro_uid_global"

    class KnownUnique(Exception):
        sqlstate = "23505"
        diag = Diagnostic()

    class UnexpectedCheck(Exception):
        sqlstate = "23514"
        diag = type("Diagnostic", (), {"constraint_name": "unexpected_check"})()

    assert _is_reconciliable_integrity_error(
        IntegrityError("insert", {}, KnownUnique())
    )
    assert not _is_reconciliable_integrity_error(
        IntegrityError("insert", {}, UnexpectedCheck())
    )


def test_raiz_historica_adicional_es_conflicto(db_session):
    event = _bootstrap_origin(db_session)
    _clear_calendar(db_session)
    assert register_calendario_outbox_delivery(db_session, outbox_event=event)
    db_session.commit()
    assert _run_inbox(
        db_session, worker_id="calendar", event_id=str(event["event_id"]), manual=True
    ).kind is InboxOutcomeKind.PROCESSED

    db_session.execute(
        text("""
        INSERT INTO configuracion_calendario_comercial(
            uid_global, version_registro, deleted_at, op_id_alta,
            op_id_ultima_modificacion)
        VALUES (:uid, 1, now(), :op, :op)
        """),
        {"uid": str(uuid4()), "op": str(uuid4())},
    )
    db_session.commit()
    convergent = deepcopy(event)
    convergent["event_id"] = uuid4()
    convergent["payload"]["data"]["op_id"] = str(uuid4())
    _rehash(convergent["payload"])
    assert register_calendario_outbox_delivery(db_session, outbox_event=convergent)
    db_session.commit()
    assert _run_inbox(
        db_session,
        worker_id="calendar-singleton",
        event_id=str(convergent["event_id"]),
        manual=True,
    ).kind is InboxOutcomeKind.CONFLICTO
