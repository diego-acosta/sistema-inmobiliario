from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.application.administrativo.services.usuario_sync_service import (
    USUARIO_SYNC_CONSUMER,
    UsuarioSyncApplicator,
    parse_usuario_outbox_envelope,
    register_usuario_outbox_delivery,
    run_usuario_inbox_once,
)
from app.application.integration.inbox_retry import InboxOutcomeKind
from app.config.database import engine
from app.infrastructure.persistence.repositories.inbox_repository import InboxRepository


CORE_HEADERS = {
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}


def _headers(op_id: str | None = None, *, version: int | None = None) -> dict[str, str]:
    headers = {**CORE_HEADERS, "X-Op-Id": op_id or str(uuid4())}
    if version is not None:
        headers["If-Match-Version"] = str(version)
    return headers


def _payload(suffix: str) -> dict:
    return {
        "codigo_usuario": f"USR-SYNC-{suffix}",
        "login": f"usr.sync.{suffix.lower()}",
        "email": f"usr.sync.{suffix.lower()}@example.com",
        "estado_usuario": "ACTIVO",
        "usuario_sistema_interno": False,
        "observaciones": "Usuario portable #510",
    }


def _snapshot(
    suffix: str,
    *,
    deleted: bool = False,
    estado: str | None = None,
) -> dict:
    now = datetime.now(UTC).replace(tzinfo=None).isoformat()
    return {
        **_payload(suffix),
        "estado_usuario": estado or ("INACTIVO" if deleted else "ACTIVO"),
        "fecha_alta": now,
        "fecha_baja": now if deleted else None,
        "deleted": deleted,
    }


def _event(
    suffix: str,
    *,
    uid: str | None = None,
    op_id: str | None = None,
    version: int = 1,
    event_type: str = "usuario_creado",
    snapshot: dict | None = None,
) -> dict:
    op_id = op_id or str(uuid4())
    return {
        "event_type": event_type,
        "aggregate_type": "usuario",
        "aggregate_uid": uid or str(uuid4()),
        "version_registro": version,
        "op_id": op_id,
        "payload": snapshot or _snapshot(suffix),
        "provenance": {"op_id_alta": op_id},
    }


def _usuario_uid(db_session, id_usuario: int) -> str:
    return db_session.execute(
        text("SELECT uid_global::text FROM usuario WHERE id_usuario=:id"),
        {"id": id_usuario},
    ).scalar_one()


def _outbox_for_user(db_session, id_usuario: int, event_type: str) -> dict:
    return dict(
        db_session.execute(
            text(
                """
                SELECT event_id::text AS event_id, event_type, aggregate_type,
                       aggregate_id, payload
                  FROM outbox_event
                 WHERE aggregate_type = 'usuario'
                   AND aggregate_id = :id_usuario
                   AND event_type = :event_type
                 ORDER BY occurred_at DESC
                 LIMIT 1
                """
            ),
            {"id_usuario": id_usuario, "event_type": event_type},
        ).mappings().one()
    )


def _retained_from_outbox(outbox: dict) -> dict:
    envelope = parse_usuario_outbox_envelope(
        event_type=outbox["event_type"],
        aggregate_type=outbox["aggregate_type"],
        value=outbox["payload"],
    )
    return {
        "event_type": outbox["event_type"],
        "aggregate_type": "usuario",
        "aggregate_uid": envelope["aggregate_uid"],
        "version_registro": envelope["version_registro"],
        "op_id": envelope["op_id"],
        "payload": envelope["snapshot"],
        "provenance": envelope["provenance"],
    }


def test_alta_genera_outbox_portable_en_misma_operacion(client, db_session):
    op_id = str(uuid4())
    response = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("OUTBOX"),
        headers=_headers(op_id),
    )
    assert response.status_code == 201
    created = response.json()["data"]
    uid = _usuario_uid(db_session, created["id_usuario"])

    outbox = _outbox_for_user(db_session, created["id_usuario"], "usuario_creado")
    envelope = outbox["payload"]
    assert outbox["aggregate_type"] == "usuario"
    assert envelope["aggregate_uid"] == uid
    assert envelope["version_registro"] == 1
    assert envelope["op_id"] == op_id
    assert "id_usuario" not in envelope
    assert "id_usuario" not in envelope["snapshot"]
    assert "fecha_ultimo_acceso" not in envelope["snapshot"]
    assert not {
        "password",
        "hash_credencial",
        "token",
        "token_sesion",
        "refresh_token",
    } & set(envelope["snapshot"])


def test_fallo_outbox_revierte_alta(client, db_session, monkeypatch):
    def fail_add_event(*args, **kwargs):
        raise RuntimeError("outbox unavailable")

    monkeypatch.setattr(
        "app.infrastructure.persistence.repositories.usuario_sistema_repository."
        "OutboxRepository.add_event",
        fail_add_event,
    )
    payload = _payload("ROLLBACK")
    response = client.post(
        "/api/v1/administrativo/usuarios",
        json=payload,
        headers=_headers(),
    )
    assert response.status_code == 500
    assert (
        db_session.execute(
            text("SELECT COUNT(*) FROM usuario WHERE codigo_usuario=:codigo"),
            {"codigo": payload["codigo_usuario"]},
        ).scalar_one()
        == 0
    )


def test_alta_remota_preserva_uid_y_pk_local_independiente(client, db_session):
    response = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("REMOTE"),
        headers=_headers(),
    )
    assert response.status_code == 201
    source = response.json()["data"]
    source_uid = _usuario_uid(db_session, source["id_usuario"])
    outbox = _outbox_for_user(db_session, source["id_usuario"], "usuario_creado")
    retained = _retained_from_outbox(outbox)

    db_session.execute(
        text("DELETE FROM usuario WHERE id_usuario=:id"),
        {"id": source["id_usuario"]},
    )
    outcome = UsuarioSyncApplicator(db_session).apply(retained)
    assert outcome.kind == InboxOutcomeKind.PROCESSED

    target = db_session.execute(
        text(
            "SELECT id_usuario, uid_global::text AS uid_global "
            "FROM usuario WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": source_uid},
    ).mappings().one()
    assert target["uid_global"] == source_uid
    assert target["id_usuario"] != source["id_usuario"]


def test_misma_version_mismo_snapshot_es_replay_y_distinto_es_conflicto(db_session):
    uid = str(uuid4())
    first = _event("SAME", uid=uid)
    applicator = UsuarioSyncApplicator(db_session)
    assert applicator.apply(first).kind == InboxOutcomeKind.PROCESSED

    same = deepcopy(first)
    same["op_id"] = str(uuid4())
    assert applicator.apply(same).kind == InboxOutcomeKind.PROCESSED

    different = deepcopy(same)
    different["op_id"] = str(uuid4())
    different["payload"]["observaciones"] = "snapshot material distinto"
    assert applicator.apply(different).kind == InboxOutcomeKind.CONFLICTO


def test_version_superior_y_salto_aplican_inferior_no_revierte(db_session):
    uid = str(uuid4())
    applicator = UsuarioSyncApplicator(db_session)
    assert applicator.apply(_event("VERS", uid=uid)).kind == InboxOutcomeKind.PROCESSED

    v3_snapshot = _snapshot("VERS")
    v3_snapshot["observaciones"] = "versión 3 aceptada por snapshot autoritativo"
    v3 = _event("VERS", uid=uid, version=3, snapshot=v3_snapshot)
    assert applicator.apply(v3).kind == InboxOutcomeKind.PROCESSED

    local = dict(
        db_session.execute(
            text(
                "SELECT version_registro, observaciones FROM usuario "
                "WHERE uid_global=CAST(:uid AS uuid)"
            ),
            {"uid": uid},
        ).mappings().one()
    )
    assert local["version_registro"] == 3
    assert local["observaciones"] == v3_snapshot["observaciones"]

    old = _event("VERS", uid=uid, version=2)
    assert applicator.apply(old).kind == InboxOutcomeKind.PROCESSED
    after = dict(
        db_session.execute(
            text(
                "SELECT version_registro, observaciones FROM usuario "
                "WHERE uid_global=CAST(:uid AS uuid)"
            ),
            {"uid": uid},
        ).mappings().one()
    )
    assert after == local


def test_baja_remota_aplica_snapshot_logico(db_session):
    uid = str(uuid4())
    applicator = UsuarioSyncApplicator(db_session)
    assert applicator.apply(_event("BAJA", uid=uid)).kind == InboxOutcomeKind.PROCESSED

    baja = _event(
        "BAJA",
        uid=uid,
        version=2,
        event_type="usuario_desactivado",
        snapshot=_snapshot("BAJA", deleted=True),
    )
    assert applicator.apply(baja).kind == InboxOutcomeKind.PROCESSED
    row = db_session.execute(
        text(
            "SELECT estado_usuario, fecha_baja, deleted_at, version_registro "
            "FROM usuario WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": uid},
    ).mappings().one()
    assert row["estado_usuario"] == "INACTIVO"
    assert row["fecha_baja"] is not None
    assert row["deleted_at"] is not None
    assert row["version_registro"] == 2


def test_colision_codigo_o_login_con_uid_distinto_es_conflicto(db_session):
    applicator = UsuarioSyncApplicator(db_session)
    local_uid = str(uuid4())
    assert applicator.apply(_event("COLL", uid=local_uid)).kind == InboxOutcomeKind.PROCESSED

    remote = _event("OTHER", uid=str(uuid4()))
    remote["payload"]["codigo_usuario"] = _snapshot("COLL")["codigo_usuario"]
    assert applicator.apply(remote).kind == InboxOutcomeKind.CONFLICTO

    remote = _event("OTHER2", uid=str(uuid4()))
    remote["payload"]["login"] = _snapshot("COLL")["login"]
    assert applicator.apply(remote).kind == InboxOutcomeKind.CONFLICTO


@pytest.mark.parametrize("forbidden", ["id_usuario", "hash_credencial", "token_sesion"])
def test_payload_con_identidad_local_o_secretos_es_rechazado(db_session, forbidden):
    event = _event("REJECT")
    event["payload"][forbidden] = 99 if forbidden == "id_usuario" else "secret"
    outcome = UsuarioSyncApplicator(db_session).apply(event)
    assert outcome.kind == InboxOutcomeKind.REJECTED
    assert outcome.reason_code == "SYNC_PAYLOAD_INVALID"


def test_usuario_no_requiere_persona_rol_o_sucursal_para_aplicar(db_session):
    outcome = UsuarioSyncApplicator(db_session).apply(_event("NODEPS"))
    assert outcome.kind == InboxOutcomeKind.PROCESSED


def test_registro_inbox_usa_uid_y_no_pk_remota(client, db_session):
    response = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("INBOX"),
        headers=_headers(),
    )
    assert response.status_code == 201
    created = response.json()["data"]
    uid = _usuario_uid(db_session, created["id_usuario"])
    outbox = _outbox_for_user(db_session, created["id_usuario"], "usuario_creado")
    assert register_usuario_outbox_delivery(db_session, outbox_event=outbox) is True

    inbox = db_session.execute(
        text(
            """
            SELECT aggregate_id, aggregate_uid::text AS aggregate_uid,
                   op_id::text AS op_id, consumer
              FROM inbox_event
             WHERE event_id=CAST(:event_id AS uuid)
               AND consumer=:consumer
            """
        ),
        {"event_id": outbox["event_id"], "consumer": USUARIO_SYNC_CONSUMER},
    ).mappings().one()
    assert inbox["aggregate_id"] == 0
    assert inbox["aggregate_uid"] == uid
    assert inbox["op_id"] == outbox["payload"]["op_id"]


def _committed_register(event: dict, *, event_id: str) -> None:
    with Session(engine) as session:
        assert InboxRepository(session).claim(
            event_id=event_id,
            event_type=event["event_type"],
            aggregate_type="usuario",
            aggregate_id=0,
            consumer=USUARIO_SYNC_CONSUMER,
            op_id=event["op_id"],
            aggregate_uid=event["aggregate_uid"],
            payload=event["payload"],
            provenance=event["provenance"],
            version_registro=event["version_registro"],
        )
        session.commit()


def _cleanup_committed(*, uid: str, op_id: str, event_ids: list[str]) -> None:
    with engine.begin() as connection:
        for event_id in event_ids:
            connection.execute(
                text(
                    "DELETE FROM inbox_event WHERE consumer=:consumer "
                    "AND event_id=CAST(:event_id AS uuid)"
                ),
                {"consumer": USUARIO_SYNC_CONSUMER, "event_id": event_id},
            )
        connection.execute(
            text(
                "DELETE FROM inbox_operation_scope "
                "WHERE consumer=:consumer AND op_id=CAST(:op_id AS uuid)"
            ),
            {"consumer": USUARIO_SYNC_CONSUMER, "op_id": op_id},
        )
        connection.execute(
            text("DELETE FROM usuario WHERE uid_global=CAST(:uid AS uuid)"),
            {"uid": uid},
        )


def test_operation_scope_usuario_replay_y_conflicto_postgresql_real():
    uid = str(uuid4())
    op_id = str(uuid4())
    event = _event("OPSCOPE-" + uuid4().hex[:8], uid=uid, op_id=op_id)
    first_id, replay_id, conflict_id = (str(uuid4()) for _ in range(3))
    try:
        _committed_register(event, event_id=first_id)
        with Session(engine) as session:
            first = run_usuario_inbox_once(
                session, worker_id="usuario-510", event_id=first_id, manual=True
            )
        assert first is not None and first.kind == InboxOutcomeKind.PROCESSED

        _committed_register(event, event_id=replay_id)
        with Session(engine) as session:
            replay = run_usuario_inbox_once(
                session, worker_id="usuario-510", event_id=replay_id, manual=True
            )
        assert replay is not None and replay.kind == InboxOutcomeKind.PROCESSED

        incompatible = deepcopy(event)
        incompatible["payload"]["observaciones"] = "mismo op_id, fingerprint distinto"
        _committed_register(incompatible, event_id=conflict_id)
        with Session(engine) as session:
            conflict = run_usuario_inbox_once(
                session, worker_id="usuario-510", event_id=conflict_id, manual=True
            )
        assert conflict is not None and conflict.kind == InboxOutcomeKind.CONFLICTO
    finally:
        _cleanup_committed(
            uid=uid,
            op_id=op_id,
            event_ids=[first_id, replay_id, conflict_id],
        )
