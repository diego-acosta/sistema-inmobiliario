from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError

from app.application.comercial.commands.generate_venta_from_reserva_venta import (
    GenerateVentaFromReservaVentaCommand,
)
from app.application.comercial.services.create_reserva_venta_service import (
    ESTADOS_RESERVA_CONFLICTIVOS,
    ESTADOS_VENTA_CONFLICTIVOS,
)
from app.application.common.results import AppResult


ESTADO_RESERVA_CONVERTIBLE = "confirmada"
ESTADO_RESERVA_FINALIZADA = "finalizada"
ESTADO_INICIAL_VENTA = "borrador"
ESTADO_BLOQUEO_RESERVA_CONFIRMADA = "RESERVADA"
VENTA_CODIGO_UNIQUE_CONSTRAINT = "uq_venta_codigo"


@dataclass(slots=True)
class VentaFromReservaCreatePayload:
    id_reserva_venta: int
    codigo_venta: str
    fecha_venta: datetime
    estado_venta: str
    monto_total: Decimal | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class VentaFromReservaObjetoCreatePayload:
    id_inmueble: int | None
    id_unidad_funcional: int | None
    precio_asignado: Decimal | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class VentaFromReservaParticipacionCreatePayload:
    id_persona: int
    id_rol_participacion: int
    tipo_relacion: str
    id_relacion: int
    fecha_desde: date | datetime
    fecha_hasta: date | datetime | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class ReservaVentaFinalizePayload:
    id_reserva_venta: int
    estado_reserva: str
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class ComercialRepository(Protocol):
    def get_reserva_venta(self, id_reserva_venta: int) -> dict[str, Any] | None:
        ...

    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def has_conflicting_active_venta(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
    ) -> bool:
        ...

    def has_conflicting_active_reserva(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        conflict_states: set[str],
        exclude_id_reserva_venta: int | None = None,
    ) -> bool:
        ...

    def venta_exists_for_reserva(self, id_reserva_venta: int) -> bool:
        ...

    def venta_codigo_exists(self, codigo_venta: str) -> bool:
        ...

    def get_current_disponibilidad_state(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> str | None:
        ...

    def generate_venta_from_reserva(
        self,
        payload: VentaFromReservaCreatePayload,
        objetos: list[VentaFromReservaObjetoCreatePayload],
        participaciones: list[VentaFromReservaParticipacionCreatePayload],
        reserva_payload: ReservaVentaFinalizePayload,
    ) -> dict[str, Any]:
        ...


class GenerateVentaFromReservaVentaService:
    def __init__(self, repository: ComercialRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: GenerateVentaFromReservaVentaCommand
    ) -> AppResult[dict[str, Any]]:
        if not command.codigo_venta.strip():
            return AppResult.fail("INVALID_REQUIRED_FIELDS")

        reserva = self.repository.get_reserva_venta(command.id_reserva_venta)
        if reserva is None or reserva["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_RESERVA_VENTA")

        if self.repository.venta_exists_for_reserva(command.id_reserva_venta):
            return AppResult.fail("RESERVA_ALREADY_CONVERTED")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != reserva["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_reserva = (reserva["estado_reserva"] or "").strip().lower()
        if estado_reserva != ESTADO_RESERVA_CONVERTIBLE:
            return AppResult.fail("INVALID_RESERVA_STATE")

        objetos = reserva["objetos"]
        if not objetos:
            return AppResult.fail("RESERVA_WITHOUT_OBJECTS")

        seen_objects: set[tuple[str, int]] = set()
        for objeto in objetos:
            id_inmueble = objeto["id_inmueble"]
            id_unidad_funcional = objeto["id_unidad_funcional"]

            if (id_inmueble is None) == (id_unidad_funcional is None):
                return AppResult.fail("INVALID_RESERVA_OBJECTS")

            object_key = (
                ("inmueble", id_inmueble)
                if id_inmueble is not None
                else ("unidad_funcional", id_unidad_funcional)
            )
            if object_key in seen_objects:
                return AppResult.fail("INVALID_RESERVA_OBJECTS")
            seen_objects.add(object_key)

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        if self.repository.venta_codigo_exists(command.codigo_venta):
            return AppResult.fail("DUPLICATE_CODIGO_VENTA")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        for objeto in objetos:
            id_inmueble = objeto["id_inmueble"]
            id_unidad_funcional = objeto["id_unidad_funcional"]

            if id_inmueble is not None and not self.repository.inmueble_exists(id_inmueble):
                return AppResult.fail("NOT_FOUND_INMUEBLE")

            if (
                id_unidad_funcional is not None
                and not self.repository.unidad_funcional_exists(id_unidad_funcional)
            ):
                return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

            current_disponibilidad = self.repository.get_current_disponibilidad_state(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                at_datetime=now,
            )
            if current_disponibilidad != ESTADO_BLOQUEO_RESERVA_CONFIRMADA:
                return AppResult.fail("INVALID_RESERVA_BLOCK")

            if self.repository.has_conflicting_active_venta(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                conflict_states=ESTADOS_VENTA_CONFLICTIVOS,
            ):
                return AppResult.fail("CONFLICTING_VENTA")

            if self.repository.has_conflicting_active_reserva(
                id_inmueble=id_inmueble,
                id_unidad_funcional=id_unidad_funcional,
                conflict_states=ESTADOS_RESERVA_CONFLICTIVOS,
                exclude_id_reserva_venta=command.id_reserva_venta,
            ):
                return AppResult.fail("CONFLICTING_RESERVA")

        payload = VentaFromReservaCreatePayload(
            id_reserva_venta=command.id_reserva_venta,
            codigo_venta=command.codigo_venta,
            fecha_venta=command.fecha_venta,
            estado_venta=ESTADO_INICIAL_VENTA,
            monto_total=command.monto_total,
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

        objetos_payload: list[VentaFromReservaObjetoCreatePayload] = []
        for objeto in objetos:
            objetos_payload.append(
                VentaFromReservaObjetoCreatePayload(
                    id_inmueble=objeto["id_inmueble"],
                    id_unidad_funcional=objeto["id_unidad_funcional"],
                    precio_asignado=None,
                    observaciones=objeto["observaciones"],
                    uid_global=str(self.uuid_generator()),
                    version_registro=1,
                    created_at=now,
                    updated_at=now,
                    id_instalacion_origen=id_instalacion,
                    id_instalacion_ultima_modificacion=id_instalacion,
                    op_id_alta=op_id,
                    op_id_ultima_modificacion=op_id,
                )
            )

        participaciones_payload: list[VentaFromReservaParticipacionCreatePayload] = []
        for participacion in reserva.get("participaciones", []):
            participaciones_payload.append(
                VentaFromReservaParticipacionCreatePayload(
                    id_persona=participacion["id_persona"],
                    id_rol_participacion=participacion["id_rol_participacion"],
                    tipo_relacion="venta",
                    id_relacion=0,
                    fecha_desde=participacion["fecha_desde"],
                    fecha_hasta=participacion["fecha_hasta"],
                    observaciones=participacion["observaciones"],
                    uid_global=str(self.uuid_generator()),
                    version_registro=1,
                    created_at=now,
                    updated_at=now,
                    id_instalacion_origen=id_instalacion,
                    id_instalacion_ultima_modificacion=id_instalacion,
                    op_id_alta=op_id,
                    op_id_ultima_modificacion=op_id,
                )
            )

        reserva_payload = ReservaVentaFinalizePayload(
            id_reserva_venta=command.id_reserva_venta,
            estado_reserva=ESTADO_RESERVA_FINALIZADA,
            version_registro_actual=reserva["version_registro"],
            version_registro_nueva=reserva["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        try:
            result = self.repository.generate_venta_from_reserva(
                payload,
                objetos_payload,
                participaciones_payload,
                reserva_payload,
            )
        except IntegrityError as exc:
            if self._is_codigo_venta_duplicate(exc):
                return AppResult.fail("DUPLICATE_CODIGO_VENTA")
            raise

        status = result.get("status")
        if status == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")

        return AppResult.ok(result["data"])

    @staticmethod
    def _is_codigo_venta_duplicate(exc: IntegrityError) -> bool:
        diag = getattr(getattr(exc, "orig", None), "diag", None)
        return getattr(diag, "constraint_name", None) == VENTA_CODIGO_UNIQUE_CONSTRAINT
