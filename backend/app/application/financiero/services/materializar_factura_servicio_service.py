from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any, Protocol
from uuid import UUID, uuid4

from app.application.common.results import AppResult
from app.application.financiero.services.create_relacion_generadora_service import (
    RelacionGeneradoraCreatePayload,
)


TIPO_ORIGEN_FACTURA_SERVICIO = "factura_servicio"
CONCEPTO_SERVICIO_TRASLADADO = "SERVICIO_TRASLADADO"
ROL_OBLIGADO_RESPONSABLE_SERVICIO = "RESPONSABLE_SERVICIO"


@dataclass(slots=True)
class ObligadoServicioTrasladadoPayload:
    uid_global: str
    id_persona: int
    rol_obligado: str
    porcentaje_responsabilidad: Decimal
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None


@dataclass(slots=True)
class ObligacionServicioTrasladadoPayload:
    uid_global_obligacion: str
    uid_global_composicion: str
    version_registro: int
    created_at: datetime
    updated_at: datetime
    id_instalacion_origen: Any
    id_instalacion_ultima_modificacion: Any
    op_id_alta: UUID | None
    op_id_ultima_modificacion: UUID | None
    id_relacion_generadora: int
    fecha_emision: date
    fecha_vencimiento: date | None
    periodo_desde: date | None
    periodo_hasta: date | None
    importe_total: Decimal
    moneda: str
    estado_obligacion: str
    id_concepto_financiero: int
    codigo_concepto_financiero: str
    obligados: list[ObligadoServicioTrasladadoPayload]


class FinancieroRepository(Protocol):
    db: Any

    def get_factura_servicio_para_materializar(
        self, id_factura_servicio: int
    ) -> dict[str, Any] | None: ...

    def get_relacion_generadora_by_origen(
        self, tipo_origen: str, id_origen: int
    ) -> dict[str, Any] | None: ...

    def create_relacion_generadora(
        self, payload: RelacionGeneradoraCreatePayload
    ) -> dict[str, Any]: ...

    def get_obligacion_activa_by_relacion_generadora(
        self, id_relacion_generadora: int
    ) -> dict[str, Any] | None: ...

    def get_concepto_financiero_by_codigo(
        self, codigo: str
    ) -> dict[str, Any] | None: ...

    def get_asignaciones_responsables_para_factura(
        self,
        *,
        id_servicio: int,
        id_inmueble: int | None,
        id_unidad_funcional: int | None,
        periodo_desde: date,
        periodo_hasta: date,
    ) -> list[dict[str, Any]]: ...

    def create_obligacion_servicio_trasladado(
        self, payload: ObligacionServicioTrasladadoPayload
    ) -> dict[str, Any]: ...


class MaterializarFacturaServicioService:
    def __init__(self, repository: FinancieroRepository, uuid_generator=None) -> None:
        self.repository = repository
        self.db = repository.db
        self.uuid_generator = uuid_generator or uuid4

    def execute(self, id_factura_servicio: int, context: Any) -> AppResult[dict[str, Any]]:
        try:
            with self._transaction():
                return self._execute_in_transaction(id_factura_servicio, context)
        except _RollbackAppResult as exc:
            return exc.result

    def _execute_in_transaction(
        self, id_factura_servicio: int, context: Any
    ) -> AppResult[dict[str, Any]]:
        factura = self.repository.get_factura_servicio_para_materializar(
            id_factura_servicio
        )
        if factura is None:
            return AppResult.fail("NOT_FOUND_FACTURA_SERVICIO")

        if (factura.get("estado_factura_servicio") or "").strip().upper() != "REGISTRADA":
            return AppResult.fail("FACTURA_SERVICIO_NO_ACTIVA")

        relacion_created = False
        relacion = self.repository.get_relacion_generadora_by_origen(
            TIPO_ORIGEN_FACTURA_SERVICIO,
            id_factura_servicio,
        )
        if relacion is None:
            relacion = self._create_relacion(id_factura_servicio, context)
            relacion_created = True

        id_relacion_generadora = relacion["id_relacion_generadora"]
        obligacion_existente = self.repository.get_obligacion_activa_by_relacion_generadora(
            id_relacion_generadora
        )
        if obligacion_existente is not None:
            return AppResult.ok(
                {
                    "resultado": "YA_MATERIALIZADA",
                    "id_factura_servicio": id_factura_servicio,
                    "id_relacion_generadora": id_relacion_generadora,
                    "id_obligacion_financiera": obligacion_existente[
                        "id_obligacion_financiera"
                    ],
                    "relacion_generadora_created": relacion_created,
                    "obligacion_created": False,
                    "obligados_creados": 0,
                }
            )

        concepto = self.repository.get_concepto_financiero_by_codigo(
            CONCEPTO_SERVICIO_TRASLADADO
        )
        if concepto is None:
            raise _RollbackAppResult(
                AppResult.fail(f"NOT_FOUND_CONCEPTO:{CONCEPTO_SERVICIO_TRASLADADO}")
            )

        periodo_desde = factura["periodo_desde"]
        periodo_hasta = factura["periodo_hasta"]
        if periodo_desde is None or periodo_hasta is None:
            raise _RollbackAppResult(AppResult.fail("RESPONSABLE_SERVICIO_AMBIGUO"))

        responsables_result = self._resolver_responsables(factura)
        if not responsables_result.success:
            raise _RollbackAppResult(responsables_result)
        responsables = responsables_result.data or []

        now = datetime.now(UTC)
        id_instalacion = getattr(context, "id_instalacion", None)
        op_id = getattr(context, "op_id", None)
        obligacion = self.repository.create_obligacion_servicio_trasladado(
            ObligacionServicioTrasladadoPayload(
                uid_global_obligacion=str(self.uuid_generator()),
                uid_global_composicion=str(self.uuid_generator()),
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
                id_relacion_generadora=id_relacion_generadora,
                fecha_emision=factura["fecha_emision"],
                fecha_vencimiento=factura["fecha_vencimiento"],
                periodo_desde=periodo_desde,
                periodo_hasta=periodo_hasta,
                importe_total=Decimal(str(factura["importe_total"])),
                moneda=factura.get("moneda") or "ARS",
                estado_obligacion="EMITIDA",
                id_concepto_financiero=concepto["id_concepto_financiero"],
                codigo_concepto_financiero=CONCEPTO_SERVICIO_TRASLADADO,
                obligados=[
                    ObligadoServicioTrasladadoPayload(
                        uid_global=str(self.uuid_generator()),
                        id_persona=resp["id_persona"],
                        rol_obligado=ROL_OBLIGADO_RESPONSABLE_SERVICIO,
                        porcentaje_responsabilidad=Decimal(
                            str(resp["porcentaje_responsabilidad"])
                        ),
                        version_registro=1,
                        created_at=now,
                        updated_at=now,
                        id_instalacion_origen=id_instalacion,
                        id_instalacion_ultima_modificacion=id_instalacion,
                        op_id_alta=op_id,
                        op_id_ultima_modificacion=op_id,
                    )
                    for resp in responsables
                ],
            )
        )

        return AppResult.ok(
            {
                "resultado": "MATERIALIZADA",
                "id_factura_servicio": id_factura_servicio,
                "id_relacion_generadora": id_relacion_generadora,
                "id_obligacion_financiera": obligacion["id_obligacion_financiera"],
                "relacion_generadora_created": relacion_created,
                "obligacion_created": True,
                "obligados_creados": len(responsables),
            }
        )

    def _resolver_responsables(
        self, factura: dict[str, Any]
    ) -> AppResult[list[dict[str, Any]]]:
        periodo_desde = factura["periodo_desde"]
        periodo_hasta = factura["periodo_hasta"]
        rows = self.repository.get_asignaciones_responsables_para_factura(
            id_servicio=factura["id_servicio"],
            id_inmueble=factura["id_inmueble"],
            id_unidad_funcional=factura["id_unidad_funcional"],
            periodo_desde=periodo_desde,
            periodo_hasta=periodo_hasta,
        )
        if not rows:
            return AppResult.fail("OBLIGADO_NO_RESUELTO")

        cruza_cambio = any(
            (row["fecha_desde"] > periodo_desde and row["fecha_desde"] <= periodo_hasta)
            or (
                row["fecha_hasta"] is not None
                and row["fecha_hasta"] >= periodo_desde
                and row["fecha_hasta"] < periodo_hasta
            )
            for row in rows
        )
        if cruza_cambio:
            return AppResult.fail("FACTURA_CRUZA_CAMBIO_RESPONSABLE")

        vigentes_periodo_completo = [
            row
            for row in rows
            if row["fecha_desde"] <= periodo_desde
            and (row["fecha_hasta"] is None or row["fecha_hasta"] >= periodo_hasta)
        ]
        if not vigentes_periodo_completo:
            return AppResult.fail("OBLIGADO_NO_RESUELTO")

        total = sum(
            Decimal(str(row["porcentaje_responsabilidad"]))
            for row in vigentes_periodo_completo
        )
        if total != Decimal("100.00") and total != Decimal("100"):
            return AppResult.fail("RESPONSABLE_SERVICIO_AMBIGUO")

        return AppResult.ok(vigentes_periodo_completo)

    def _create_relacion(self, id_factura_servicio: int, context: Any) -> dict[str, Any]:
        now = datetime.now(UTC)
        id_instalacion = getattr(context, "id_instalacion", None)
        op_id = getattr(context, "op_id", None)
        return self.repository.create_relacion_generadora(
            RelacionGeneradoraCreatePayload(
                tipo_origen=TIPO_ORIGEN_FACTURA_SERVICIO,
                id_origen=id_factura_servicio,
                descripcion="Relacion generadora creada desde factura_servicio",
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

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()


class _RollbackAppResult(Exception):
    def __init__(self, result: AppResult[Any]) -> None:
        self.result = result
