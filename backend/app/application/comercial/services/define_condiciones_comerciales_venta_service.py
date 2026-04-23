from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID

from app.application.comercial.commands.define_condiciones_comerciales_venta import (
    DefineCondicionesComercialesVentaCommand,
)
from app.application.common.results import AppResult


ESTADO_VENTA_DEFINIBLE = "borrador"


@dataclass(slots=True)
class VentaCondicionComercialUpdatePayload:
    id_venta: int
    monto_total: Decimal
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class VentaObjetoPrecioUpdatePayload:
    id_venta_objeto: int
    precio_asignado: Decimal
    version_registro_actual: int
    version_registro_nueva: int
    updated_at: datetime
    id_instalacion_ultima_modificacion: Any
    op_id_ultima_modificacion: UUID | None


class ComercialRepository(Protocol):
    def get_venta(self, id_venta: int) -> dict[str, Any] | None:
        ...

    def define_condiciones_comerciales_venta(
        self,
        payload: VentaCondicionComercialUpdatePayload,
        objetos: list[VentaObjetoPrecioUpdatePayload],
    ) -> dict[str, Any]:
        ...


class DefineCondicionesComercialesVentaService:
    def __init__(self, repository: ComercialRepository) -> None:
        self.repository = repository

    def execute(
        self, command: DefineCondicionesComercialesVentaCommand
    ) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta(command.id_venta)
        if venta is None or venta["deleted_at"] is not None:
            return AppResult.fail("NOT_FOUND_VENTA")

        if command.if_match_version is None:
            return AppResult.fail("CONCURRENCY_ERROR")

        if command.if_match_version != venta["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")

        estado_venta = (venta["estado_venta"] or "").strip().lower()
        if estado_venta != ESTADO_VENTA_DEFINIBLE:
            return AppResult.fail("INVALID_VENTA_STATE")

        objetos_venta = venta["objetos"]
        if not objetos_venta:
            return AppResult.fail("VENTA_WITHOUT_OBJECTS")

        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

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

        if len(command.objetos) != len(existing_objects_by_key):
            return AppResult.fail("MISSING_VENTA_OBJECTS")

        request_objects_by_key: dict[tuple[str, int], Decimal] = {}
        for objeto in command.objetos:
            if (objeto.id_inmueble is None) == (objeto.id_unidad_funcional is None):
                return AppResult.fail("EXACTLY_ONE_OBJECT_PARENT_REQUIRED")

            if objeto.precio_asignado <= 0:
                return AppResult.fail("INVALID_PRECIO_ASIGNADO")

            object_key = (
                ("inmueble", objeto.id_inmueble)
                if objeto.id_inmueble is not None
                else ("unidad_funcional", objeto.id_unidad_funcional)
            )
            if object_key in request_objects_by_key:
                return AppResult.fail("DUPLICATE_OBJECT")
            request_objects_by_key[object_key] = objeto.precio_asignado

        if set(request_objects_by_key) != set(existing_objects_by_key):
            return AppResult.fail("MISSING_VENTA_OBJECTS")

        suma_precios = sum(request_objects_by_key.values(), start=Decimal("0"))
        if suma_precios != command.monto_total:
            return AppResult.fail("INVALID_MONTO_TOTAL")

        now = datetime.now(UTC)
        op_id = getattr(command.context, "op_id", None)

        payload = VentaCondicionComercialUpdatePayload(
            id_venta=command.id_venta,
            monto_total=command.monto_total,
            version_registro_actual=venta["version_registro"],
            version_registro_nueva=venta["version_registro"] + 1,
            updated_at=now,
            id_instalacion_ultima_modificacion=id_instalacion,
            op_id_ultima_modificacion=op_id,
        )

        objetos_payload: list[VentaObjetoPrecioUpdatePayload] = []
        for object_key, precio_asignado in request_objects_by_key.items():
            objeto_actual = existing_objects_by_key[object_key]
            objetos_payload.append(
                VentaObjetoPrecioUpdatePayload(
                    id_venta_objeto=objeto_actual["id_venta_objeto"],
                    precio_asignado=precio_asignado,
                    version_registro_actual=objeto_actual["version_registro"],
                    version_registro_nueva=objeto_actual["version_registro"] + 1,
                    updated_at=now,
                    id_instalacion_ultima_modificacion=id_instalacion,
                    op_id_ultima_modificacion=op_id,
                )
            )

        result = self.repository.define_condiciones_comerciales_venta(
            payload,
            objetos_payload,
        )
        status = result.get("status")
        if status == "CONCURRENCY_ERROR":
            return AppResult.fail("CONCURRENCY_ERROR")
        if status == "OBJECT_UPDATE_FAILED":
            return AppResult.fail("INVALID_VENTA_OBJECTS")

        return AppResult.ok(result["data"])
