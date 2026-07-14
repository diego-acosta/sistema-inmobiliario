from datetime import date
from uuid import UUID

from app.api.core_ef_headers import CoreEFHeaders
from app.application.common.results import AppResult
from app.application.financiero.services.preparar_corridas_indexacion_cuotas_v2_service import (
    PrepararCorridasIndexacionCuotasV2Command,
    PrepararCorridasIndexacionCuotasV2Service,
    _fin_de_mes,
    _inicio_de_mes,
)
from sqlalchemy.exc import IntegrityError


class Repo:
    def __init__(self):
        self.existing = None
        self.fecha_corte_recibida = None
        self.fecha_valor_original_recibida = None
        self.rolled_back = False
        self.conflicto = False
    def get_valor_publicado(self, id_valor):
        if id_valor == 404:
            return None
        return {"id_indice_financiero": 1, "fecha_valor": date(2026, 7, 15)}
    def list_configuraciones_alcanzadas(self, id_indice_financiero, fecha_valor_original, fecha_corte):
        self.fecha_corte_recibida = fecha_corte
        self.fecha_valor_original_recibida = fecha_valor_original
        return [
            {"id_plan_pago_venta": 10, "id_plan_pago_venta_bloque": 20, "id_plan_pago_venta_bloque_indexacion": 30},
            {"id_plan_pago_venta": 11, "id_plan_pago_venta_bloque": 21, "id_plan_pago_venta_bloque_indexacion": 31},
        ]
    def get_corrida_existente(self, **kwargs):
        if self.existing is not None:
            return self.existing
        if kwargs["id_plan_pago_venta"] == 11:
            return {"id_corrida_indexacion_financiera": 99, "id_indice_financiero_valor_aplicado": 123, "hash_corrida": "h", "estado_corrida": "APLICADA", "cantidad_analizada": 2, "cantidad_elegible": 2}
        return None
    def rollback(self):
        self.rolled_back = True
    def is_conflicto_unico_publicacion(self, exc):
        return self.conflicto


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
    assert repo.fecha_valor_original_recibida == date(2026, 7, 15)
    assert result.data["periodo_aplicado"] == date(2026, 7, 1)
    assert result.data["cantidad_requiere_correccion"] == 0


def test_preparar_corridas_valor_no_publicado_o_inexistente_aborta():
    result = PrepararCorridasIndexacionCuotasV2Service(Repo(), Preview()).execute(
        PrepararCorridasIndexacionCuotasV2Command(404), _core()
    )
    assert not result.success
    assert result.errors == ["VALOR_INDICE_PUBLICADO_INEXISTENTE"]


def test_helpers_mensuales_dia_uno_intermedio_y_diciembre():
    assert _inicio_de_mes(date(2026, 6, 1)) == date(2026, 6, 1)
    assert _inicio_de_mes(date(2026, 6, 15)) == date(2026, 6, 1)
    assert _fin_de_mes(date(2026, 6, 15)) == date(2026, 6, 30)
    assert _fin_de_mes(date(2026, 12, 7)) == date(2026, 12, 31)


def test_corrida_existente_con_otro_valor_requiere_correccion():
    repo = Repo()
    repo.existing = {"id_corrida_indexacion_financiera": 90, "id_indice_financiero_valor_aplicado": 122, "hash_corrida": "original", "estado_corrida": "PREVISUALIZADA", "cantidad_analizada": 2, "cantidad_elegible": 1}
    preview = Preview()
    result = PrepararCorridasIndexacionCuotasV2Service(repo, preview).execute(PrepararCorridasIndexacionCuotasV2Command(123), _core())
    assert result.data["cantidad_requiere_correccion"] == 2
    assert result.data["cantidad_corridas_existentes"] == 0
    assert {r["resultado"] for r in result.data["resultados"]} == {"REQUIERE_CORRECCION"}
    assert result.data["resultados"][0]["error"] == "PERIODO_ORDINARIO_YA_PREPARADO_CON_OTRO_VALOR"
    assert result.data["resultados"][0]["id_indice_financiero_valor_solicitado"] == 123
    assert result.data["resultados"][0]["id_indice_financiero_valor_existente"] == 122
    assert preview.commands == []


def test_corrida_existente_con_dia_intermedio_del_mismo_mes_se_clasifica_sin_preview():
    for id_valor_existente, resultado_esperado in ((123, "EXISTENTE"), (122, "REQUIERE_CORRECCION")):
        repo = Repo()
        repo.existing = {
            "id_corrida_indexacion_financiera": 93,
            "id_indice_financiero_valor_aplicado": id_valor_existente,
            "periodo_aplicado": date(2026, 7, 15),
            "fecha_corte": date(2026, 7, 31),
            "hash_corrida": "historica-dia-15",
            "estado_corrida": "PREVISUALIZADA",
            "cantidad_analizada": 1,
            "cantidad_elegible": 1,
        }
        preview = Preview()
        result = PrepararCorridasIndexacionCuotasV2Service(repo, preview).execute(
            PrepararCorridasIndexacionCuotasV2Command(123), _core()
        )
        assert result.data["periodo_aplicado"] == date(2026, 7, 1)
        assert {r["resultado"] for r in result.data["resultados"]} == {resultado_esperado}
        assert result.data["cantidad_corridas_creadas"] == 0
        assert preview.commands == []


class PreviewConIntegrityError:
    def execute(self, command, core_ef):
        raise IntegrityError("insert", {}, Exception("duplicate"))


def test_conflicto_concurrente_recarga_mismo_valor():
    repo = Repo()
    calls = 0
    existente = {"id_corrida_indexacion_financiera": 91, "id_indice_financiero_valor_aplicado": 123, "hash_corrida": "ganadora", "estado_corrida": "PREVISUALIZADA", "cantidad_analizada": 1, "cantidad_elegible": 1}
    original = repo.get_corrida_existente
    def get_corrida_existente(**kwargs):
        nonlocal calls
        calls += 1
        return None if calls == 1 else existente
    repo.get_corrida_existente = get_corrida_existente
    repo.conflicto = True
    result = PrepararCorridasIndexacionCuotasV2Service(repo, PreviewConIntegrityError()).execute(PrepararCorridasIndexacionCuotasV2Command(123), _core())
    assert result.data["resultados"][0]["resultado"] == "EXISTENTE"
    assert repo.rolled_back is True


def test_conflicto_concurrente_recarga_otro_valor_y_requiere_correccion():
    repo = Repo()
    calls = 0
    existente = {"id_corrida_indexacion_financiera": 92, "id_indice_financiero_valor_aplicado": 122, "hash_corrida": "ganadora-otra", "estado_corrida": "PREVISUALIZADA", "cantidad_analizada": 1, "cantidad_elegible": 1}
    def get_corrida_existente(**kwargs):
        nonlocal calls
        calls += 1
        return None if calls == 1 else existente
    repo.get_corrida_existente = get_corrida_existente
    repo.conflicto = True
    result = PrepararCorridasIndexacionCuotasV2Service(repo, PreviewConIntegrityError()).execute(PrepararCorridasIndexacionCuotasV2Command(123), _core())
    assert result.data["resultados"][0]["resultado"] == "REQUIERE_CORRECCION"
    assert result.data["cantidad_requiere_correccion"] == 2
    assert result.data["resultados"][0]["id_indice_financiero_valor_existente"] == 122


def test_integrity_error_ajeno_se_reporta_por_grupo_y_conserva_orden():
    repo = Repo()
    result = PrepararCorridasIndexacionCuotasV2Service(repo, PreviewConIntegrityError()).execute(PrepararCorridasIndexacionCuotasV2Command(123), _core())
    assert [r["id_plan_pago_venta"] for r in result.data["resultados"]] == [10, 11]
    assert result.data["resultados"][0]["error"] == "ERROR_INTEGRIDAD_PREPARACION_CORRIDA"
    assert result.data["cantidad_errores"] == 1
