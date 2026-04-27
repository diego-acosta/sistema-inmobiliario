from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.outbox import OutboxEventPayload
from app.application.common.results import AppResult
from app.application.locativo.commands.convert_solicitud_alquiler_to_reserva_locativa import (
    ConvertSolicitudAlquilerToReservaLocativaCommand,
)
from app.application.locativo.services.confirmar_reserva_locativa_service import (
    AGGREGATE_TYPE,
    ESTADO_CONFIRMADA,
    EVENT_TYPE_CONFIRMADA,
    ReservaLocativaConfirmarPayload,
)
from app.application.locativo.services.create_reserva_locativa_service import (
    ESTADO_INICIAL_RESERVA_LOCATIVA,
    ESTADOS_ACTIVOS_RESERVA_LOCATIVA,
    ReservaLocativaCreatePayload,
    ReservaLocativaObjetoCreatePayload,
)


ESTADO_APROBADA = "aprobada"


class LocativoRepository(Protocol):
    def get_solicitud_alquiler(self, id_solicitud_alquiler: int) -> dict[str, Any] | None: ...

    def has_reserva_locativa_for_solicitud(self, id_solicitud_alquiler: int) -> bool: ...

    def inmueble_exists(self, id_inmueble: int) -> bool: ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool: ...

    def has_current_disponibilidad_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool: ...

    def has_current_disponibilidad_no_disponible(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool: ...

    def has_conflicting_active_reserva_locativa(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
        exclude_id_reserva_locativa: int | None = None,
    ) -> bool: ...

    def create_reserva_locativa_sin_commit(
        self,
        payload: ReservaLocativaCreatePayload,
        objetos: list[ReservaLocativaObjetoCreatePayload],
    ) -> dict[str, Any]: ...

    def vincular_solicitud_a_reserva_locativa(
        self, id_reserva_locativa: int, id_solicitud_alquiler: int
    ) -> None: ...

    def confirmar_reserva_locativa_sin_commit(
        self,
        payload: ReservaLocativaConfirmarPayload,
        outbox_event: OutboxEventPayload,
    ) -> dict[str, Any]: ...

    def commit(self) -> None: ...

    def rollback(self) -> None: ...


class ConvertSolicitudAlquilerToReservaLocativaService:
    def __init__(self, repository: LocativoRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: ConvertSolicitudAlquilerToReservaLocativaCommand
    ) -> AppResult[dict[str, Any]]:
        # ── validaciones de solicitud ──────────────────────────────────────────
        solicitud = self.repository.get_solicitud_alquiler(command.id_solicitud_alquiler)
        if solicitud is None or solicitud["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_SOLICITUD_ALQUILER")

        estado = (solicitud["estado_solicitud"] or "").strip().lower()
        if estado != ESTADO_APROBADA:
            return AppResult.fail("SOLICITUD_NOT_APROBADA")

        if self.repository.has_reserva_locativa_for_solicitud(command.id_solicitud_alquiler):
            return AppResult.fail("SOLICITUD_YA_CONVERTIDA")

        # ── validaciones de reserva ────────────────────────────────────────────
        if not command.codigo_reserva.strip():
            return AppResult.fail("INVALID_REQUIRED_FIELDS")

        if (
            command.fecha_vencimiento is not None
            and command.fecha_vencimiento < command.fecha_reserva
        ):
            return AppResult.fail("INVALID_DATE_RANGE")

        if not command.objetos:
            return AppResult.fail("OBJETOS_REQUIRED")

        seen: set[tuple[str, int]] = set()
        for objeto in command.objetos:
            if (objeto.id_inmueble is None) == (objeto.id_unidad_funcional is None):
                return AppResult.fail("EXACTLY_ONE_OBJECT_PARENT_REQUIRED")

            if objeto.id_inmueble is not None:
                key: tuple[str, int] = ("inmueble", objeto.id_inmueble)
                if not self.repository.inmueble_exists(objeto.id_inmueble):
                    return AppResult.fail("NOT_FOUND_INMUEBLE")
            else:
                key = ("unidad_funcional", objeto.id_unidad_funcional)
                if not self.repository.unidad_funcional_exists(objeto.id_unidad_funcional):
                    return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

            if key in seen:
                return AppResult.fail("DUPLICATE_OBJECT")
            seen.add(key)

        for objeto in command.objetos:
            if self.repository.has_current_disponibilidad_no_disponible(
                id_inmueble=objeto.id_inmueble,
                id_unidad_funcional=objeto.id_unidad_funcional,
                at_datetime=command.fecha_reserva,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if not self.repository.has_current_disponibilidad_disponible(
                id_inmueble=objeto.id_inmueble,
                id_unidad_funcional=objeto.id_unidad_funcional,
                at_datetime=command.fecha_reserva,
            ):
                return AppResult.fail("OBJECT_NOT_AVAILABLE")

            if self.repository.has_conflicting_active_reserva_locativa(
                id_inmueble=objeto.id_inmueble,
                id_unidad_funcional=objeto.id_unidad_funcional,
                conflict_states=ESTADOS_ACTIVOS_RESERVA_LOCATIVA,
            ):
                return AppResult.fail("CONFLICTING_RESERVA_LOCATIVA")

        # ── construcción de payloads ───────────────────────────────────────────
        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        create_payload = ReservaLocativaCreatePayload(
            codigo_reserva=command.codigo_reserva,
            fecha_reserva=command.fecha_reserva,
            estado_reserva=ESTADO_INICIAL_RESERVA_LOCATIVA,
            fecha_vencimiento=command.fecha_vencimiento,
            observaciones=command.observaciones,
            uid_global=str(self.uuid_generator()),
            version_registro=1,
            created_at=now,
            updated_at=now,
            id_instalacion_origen=id_instalacion,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_alta=op_id,
            op_id_ultima_modificacion=op_id,
        )

        objetos_payload: list[ReservaLocativaObjetoCreatePayload] = [
            ReservaLocativaObjetoCreatePayload(
                id_inmueble=o.id_inmueble,
                id_unidad_funcional=o.id_unidad_funcional,
                observaciones=o.observaciones,
                uid_global=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
            for o in command.objetos
        ]

        # ── transacción única: create + link + (opcional) confirm ──────────────
        try:
            created = self.repository.create_reserva_locativa_sin_commit(
                create_payload, objetos_payload
            )
            self.repository.vincular_solicitud_a_reserva_locativa(
                created["id_reserva_locativa"], command.id_solicitud_alquiler
            )

            if not command.confirmar:
                self.repository.commit()
                return AppResult.ok(created)

            confirmar_payload = ReservaLocativaConfirmarPayload(
                id_reserva_locativa=created["id_reserva_locativa"],
                estado_reserva=ESTADO_CONFIRMADA,
                version_registro_actual=created["version_registro"],
                version_registro_nueva=created["version_registro"] + 1,
                updated_at=datetime.now(UTC),
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_ultima_modificacion=op_id,
            )

            outbox_event = OutboxEventPayload(
                event_type=EVENT_TYPE_CONFIRMADA,
                aggregate_type=AGGREGATE_TYPE,
                aggregate_id=created["id_reserva_locativa"],
                payload={
                    "id_reserva_locativa": created["id_reserva_locativa"],
                    "codigo_reserva": created["codigo_reserva"],
                    "estado_reserva": ESTADO_CONFIRMADA,
                    "objetos": [
                        {
                            "id_inmueble": o["id_inmueble"],
                            "id_unidad_funcional": o["id_unidad_funcional"],
                        }
                        for o in created["objetos"]
                    ],
                },
                occurred_at=datetime.now(UTC),
            )

            confirm_result = self.repository.confirmar_reserva_locativa_sin_commit(
                confirmar_payload, outbox_event
            )
            if confirm_result.get("status") == "CONCURRENCY_ERROR":
                self.repository.rollback()
                return AppResult.fail("CONCURRENCY_ERROR")

            self.repository.commit()
            return AppResult.ok(confirm_result["data"])

        except Exception:
            self.repository.rollback()
            raise
