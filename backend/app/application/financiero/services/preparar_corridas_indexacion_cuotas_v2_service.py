from __future__ import annotations

import calendar
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

from sqlalchemy.exc import IntegrityError

from app.api.core_ef_headers import CoreEFHeaders
from app.application.common.results import AppResult
from app.application.financiero.services.preview_indexacion_cuotas_v2_service import (
    PreviewIndexacionCuotasV2Command,
    PreviewIndexacionCuotasV2Service,
)

ORIGEN_PUBLICACION_INDICE = "PUBLICACION_INDICE"
CONFLICTO_CONCURRENTE_CORRIDA_INDEXACION = "CONFLICTO_CONCURRENTE_CORRIDA_INDEXACION"
ERROR_INTEGRIDAD_PREPARACION_CORRIDA = "ERROR_INTEGRIDAD_PREPARACION_CORRIDA"


@dataclass(frozen=True, slots=True)
class PrepararCorridasIndexacionCuotasV2Command:
    id_indice_financiero_valor: int
    motivo: str | None = None


class PrepararCorridasIndexacionCuotasV2Repository(Protocol):
    def get_valor_publicado(self, id_valor: int) -> dict[str, Any] | None: ...
    def list_configuraciones_alcanzadas(self, id_indice_financiero: int, fecha_valor_original: date, fecha_corte: date) -> list[dict[str, Any]]: ...
    def get_corrida_existente(self, *, id_plan_pago_venta: int, id_plan_pago_venta_bloque: int, id_plan_pago_venta_bloque_indexacion: int, id_indice_financiero: int, periodo_aplicado: date) -> dict[str, Any] | None: ...
    def rollback(self) -> None: ...
    def is_conflicto_unico_publicacion(self, exc: IntegrityError) -> bool: ...


class PrepararCorridasIndexacionCuotasV2Service:
    def __init__(self, repository: PrepararCorridasIndexacionCuotasV2Repository, preview_service: PreviewIndexacionCuotasV2Service) -> None:
        self.repository = repository
        self.preview_service = preview_service

    def execute(self, command: PrepararCorridasIndexacionCuotasV2Command, core_ef: CoreEFHeaders) -> AppResult[dict[str, Any]]:
        valor = self.repository.get_valor_publicado(command.id_indice_financiero_valor)
        if valor is None:
            return AppResult.fail("VALOR_INDICE_PUBLICADO_INEXISTENTE")
        periodo_aplicado = _inicio_de_mes(valor["fecha_valor"])
        fecha_corte = _fin_de_mes(periodo_aplicado)
        configs = self.repository.list_configuraciones_alcanzadas(valor["id_indice_financiero"], valor["fecha_valor"], fecha_corte)
        resultados: list[dict[str, Any]] = []
        creadas = existentes = requiere_correccion = sin_obligaciones = errores = 0
        for cfg in configs:
            base = {
                "id_plan_pago_venta": cfg["id_plan_pago_venta"],
                "id_plan_pago_venta_bloque": cfg["id_plan_pago_venta_bloque"],
                "id_plan_pago_venta_bloque_indexacion": cfg["id_plan_pago_venta_bloque_indexacion"],
                "id_indice_financiero": valor["id_indice_financiero"],
                "periodo_aplicado": periodo_aplicado,
            }
            existente = self.repository.get_corrida_existente(**base)
            if existente is not None:
                fila, es_correccion = _clasificar_existente(base, existente, command.id_indice_financiero_valor)
                existentes += not es_correccion
                requiere_correccion += es_correccion
                resultados.append(fila)
                continue
            preview_base = {**base, "id_indice_financiero_valor_aplicado": command.id_indice_financiero_valor}
            result = self._crear_preview(preview_base, fecha_corte, command, core_ef)
            if result.success:
                creadas += 1
                data = result.data
                resultados.append({**preview_base, "id_indice_financiero_valor_solicitado": command.id_indice_financiero_valor, "id_indice_financiero_valor_existente": None, "id_corrida_indexacion_financiera": data["id_corrida_indexacion_financiera"], "hash_corrida": data["hash_corrida"], "estado_corrida": "PREVISUALIZADA", "cantidad_analizada": data["resumen"]["cantidad_analizada"], "cantidad_elegible": data["resumen"]["cantidad_elegible"], "resultado": "CREADA", "error": None})
                continue
            error = result.errors[0]
            if error == CONFLICTO_CONCURRENTE_CORRIDA_INDEXACION:
                existente = self.repository.get_corrida_existente(**base)
                if existente is not None:
                    fila, es_correccion = _clasificar_existente(base, existente, command.id_indice_financiero_valor)
                    existentes += not es_correccion
                    requiere_correccion += es_correccion
                    resultados.append(fila)
                    continue
            if error == "SIN_OBLIGACIONES_ANALIZABLES":
                sin_obligaciones += 1
                estado = "SIN_OBLIGACIONES"
            else:
                errores += 1
                estado = "ERROR"
            resultados.append({**preview_base, "id_indice_financiero_valor_solicitado": command.id_indice_financiero_valor, "id_indice_financiero_valor_existente": None, "id_corrida_indexacion_financiera": None, "hash_corrida": None, "estado_corrida": estado, "cantidad_analizada": 0, "cantidad_elegible": 0, "resultado": estado, "error": error})
        return AppResult.ok({"id_indice_financiero_valor": command.id_indice_financiero_valor, "id_indice_financiero": valor["id_indice_financiero"], "periodo_aplicado": periodo_aplicado, "fecha_corte": fecha_corte, "cantidad_configuraciones_analizadas": len(configs), "cantidad_corridas_creadas": creadas, "cantidad_corridas_existentes": existentes, "cantidad_requiere_correccion": requiere_correccion, "cantidad_sin_obligaciones": sin_obligaciones, "cantidad_errores": errores, "resultados": resultados})

    def _crear_preview(self, base: dict[str, Any], fecha_corte: date, command: PrepararCorridasIndexacionCuotasV2Command, core_ef: CoreEFHeaders) -> AppResult[dict[str, Any]]:
        group_core = CoreEFHeaders(x_op_id=_derive_group_op_id(core_ef.x_op_id, base), x_usuario_id=core_ef.x_usuario_id, x_sucursal_id=core_ef.x_sucursal_id, x_instalacion_id=core_ef.x_instalacion_id, if_match_version=None)
        try:
            return self.preview_service.execute(PreviewIndexacionCuotasV2Command(**base, fecha_corte=fecha_corte, persistir=True, origen_corrida=ORIGEN_PUBLICACION_INDICE, motivo=command.motivo or "Preparación automática por publicación de índice financiero"), group_core)
        except IntegrityError as exc:
            self.repository.rollback()
            if self.repository.is_conflicto_unico_publicacion(exc):
                return AppResult.fail(CONFLICTO_CONCURRENTE_CORRIDA_INDEXACION)
            return AppResult.fail(ERROR_INTEGRIDAD_PREPARACION_CORRIDA)


def _fin_de_mes(periodo: date) -> date:
    return date(periodo.year, periodo.month, calendar.monthrange(periodo.year, periodo.month)[1])


def _inicio_de_mes(periodo: date) -> date:
    return date(periodo.year, periodo.month, 1)


def _derive_group_op_id(root: uuid.UUID, base: dict[str, Any]) -> uuid.UUID:
    seed = "|".join(str(base[k]) for k in sorted(base))
    return uuid.uuid5(root, seed)


def _row_resumen(row: dict[str, Any]) -> dict[str, Any]:
    return {"id_corrida_indexacion_financiera": row["id_corrida_indexacion_financiera"], "id_indice_financiero_valor_aplicado": row["id_indice_financiero_valor_aplicado"], "hash_corrida": row["hash_corrida"], "estado_corrida": row["estado_corrida"], "cantidad_analizada": row.get("cantidad_analizada", 0), "cantidad_elegible": row.get("cantidad_elegible", 0)}


def _clasificar_existente(base: dict[str, Any], row: dict[str, Any], id_valor_solicitado: int) -> tuple[dict[str, Any], bool]:
    id_valor_existente = row["id_indice_financiero_valor_aplicado"]
    requiere_correccion = id_valor_existente != id_valor_solicitado
    return ({
        **base,
        **_row_resumen(row),
        "id_indice_financiero_valor_solicitado": id_valor_solicitado,
        "id_indice_financiero_valor_existente": id_valor_existente,
        "resultado": "REQUIERE_CORRECCION" if requiere_correccion else "EXISTENTE",
        "error": "PERIODO_ORDINARIO_YA_PREPARADO_CON_OTRO_VALOR" if requiere_correccion else None,
    }, requiere_correccion)
