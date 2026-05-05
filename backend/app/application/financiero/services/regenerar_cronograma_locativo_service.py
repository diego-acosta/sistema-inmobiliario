from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any, Protocol
from uuid import uuid4

from app.application.common.results import AppResult
from app.application.financiero.services.cronograma_locativo_builder import (
    PeriodoCronogramaPayload,
    ROL_OBLIGADO_LOCATARIO,
    calcular_fecha_vencimiento_canon,
    calcular_importes_prorateados,
    generate_monthly_periods,
    get_segmentos_para_periodo,
)


class LocativoRepository(Protocol):
    def get_contrato_alquiler(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None: ...

    def get_locatario_principal_contrato(
        self, id_contrato_alquiler: int
    ) -> dict[str, Any] | None: ...


class FinancieroRepository(Protocol):
    def get_relacion_generadora_by_origen(
        self, tipo_origen: str, id_origen: int
    ) -> dict[str, Any] | None: ...

    def get_concepto_financiero_by_codigo(
        self, codigo: str
    ) -> dict[str, Any] | None: ...

    def get_obligaciones_reemplazables(
        self, id_relacion_generadora: int, fecha_corte: date
    ) -> list[dict[str, Any]]: ...

    def marcar_obligaciones_reemplazadas(self, ids: list[int]) -> int: ...

    def create_cronograma_obligaciones(
        self, periodos: list[PeriodoCronogramaPayload]
    ) -> int: ...

    def get_obligaciones_activas_desde(
        self, id_relacion_generadora: int, fecha_corte: date
    ) -> list[dict[str, Any]]: ...

    def vincular_obligaciones_reemplazo_1_a_1(
        self, pares: list[tuple[int, int]]
    ) -> int: ...


class RegenerarCronogramaLocativoService:
    def __init__(
        self,
        locativo_repository: LocativoRepository,
        financiero_repository: FinancieroRepository,
        uuid_generator=None,
    ) -> None:
        self.locativo_repo = locativo_repository
        self.financiero_repo = financiero_repository
        self.uuid_generator = uuid_generator or uuid4

    def execute(
        self,
        id_contrato_alquiler: int,
        fecha_corte: date,
        context: Any,
    ) -> AppResult[dict[str, Any]]:
        contrato = self.locativo_repo.get_contrato_alquiler(id_contrato_alquiler)
        if contrato is None or contrato.get("deleted_at") is not None:
            return AppResult.fail("NOT_FOUND_CONTRATO")

        fecha_fin = contrato.get("fecha_fin")
        if fecha_fin is None:
            return AppResult.fail("CONTRATO_SIN_FECHA_FIN")

        if fecha_corte > fecha_fin:
            return AppResult.ok({
                "reemplazadas": 0,
                "generadas": 0,
                "omitidas": 0,
                "razon": "fecha_corte_posterior_a_fin",
            })

        relacion = self.financiero_repo.get_relacion_generadora_by_origen(
            "contrato_alquiler", id_contrato_alquiler
        )
        if relacion is None:
            return AppResult.fail("NOT_FOUND_RELACION_GENERADORA")

        id_rg = relacion["id_relacion_generadora"]

        reemplazables = self.financiero_repo.get_obligaciones_reemplazables(
            id_rg, fecha_corte
        )

        reemplazadas = 0
        if reemplazables:
            ids = [ob["id_obligacion_financiera"] for ob in reemplazables]
            reemplazadas = self.financiero_repo.marcar_obligaciones_reemplazadas(ids)

        condiciones = contrato.get("condiciones_economicas_alquiler") or []
        fecha_gen_inicio = max(fecha_corte, contrato["fecha_inicio"])
        periodos = generate_monthly_periods(fecha_gen_inicio, fecha_fin)

        segmentos_todos: list[tuple[date, date, dict[str, Any], float, date, date]] = []
        omitidas = 0

        for periodo_desde_mes, periodo_hasta_mes in periodos:
            segs = get_segmentos_para_periodo(condiciones, periodo_desde_mes, periodo_hasta_mes)
            if not segs:
                omitidas += 1
                continue
            importes = calcular_importes_prorateados(segs, periodo_desde_mes)
            fecha_venc = calcular_fecha_vencimiento_canon(
                periodo_desde_mes, contrato.get("dia_vencimiento_canon")
            )
            for (seg_desde, seg_hasta, condicion), importe in zip(segs, importes):
                segmentos_todos.append(
                    (seg_desde, seg_hasta, condicion, importe, fecha_venc, periodo_desde_mes)
                )

        if not segmentos_todos:
            return AppResult.ok({
                "reemplazadas": reemplazadas,
                "generadas": 0,
                "omitidas": omitidas,
                "razon": "sin_condicion_aplicable",
            })

        locatario = self.locativo_repo.get_locatario_principal_contrato(
            id_contrato_alquiler
        )
        if locatario is None:
            return AppResult.fail("SIN_LOCATARIO_PRINCIPAL")

        concepto = self.financiero_repo.get_concepto_financiero_by_codigo("CANON_LOCATIVO")
        if concepto is None:
            return AppResult.fail("NOT_FOUND_CONCEPTO_CANON_LOCATIVO")

        id_concepto = concepto["id_concepto_financiero"]
        id_instalacion = getattr(context, "id_instalacion", None)
        op_id = getattr(context, "op_id", None)
        now = datetime.now(UTC)

        payloads = [
            PeriodoCronogramaPayload(
                id_relacion_generadora=id_rg,
                fecha_emision=emision_mes,
                fecha_vencimiento=fecha_vencimiento,
                periodo_desde=seg_desde,
                periodo_hasta=seg_hasta,
                importe_total=importe,
                moneda=condicion.get("moneda") or "ARS",
                estado_obligacion="EMITIDA",
                id_concepto_financiero=id_concepto,
                uid_global_obligacion=str(self.uuid_generator()),
                uid_global_composicion=str(self.uuid_generator()),
                uid_global_obligado=str(self.uuid_generator()),
                id_persona_obligado=locatario["id_persona"],
                rol_obligado=ROL_OBLIGADO_LOCATARIO,
                version_registro=1,
                created_at=now,
                updated_at=now,
                id_instalacion_origen=id_instalacion,
                id_instalacion_ultima_modificacion=id_instalacion,
                op_id_alta=op_id,
                op_id_ultima_modificacion=op_id,
            )
            for seg_desde, seg_hasta, condicion, importe, fecha_vencimiento, emision_mes
            in segmentos_todos
        ]

        generadas = self.financiero_repo.create_cronograma_obligaciones(payloads)
        self._vincular_reemplazos_1_a_1(id_rg, fecha_corte, reemplazables)
        return AppResult.ok({
            "reemplazadas": reemplazadas,
            "generadas": generadas,
            "omitidas": omitidas,
        })

    def _vincular_reemplazos_1_a_1(
        self,
        id_relacion_generadora: int,
        fecha_corte: date,
        reemplazables: list[dict[str, Any]],
    ) -> None:
        if not reemplazables:
            return

        nuevas = self.financiero_repo.get_obligaciones_activas_desde(
            id_relacion_generadora, fecha_corte
        )

        viejas_por_periodo: dict[tuple[date, date], list[dict[str, Any]]] = {}
        for ob in reemplazables:
            key = (ob["periodo_desde"], ob["periodo_hasta"])
            viejas_por_periodo.setdefault(key, []).append(ob)

        nuevas_por_periodo: dict[tuple[date, date], list[dict[str, Any]]] = {}
        for ob in nuevas:
            key = (ob["periodo_desde"], ob["periodo_hasta"])
            nuevas_por_periodo.setdefault(key, []).append(ob)

        pares: list[tuple[int, int]] = []
        for key, viejas in viejas_por_periodo.items():
            nuevas_exactas = nuevas_por_periodo.get(key, [])
            if len(viejas) == 1 and len(nuevas_exactas) == 1:
                pares.append((
                    viejas[0]["id_obligacion_financiera"],
                    nuevas_exactas[0]["id_obligacion_financiera"],
                ))

        if pares:
            self.financiero_repo.vincular_obligaciones_reemplazo_1_a_1(pares)
