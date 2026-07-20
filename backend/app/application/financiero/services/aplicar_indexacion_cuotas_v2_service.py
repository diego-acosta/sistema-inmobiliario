from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Protocol

from app.api.core_ef_headers import CoreEFHeaders
from app.application.common.results import AppResult
from app.application.financiero.services.indexacion_cuotas_v2_hash import (
    Q2,
    build_indexacion_cuotas_v2_hash,
)

ESTADOS_APLICABLES = {"PREVISUALIZADA", "PENDIENTE_APLICACION"}
ESTADOS_OBLIGACION_ELEGIBLES = {"PROYECTADA", "EMITIDA", "EXIGIBLE", "VENCIDA"}


@dataclass(frozen=True, slots=True)
class AplicarIndexacionCuotasV2Command:
    id_corrida_indexacion_financiera: int
    hash_corrida: str


class AplicarIndexacionCuotasV2Repository(Protocol):
    def get_corrida_for_update(self, corrida_id: int) -> dict[str, Any] | None: ...
    def get_corrida_by_apply_op(self, op_id: Any) -> dict[str, Any] | None: ...
    def list_detalles_for_update(self, corrida_id: int) -> list[dict[str, Any]]: ...
    def get_obligacion_actual_for_update(self, obligacion_id: int) -> dict[str, Any] | None: ...
    def get_obligacion_version_actual_for_update(self, obligacion_id: int) -> int | None: ...
    def get_lock_conflict(self, uid_entidad: Any, op_id: Any) -> dict[str, Any] | None: ...
    def acquire_lock(self, uid_entidad: Any, core_ef: CoreEFHeaders) -> None: ...
    def release_locks(self, op_id: Any) -> None: ...
    def upsert_ajuste(self, obligacion_id: int, ajuste_id: int | None, ajuste_version: int | None, importe: Any, core_ef: CoreEFHeaders) -> int: ...
    def upsert_trazabilidad(self, detalle: dict[str, Any], corrida: dict[str, Any], actual: dict[str, Any], core_ef: CoreEFHeaders) -> int: ...
    def update_obligacion(self, detalle: dict[str, Any], core_ef: CoreEFHeaders) -> bool: ...
    def update_detalle_aplicado(self, detalle_id: int, version_resultante: int, ajuste_id: int, ofi_id: int, core_ef: CoreEFHeaders) -> None: ...
    def update_corrida_aplicada(self, corrida_id: int, version: int, cantidad: int, core_ef: CoreEFHeaders) -> bool: ...
    def insert_outbox(self, corrida: dict[str, Any], cantidad: int, core_ef: CoreEFHeaders) -> None: ...
    def release_locks(self, op_id: Any) -> None: ...
    def commit(self) -> None: ...
    def mark_failed_new_transaction(self, corrida_id: int, core_ef: CoreEFHeaders, code: str, stage: str) -> None: ...


class AplicarIndexacionCuotasV2Service:
    def __init__(self, repository: AplicarIndexacionCuotasV2Repository) -> None:
        self.repository = repository

    def execute(self, command: AplicarIndexacionCuotasV2Command, core_ef: CoreEFHeaders) -> AppResult[dict[str, Any]]:
        if core_ef.if_match_version is None:
            return AppResult.fail("IF_MATCH_VERSION_REQUERIDO")
        if not command.hash_corrida:
            return AppResult.fail("HASH_CORRIDA_REQUERIDO")
        existing_by_op = self.repository.get_corrida_by_apply_op(core_ef.x_op_id)
        if existing_by_op is not None and existing_by_op["id_corrida_indexacion_financiera"] != command.id_corrida_indexacion_financiera:
            return AppResult.fail("IDEMPOTENCIA_OP_ID_EN_OTRA_CORRIDA")
        if existing_by_op is not None and existing_by_op["hash_corrida"] != command.hash_corrida:
            return AppResult.fail("IDEMPOTENCIA_PAYLOAD_INCOMPATIBLE")
        if existing_by_op is not None and existing_by_op["estado_corrida"] == "APLICADA":
            return AppResult.ok(self._response(existing_by_op, int(existing_by_op.get("cantidad_aplicada") or 0), idempotente=True))

        try:
            corrida = self.repository.get_corrida_for_update(command.id_corrida_indexacion_financiera)
            if corrida is None:
                return AppResult.fail("CORRIDA_INDEXACION_INEXISTENTE")
            if command.hash_corrida != corrida["hash_corrida"]:
                return AppResult.fail("HASH_CORRIDA_INVALIDO")
            if corrida.get("id_corrida_reemplazante") is not None:
                return AppResult.fail("CORRIDA_INDEXACION_REEMPLAZADA")

            detalles = self.repository.list_detalles_for_update(command.id_corrida_indexacion_financiera)
            hash_recomputado = self._recomputar_hash(corrida, detalles)
            if hash_recomputado != corrida["hash_corrida"]:
                return AppResult.fail("CORRIDA_HASH_PERSISTIDO_INCONSISTENTE")
            if corrida["estado_corrida"] == "APLICADA":
                return AppResult.ok(self._response(corrida, int(corrida.get("cantidad_aplicada") or 0), idempotente=True))
            if corrida["estado_corrida"] not in ESTADOS_APLICABLES:
                return AppResult.fail("CORRIDA_INDEXACION_NO_APLICABLE")
            if corrida["version_registro"] != core_ef.if_match_version:
                return AppResult.fail("VERSION_CORRIDA_INCOMPATIBLE")
            elegibles = [d for d in detalles if d["estado_elegibilidad"] == "ELEGIBLE"]
            if not elegibles:
                return AppResult.fail("CORRIDA_SIN_DETALLES_ELEGIBLES")

            cantidad = 0
            for detalle in elegibles:
                actual = self.repository.get_obligacion_actual_for_update(detalle["id_obligacion_financiera"])
                self._validar_detalle(corrida, detalle, actual)
                assert actual is not None
                if self.repository.get_lock_conflict(actual["uid_global"], core_ef.x_op_id) is not None:
                    raise AplicacionIndexacionError("LOCK_LOGICO_OCUPADO", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
                self.repository.acquire_lock(actual["uid_global"], core_ef)
                if not self.repository.update_obligacion(detalle, core_ef):
                    raise AplicacionIndexacionError("VERSION_OBLIGACION_INCOMPATIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
                ajuste_id = self.repository.upsert_ajuste(
                    detalle["id_obligacion_financiera"],
                    actual.get("id_composicion_ajuste_indexacion"),
                    actual.get("ajuste_version"),
                    detalle["ajuste_nuevo"],
                    core_ef,
                )
                ofi_id = self.repository.upsert_trazabilidad(detalle, corrida, actual, core_ef)
                version_final = self.repository.get_obligacion_version_actual_for_update(
                    detalle["id_obligacion_financiera"]
                )
                if version_final is None:
                    raise AplicacionIndexacionError(
                        "OBLIGACION_INDEXACION_INEXISTENTE",
                        mark_failed=True,
                        stage="MUTACION",
                    )
                self.repository.update_detalle_aplicado(
                    detalle["id_corrida_indexacion_financiera_detalle"],
                    version_final,
                    ajuste_id,
                    ofi_id,
                    core_ef,
                )
                cantidad += 1
            if not self.repository.update_corrida_aplicada(command.id_corrida_indexacion_financiera, core_ef.if_match_version, cantidad, core_ef):
                raise AplicacionIndexacionError("VERSION_CORRIDA_INCOMPATIBLE", mark_failed=True, stage="MUTACION")
            self.repository.insert_outbox(corrida, cantidad, core_ef)
            self.repository.release_locks(core_ef.x_op_id)
            self.repository.commit()
            return AppResult.ok(self._response(corrida, cantidad, idempotente=False))
        except AplicacionIndexacionError as exc:
            if exc.mark_failed:
                self.repository.mark_failed_new_transaction(command.id_corrida_indexacion_financiera, core_ef, exc.code, exc.stage)
            return AppResult.fail(exc.code)
        except RuntimeError as exc:
            code = str(exc)
            if code not in {"VERSION_AJUSTE_INDEXACION_INCOMPATIBLE", "TRAZABILIDAD_INDEXACION_INCOMPATIBLE"}:
                code = "ERROR_TRANSACCIONAL_INDEXACION"
            self.repository.mark_failed_new_transaction(command.id_corrida_indexacion_financiera, core_ef, code, "MUTACION")
            return AppResult.fail(code)
        except Exception:
            self.repository.mark_failed_new_transaction(command.id_corrida_indexacion_financiera, core_ef, "ERROR_TRANSACCIONAL_INDEXACION", "TRANSACCION_FUNCIONAL")
            return AppResult.fail("ERROR_TRANSACCIONAL_INDEXACION")


    def _recomputar_hash(self, corrida: dict[str, Any], detalles: list[dict[str, Any]]) -> str:
        if not detalles:
            raise AplicacionIndexacionError("CORRIDA_SIN_DETALLES_ELEGIBLES", mark_failed=False, stage="PREVALIDACION")
        first = detalles[0]
        return build_indexacion_cuotas_v2_hash(
            snapshot_alcance=dict(corrida.get("snapshot_alcance") or {}),
            valor_base_indice=_dec(first["valor_indice_base"]),
            valor_aplicado_indice=_dec(first["valor_indice_aplicado"]),
            coeficiente_indexacion=_dec(first["coeficiente_indexacion"]),
            detalles=detalles,
        )

    def _validar_matematica_detalle(self, detalle: dict[str, Any]) -> None:
        version = detalle.get("version_esperada")
        if version is None or int(version) <= 0:
            raise AplicacionIndexacionError("DETALLE_CORRIDA_INCONSISTENTE", mark_failed=False, stage="PREVALIDACION")
        capital = _dec(detalle["capital_base"]).quantize(Q2)
        ajuste_anterior = _dec(detalle["ajuste_anterior"]).quantize(Q2)
        ajuste_nuevo = _dec(detalle["ajuste_nuevo"]).quantize(Q2)
        diferencia = _dec(detalle["diferencia_neta"]).quantize(Q2)
        importe_anterior = _dec(detalle["importe_anterior"]).quantize(Q2)
        importe_nuevo = _dec(detalle["importe_nuevo"]).quantize(Q2)
        saldo_anterior = _dec(detalle["saldo_anterior"]).quantize(Q2)
        saldo_nuevo = _dec(detalle["saldo_nuevo"]).quantize(Q2)
        coeficiente = _dec(detalle["coeficiente_indexacion"])
        if (
            capital < 0
            or ajuste_anterior < 0
            or ajuste_nuevo < 0
            or importe_anterior < 0
            or importe_nuevo < 0
            or saldo_anterior < 0
            or saldo_nuevo < 0
            or coeficiente <= 0
        ):
            raise AplicacionIndexacionError("DETALLE_CORRIDA_INCONSISTENTE", mark_failed=False, stage="PREVALIDACION")
        if diferencia != (ajuste_nuevo - ajuste_anterior).quantize(Q2, rounding=ROUND_HALF_UP):
            raise AplicacionIndexacionError("DETALLE_CORRIDA_INCONSISTENTE", mark_failed=False, stage="PREVALIDACION")
        if importe_nuevo != (importe_anterior + diferencia).quantize(Q2, rounding=ROUND_HALF_UP):
            raise AplicacionIndexacionError("DETALLE_CORRIDA_INCONSISTENTE", mark_failed=False, stage="PREVALIDACION")
        if saldo_nuevo != (saldo_anterior + diferencia).quantize(Q2, rounding=ROUND_HALF_UP):
            raise AplicacionIndexacionError("DETALLE_CORRIDA_INCONSISTENTE", mark_failed=False, stage="PREVALIDACION")
        if not isinstance(detalle.get("snapshot_antes"), dict) or not isinstance(detalle.get("snapshot_despues"), dict):
            raise AplicacionIndexacionError("DETALLE_CORRIDA_INCONSISTENTE", mark_failed=False, stage="PREVALIDACION")

    def _validar_detalle(self, corrida: dict[str, Any], detalle: dict[str, Any], actual: dict[str, Any] | None) -> None:
        self._validar_matematica_detalle(detalle)
        if actual is None:
            raise AplicacionIndexacionError("OBLIGACION_INDEXACION_INEXISTENTE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if actual["estado_obligacion"] not in ESTADOS_OBLIGACION_ELEGIBLES:
            raise AplicacionIndexacionError("OBLIGACION_NO_ELEGIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if int(actual["version_registro"]) != int(detalle["version_esperada"]):
            raise AplicacionIndexacionError("VERSION_OBLIGACION_INCOMPATIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if actual.get("tiene_imputaciones") or actual.get("tiene_pagos"):
            raise AplicacionIndexacionError("OBLIGACION_CON_IMPUTACIONES_ACTIVAS", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if actual.get("tiene_punitorios"):
            raise AplicacionIndexacionError("OBLIGACION_CON_MORA_INCOMPATIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if actual.get("id_composicion_capital_venta") != detalle.get("id_composicion_capital_venta"):
            raise AplicacionIndexacionError("COMPOSICION_CAPITAL_INCOMPATIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if Decimal(str(actual.get("capital_base") or 0)) != Decimal(str(detalle["capital_base"])):
            raise AplicacionIndexacionError("CAPITAL_BASE_INCOMPATIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if Decimal(str(actual.get("ajuste_anterior") or 0)) != Decimal(str(detalle["ajuste_anterior"])):
            raise AplicacionIndexacionError("AJUSTE_INDEXACION_INCOMPATIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if Decimal(str(detalle["ajuste_nuevo"])) < 0 or Decimal(str(detalle["importe_nuevo"])) < 0 or Decimal(str(detalle["saldo_nuevo"])) < 0:
            raise AplicacionIndexacionError("AJUSTE_NEGATIVO_NO_SOPORTADO", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if actual.get("id_obligacion_financiera_indexacion") != detalle.get("id_obligacion_financiera_indexacion"):
            raise AplicacionIndexacionError("TRAZABILIDAD_INDEXACION_INCOMPATIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if actual.get("ofi_id_indice_financiero_valor") is not None and actual.get("ofi_id_indice_financiero_valor") != corrida.get("id_indice_financiero_valor_aplicado"):
            raise AplicacionIndexacionError("TRAZABILIDAD_INDEXACION_INCOMPATIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if actual.get("ofi_valor_aplicado_indice") is not None and Decimal(str(actual.get("ofi_valor_aplicado_indice"))) != Decimal(str(detalle["valor_indice_aplicado"])):
            raise AplicacionIndexacionError("TRAZABILIDAD_INDEXACION_INCOMPATIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")
        if actual.get("moneda") != "ARS":
            raise AplicacionIndexacionError("MONEDA_OBLIGACION_INCOMPATIBLE", mark_failed=True, stage="VALIDACION_TRANSACCIONAL")

    @staticmethod
    def _response(corrida: dict[str, Any], cantidad: int, *, idempotente: bool) -> dict[str, Any]:
        return {
            "modo": "IDEMPOTENTE" if idempotente else "APLICADA",
            "id_corrida_indexacion_financiera": corrida["id_corrida_indexacion_financiera"],
            "estado_corrida": "APLICADA",
            "cantidad_aplicada": cantidad,
            "hash_corrida": corrida["hash_corrida"],
            "idempotente": idempotente,
        }


class AplicacionIndexacionError(Exception):
    def __init__(self, code: str, *, mark_failed: bool = True, stage: str = "VALIDACION_APLICACION") -> None:
        self.code = code
        self.mark_failed = mark_failed
        self.stage = stage
        super().__init__(code)


def _dec(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))
