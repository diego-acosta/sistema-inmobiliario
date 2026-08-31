from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from app.api.core_ef_headers import CoreEFHeaders
from app.application.administrativo.services.usuario_sync_service import (
    USUARIO_SYNC_CONSUMER,
    UsuarioSyncApplicator,
    UsuarioSyncPayloadError,
    parse_usuario_outbox_envelope,
    register_usuario_outbox_delivery,
    run_usuario_inbox_once,
)
from app.application.integration.inbox_retry import InboxOutcomeKind
from app.config.database import engine
from app.infrastructure.persistence.repositories.inbox_repository import (
    InboxOwnershipLost,
    InboxRepository,
    compute_retained_envelope_fingerprint,
)
from app.infrastructure.persistence.repositories.usuario_sistema_repository import (
    UsuarioIdempotencyConflictError,
    UsuarioSistemaRepository,
)
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

CORE_HEADERS = {
    "X-Usuario-Id": "1",
    "X-Sucursal-Id": "1",
    "X-Instalacion-Id": "1",
}
TEST_INSTALLATION_UID = str(uuid4())
_DEFAULT_OP_ID_ALTA = object()


def _core(op_id: str, *, version: int | None = None) -> CoreEFHeaders:
    return CoreEFHeaders(
        x_op_id=UUID(op_id),
        x_usuario_id=1,
        x_sucursal_id=1,
        x_instalacion_id=1,
        if_match_version=version,
    )


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
    op_id_alta: object = _DEFAULT_OP_ID_ALTA,
) -> dict:
    op_id = op_id or str(uuid4())
    if op_id_alta is _DEFAULT_OP_ID_ALTA:
        op_id_alta = op_id if event_type == "usuario_creado" else str(uuid4())
    return {
        "event_type": event_type,
        "aggregate_type": "usuario",
        "aggregate_uid": uid or str(uuid4()),
        "version_registro": version,
        "op_id": op_id,
        "payload": snapshot or _snapshot(suffix),
        "provenance": {
            "installation_uid": TEST_INSTALLATION_UID,
            "op_id_alta": op_id_alta,
        },
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
                       aggregate_id, payload, occurred_at
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
    assert envelope["provenance"]["installation_uid"]
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


def test_baja_genera_outbox_portable_con_misma_operacion(client, db_session):
    create = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("BAJA-OUTBOX"),
        headers=_headers(),
    )
    assert create.status_code == 201
    created = create.json()["data"]
    op_id = str(uuid4())

    baja = client.patch(
        f"/api/v1/administrativo/usuarios/{created['id_usuario']}/baja",
        headers=_headers(op_id, version=created["version_registro"]),
    )
    assert baja.status_code == 200

    outbox = _outbox_for_user(
        db_session, created["id_usuario"], "usuario_desactivado"
    )
    envelope = outbox["payload"]
    assert envelope["op_id"] == op_id
    assert envelope["version_registro"] == 2
    assert envelope["snapshot"]["estado_usuario"] == "INACTIVO"
    assert envelope["snapshot"]["deleted"] is True
    assert envelope["snapshot"]["fecha_baja"] is not None


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


def test_fallo_outbox_revierte_baja_y_version(client, db_session, monkeypatch):
    created = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("ROLLBACK-BAJA"),
        headers=_headers(),
    ).json()["data"]

    def fail_add_event(*args, **kwargs):
        raise RuntimeError("outbox unavailable")

    monkeypatch.setattr(
        "app.infrastructure.persistence.repositories.usuario_sistema_repository."
        "OutboxRepository.add_event",
        fail_add_event,
    )
    response = client.patch(
        f"/api/v1/administrativo/usuarios/{created['id_usuario']}/baja",
        headers=_headers(version=created["version_registro"]),
    )
    assert response.status_code == 500
    row = db_session.execute(
        text(
            "SELECT estado_usuario, fecha_baja, deleted_at, version_registro "
            "FROM usuario WHERE id_usuario=:id"
        ),
        {"id": created["id_usuario"]},
    ).mappings().one()
    assert row["estado_usuario"] == "ACTIVO"
    assert row["fecha_baja"] is None
    assert row["deleted_at"] is None
    assert row["version_registro"] == created["version_registro"]


def test_retry_nuevo_mismo_op_id_no_duplica_outbox(client, db_session):
    op_id = str(uuid4())
    payload = _payload("RETRY-OUTBOX")
    first = client.post(
        "/api/v1/administrativo/usuarios", json=payload, headers=_headers(op_id)
    )
    retry = client.post(
        "/api/v1/administrativo/usuarios", json=payload, headers=_headers(op_id)
    )
    assert first.status_code == retry.status_code == 201
    id_usuario = first.json()["data"]["id_usuario"]
    assert db_session.execute(
        text(
            "SELECT count(*) FROM outbox_event WHERE aggregate_type='usuario' "
            "AND aggregate_id=:id AND event_type='usuario_creado'"
        ),
        {"id": id_usuario},
    ).scalar_one() == 1


def test_op_id_de_alta_no_puede_reutilizarse_para_baja(client, db_session):
    op_id = str(uuid4())
    created = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("OP-ALTA-BAJA"),
        headers=_headers(op_id),
    ).json()["data"]

    response = client.patch(
        f"/api/v1/administrativo/usuarios/{created['id_usuario']}/baja",
        headers=_headers(op_id, version=created["version_registro"]),
    )
    assert response.status_code == 409
    assert response.json()["error_code"] == "IDEMPOTENT_DUPLICATE"

    row = db_session.execute(
        text(
            "SELECT estado_usuario, version_registro, deleted_at FROM usuario "
            "WHERE id_usuario=:id"
        ),
        {"id": created["id_usuario"]},
    ).mappings().one()
    assert row["estado_usuario"] == "ACTIVO"
    assert row["version_registro"] == created["version_registro"]
    assert row["deleted_at"] is None
    counts = dict(
        db_session.execute(
            text(
                "SELECT count(*) FILTER (WHERE event_type='usuario_creado') AS altas, "
                "count(*) FILTER (WHERE event_type='usuario_desactivado') AS bajas "
                "FROM outbox_event WHERE aggregate_type='usuario' AND aggregate_id=:id"
            ),
            {"id": created["id_usuario"]},
        ).mappings().one()
    )
    assert counts == {"altas": 1, "bajas": 0}


def test_retry_de_misma_baja_no_duplica_outbox(client, db_session):
    created = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("RETRY-BAJA-OUTBOX"),
        headers=_headers(),
    ).json()["data"]
    op_id = str(uuid4())
    headers = _headers(op_id, version=created["version_registro"])

    first = client.patch(
        f"/api/v1/administrativo/usuarios/{created['id_usuario']}/baja",
        headers=headers,
    )
    retry = client.patch(
        f"/api/v1/administrativo/usuarios/{created['id_usuario']}/baja",
        headers=headers,
    )
    assert first.status_code == retry.status_code == 200
    assert first.json()["data"] == retry.json()["data"]
    assert db_session.execute(
        text(
            "SELECT count(*) FROM outbox_event WHERE aggregate_type='usuario' "
            "AND aggregate_id=:id AND event_type='usuario_desactivado'"
        ),
        {"id": created["id_usuario"]},
    ).scalar_one() == 1


@pytest.mark.parametrize(
    ("field", "maximum"),
    [("codigo_usuario", 50), ("login", 100), ("email", 150)],
)
def test_limites_fisicos_portables_aceptan_maximo_y_rechazan_exceso(
    field, maximum
):
    event = _event(f"LIMIT-{field}")
    event["payload"][field] = "x" * maximum
    envelope = {
        "aggregate_uid": event["aggregate_uid"],
        "version_registro": event["version_registro"],
        "op_id": event["op_id"],
        "provenance": event["provenance"],
        "snapshot": event["payload"],
    }
    parsed = parse_usuario_outbox_envelope(
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        value=envelope,
    )
    assert parsed["snapshot"][field] == "x" * maximum

    oversized = deepcopy(envelope)
    oversized["snapshot"][field] = "x" * (maximum + 1)
    with pytest.raises(UsuarioSyncPayloadError, match="SYNC_PAYLOAD_INVALID"):
        parse_usuario_outbox_envelope(
            event_type=event["event_type"],
            aggregate_type=event["aggregate_type"],
            value=oversized,
        )


def test_estado_portable_sobredimensionado_es_rechazado():
    event = _event("LIMIT-ESTADO")
    event["payload"]["estado_usuario"] = "x" * 31
    with pytest.raises(UsuarioSyncPayloadError, match="SYNC_PAYLOAD_INVALID"):
        parse_usuario_outbox_envelope(
            event_type=event["event_type"],
            aggregate_type=event["aggregate_type"],
            value={
                "aggregate_uid": event["aggregate_uid"],
                "version_registro": event["version_registro"],
                "op_id": event["op_id"],
                "provenance": event["provenance"],
                "snapshot": event["payload"],
            },
        )


def test_textos_portables_canonicalizan_como_el_request_local():
    event = _event("TEXT-CANON")
    event["payload"]["codigo_usuario"] = "  USR-TEXT-CANON  "
    event["payload"]["login"] = "  usr.text.canon  "
    event["payload"]["estado_usuario"] = "  inactivo  "
    parsed = parse_usuario_outbox_envelope(
        event_type=event["event_type"],
        aggregate_type=event["aggregate_type"],
        value={
            "aggregate_uid": event["aggregate_uid"],
            "version_registro": event["version_registro"],
            "op_id": event["op_id"],
            "provenance": event["provenance"],
            "snapshot": event["payload"],
        },
    )
    assert parsed["snapshot"]["codigo_usuario"] == "USR-TEXT-CANON"
    assert parsed["snapshot"]["login"] == "usr.text.canon"
    assert parsed["snapshot"]["estado_usuario"] == "INACTIVO"


def test_timestamps_equivalentes_canonicalizan_snapshot_y_fingerprint():
    base = _event("TIME")
    zulu = deepcopy(base)
    zulu["payload"]["fecha_alta"] = "2026-08-28T12:00:00Z"
    offset = deepcopy(base)
    offset["payload"]["fecha_alta"] = "2026-08-28T09:00:00-03:00"
    plus_zero = deepcopy(base)
    plus_zero["payload"]["fecha_alta"] = "2026-08-28T12:00:00+00:00"

    parsed = [
        parse_usuario_outbox_envelope(
            event_type=item["event_type"],
            aggregate_type=item["aggregate_type"],
            value={
                "aggregate_uid": item["aggregate_uid"],
                "version_registro": item["version_registro"],
                "op_id": item["op_id"],
                "provenance": item["provenance"],
                "snapshot": item["payload"],
            },
        )
        for item in (zulu, offset, plus_zero)
    ]
    assert {item["snapshot"]["fecha_alta"] for item in parsed} == {
        "2026-08-28T12:00:00"
    }
    fingerprints = {
        compute_retained_envelope_fingerprint(
            event_type="usuario_creado",
            aggregate_type="usuario",
            aggregate_uid=item["aggregate_uid"],
            version_registro=item["version_registro"],
            payload=item["snapshot"],
            provenance=item["provenance"],
            op_id=item["op_id"],
        )
        for item in parsed
    }
    assert len(fingerprints) == 1


def test_instantes_distintos_permanecen_materialmente_distintos():
    first = _event("TIME-DIFF")
    second = deepcopy(first)
    first["payload"]["fecha_alta"] = "2026-08-28T12:00:00Z"
    second["payload"]["fecha_alta"] = "2026-08-28T12:00:01+00:00"
    envelopes = []
    for item in (first, second):
        envelopes.append(
            parse_usuario_outbox_envelope(
                event_type=item["event_type"],
                aggregate_type=item["aggregate_type"],
                value={
                    "aggregate_uid": item["aggregate_uid"],
                    "version_registro": item["version_registro"],
                    "op_id": item["op_id"],
                    "provenance": item["provenance"],
                    "snapshot": item["payload"],
                },
            )
        )
    assert envelopes[0]["snapshot"] != envelopes[1]["snapshot"]
    fingerprints = [
        compute_retained_envelope_fingerprint(
            event_type="usuario_creado",
            aggregate_type="usuario",
            aggregate_uid=item["aggregate_uid"],
            version_registro=item["version_registro"],
            payload=item["snapshot"],
            provenance=item["provenance"],
            op_id=item["op_id"],
        )
        for item in envelopes
    ]
    assert fingerprints[0] != fingerprints[1]


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
    assert applicator.apply(same).kind == InboxOutcomeKind.PROCESSED

    different = deepcopy(same)
    different["payload"]["observaciones"] = "snapshot material distinto"
    assert applicator.apply(different).kind == InboxOutcomeKind.CONFLICTO


@pytest.mark.parametrize("estado_usuario", ["ACTIVO", "INACTIVO"])
def test_usuario_creado_acepta_estados_del_request_local(db_session, estado_usuario):
    event = _event(f"CREATE-{estado_usuario}")
    event["payload"]["estado_usuario"] = estado_usuario
    outcome = UsuarioSyncApplicator(db_session).apply(event)
    assert outcome.kind == InboxOutcomeKind.PROCESSED
    row = db_session.execute(
        text(
            "SELECT estado_usuario, fecha_baja, deleted_at FROM usuario "
            "WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": event["aggregate_uid"]},
    ).mappings().one()
    assert row["estado_usuario"] == estado_usuario
    assert row["fecha_baja"] is None
    assert row["deleted_at"] is None


def test_usuario_creado_rechaza_estado_fuera_del_request_local(db_session):
    event = _event("CREATE-CORRUPTO")
    event["payload"]["estado_usuario"] = "CORRUPTO"
    outcome = UsuarioSyncApplicator(db_session).apply(event)
    assert outcome.kind == InboxOutcomeKind.REJECTED
    assert outcome.reason_code == "SYNC_PAYLOAD_INVALID"
    assert db_session.execute(
        text("SELECT count(*) FROM usuario WHERE uid_global=CAST(:uid AS uuid)"),
        {"uid": event["aggregate_uid"]},
    ).scalar_one() == 0


def test_version_superior_y_salto_aplican_inferior_no_revierte(db_session):
    uid = str(uuid4())
    applicator = UsuarioSyncApplicator(db_session)
    alta = _event("VERS", uid=uid)
    assert applicator.apply(alta).kind == InboxOutcomeKind.PROCESSED

    v3_snapshot = _snapshot("VERS", deleted=True)
    v3_snapshot["observaciones"] = "versión 3 aceptada por snapshot autoritativo"
    v3 = _event(
        "VERS",
        uid=uid,
        version=3,
        event_type="usuario_desactivado",
        snapshot=v3_snapshot,
        op_id_alta=alta["op_id"],
    )
    assert applicator.apply(v3).kind == InboxOutcomeKind.PROCESSED

    local = dict(
        db_session.execute(
            text(
                "SELECT version_registro, estado_usuario, fecha_baja, deleted_at, "
                "observaciones FROM usuario "
                "WHERE uid_global=CAST(:uid AS uuid)"
            ),
            {"uid": uid},
        ).mappings().one()
    )
    assert local["version_registro"] == 3
    assert local["estado_usuario"] == "INACTIVO"
    assert local["fecha_baja"] is not None
    assert local["deleted_at"] is not None
    assert local["observaciones"] == v3_snapshot["observaciones"]

    v2_snapshot = _snapshot("VERS", deleted=True)
    v2_snapshot["observaciones"] = "versión 2 obsoleta no debe reemplazar V3"
    old = _event(
        "VERS",
        uid=uid,
        version=2,
        event_type="usuario_desactivado",
        snapshot=v2_snapshot,
        op_id_alta=alta["op_id"],
    )
    assert applicator.apply(old).kind == InboxOutcomeKind.PROCESSED
    after = dict(
        db_session.execute(
            text(
                "SELECT version_registro, estado_usuario, fecha_baja, deleted_at, "
                "observaciones FROM usuario "
                "WHERE uid_global=CAST(:uid AS uuid)"
            ),
            {"uid": uid},
        ).mappings().one()
    )
    assert after == local


def test_baja_remota_aplica_snapshot_logico(db_session):
    uid = str(uuid4())
    applicator = UsuarioSyncApplicator(db_session)
    alta = _event("BAJA", uid=uid)
    assert applicator.apply(alta).kind == InboxOutcomeKind.PROCESSED

    baja = _event(
        "BAJA",
        uid=uid,
        version=2,
        event_type="usuario_desactivado",
        snapshot=_snapshot("BAJA", deleted=True),
    )
    assert baja["op_id"] != alta["op_id"]
    baja["provenance"]["op_id_alta"] = alta["op_id"]
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


@pytest.mark.parametrize("incoming_provenance", ["MATCH", "NULL"])
def test_baja_remota_acepta_provenance_compatible_o_desconocida(
    db_session, incoming_provenance
):
    uid = str(uuid4())
    applicator = UsuarioSyncApplicator(db_session)
    alta = _event("BAJA-PROVENANCE-OK", uid=uid)
    assert applicator.apply(alta).kind == InboxOutcomeKind.PROCESSED

    baja = _event(
        "BAJA-PROVENANCE-OK",
        uid=uid,
        version=2,
        event_type="usuario_desactivado",
        snapshot=_snapshot("BAJA-PROVENANCE-OK", deleted=True),
        op_id_alta=alta["op_id"] if incoming_provenance == "MATCH" else None,
    )
    assert applicator.apply(baja).kind == InboxOutcomeKind.PROCESSED
    row = db_session.execute(
        text(
            "SELECT version_registro, estado_usuario, op_id_alta::text AS op_alta "
            "FROM usuario WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": uid},
    ).mappings().one()
    assert row["version_registro"] == 2
    assert row["estado_usuario"] == "INACTIVO"
    assert row["op_alta"] == alta["op_id"]


def test_baja_remota_rechaza_provenance_de_alta_contradictoria(db_session):
    uid = str(uuid4())
    applicator = UsuarioSyncApplicator(db_session)
    alta = _event("BAJA-PROVENANCE-CONFLICT", uid=uid)
    assert applicator.apply(alta).kind == InboxOutcomeKind.PROCESSED
    before = dict(
        db_session.execute(
            text(
                "SELECT version_registro, estado_usuario, fecha_baja, deleted_at, "
                "op_id_alta::text AS op_alta, "
                "op_id_ultima_modificacion::text AS op_ultima FROM usuario "
                "WHERE uid_global=CAST(:uid AS uuid)"
            ),
            {"uid": uid},
        ).mappings().one()
    )

    baja = _event(
        "BAJA-PROVENANCE-CONFLICT",
        uid=uid,
        version=3,
        event_type="usuario_desactivado",
        snapshot=_snapshot("BAJA-PROVENANCE-CONFLICT", deleted=True),
        op_id_alta=str(uuid4()),
    )
    assert applicator.apply(baja).kind == InboxOutcomeKind.CONFLICTO
    after = dict(
        db_session.execute(
            text(
                "SELECT version_registro, estado_usuario, fecha_baja, deleted_at, "
                "op_id_alta::text AS op_alta, "
                "op_id_ultima_modificacion::text AS op_ultima FROM usuario "
                "WHERE uid_global=CAST(:uid AS uuid)"
            ),
            {"uid": uid},
        ).mappings().one()
    )
    assert after == before


def test_baja_obsoleta_ignora_provenance_de_alta_contradictoria(db_session):
    uid = str(uuid4())
    applicator = UsuarioSyncApplicator(db_session)
    alta = _event("BAJA-PROVENANCE-OBSOLETE", uid=uid)
    assert applicator.apply(alta).kind == InboxOutcomeKind.PROCESSED
    current = _event(
        "BAJA-PROVENANCE-OBSOLETE",
        uid=uid,
        version=3,
        event_type="usuario_desactivado",
        snapshot=_snapshot("BAJA-PROVENANCE-OBSOLETE", deleted=True),
        op_id_alta=alta["op_id"],
    )
    assert applicator.apply(current).kind == InboxOutcomeKind.PROCESSED
    before = dict(
        db_session.execute(
            text(
                "SELECT version_registro, estado_usuario, op_id_alta::text AS op_alta, "
                "op_id_ultima_modificacion::text AS op_ultima FROM usuario "
                "WHERE uid_global=CAST(:uid AS uuid)"
            ),
            {"uid": uid},
        ).mappings().one()
    )

    obsolete = _event(
        "BAJA-PROVENANCE-OBSOLETE",
        uid=uid,
        version=2,
        event_type="usuario_desactivado",
        snapshot=_snapshot("BAJA-PROVENANCE-OBSOLETE", deleted=True),
        op_id_alta=str(uuid4()),
    )
    assert applicator.apply(obsolete).kind == InboxOutcomeKind.PROCESSED
    after = dict(
        db_session.execute(
            text(
                "SELECT version_registro, estado_usuario, op_id_alta::text AS op_alta, "
                "op_id_ultima_modificacion::text AS op_ultima FROM usuario "
                "WHERE uid_global=CAST(:uid AS uuid)"
            ),
            {"uid": uid},
        ).mappings().one()
    )
    assert after == before


def test_cas_remoto_no_inventa_provenance_de_alta_legacy(db_session):
    uid = str(uuid4())
    applicator = UsuarioSyncApplicator(db_session)
    first = _event(
        "BAJA-PROVENANCE-LEGACY",
        uid=uid,
        version=2,
        event_type="usuario_desactivado",
        snapshot=_snapshot("BAJA-PROVENANCE-LEGACY", deleted=True),
        op_id_alta=None,
    )
    assert applicator.apply(first).kind == InboxOutcomeKind.PROCESSED

    higher = _event(
        "BAJA-PROVENANCE-LEGACY",
        uid=uid,
        version=3,
        event_type="usuario_desactivado",
        snapshot=_snapshot("BAJA-PROVENANCE-LEGACY", deleted=True),
        op_id_alta=str(uuid4()),
    )
    assert applicator.apply(higher).kind == InboxOutcomeKind.PROCESSED
    row = db_session.execute(
        text(
            "SELECT version_registro, op_id_alta, "
            "op_id_ultima_modificacion::text AS op_ultima FROM usuario "
            "WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": uid},
    ).mappings().one()
    assert row["version_registro"] == 3
    assert row["op_id_alta"] is None
    assert row["op_ultima"] == higher["op_id"]


@pytest.mark.parametrize(
    ("field", "value"),
    [("deleted", False), ("fecha_baja", None), ("estado_usuario", "ACTIVO")],
)
def test_baja_remota_snapshot_incoherente_es_rejected(db_session, field, value):
    snapshot = _snapshot("BAJA-INVALIDA", deleted=True)
    snapshot[field] = value
    outcome = UsuarioSyncApplicator(db_session).apply(
        _event(
            "BAJA-INVALIDA",
            version=2,
            event_type="usuario_desactivado",
            snapshot=snapshot,
        )
    )
    assert outcome.kind == InboxOutcomeKind.REJECTED


def test_baja_uid_inexistente_materializa_inactivo_sin_inventar_op_id_alta(db_session):
    uid = str(uuid4())
    event = _event(
        "BAJA-FIRST",
        uid=uid,
        version=4,
        event_type="usuario_desactivado",
        snapshot=_snapshot("BAJA-FIRST", deleted=True),
        op_id_alta=None,
    )
    outcome = UsuarioSyncApplicator(db_session).apply(event)
    assert outcome.kind == InboxOutcomeKind.PROCESSED
    row = db_session.execute(
        text(
            "SELECT uid_global::text AS uid_global, estado_usuario, deleted_at, "
            "version_registro, op_id_alta, op_id_ultima_modificacion::text AS op_ultima "
            "FROM usuario WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": uid},
    ).mappings().one()
    assert row["uid_global"] == uid
    assert row["estado_usuario"] == "INACTIVO"
    assert row["deleted_at"] is not None
    assert row["version_registro"] == 4
    assert row["op_id_alta"] is None
    assert row["op_ultima"] == event["op_id"]


@pytest.mark.parametrize("existing_uid", [False, True])
def test_baja_rechaza_su_op_id_como_provenance_de_alta(db_session, existing_uid):
    uid = str(uuid4())
    applicator = UsuarioSyncApplicator(db_session)
    if existing_uid:
        assert applicator.apply(_event("BAJA-SELF-OP", uid=uid)).kind == (
            InboxOutcomeKind.PROCESSED
        )

    baja_op_id = str(uuid4())
    event = _event(
        "BAJA-SELF-OP",
        uid=uid,
        op_id=baja_op_id,
        version=2,
        event_type="usuario_desactivado",
        snapshot=_snapshot("BAJA-SELF-OP", deleted=True),
        op_id_alta=baja_op_id,
    )
    outcome = applicator.apply(event)
    assert outcome.kind == InboxOutcomeKind.REJECTED
    assert outcome.reason_code == "SYNC_PAYLOAD_INVALID"

    rows = db_session.execute(
        text(
            "SELECT version_registro, estado_usuario, deleted_at FROM usuario "
            "WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": uid},
    ).mappings().all()
    if existing_uid:
        assert [dict(row) for row in rows] == [
            {
                "version_registro": 1,
                "estado_usuario": "ACTIVO",
                "deleted_at": None,
            }
        ]
    else:
        assert rows == []


def test_alta_remota_conserva_op_id_alta_igual_al_op_id(db_session):
    event = _event("PROVENANCE")
    assert (
        UsuarioSyncApplicator(db_session).apply(event).kind
        == InboxOutcomeKind.PROCESSED
    )
    row = db_session.execute(
        text(
            "SELECT op_id_alta::text AS op_alta, "
            "op_id_ultima_modificacion::text AS op_ultima FROM usuario "
            "WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": event["aggregate_uid"]},
    ).mappings().one()
    assert row["op_alta"] == event["op_id"]
    assert row["op_ultima"] == event["op_id"]


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


def test_evento_obsoleto_no_evalua_colision_que_no_aplicara(db_session):
    applicator = UsuarioSyncApplicator(db_session)
    target = _event("OBSOLETE-TARGET")
    assert applicator.apply(target).kind == InboxOutcomeKind.PROCESSED
    v3 = _event(
        "OBSOLETE-TARGET",
        uid=target["aggregate_uid"],
        version=3,
        event_type="usuario_desactivado",
        snapshot=_snapshot("OBSOLETE-TARGET", deleted=True),
        op_id_alta=target["op_id"],
    )
    assert applicator.apply(v3).kind == InboxOutcomeKind.PROCESSED

    other = _event("OBSOLETE-OTHER")
    assert applicator.apply(other).kind == InboxOutcomeKind.PROCESSED
    obsolete = _event(
        "OBSOLETE-TARGET",
        uid=target["aggregate_uid"],
        version=2,
        event_type="usuario_desactivado",
        snapshot=_snapshot("OBSOLETE-OTHER", deleted=True),
        op_id_alta=str(uuid4()),
    )
    assert obsolete["provenance"]["op_id_alta"] != target["op_id"]
    assert applicator.apply(obsolete).kind == InboxOutcomeKind.PROCESSED
    current = db_session.execute(
        text(
            "SELECT codigo_usuario, version_registro FROM usuario "
            "WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": target["aggregate_uid"]},
    ).mappings().one()
    assert current["codigo_usuario"] == target["payload"]["codigo_usuario"]
    assert current["version_registro"] == 3

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
    assert register_usuario_outbox_delivery(db_session, outbox_event=outbox) is False

    inbox = db_session.execute(
        text(
            """
            SELECT aggregate_id, aggregate_uid::text AS aggregate_uid,
                   op_id::text AS op_id, consumer, provenance
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
    assert inbox["provenance"]["installation_uid"] == outbox["payload"]["provenance"]["installation_uid"]


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


def test_processor_rechaza_email_sobredimensionado_sin_materializar_usuario():
    event = _event("OVERSIZED-EMAIL-" + uuid4().hex[:8])
    event["payload"]["email"] = "x" * 151
    event_id = str(uuid4())
    _committed_register(event, event_id=event_id)
    try:
        with Session(engine) as session:
            outcome = run_usuario_inbox_once(
                session,
                worker_id="usuario-oversized",
                event_id=event_id,
                manual=True,
            )
        assert outcome is not None
        assert outcome.kind == InboxOutcomeKind.REJECTED
        assert outcome.reason_code == "SYNC_PAYLOAD_INVALID"

        with Session(engine) as verify:
            assert verify.execute(
                text(
                    "SELECT count(*) FROM usuario "
                    "WHERE uid_global=CAST(:uid AS uuid)"
                ),
                {"uid": event["aggregate_uid"]},
            ).scalar_one() == 0
            delivery = verify.execute(
                text(
                    "SELECT status, error_detail FROM inbox_event "
                    "WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer"
                ),
                {"event_id": event_id, "consumer": USUARIO_SYNC_CONSUMER},
            ).mappings().one()
            assert dict(delivery) == {
                "status": "REJECTED",
                "error_detail": "SYNC_PAYLOAD_INVALID",
            }
    finally:
        _cleanup_committed(
            uid=event["aggregate_uid"],
            op_id=event["op_id"],
            event_ids=[event_id],
        )


def test_processor_rechaza_overflow_temporal_y_terminaliza_delivery():
    event = _event("DATETIME-OVERFLOW-" + uuid4().hex[:8])
    event["payload"]["fecha_alta"] = "0001-01-01T00:00:00+14:00"
    event_id = str(uuid4())
    _committed_register(event, event_id=event_id)
    try:
        with Session(engine) as session:
            outcome = run_usuario_inbox_once(
                session,
                worker_id="usuario-datetime-overflow",
                event_id=event_id,
                manual=True,
            )
        assert outcome is not None
        assert outcome.kind == InboxOutcomeKind.REJECTED
        assert outcome.reason_code == "SYNC_PAYLOAD_INVALID"

        with Session(engine) as verify:
            assert verify.execute(
                text(
                    "SELECT count(*) FROM usuario "
                    "WHERE uid_global=CAST(:uid AS uuid)"
                ),
                {"uid": event["aggregate_uid"]},
            ).scalar_one() == 0
            delivery = verify.execute(
                text(
                    "SELECT status, error_detail FROM inbox_event "
                    "WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer"
                ),
                {"event_id": event_id, "consumer": USUARIO_SYNC_CONSUMER},
            ).mappings().one()
            assert dict(delivery) == {
                "status": "REJECTED",
                "error_detail": "SYNC_PAYLOAD_INVALID",
            }
    finally:
        _cleanup_committed(
            uid=event["aggregate_uid"],
            op_id=event["op_id"],
            event_ids=[event_id],
        )


@pytest.mark.parametrize("provenance_kind", ["NULL", "DISTINCT"])
def test_processor_rechaza_alta_con_provenance_incompatible(provenance_kind):
    event = _event("INVALID-PROVENANCE-" + uuid4().hex[:8])
    op_id_alta = None if provenance_kind == "NULL" else str(uuid4())
    assert op_id_alta != event["op_id"]
    event["provenance"]["op_id_alta"] = op_id_alta
    event_id = str(uuid4())
    _committed_register(event, event_id=event_id)
    try:
        with Session(engine) as session:
            outcome = run_usuario_inbox_once(
                session,
                worker_id="usuario-invalid-provenance",
                event_id=event_id,
                manual=True,
            )
        assert outcome is not None
        assert outcome.kind == InboxOutcomeKind.REJECTED
        assert outcome.reason_code == "SYNC_PAYLOAD_INVALID"

        with Session(engine) as verify:
            assert verify.execute(
                text(
                    "SELECT count(*) FROM usuario "
                    "WHERE uid_global=CAST(:uid AS uuid)"
                ),
                {"uid": event["aggregate_uid"]},
            ).scalar_one() == 0
            delivery = verify.execute(
                text(
                    "SELECT status, error_detail FROM inbox_event "
                    "WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer"
                ),
                {"event_id": event_id, "consumer": USUARIO_SYNC_CONSUMER},
            ).mappings().one()
            assert dict(delivery) == {
                "status": "REJECTED",
                "error_detail": "SYNC_PAYLOAD_INVALID",
            }
    finally:
        _cleanup_committed(
            uid=event["aggregate_uid"],
            op_id=event["op_id"],
            event_ids=[event_id],
        )


def test_integrity_error_del_applicator_revierte_insert_parcial(db_session, monkeypatch):
    event = _event("PARTIAL")
    applicator = UsuarioSyncApplicator(db_session)
    real_create = applicator.repository.create_remote_snapshot

    def insert_then_fail(**kwargs):
        real_create(**kwargs)
        raise IntegrityError("forced", {}, RuntimeError("forced"))

    monkeypatch.setattr(
        applicator.repository, "create_remote_snapshot", insert_then_fail
    )
    assert applicator.apply(event).kind == InboxOutcomeKind.CONFLICTO
    assert db_session.execute(
        text("SELECT count(*) FROM usuario WHERE uid_global=CAST(:uid AS uuid)"),
        {"uid": event["aggregate_uid"]},
    ).scalar_one() == 0


def test_fallo_fencing_revierte_efecto_del_applicator(monkeypatch):
    event = _event("FENCING-" + uuid4().hex[:8])
    event_id = str(uuid4())
    _committed_register(event, event_id=event_id)

    def lose_fence(*args, **kwargs):
        raise InboxOwnershipLost(InboxOwnershipLost.code)

    try:
        with Session(engine) as session:
            monkeypatch.setattr(
                InboxRepository, "finish_operation_scope", lose_fence
            )
            with pytest.raises(InboxOwnershipLost):
                run_usuario_inbox_once(
                    session, worker_id="usuario-fence", event_id=event_id, manual=True
                )
        with Session(engine) as verify:
            assert verify.execute(
                text(
                    "SELECT count(*) FROM usuario "
                    "WHERE uid_global=CAST(:uid AS uuid)"
                ),
                {"uid": event["aggregate_uid"]},
            ).scalar_one() == 0
    finally:
        _cleanup_committed(
            uid=event["aggregate_uid"], op_id=event["op_id"], event_ids=[event_id]
        )


def test_fallo_commit_exterior_revierte_y_permite_reproceso(monkeypatch):
    event = _event("OUTER-" + uuid4().hex[:8])
    event_id = str(uuid4())
    _committed_register(event, event_id=event_id)
    try:
        with Session(engine) as session:
            real_commit = session.commit

            def fail_commit():
                raise RuntimeError("forced outer commit failure")

            monkeypatch.setattr(session, "commit", fail_commit)
            with pytest.raises(RuntimeError, match="forced outer commit failure"):
                run_usuario_inbox_once(
                    session, worker_id="usuario-outer", event_id=event_id, manual=True
                )
            monkeypatch.setattr(session, "commit", real_commit)

        with engine.begin() as connection:
            assert connection.execute(
                text(
                    "SELECT count(*) FROM usuario "
                    "WHERE uid_global=CAST(:uid AS uuid)"
                ),
                {"uid": event["aggregate_uid"]},
            ).scalar_one() == 0
            connection.execute(
                text(
                    "UPDATE inbox_event SET lease_expires_at="
                    "clock_timestamp() AT TIME ZONE 'UTC' - interval '1 second' "
                    "WHERE event_id=CAST(:event_id AS uuid) AND consumer=:consumer"
                ),
                {"event_id": event_id, "consumer": USUARIO_SYNC_CONSUMER},
            )
            connection.execute(
                text(
                    "UPDATE inbox_operation_scope SET lease_expires_at="
                    "clock_timestamp() AT TIME ZONE 'UTC' - interval '1 second' "
                    "WHERE consumer=:consumer AND op_id=CAST(:op_id AS uuid)"
                ),
                {"consumer": USUARIO_SYNC_CONSUMER, "op_id": event["op_id"]},
            )

        with Session(engine) as retry_session:
            outcome = run_usuario_inbox_once(
                retry_session,
                worker_id="usuario-outer-retry",
                event_id=event_id,
                manual=True,
            )
        assert outcome is not None and outcome.kind == InboxOutcomeKind.PROCESSED
        with Session(engine) as verify:
            assert verify.execute(
                text(
                    "SELECT count(*) FROM usuario "
                    "WHERE uid_global=CAST(:uid AS uuid)"
                ),
                {"uid": event["aggregate_uid"]},
            ).scalar_one() == 1
    finally:
        _cleanup_committed(
            uid=event["aggregate_uid"], op_id=event["op_id"], event_ids=[event_id]
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


def _run_applicator_race(
    events: dict[str, dict], *, winner: str, delayed_method: str
) -> dict[str, InboxOutcomeKind]:
    initial_reads = threading.Barrier(2)
    winner_committed = threading.Event()
    outcomes: dict[str, InboxOutcomeKind] = {}
    result_lock = threading.Lock()

    def worker(name: str) -> None:
        try:
            with Session(engine) as session:
                applicator = UsuarioSyncApplicator(session)
                real_get = applicator.repository.get_by_uid_global
                first_read = True

                def synchronized_get(uid_global: str):
                    nonlocal first_read
                    current = real_get(uid_global)
                    if first_read:
                        first_read = False
                        initial_reads.wait(timeout=5)
                    return current

                applicator.repository.get_by_uid_global = synchronized_get
                if name != winner:
                    real_write = getattr(applicator.repository, delayed_method)

                    def delayed_write(**kwargs):
                        assert winner_committed.wait(timeout=5)
                        return real_write(**kwargs)

                    setattr(applicator.repository, delayed_method, delayed_write)

                outcome = applicator.apply(events[name])
                session.commit()
                with result_lock:
                    outcomes[name] = outcome.kind
        finally:
            if name == winner:
                winner_committed.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(worker, name) for name in events]
        for future in futures:
            future.result(timeout=10)
    return outcomes


@pytest.mark.parametrize("winner", ["v1", "v2"])
def test_insert_race_v1_v2_mismo_uid_converge_a_baja_v2(winner):
    uid = str(uuid4())
    suffix = "INSERT-RACE-" + uuid4().hex[:8]
    v1 = _event(suffix, uid=uid)
    v2_snapshot = deepcopy(v1["payload"])
    v2_snapshot.update(
        {
            "estado_usuario": "INACTIVO",
            "fecha_baja": "2026-08-29T10:00:02",
            "deleted": True,
            "observaciones": "baja V2 ganadora",
        }
    )
    v2 = _event(
        suffix,
        uid=uid,
        version=2,
        event_type="usuario_desactivado",
        snapshot=v2_snapshot,
        op_id_alta=v1["op_id"],
    )
    assert v2["op_id"] != v1["op_id"]
    try:
        outcomes = _run_applicator_race(
            {"v1": v1, "v2": v2},
            winner=winner,
            delayed_method="create_remote_snapshot",
        )
        assert outcomes == {
            "v1": InboxOutcomeKind.PROCESSED,
            "v2": InboxOutcomeKind.PROCESSED,
        }
        with Session(engine) as verify:
            row = UsuarioSistemaRepository(verify).get_by_uid_global(uid)
            assert row is not None
            assert row["version_registro"] == 2
            assert row["estado_usuario"] == "INACTIVO"
            assert row["deleted_at"] is not None
            assert row["observaciones"] == "baja V2 ganadora"
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM usuario WHERE uid_global=CAST(:uid AS uuid)"),
                {"uid": uid},
            )


@pytest.mark.parametrize("winner", ["v2", "v3"])
def test_cas_race_v2_v3_desde_v1_converge_a_v3(winner):
    uid = str(uuid4())
    suffix = "CAS-RACE-" + uuid4().hex[:8]
    v1 = _event(suffix, uid=uid)
    with Session(engine) as seed_session:
        assert UsuarioSyncApplicator(seed_session).apply(v1).kind == (
            InboxOutcomeKind.PROCESSED
        )
        seed_session.commit()

    def deactivation(version: int) -> dict:
        snapshot = deepcopy(v1["payload"])
        snapshot.update(
            {
                "estado_usuario": "INACTIVO",
                "fecha_baja": f"2026-08-29T10:00:0{version}",
                "deleted": True,
                "observaciones": f"snapshot V{version}",
            }
        )
        return _event(
            suffix,
            uid=uid,
            version=version,
            event_type="usuario_desactivado",
            snapshot=snapshot,
            op_id_alta=v1["op_id"],
        )

    try:
        v2 = deactivation(2)
        v3 = deactivation(3)
        assert v1["op_id"] not in {v2["op_id"], v3["op_id"]}
        assert v2["op_id"] != v3["op_id"]
        outcomes = _run_applicator_race(
            {"v2": v2, "v3": v3},
            winner=winner,
            delayed_method="apply_remote_snapshot_cas",
        )
        assert outcomes == {
            "v2": InboxOutcomeKind.PROCESSED,
            "v3": InboxOutcomeKind.PROCESSED,
        }
        with Session(engine) as verify:
            row = UsuarioSistemaRepository(verify).get_by_uid_global(uid)
            assert row is not None
            assert row["version_registro"] == 3
            assert row["observaciones"] == "snapshot V3"
            assert row["deleted_at"] is not None
    finally:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM usuario WHERE uid_global=CAST(:uid AS uuid)"),
                {"uid": uid},
            )


def test_op_id_global_rechaza_altas_de_usuarios_distintos(client, db_session):
    op_id = str(uuid4())
    first = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("GLOBAL-ALTA-A-" + uuid4().hex[:6]),
        headers=_headers(op_id),
    )
    second = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("GLOBAL-ALTA-B-" + uuid4().hex[:6]),
        headers=_headers(op_id),
    )
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error_code"] == "IDEMPOTENT_DUPLICATE"
    assert db_session.execute(
        text("SELECT count(*) FROM outbox_event WHERE payload->>'op_id'=:op_id"),
        {"op_id": op_id},
    ).scalar_one() == 1


def test_op_id_global_rechaza_alta_y_baja_de_usuarios_distintos(client, db_session):
    op_id = str(uuid4())
    first = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("GLOBAL-CROSS-A-" + uuid4().hex[:6]),
        headers=_headers(op_id),
    )
    target = client.post(
        "/api/v1/administrativo/usuarios",
        json=_payload("GLOBAL-CROSS-B-" + uuid4().hex[:6]),
        headers=_headers(),
    )
    assert first.status_code == target.status_code == 201
    target_row = target.json()["data"]

    rejected = client.patch(
        f"/api/v1/administrativo/usuarios/{target_row['id_usuario']}/baja",
        headers=_headers(op_id, version=target_row["version_registro"]),
    )
    assert rejected.status_code == 409
    assert rejected.json()["error_code"] == "IDEMPOTENT_DUPLICATE"
    row = UsuarioSistemaRepository(db_session).get(target_row["id_usuario"])
    assert row is not None
    assert row["estado_usuario"] == "ACTIVO"
    assert row["version_registro"] == 1
    assert row["deleted_at"] is None


def _create_committed_usuario(payload: dict, *, op_id: str) -> dict:
    with Session(engine) as session:
        return UsuarioSistemaRepository(session).create(payload, _core(op_id))


def _cleanup_committed_usuarios(*, user_ids: list[int], op_ids: list[str]) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "DELETE FROM outbox_event WHERE aggregate_type='usuario' "
                "AND aggregate_id=ANY(:user_ids)"
            ),
            {"user_ids": user_ids},
        )
        for trigger_name in (
            "trg_bud_operacion_idempotente_inmutable",
            "trg_bt_operacion_idempotente_inmutable",
        ):
            connection.execute(
                text(
                    "ALTER TABLE operacion_idempotente DISABLE TRIGGER "
                    f"{trigger_name}"
                )
            )
        try:
            connection.execute(
                text("DELETE FROM operacion_idempotente WHERE op_id=ANY(:op_ids)"),
                {"op_ids": [UUID(value) for value in op_ids]},
            )
        finally:
            for trigger_name in (
                "trg_bud_operacion_idempotente_inmutable",
                "trg_bt_operacion_idempotente_inmutable",
            ):
                connection.execute(
                    text(
                        "ALTER TABLE operacion_idempotente ENABLE ALWAYS TRIGGER "
                        f"{trigger_name}"
                    )
                )
        connection.execute(
            text("DELETE FROM usuario WHERE id_usuario=ANY(:user_ids)"),
            {"user_ids": user_ids},
        )


def test_producer_escribe_timestamps_utc_naive_con_timezone_no_utc():
    create_op_id = str(uuid4())
    baja_op_id = str(uuid4())
    created = []
    try:
        with Session(engine) as create_session:
            create_session.execute(
                text("SET LOCAL TIME ZONE 'America/Argentina/Buenos_Aires'")
            )
            clock = create_session.execute(
                text(
                    "SELECT CURRENT_TIMESTAMP::timestamp AS wall_time, "
                    "CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AS utc_naive"
                )
            ).mappings().one()
            assert clock["wall_time"] != clock["utc_naive"]
            row = UsuarioSistemaRepository(create_session).create(
                _payload("TZ-UTC-" + uuid4().hex[:8]),
                _core(create_op_id),
            )
            created.append(row)
            assert row["fecha_alta"] == clock["utc_naive"]
            assert row["updated_at"] == clock["utc_naive"]

        with Session(engine) as baja_session:
            baja_session.execute(
                text("SET LOCAL TIME ZONE 'America/Argentina/Buenos_Aires'")
            )
            baja_clock = baja_session.execute(
                text("SELECT CURRENT_TIMESTAMP AT TIME ZONE 'UTC'")
            ).scalar_one()
            baja = UsuarioSistemaRepository(baja_session).baja_logica(
                row["id_usuario"],
                core=_core(baja_op_id, version=row["version_registro"]),
                if_match_version=row["version_registro"],
            )
            assert baja is not None
            assert baja["fecha_baja"] == baja_clock
            assert baja["deleted_at"] == baja_clock
            assert baja["updated_at"] == baja_clock

        with Session(engine) as verify:
            utc_after = verify.execute(
                text("SELECT clock_timestamp() AT TIME ZONE 'UTC'")
            ).scalar_one()
            alta_outbox = _outbox_for_user(
                verify, row["id_usuario"], "usuario_creado"
            )
            baja_outbox = _outbox_for_user(
                verify, row["id_usuario"], "usuario_desactivado"
            )
            assert alta_outbox["payload"]["snapshot"]["fecha_alta"] == (
                clock["utc_naive"].isoformat()
            )
            assert baja_outbox["payload"]["snapshot"]["fecha_alta"] == (
                clock["utc_naive"].isoformat()
            )
            assert baja_outbox["payload"]["snapshot"]["fecha_baja"] == (
                baja_clock.isoformat()
            )
            assert alta_outbox["occurred_at"].tzinfo is None
            assert baja_outbox["occurred_at"].tzinfo is None
            assert clock["utc_naive"] <= alta_outbox["occurred_at"] <= utc_after
            assert baja_clock <= baja_outbox["occurred_at"] <= utc_after
    finally:
        _cleanup_committed_usuarios(
            user_ids=[row["id_usuario"] for row in created],
            op_ids=[create_op_id, baja_op_id],
        )


@pytest.mark.parametrize(
    ("event_type", "version", "deleted"),
    [
        ("usuario_creado", 1, False),
        ("usuario_desactivado", 4, True),
    ],
)
def test_apply_remoto_inserta_metadata_utc_naive_con_timezone_no_utc(
    db_session, event_type, version, deleted
):
    db_session.execute(text("SET LOCAL TIME ZONE 'America/Argentina/Buenos_Aires'"))
    clock = db_session.execute(
        text(
            "SELECT CURRENT_TIMESTAMP::timestamp AS wall_time, "
            "CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AS utc_naive"
        )
    ).mappings().one()
    assert clock["wall_time"] != clock["utc_naive"]

    event = _event(
        f"REMOTE-TZ-{event_type}",
        version=version,
        event_type=event_type,
        snapshot=_snapshot(f"REMOTE-TZ-{event_type}", deleted=deleted),
        op_id_alta=None if deleted else _DEFAULT_OP_ID_ALTA,
    )
    expected_fecha_baja = event["payload"]["fecha_baja"]
    outcome = UsuarioSyncApplicator(db_session).apply(event)
    assert outcome.kind == InboxOutcomeKind.PROCESSED

    row = db_session.execute(
        text(
            "SELECT fecha_alta, fecha_baja, updated_at, deleted_at, "
            "id_instalacion_origen, id_instalacion_ultima_modificacion "
            "FROM usuario WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": event["aggregate_uid"]},
    ).mappings().one()
    assert row["fecha_alta"].isoformat() == event["payload"]["fecha_alta"]
    assert (
        row["fecha_baja"].isoformat() if row["fecha_baja"] is not None else None
    ) == expected_fecha_baja
    assert row["updated_at"] == clock["utc_naive"]
    assert row["deleted_at"] == (clock["utc_naive"] if deleted else None)
    assert row["id_instalacion_origen"] is None
    assert row["id_instalacion_ultima_modificacion"] is None


def test_cas_remoto_neutraliza_provenance_local_y_usa_metadata_utc_naive(db_session):
    local = UsuarioSistemaRepository(db_session).create(
        _payload("REMOTE-CAS-TZ-" + uuid4().hex[:6]),
        _core(str(uuid4())),
    )
    assert local["id_instalacion_origen"] == 1
    assert local["id_instalacion_ultima_modificacion"] == 1

    db_session.execute(text("SET LOCAL TIME ZONE 'America/Argentina/Buenos_Aires'"))
    clock = db_session.execute(
        text(
            "SELECT CURRENT_TIMESTAMP::timestamp AS wall_time, "
            "CURRENT_TIMESTAMP AT TIME ZONE 'UTC' AS utc_naive"
        )
    ).mappings().one()
    assert clock["wall_time"] != clock["utc_naive"]

    remote_op_id = str(uuid4())
    snapshot = _snapshot("REMOTE-CAS-TZ", deleted=True)
    event = _event(
        "REMOTE-CAS-TZ",
        uid=str(local["uid_global"]),
        op_id=remote_op_id,
        version=3,
        event_type="usuario_desactivado",
        snapshot=snapshot,
        op_id_alta=str(local["op_id_alta"]),
    )
    assert event["provenance"]["installation_uid"] == TEST_INSTALLATION_UID
    outcome = UsuarioSyncApplicator(db_session).apply(event)
    assert outcome.kind == InboxOutcomeKind.PROCESSED

    row = db_session.execute(
        text(
            "SELECT version_registro, fecha_alta, fecha_baja, updated_at, deleted_at, "
            "id_instalacion_origen, id_instalacion_ultima_modificacion, "
            "op_id_ultima_modificacion::text AS op_id_ultima_modificacion "
            "FROM usuario WHERE uid_global=CAST(:uid AS uuid)"
        ),
        {"uid": event["aggregate_uid"]},
    ).mappings().one()
    assert row["version_registro"] == 3
    assert row["fecha_alta"].isoformat() == snapshot["fecha_alta"]
    assert row["fecha_baja"].isoformat() == snapshot["fecha_baja"]
    assert row["updated_at"] == clock["utc_naive"]
    assert row["deleted_at"] == clock["utc_naive"]
    assert row["id_instalacion_origen"] == 1
    assert row["id_instalacion_ultima_modificacion"] is None
    assert row["op_id_ultima_modificacion"] == remote_op_id


def test_op_id_global_serializa_bajas_concurrentes_de_usuarios_distintos():
    created = []
    create_op_ids = []
    op_id = str(uuid4())
    try:
        for suffix in ("A", "B"):
            create_op_id = str(uuid4())
            create_op_ids.append(create_op_id)
            created.append(
                _create_committed_usuario(
                    _payload(f"GLOBAL-BAJA-{suffix}-" + uuid4().hex[:6]),
                    op_id=create_op_id,
                )
            )

        with Session(engine) as visible_session:
            assert all(
                UsuarioSistemaRepository(visible_session).get(row["id_usuario"])
                is not None
                for row in created
            )

        start = threading.Barrier(2)

        def deactivate(row: dict) -> tuple[int, str]:
            with Session(engine) as session:
                start.wait(timeout=5)
                try:
                    result = UsuarioSistemaRepository(session).baja_logica(
                        row["id_usuario"],
                        core=_core(op_id, version=row["version_registro"]),
                        if_match_version=row["version_registro"],
                    )
                    assert result is not None
                    return row["id_usuario"], "PROCESSED"
                except UsuarioIdempotencyConflictError:
                    session.rollback()
                    return row["id_usuario"], "CONFLICTO"

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(deactivate, created))
        assert sorted(result for _, result in results) == ["CONFLICTO", "PROCESSED"]
        processed_id = next(
            id_usuario for id_usuario, result in results if result == "PROCESSED"
        )
        conflict_id = next(
            id_usuario for id_usuario, result in results if result == "CONFLICTO"
        )

        with Session(engine) as verify:
            states = {
                row["id_usuario"]: UsuarioSistemaRepository(verify).get(
                    row["id_usuario"]
                )
                for row in created
            }
            assert states[processed_id] is not None
            assert states[processed_id]["deleted_at"] is not None
            assert states[processed_id]["estado_usuario"] == "INACTIVO"
            assert states[conflict_id] is not None
            assert states[conflict_id]["deleted_at"] is None
            assert states[conflict_id]["estado_usuario"] == "ACTIVO"

            outbox = verify.execute(
                text(
                    "SELECT aggregate_id FROM outbox_event "
                    "WHERE event_type='usuario_desactivado' "
                    "AND payload->>'op_id'=:op_id"
                ),
                {"op_id": op_id},
            ).mappings().one()
            assert outbox["aggregate_id"] == processed_id

            receipt = verify.execute(
                text(
                    "SELECT command_code, target_type, target_key, "
                    "result_target_uid::text AS result_target_uid, result_version "
                    "FROM operacion_idempotente WHERE op_id=CAST(:op_id AS uuid)"
                ),
                {"op_id": op_id},
            ).mappings().one()
            assert receipt["command_code"] == "ADMIN.USUARIO.DEACTIVATE"
            assert receipt["target_type"] == "USUARIO"
            assert receipt["target_key"] == str(processed_id)
            assert receipt["result_target_uid"] == str(
                states[processed_id]["uid_global"]
            )
            assert receipt["result_version"] == 2
    finally:
        _cleanup_committed_usuarios(
            user_ids=[row["id_usuario"] for row in created],
            op_ids=[*create_op_ids, op_id],
        )
