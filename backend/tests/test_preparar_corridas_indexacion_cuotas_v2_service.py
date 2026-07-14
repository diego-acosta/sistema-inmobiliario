from datetime import date
from uuid import UUID

from app.api.core_ef_headers import CoreEFHeaders
from app.application.common.results import AppResult
from app.application.financiero.services.preparar_corridas_indexacion_cuotas_v2_service import (
    PrepararCorridasIndexacionCuotasV2Command,
    PrepararCorridasIndexacionCuotasV2Service,
)


class Repo:
    def __init__(self):
        self.existing = None
        self.fecha_corte_recibida = None
    def get_valor_publicado(self, id_valor):
        if id_valor == 404:
            return None
        return {"id_indice_financiero": 1, "fecha_valor": date(2026, 7, 1)}
    def list_configuraciones_alcanzadas(self, id_indice_financiero, periodo_aplicado, fecha_corte):
        self.fecha_corte_recibida = fecha_corte
        return [
            {"id_plan_pago_venta": 10, "id_plan_pago_venta_bloque": 20, "id_plan_pago_venta_bloque_indexacion": 30},
            {"id_plan_pago_venta": 11, "id_plan_pago_venta_bloque": 21, "id_plan_pago_venta_bloque_indexacion": 31},
        ]
    def get_corrida_existente(self, **kwargs):
        if kwargs["id_plan_pago_venta"] == 11:
            return {"id_corrida_indexacion_financiera": 99, "hash_corrida": "h", "estado_corrida": "APLICADA", "cantidad_analizada": 2, "cantidad_elegible": 2}
        return None
    def rollback(self):
        self.rolled_back = True
    def is_conflicto_unico_publicacion(self, exc):
        return getattr(exc, "is_publicacion", False)


class Preview:
    def __init__(self):
        self.commands = []
    def execute(self, command, core_ef):
        self.commands.append((command, core_ef))
        return AppResult.ok({
            "id_corrida_indexacion_financiera": 88,
            "hash_corrida": "hash",
            "resumen": {"cantidad_analizada": 3, "cantidad_elegible": 3},
        })


def _core():
    return CoreEFHeaders(UUID("550e8400-e29b-41d4-a716-446655440000"), 1, 1, 1)


def test_preparar_corridas_crea_y_reusa_existente():
    preview = Preview()
    repo = Repo()
    result = PrepararCorridasIndexacionCuotasV2Service(repo, preview).execute(
        PrepararCorridasIndexacionCuotasV2Command(123), _core()
    )
    assert result.success
    assert result.data["cantidad_configuraciones_analizadas"] == 2
    assert result.data["cantidad_corridas_creadas"] == 1
    assert result.data["cantidad_corridas_existentes"] == 1
    assert result.data["resultados"][0]["resultado"] == "CREADA"
    assert result.data["resultados"][1]["resultado"] == "EXISTENTE"
    assert preview.commands[0][0].origen_corrida == "PUBLICACION_INDICE"
    assert preview.commands[0][0].persistir is True
    assert preview.commands[0][0].fecha_corte == date(2026, 7, 31)
    assert repo.fecha_corte_recibida == date(2026, 7, 31)


def test_preparar_corridas_valor_no_publicado_o_inexistente_aborta():
    result = PrepararCorridasIndexacionCuotasV2Service(Repo(), Preview()).execute(
        PrepararCorridasIndexacionCuotasV2Command(404), _core()
    )
    assert not result.success
    assert result.errors == ["VALOR_INDICE_PUBLICADO_INEXISTENTE"]
