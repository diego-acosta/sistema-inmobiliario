from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol

from app.api.core_ef_headers import CoreEFHeaders
from app.application.common.results import AppResult

ESTADOS_APLICABLES = {"PREVISUALIZADA", "PENDIENTE_APLICACION"}
ESTADOS_OBLIGACION_ELEGIBLES = {"PROYECTADA", "EMITIDA", "EXIGIBLE", "VENCIDA"}


@dataclass(frozen=True, slots=True)
class AplicarIndexacionCuotasV2Command:
    id_corrida_indexacion_financiera: int
    hash_corrida: str | None = None


class AplicarIndexacionCuotasV2Repository(Protocol):
    def get_corrida_for_update(self, corrida_id: int) -> dict[str, Any] | None: ...
    def get_corrida_by_apply_op(self, op_id: Any) -> dict[str, Any] | None: ...
    def list_detalles_for_update(self, corrida_id: int) -> list[dict[str, Any]]: ...
    def get_obligacion_actual_for_update(self, obligacion_id: int) -> dict[str, Any] | None: ...
    def get_lock_conflict(self, uid_entidad: Any, op_id: Any) -> dict[str, Any] | None: ...
    def acquire_lock(self, uid_entidad: Any, core_ef: CoreEFHeaders) -> None: ...
    def release_locks(self, op_id: Any) -> None: ...
    def upsert_ajuste(self, obligacion_id: int, ajuste_id: int | None, importe: Any, core_ef: CoreEFHeaders) -> int: ...
    def upsert_trazabilidad(self, detalle: dict[str, Any], corrida: dict[str, Any], core_ef: CoreEFHeaders) -> int: ...
    def update_obligacion(self, detalle: dict[str, Any], core_ef: CoreEFHeaders) -> bool: ...
    def update_detalle_aplicado(self, detalle_id: int, version_resultante: int, ajuste_id: int, ofi_id: int, snapshot_despues: dict[str, Any], core_ef: CoreEFHeaders) -> None: ...
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
        existing_by_op = self.repository.get_corrida_by_apply_op(core_ef.x_op_id)
        if existing_by_op is not None and existing_by_op["id_corrida_indexacion_financiera"] != command.id_corrida_indexacion_financiera:
            return AppResult.fail("IDEMPOTENCIA_OP_ID_EN_OTRA_CORRIDA")
        if existing_by_op is not None and existing_by_op["estado_corrida"] == "APLICADA":
            return AppResult.ok(self._response(existing_by_op, 0, idempotente=True))

        try:
            corrida = self.repository.get_corrida_for_update(command.id_corrida_indexacion_financiera)
            if corrida is None:
                return AppResult.fail("CORRIDA_INDEXACION_INEXISTENTE")
            if command.hash_corrida is not None and command.hash_corrida != corrida["hash_corrida"]:
                return AppResult.fail("HASH_CORRIDA_INVALIDO")
            if corrida["version_registro"] != core_ef.if_match_version:
                return AppResult.fail("VERSION_CORRIDA_INCOMPATIBLE")
            if corrida["estado_corrida"] == "APLICADA":
                return AppResult.ok(self._response(corrida, int(corrida.get("cantidad_aplicada") or 0), idempotente=True))
            if corrida["estado_corrida"] not in ESTADOS_APLICABLES:
                return AppResult.fail("CORRIDA_INDEXACION_NO_APLICABLE")
            if corrida.get("id_corrida_reemplazante") is not None:
                return AppResult.fail("CORRIDA_INDEXACION_REEMPLAZADA")

            detalles = self.repository.list_detalles_for_update(command.id_corrida_indexacion_financiera)
            elegibles = [d for d in detalles if d["estado_elegibilidad"] == "ELEGIBLE"]
            if not elegibles:
                return AppResult.fail("CORRIDA_SIN_DETALLES_ELEGIBLES")

            cantidad = 0
            for detalle in elegibles:
                actual = self.repository.get_obligacion_actual_for_update(detalle["id_obligacion_financiera"])
                self._validar_detalle(corrida, detalle, actual)
                assert actual is not None
                if self.repository.get_lock_conflict(actual["uid_global"], core_ef.x_op_id) is not None:
                    raise AplicacionIndexacionError("LOCK_LOGICO_OCUPADO")
                self.repository.acquire_lock(actual["uid_global"], core_ef)
                if not self.repository.update_obligacion(detalle, core_ef):
                    raise AplicacionIndexacionError("VERSION_OBLIGACION_INCOMPATIBLE")
                ajuste_id = self.repository.upsert_ajuste(
                    detalle["id_obligacion_financiera"],
                    actual.get("id_composicion_ajuste_indexacion"),
                    detalle["ajuste_nuevo"],
                    core_ef,
                )
                ofi_id = self.repository.upsert_trazabilidad(detalle, corrida, core_ef)
                snapshot = dict(detalle.get("snapshot_despues") or {})
                snapshot.update({"aplicada": True, "id_composicion_ajuste_indexacion": ajuste_id, "id_obligacion_financiera_indexacion": ofi_id})
                self.repository.update_detalle_aplicado(
                    detalle["id_corrida_indexacion_financiera_detalle"],
                    int(detalle["version_esperada"]) + 1,
                    ajuste_id,
                    ofi_id,
                    snapshot,
                    core_ef,
                )
                cantidad += 1
            if not self.repository.update_corrida_aplicada(command.id_corrida_indexacion_financiera, core_ef.if_match_version, cantidad, core_ef):
                raise AplicacionIndexacionError("VERSION_CORRIDA_INCOMPATIBLE")
            self.repository.insert_outbox(corrida, cantidad, core_ef)
            self.repository.release_locks(core_ef.x_op_id)
            self.repository.commit()
            return AppResult.ok(self._response(corrida, cantidad, idempotente=False))
        except AplicacionIndexacionError as exc:
            self.repository.mark_failed_new_transaction(command.id_corrida_indexacion_financiera, core_ef, exc.code, "VALIDACION_APLICACION")
            return AppResult.fail(exc.code)
        except Exception:
            self.repository.mark_failed_new_transaction(command.id_corrida_indexacion_financiera, core_ef, "ERROR_TRANSACCIONAL_INDEXACION", "TRANSACCION_FUNCIONAL")
            return AppResult.fail("ERROR_TRANSACCIONAL_INDEXACION")

    def _validar_detalle(self, corrida: dict[str, Any], detalle: dict[str, Any], actual: dict[str, Any] | None) -> None:
        if actual is None:
            raise AplicacionIndexacionError("OBLIGACION_INDEXACION_INEXISTENTE")
        if actual["estado_obligacion"] not in ESTADOS_OBLIGACION_ELEGIBLES:
            raise AplicacionIndexacionError("OBLIGACION_NO_ELEGIBLE")
        if int(actual["version_registro"]) != int(detalle["version_esperada"]):
            raise AplicacionIndexacionError("VERSION_OBLIGACION_INCOMPATIBLE")
        if actual.get("tiene_imputaciones") or actual.get("tiene_pagos"):
            raise AplicacionIndexacionError("OBLIGACION_CON_IMPUTACIONES_ACTIVAS")
        if actual.get("tiene_punitorios"):
            raise AplicacionIndexacionError("OBLIGACION_CON_MORA_INCOMPATIBLE")
        if actual.get("id_composicion_capital_venta") != detalle.get("id_composicion_capital_venta"):
            raise AplicacionIndexacionError("COMPOSICION_CAPITAL_INCOMPATIBLE")
        if Decimal(str(actual.get("capital_base") or 0)) != Decimal(str(detalle["capital_base"])):
            raise AplicacionIndexacionError("CAPITAL_BASE_INCOMPATIBLE")
        if Decimal(str(actual.get("ajuste_anterior") or 0)) != Decimal(str(detalle["ajuste_anterior"])):
            raise AplicacionIndexacionError("AJUSTE_INDEXACION_INCOMPATIBLE")
        if Decimal(str(detalle["ajuste_nuevo"])) < 0 or Decimal(str(detalle["importe_nuevo"])) < 0 or Decimal(str(detalle["saldo_nuevo"])) < 0:
            raise AplicacionIndexacionError("AJUSTE_NEGATIVO_NO_SOPORTADO")
        if actual.get("moneda") != "ARS":
            raise AplicacionIndexacionError("MONEDA_OBLIGACION_INCOMPATIBLE")

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
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)
