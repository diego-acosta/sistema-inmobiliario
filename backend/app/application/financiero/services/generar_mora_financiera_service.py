from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.financiero.commands.generar_mora_financiera import (
    GenerarMoraFinancieraCommand,
)


CODIGO_INTERES_MORA = "INTERES_MORA"
TASA_DIARIA_MORA = Decimal("0.001")


@dataclass(slots=True)
class MoraObligacionCreatePayload:
    id_relacion_generadora: int
    id_obligacion_base: int
    fecha_proceso: date
    fecha_emision: date
    fecha_vencimiento: date
    importe_total: Decimal
    estado_obligacion: str
    observaciones: str
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class MoraComposicionCreatePayload:
    id_concepto_financiero: int
    codigo_concepto_financiero: str
    orden_composicion: int
    importe_componente: Decimal
    detalle_calculo: str
    uid_global: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


class FinancieroRepository(Protocol):
    def get_concepto_financiero_by_codigo(
        self, codigo: str
    ) -> dict[str, Any] | None: ...

    def buscar_obligaciones_elegibles_mora(
        self, fecha_proceso: date
    ) -> list[dict[str, Any]]: ...

    def existe_mora_para_obligacion_fecha(
        self, id_obligacion_base: int, fecha_proceso: date
    ) -> bool: ...

    def crear_moras_financieras(
        self,
        moras: list[
            tuple[MoraObligacionCreatePayload, MoraComposicionCreatePayload]
        ],
    ) -> None: ...


class GenerarMoraFinancieraService:
    def __init__(
        self, repository: FinancieroRepository, uuid_generator=None
    ) -> None:
        self.repository = repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self, command: GenerarMoraFinancieraCommand
    ) -> AppResult[dict[str, Any]]:
        fecha_proceso = command.fecha_proceso or date.today()

        concepto = self.repository.get_concepto_financiero_by_codigo(
            CODIGO_INTERES_MORA
        )
        if concepto is None:
            return AppResult.fail("NOT_FOUND_CONCEPTO_INTERES_MORA")

        obligaciones = self.repository.buscar_obligaciones_elegibles_mora(
            fecha_proceso
        )

        now = datetime.now(UTC)
        id_instalacion = getattr(command.context, "id_instalacion", None)
        op_id = getattr(command.context, "op_id", None)
        moras: list[
            tuple[MoraObligacionCreatePayload, MoraComposicionCreatePayload]
        ] = []

        for obligacion in obligaciones:
            id_obligacion_base = obligacion["id_obligacion_financiera"]
            if self.repository.existe_mora_para_obligacion_fecha(
                id_obligacion_base, fecha_proceso
            ):
                continue

            saldo = Decimal(str(obligacion["saldo_pendiente"]))
            importe_mora = (saldo * TASA_DIARIA_MORA).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if importe_mora <= 0:
                continue

            observaciones = (
                f"MORA_AUTO id_obligacion_base={id_obligacion_base} "
                f"fecha_proceso={fecha_proceso.isoformat()} "
                f"tasa_diaria={TASA_DIARIA_MORA}"
            )
            detalle_calculo = (
                f"saldo_pendiente={saldo};tasa_diaria={TASA_DIARIA_MORA};"
                f"fecha_proceso={fecha_proceso.isoformat()}"
            )

            moras.append(
                (
                    MoraObligacionCreatePayload(
                        id_relacion_generadora=obligacion[
                            "id_relacion_generadora"
                        ],
                        id_obligacion_base=id_obligacion_base,
                        fecha_proceso=fecha_proceso,
                        fecha_emision=fecha_proceso,
                        fecha_vencimiento=fecha_proceso,
                        importe_total=importe_mora,
                        estado_obligacion="EXIGIBLE",
                        observaciones=observaciones,
                        uid_global=str(self.uuid_generator()),
                        version_registro=1,
                        created_at=now,
                        updated_at=now,
                        id_instalacion_origen=id_instalacion,
                        id_instalacion_ultima_modificacion=id_instalacion,
                        op_id_alta=op_id,
                        op_id_ultima_modificacion=op_id,
                    ),
                    MoraComposicionCreatePayload(
                        id_concepto_financiero=concepto[
                            "id_concepto_financiero"
                        ],
                        codigo_concepto_financiero=CODIGO_INTERES_MORA,
                        orden_composicion=1,
                        importe_componente=importe_mora,
                        detalle_calculo=detalle_calculo,
                        uid_global=str(self.uuid_generator()),
                        version_registro=1,
                        created_at=now,
                        updated_at=now,
                        id_instalacion_origen=id_instalacion,
                        id_instalacion_ultima_modificacion=id_instalacion,
                        op_id_alta=op_id,
                        op_id_ultima_modificacion=op_id,
                    ),
                )
            )

        self.repository.crear_moras_financieras(moras)

        return AppResult.ok(
            {
                "fecha_proceso": fecha_proceso,
                "procesadas": len(obligaciones),
                "generadas": len(moras),
            }
        )
