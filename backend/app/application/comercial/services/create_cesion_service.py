from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.comercial.commands.create_cesion import CreateCesionCommand
from app.application.common.results import AppResult


ESTADO_VENTA_CEDIBLE = "confirmada"


@dataclass(slots=True)
class CesionCreatePayload:
    id_venta: int
    fecha_cesion: datetime
    tipo_cesion: str | None
    observaciones: str | None
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class ComercialRepository(Protocol):
    def get_venta(self, id_venta: int) -> dict[str, Any] | None:
        ...

    def has_current_ocupacion_conflict(
        self,
        *,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        at_datetime: datetime,
    ) -> bool:
        ...

    def cesion_exists_for_venta(self, id_venta: int) -> bool:
        ...

    def escrituracion_exists_for_venta(self, id_venta: int) -> bool:
        ...

    def rescision_exists_for_venta(self, id_venta: int) -> bool:
        ...

    def create_cesion(self, payload: CesionCreatePayload) -> dict[str, Any]:
        ...


class CreateCesionService:
    def __init__(self, repository: ComercialRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, command: CreateCesionCommand) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta(command.id_venta)
        if venta is None or venta["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_VENTA")

        estado_venta = (venta["estado_venta"] or "").strip().lower()
        if estado_venta != ESTADO_VENTA_CEDIBLE:
            return AppResult.fail("INVALID_VENTA_STATE")

        objetos = venta["objetos"]
        if not objetos:
            return AppResult.fail("VENTA_WITHOUT_OBJECTS")

        seen_objects: set[tuple[str, int]] = set()
        for objeto in objetos:
            id_inmueble = objeto["id_inmueble"]
            id_unidad_funcional = objeto["id_unidad_funcional"]

            if (id_inmueble is None) == (id_unidad_funcional is None):
                return AppResult.fail("INVALID_VENTA_OBJECTS")

            object_key = (
                ("inmueble", id_inmueble)
                if id_inmueble is not None
                else ("unidad_funcional", id_unidad_funcional)
            )
            if object_key in seen_objects:
                return AppResult.fail("INVALID_VENTA_OBJECTS")
            seen_objects.add(object_key)

            precio_asignado = objeto["precio_asignado"]
            if precio_asignado is None or precio_asignado <= 0:
                return AppResult.fail("INCOMPLETE_VENTA_CONDITIONS")

        monto_total = venta["monto_total"]
        if monto_total is None or monto_total <= 0:
            return AppResult.fail("INCOMPLETE_VENTA_CONDITIONS")

        suma_precios = sum(
            (objeto["precio_asignado"] for objeto in objetos),
            start=Decimal("0"),
        )
        if suma_precios != monto_total:
            return AppResult.fail("INCOMPLETE_VENTA_CONDITIONS")

        if self.repository.rescision_exists_for_venta(command.id_venta):
            return AppResult.fail("CONFLICTING_RESCISION")

        if self.repository.escrituracion_exists_for_venta(command.id_venta):
            return AppResult.fail("CONFLICTING_ESCRITURACION")

        if self.repository.cesion_exists_for_venta(command.id_venta):
            return AppResult.fail("CONFLICTING_CESION")

        now = datetime.now(UTC)
        for objeto in objetos:
            if self.repository.has_current_ocupacion_conflict(
                id_inmueble=objeto["id_inmueble"],
                id_unidad_funcional=objeto["id_unidad_funcional"],
                at_datetime=now,
            ):
                return AppResult.fail("CONFLICTING_OCUPACION")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        op_id = getattr(command.context, "op_id", None)
        payload = CesionCreatePayload(
            id_venta=command.id_venta,
            fecha_cesion=command.fecha_cesion,
            tipo_cesion=command.tipo_cesion,
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

        return AppResult.ok(self.repository.create_cesion(payload)["data"])
