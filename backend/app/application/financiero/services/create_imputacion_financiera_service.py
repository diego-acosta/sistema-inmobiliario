from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.financiero.commands.create_imputacion_financiera import (
    CreateImputacionFinancieraCommand,
)

ESTADOS_ACEPTAN_IMPUTACION = {
    "PROYECTADA",
    "EMITIDA",
    "EXIGIBLE",
    "PARCIALMENTE_CANCELADA",
    "VENCIDA",
}

# Menor índice = mayor prioridad. Conceptos no listados van al final ordenados por orden_composicion.
_PRIORIDAD: dict[str, int] = {
    "PUNITORIO": 0,
    "CARGO_ADMINISTRATIVO": 2,
    "INTERES_FINANCIERO": 3,
    "AJUSTE_INDEXACION": 4,
    "CAPITAL_VENTA": 5,
    "ANTICIPO_VENTA": 6,
    "CANON_LOCATIVO": 7,
    "EXPENSA_TRASLADADA": 8,
    "SERVICIO_TRASLADADO": 9,
    "IMPUESTO_TRASLADADO": 10,
}


def _clave_orden(comp: dict[str, Any]) -> tuple[int, int]:
    return (_PRIORIDAD.get(comp["codigo_concepto_financiero"], 999), comp["orden_composicion"])


@dataclass(slots=True)
class MovimientoCreatePayload:
    fecha_movimiento: datetime
    tipo_movimiento: str
    importe: float
    signo: str
    estado_movimiento: str
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class AplicacionLineItem:
    id_composicion_obligacion: int
    importe_aplicado: float
    orden_aplicacion: int
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class ImputacionCreatePayload:
    id_obligacion_financiera: int
    fecha_aplicacion: datetime
    tipo_aplicacion: str
    origen_automatico_o_manual: str
    movimiento: MovimientoCreatePayload
    lineas: list[AplicacionLineItem]


class FinancieroRepository(Protocol):
    def get_obligacion_para_imputacion(
        self, id_obligacion_financiera: int
    ) -> dict[str, Any] | None: ...

    def get_composiciones_para_imputar(
        self, id_obligacion_financiera: int
    ) -> list[dict[str, Any]]: ...

    def create_imputacion(
        self, payload: ImputacionCreatePayload
    ) -> dict[str, Any]: ...


class CreateImputacionFinancieraService:
    def __init__(
        self, repository: FinancieroRepository, uuid_generator=None
    ) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: CreateImputacionFinancieraCommand
    ) -> AppResult[dict[str, Any]]:
        obligacion = self.repository.get_obligacion_para_imputacion(
            command.id_obligacion_financiera
        )
        if obligacion is None or obligacion.get("deleted_at") is not None:
            return AppResult.fail("NOT_FOUND_OBLIGACION")

        if command.monto <= 0:
            return AppResult.fail("MONTO_INVALIDO")

        estado = obligacion["estado_obligacion"]
        if estado not in ESTADOS_ACEPTAN_IMPUTACION:
            return AppResult.fail("ESTADO_NO_ACEPTA_IMPUTACION")

        saldo = float(obligacion["saldo_pendiente"])
        if round(command.monto, 2) > round(saldo, 2):
            return AppResult.fail("MONTO_EXCEDE_SALDO")

        composiciones = self.repository.get_composiciones_para_imputar(
            command.id_obligacion_financiera
        )
        if not composiciones:
            return AppResult.fail("SIN_COMPOSICIONES_DISPONIBLES")

        composiciones_ordenadas = sorted(composiciones, key=_clave_orden)

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)

        monto_restante = round(command.monto, 2)
        lineas: list[AplicacionLineItem] = []

        for i, comp in enumerate(composiciones_ordenadas):
            if monto_restante <= 0:
                break
            aplicado = round(min(float(comp["saldo_componente"]), monto_restante), 2)
            if aplicado <= 0:
                continue
            lineas.append(
                AplicacionLineItem(
                    id_composicion_obligacion=comp["id_composicion_obligacion"],
                    importe_aplicado=aplicado,
                    orden_aplicacion=len(lineas) + 1,
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
            monto_restante = round(monto_restante - aplicado, 2)

        if monto_restante > 0:
            return AppResult.fail("SALDO_INSUFICIENTE_EN_COMPOSICIONES")

        payload = ImputacionCreatePayload(
            id_obligacion_financiera=command.id_obligacion_financiera,
            fecha_aplicacion=now,
            tipo_aplicacion="PAGO",
            origen_automatico_o_manual="MANUAL",
            movimiento=MovimientoCreatePayload(
                fecha_movimiento=now,
                tipo_movimiento="PAGO",
                importe=command.monto,
                signo="CREDITO",
                estado_movimiento="APLICADO",
                uid_global=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            ),
            lineas=lineas,
        )

        created = self.repository.create_imputacion(payload)
        return AppResult.ok(created)
