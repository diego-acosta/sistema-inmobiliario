from unittest.mock import Mock
from uuid import UUID

from app.api.core_ef_headers import CoreEFHeaders
from app.application.financiero.services.aplicar_indexacion_cuotas_v2_service import (
    AplicarIndexacionCuotasV2Command,
    AplicarIndexacionCuotasV2Service,
)


CORE = CoreEFHeaders(UUID("550e8400-e29b-41d4-a716-446655441101"), 1, 1, 1, 1)


def _corrida():
    return {
        "id_corrida_indexacion_financiera": 7,
        "hash_corrida": "a" * 64,
        "estado_corrida": "PREVISUALIZADA",
        "version_registro": 1,
        "id_indice_financiero_valor_aplicado": 1,
        "periodo_aplicado": "2026-07-01",
        "periodo_base": "2026-01-01",
    }


def _detalle():
    return {
        "id_corrida_indexacion_financiera_detalle": 11,
        "id_obligacion_financiera": 12,
        "id_composicion_capital_venta": 2,
        "id_composicion_ajuste_indexacion": 3,
        "id_obligacion_financiera_indexacion": 4,
        "version_esperada": 4,
        "capital_base": 100,
        "valor_indice_base": 100,
        "valor_indice_aplicado": 125,
        "coeficiente_indexacion": "1.25",
        "ajuste_anterior": 25,
        "ajuste_nuevo": 25,
        "diferencia_neta": 0,
        "importe_anterior": 125,
        "importe_nuevo": 125,
        "saldo_anterior": 125,
        "saldo_nuevo": 125,
        "estado_elegibilidad": "ELEGIBLE",
        "snapshot_antes": {},
        "snapshot_despues": {},
    }


def _actual():
    return {
        "uid_global": "uid-12",
        "estado_obligacion": "PROYECTADA",
        "version_registro": 4,
        "id_composicion_capital_venta": 2,
        "capital_base": 100,
        "ajuste_anterior": 25,
        "id_obligacion_financiera_indexacion": 4,
        "ofi_id_indice_financiero_valor": 1,
        "ofi_valor_aplicado_indice": 125,
        "moneda": "ARS",
        "ajuste_version": 1,
        "ofi_version_registro": 1,
    }


def _repository():
    repo = Mock()
    corrida, detalle, actual = _corrida(), _detalle(), _actual()
    repo.get_corrida_by_apply_op.return_value = None
    repo.get_corrida_for_update.return_value = corrida
    repo.list_detalles_for_update.return_value = [detalle]
    repo.get_obligacion_actual_for_update.return_value = actual
    repo.get_lock_conflict.return_value = None
    repo.update_obligacion.return_value = True
    repo.upsert_ajuste.return_value = 3
    repo.upsert_trazabilidad.return_value = 4
    repo.get_obligacion_version_actual_for_update.return_value = 6
    repo.update_corrida_aplicada.return_value = True
    return repo


def _service(repo):
    service = AplicarIndexacionCuotasV2Service(repo)
    service._recomputar_hash = Mock(return_value="a" * 64)
    return service


def test_usa_version_final_releida_y_respeta_orden_de_mutaciones():
    repo = _repository()
    result = _service(repo).execute(AplicarIndexacionCuotasV2Command(7, "a" * 64), CORE)

    assert result.success
    repo.update_detalle_aplicado.assert_called_once_with(11, 6, 3, 4, CORE)
    calls = [call[0] for call in repo.method_calls]
    assert calls.index("update_obligacion") < calls.index("upsert_ajuste")
    assert calls.index("upsert_ajuste") < calls.index("upsert_trazabilidad")
    assert calls.index("upsert_trazabilidad") < calls.index("get_obligacion_version_actual_for_update")
    assert calls.index("get_obligacion_version_actual_for_update") < calls.index("update_detalle_aplicado")


def test_falla_si_la_obligacion_desaparece_al_releer_version_final():
    repo = _repository()
    repo.get_obligacion_version_actual_for_update.return_value = None

    result = _service(repo).execute(AplicarIndexacionCuotasV2Command(7, "a" * 64), CORE)

    assert not result.success
    assert result.errors == ["OBLIGACION_INDEXACION_INEXISTENTE"]
    repo.update_detalle_aplicado.assert_not_called()
    repo.mark_failed_new_transaction.assert_called_once_with(7, CORE, "OBLIGACION_INDEXACION_INEXISTENTE", "MUTACION")


def test_error_al_releer_version_final_revierte_y_marca_fallida():
    repo = _repository()
    repo.get_obligacion_version_actual_for_update.side_effect = RuntimeError("db unavailable")

    result = _service(repo).execute(AplicarIndexacionCuotasV2Command(7, "a" * 64), CORE)

    assert not result.success
    assert result.errors == ["ERROR_TRANSACCIONAL_INDEXACION"]
    repo.update_detalle_aplicado.assert_not_called()
    repo.mark_failed_new_transaction.assert_called_once_with(7, CORE, "ERROR_TRANSACCIONAL_INDEXACION", "MUTACION")


def test_replay_idempotente_no_relee_ni_muta_version_final():
    repo = _repository()
    applied = {**_corrida(), "estado_corrida": "APLICADA", "cantidad_aplicada": 1}
    repo.get_corrida_by_apply_op.return_value = applied

    result = _service(repo).execute(AplicarIndexacionCuotasV2Command(7, "a" * 64), CORE)

    assert result.success
    assert result.data["idempotente"] is True
    repo.get_obligacion_version_actual_for_update.assert_not_called()
    repo.update_obligacion.assert_not_called()
    repo.update_detalle_aplicado.assert_not_called()
