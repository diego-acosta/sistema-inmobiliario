from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.comercial.commands.create_instrumento_compraventa import (
    CreateInstrumentoCompraventaCommand,
)
from app.application.common.results import AppResult


ESTADO_VENTA_INSTRUMENTABLE = "confirmada"
ESTADOS_INSTRUMENTO_VALIDOS = {
    "anulado",
    "firmado",
    "generado",
    "pendiente",
    "vigente",
}


@dataclass(slots=True)
class InstrumentoCompraventaCreatePayload:
    id_venta: int
    tipo_instrumento: str
    numero_instrumento: str | None
    fecha_instrumento: datetime
    estado_instrumento: str
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
class InstrumentoCompraventaObjetoCreatePayload:
    id_inmueble: int | None
    id_unidad_funcional: int | None
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

    def inmueble_exists(self, id_inmueble: int) -> bool:
        ...

    def unidad_funcional_exists(self, id_unidad_funcional: int) -> bool:
        ...

    def create_instrumento_compraventa(
        self,
        payload: InstrumentoCompraventaCreatePayload,
        objetos: list[InstrumentoCompraventaObjetoCreatePayload],
    ) -> dict[str, Any]:
        ...


class CreateInstrumentoCompraventaService:
    def __init__(self, repository: ComercialRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateInstrumentoCompraventaCommand
    ) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta(command.id_venta)
        if venta is None or venta["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_VENTA")

        estado_venta = (venta["estado_venta"] or "").strip().lower()
        if estado_venta != ESTADO_VENTA_INSTRUMENTABLE:
            return AppResult.fail("INVALID_VENTA_STATE")

        objetos_venta = venta["objetos"]
        if not objetos_venta:
            return AppResult.fail("VENTA_WITHOUT_OBJECTS")

        existing_objects_by_key: dict[tuple[str, int], dict[str, Any]] = {}
        for objeto in objetos_venta:
            id_inmueble = objeto["id_inmueble"]
            id_unidad_funcional = objeto["id_unidad_funcional"]

            if (id_inmueble is None) == (id_unidad_funcional is None):
                return AppResult.fail("INVALID_VENTA_OBJECTS")

            object_key = (
                ("inmueble", id_inmueble)
                if id_inmueble is not None
                else ("unidad_funcional", id_unidad_funcional)
            )
            if object_key in existing_objects_by_key:
                return AppResult.fail("INVALID_VENTA_OBJECTS")
            existing_objects_by_key[object_key] = objeto

            precio_asignado = objeto["precio_asignado"]
            if precio_asignado is None or precio_asignado <= 0:
                return AppResult.fail("INCOMPLETE_VENTA_CONDITIONS")

        monto_total = venta["monto_total"]
        if monto_total is None or monto_total <= 0:
            return AppResult.fail("INCOMPLETE_VENTA_CONDITIONS")

        suma_precios = sum(
            (objeto["precio_asignado"] for objeto in objetos_venta),
            start=Decimal("0"),
        )
        if suma_precios != monto_total:
            return AppResult.fail("INCOMPLETE_VENTA_CONDITIONS")

        if not command.tipo_instrumento.strip():
            return AppResult.fail("INVALID_REQUIRED_FIELDS")

        estado_instrumento = command.estado_instrumento.strip().lower()
        if estado_instrumento not in ESTADOS_INSTRUMENTO_VALIDOS:
            return AppResult.fail("INVALID_ESTADO_INSTRUMENTO")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        request_objects_by_key: dict[tuple[str, int], str | None] = {}
        for objeto in command.objetos:
            if (objeto.id_inmueble is None) == (objeto.id_unidad_funcional is None):
                return AppResult.fail("EXACTLY_ONE_OBJECT_PARENT_REQUIRED")

            object_key = (
                ("inmueble", objeto.id_inmueble)
                if objeto.id_inmueble is not None
                else ("unidad_funcional", objeto.id_unidad_funcional)
            )
            if object_key in request_objects_by_key:
                return AppResult.fail("DUPLICATE_OBJECT")

            if object_key not in existing_objects_by_key:
                return AppResult.fail("INVALID_INSTRUMENT_ASSOCIATION")

            if objeto.id_inmueble is not None and not self.repository.inmueble_exists(
                objeto.id_inmueble
            ):
                return AppResult.fail("NOT_FOUND_INMUEBLE")

            if (
                objeto.id_unidad_funcional is not None
                and not self.repository.unidad_funcional_exists(objeto.id_unidad_funcional)
            ):
                return AppResult.fail("NOT_FOUND_UNIDAD_FUNCIONAL")

            request_objects_by_key[object_key] = objeto.observaciones

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = InstrumentoCompraventaCreatePayload(
            id_venta=command.id_venta,
            tipo_instrumento=command.tipo_instrumento,
            numero_instrumento=command.numero_instrumento,
            fecha_instrumento=command.fecha_instrumento,
            estado_instrumento=estado_instrumento,
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

        objetos_payload: list[InstrumentoCompraventaObjetoCreatePayload] = []
        for object_key, observaciones in request_objects_by_key.items():
            object_type, object_id = object_key
            objetos_payload.append(
                InstrumentoCompraventaObjetoCreatePayload(
                    id_inmueble=object_id if object_type == "inmueble" else None,
                    id_unidad_funcional=(
                        object_id if object_type == "unidad_funcional" else None
                    ),
                    observaciones=observaciones,
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

        return AppResult.ok(
            self.repository.create_instrumento_compraventa(payload, objetos_payload)["data"]
        )
