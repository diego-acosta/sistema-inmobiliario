from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.application.common.synchronization_policy import validate_sync_event
from app.application.integration.inbox_retry import (
    InboxOutcome,
    InboxOutcomeKind,
    InboxRetryProcessor,
)
from app.infrastructure.persistence.repositories.inbox_repository import InboxRepository
from app.infrastructure.persistence.repositories.usuario_sistema_repository import (
    UsuarioSistemaRepository,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

USUARIO_SYNC_CONSUMER = "administrativo.usuario"
USUARIO_SYNC_EVENTS = frozenset({"usuario_creado", "usuario_desactivado"})

_OUTBOX_ENVELOPE_FIELDS = frozenset(
    {"aggregate_uid", "version_registro", "op_id", "provenance", "snapshot"}
)
_SNAPSHOT_FIELDS = frozenset(
    {
        "codigo_usuario",
        "login",
        "email",
        "estado_usuario",
        "usuario_sistema_interno",
        "observaciones",
        "fecha_alta",
        "fecha_baja",
        "deleted",
    }
)
_PROVENANCE_FIELDS = frozenset({"installation_uid", "op_id_alta"})


class UsuarioSyncPayloadError(ValueError):
    code = "SYNC_PAYLOAD_INVALID"


def _canonical_uuid(value: Any) -> str:
    try:
        return str(UUID(str(value)))
    except (AttributeError, TypeError, ValueError):
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code) from None


def _validate_portable_datetime(value: Any, *, nullable: bool) -> str | None:
    if value is None and nullable:
        return None
    if not isinstance(value, str) or not value.strip():
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code) from None
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(UTC).replace(tzinfo=None)
    return parsed.isoformat()


def _validate_event_version(event_type: str, version: Any) -> int:
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    if event_type == "usuario_creado" and version != 1:
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    if event_type == "usuario_desactivado" and version < 2:
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    return version


def _validate_snapshot(event_type: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _SNAPSHOT_FIELDS:
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)

    for field in ("codigo_usuario", "login", "estado_usuario"):
        if not isinstance(value[field], str) or not value[field].strip():
            raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    if value["email"] is not None and not isinstance(value["email"], str):
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    if value["observaciones"] is not None and not isinstance(value["observaciones"], str):
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    if not isinstance(value["usuario_sistema_interno"], bool):
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    if not isinstance(value["deleted"], bool):
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)

    snapshot = dict(value)
    snapshot["fecha_alta"] = _validate_portable_datetime(
        value["fecha_alta"], nullable=False
    )
    snapshot["fecha_baja"] = _validate_portable_datetime(
        value["fecha_baja"], nullable=True
    )

    if event_type == "usuario_creado":
        if snapshot["deleted"] or snapshot["fecha_baja"] is not None:
            raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    elif event_type == "usuario_desactivado":
        if (
            not snapshot["deleted"]
            or snapshot["fecha_baja"] is None
            or snapshot["estado_usuario"] != "INACTIVO"
        ):
            raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    else:
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)

    validate_sync_event(event_type, "usuario", snapshot)
    return snapshot


def _validate_provenance(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != _PROVENANCE_FIELDS:
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    op_id_alta = value.get("op_id_alta")
    return {
        "installation_uid": _canonical_uuid(value.get("installation_uid")),
        "op_id_alta": _canonical_uuid(op_id_alta) if op_id_alta is not None else None,
    }


def parse_usuario_outbox_envelope(
    *, event_type: str, aggregate_type: str, value: Any
) -> dict[str, Any]:
    if event_type not in USUARIO_SYNC_EVENTS or aggregate_type != "usuario":
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)
    if not isinstance(value, dict) or set(value) != _OUTBOX_ENVELOPE_FIELDS:
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)

    version = _validate_event_version(event_type, value["version_registro"])
    snapshot = _validate_snapshot(event_type, value["snapshot"])
    return {
        "aggregate_uid": _canonical_uuid(value["aggregate_uid"]),
        "version_registro": version,
        "op_id": _canonical_uuid(value["op_id"]),
        "provenance": _validate_provenance(value["provenance"]),
        "snapshot": snapshot,
    }


def register_usuario_outbox_delivery(
    session: Session, *, outbox_event: dict[str, Any]
) -> bool:
    """Registra en inbox una delivery portable; no publica ni confirma transacción."""
    event_type = outbox_event.get("event_type")
    aggregate_type = outbox_event.get("aggregate_type")
    event_id = _canonical_uuid(outbox_event.get("event_id"))
    envelope = parse_usuario_outbox_envelope(
        event_type=event_type,
        aggregate_type=aggregate_type,
        value=outbox_event.get("payload"),
    )
    return InboxRepository(session).claim(
        event_id=event_id,
        event_type=event_type,
        aggregate_type="usuario",
        # El PK del origen no cruza como identidad; el campo legacy queda neutro.
        aggregate_id=0,
        consumer=USUARIO_SYNC_CONSUMER,
        op_id=envelope["op_id"],
        payload=envelope["snapshot"],
        provenance=envelope["provenance"],
        aggregate_uid=envelope["aggregate_uid"],
        version_registro=envelope["version_registro"],
    )


def _parse_retained_event(event: dict[str, Any]) -> dict[str, Any]:
    event_type = event.get("event_type")
    if event_type not in USUARIO_SYNC_EVENTS or event.get("aggregate_type") != "usuario":
        raise UsuarioSyncPayloadError(UsuarioSyncPayloadError.code)

    version = _validate_event_version(event_type, event.get("version_registro"))
    snapshot = _validate_snapshot(event_type, event.get("payload"))
    provenance = _validate_provenance(event.get("provenance"))
    return {
        "event_type": event_type,
        "aggregate_uid": _canonical_uuid(event.get("aggregate_uid")),
        "version_registro": version,
        "op_id": _canonical_uuid(event.get("op_id")),
        "provenance": provenance,
        "snapshot": snapshot,
    }


class UsuarioSyncApplicator:
    """Aplica snapshots portables de usuario dentro de la transacción de #512."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = UsuarioSistemaRepository(session)

    @staticmethod
    def _conflict() -> InboxOutcome:
        return InboxOutcome(InboxOutcomeKind.CONFLICTO, "SYNC_OPERATION_CONFLICT")

    @staticmethod
    def _processed() -> InboxOutcome:
        return InboxOutcome(InboxOutcomeKind.PROCESSED)

    @staticmethod
    def _same_uid(row: dict[str, Any] | None, uid_global: str) -> bool:
        return row is None or str(row["uid_global"]) == uid_global

    def _has_identity_collision(
        self, *, uid_global: str, snapshot: dict[str, Any]
    ) -> bool:
        by_code = self.repository.get_by_codigo_exact(snapshot["codigo_usuario"])
        if not self._same_uid(by_code, uid_global):
            return True
        by_login = self.repository.get_by_login_exact(snapshot["login"])
        return not self._same_uid(by_login, uid_global)

    def _create_missing(self, envelope: dict[str, Any]) -> InboxOutcome:
        if self._has_identity_collision(
            uid_global=envelope["aggregate_uid"], snapshot=envelope["snapshot"]
        ):
            return self._conflict()
        nested = self.session.begin_nested()
        try:
            self.repository.create_remote_snapshot(
                uid_global=envelope["aggregate_uid"],
                version_registro=envelope["version_registro"],
                snapshot=envelope["snapshot"],
                op_id_alta=envelope["provenance"]["op_id_alta"],
                op_id_ultima_modificacion=envelope["op_id"],
            )
            nested.commit()
        except IntegrityError:
            nested.rollback()
            return self._conflict()
        return self._processed()

    def _apply_higher(
        self, *, local: dict[str, Any], envelope: dict[str, Any]
    ) -> InboxOutcome:
        if self._has_identity_collision(
            uid_global=envelope["aggregate_uid"], snapshot=envelope["snapshot"]
        ):
            return self._conflict()
        nested = self.session.begin_nested()
        try:
            updated = self.repository.apply_remote_snapshot_cas(
                uid_global=envelope["aggregate_uid"],
                expected_version=local["version_registro"],
                incoming_version=envelope["version_registro"],
                snapshot=envelope["snapshot"],
                op_id=envelope["op_id"],
            )
            nested.commit()
        except IntegrityError:
            nested.rollback()
            return self._conflict()
        if updated is not None:
            return self._processed()

        current = self.repository.get_by_uid_global(envelope["aggregate_uid"])
        if current is None:
            return self._conflict()
        if (
            current["version_registro"] == envelope["version_registro"]
            and self.repository.portable_snapshot(current) == envelope["snapshot"]
        ):
            return self._processed()
        return self._conflict()

    def apply(self, event: dict[str, Any]) -> InboxOutcome:
        try:
            envelope = _parse_retained_event(event)
        except UsuarioSyncPayloadError:
            return InboxOutcome(
                InboxOutcomeKind.REJECTED, UsuarioSyncPayloadError.code
            )

        uid_global = envelope["aggregate_uid"]
        snapshot = envelope["snapshot"]
        local = self.repository.get_by_uid_global(uid_global)

        if local is None:
            return self._create_missing(envelope)

        local_version = local["version_registro"]
        incoming_version = envelope["version_registro"]
        if incoming_version < local_version:
            return self._processed()
        if incoming_version == local_version:
            if self.repository.portable_snapshot(local) == snapshot:
                return self._processed()
            return self._conflict()
        return self._apply_higher(local=local, envelope=envelope)


def run_usuario_inbox_once(
    session: Session,
    *,
    worker_id: str,
    event_id: str | None = None,
    manual: bool = False,
) -> InboxOutcome | None:
    processor = InboxRetryProcessor(session, consumer=USUARIO_SYNC_CONSUMER)
    return processor.run_once(
        UsuarioSyncApplicator(session).apply,
        worker_id=worker_id,
        event_id=event_id,
        manual=manual,
    )
