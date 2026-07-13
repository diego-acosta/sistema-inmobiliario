from datetime import date
from decimal import Decimal
from uuid import UUID

from app.api.core_ef_headers import CoreEFHeaders
from app.application.financiero.services.preview_indexacion_cuotas_v2_service import (
    PreviewIndexacionCuotasV2Command,
    PreviewIndexacionCuotasV2Service,
)


class Repo:
    def __init__(self):
        self.created = []
        self.existing = None
        self.rows = [
            {
                "id_obligacion_financiera": 10,
                "version_registro": 1,
                "estado_obligacion": "EMITIDA",
                "importe_total": Decimal("1000.00"),
                "saldo_pendiente": Decimal("1000.00"),
                "capital_base": Decimal("1000.00"),
                "ajuste_anterior": Decimal("0.00"),
                "id_composicion_capital_venta": 20,
                "id_composicion_ajuste_indexacion": None,
                "id_obligacion_financiera_indexacion": None,
                "tiene_imputaciones": False,
                "tiene_pagos": False,
                "tiene_mora": False,
                "tiene_punitorios": False,
                "tiene_recibos": False,
            }
        ]

    def get_scope(self, command):
        return {
            "fecha_base_indice": date(2026, 1, 1),
            "valor_base_indice": Decimal("100.00000000"),
        }

    def get_valor_indice(self, id_valor):
        return {"id_indice_financiero": 1, "valor_indice": Decimal("125.00000000"), "fecha_publicacion": date(2026, 2, 1)}

    def list_obligaciones_bloque(self, id_bloque, fecha_corte):
        return list(self.rows)

    def get_corrida_by_op_id(self, op_id):
        return self.existing

    def create_corrida_preview(self, payload, detalles):
        self.created.append((payload, detalles))
        return {"id_corrida_indexacion_financiera": 99}


def cmd(**kw):
    data = dict(
        id_plan_pago_venta=1,
        id_plan_pago_venta_bloque=2,
        id_plan_pago_venta_bloque_indexacion=3,
        id_indice_financiero=1,
        id_indice_financiero_valor_aplicado=4,
        fecha_corte=date(2026, 2, 28),
        periodo_aplicado=date(2026, 2, 1),
    )
    data.update(kw)
    return PreviewIndexacionCuotasV2Command(**data)


def test_preview_efimero_calcula_coeficiente_ajustes_y_hash_estable():
    repo = Repo()
    service = PreviewIndexacionCuotasV2Service(repo)
    r1 = service.execute(cmd())
    r2 = service.execute(cmd())
    assert r1.success
    assert r1.data["coeficiente_indexacion"] == Decimal("1.25000000")
    det = r1.data["detalles"][0]
    assert det["ajuste_nuevo"] == Decimal("250.00")
    assert det["snapshot_antes"]["estado_obligacion"] == "EMITIDA"
    assert det["diferencia_neta"] == Decimal("250.00")
    assert det["importe_nuevo"] == Decimal("1250.00")
    assert det["saldo_nuevo"] == Decimal("1250.00")
    assert r1.data["hash_corrida"] == r2.data["hash_corrida"]
    assert repo.created == []


def test_hash_cambia_con_version():
    repo = Repo()
    service = PreviewIndexacionCuotasV2Service(repo)
    original = service.execute(cmd()).data["hash_corrida"]
    repo.rows[0]["version_registro"] = 2
    changed = service.execute(cmd()).data["hash_corrida"]
    assert original != changed


def test_ajuste_negativo_excluye_obligacion():
    repo = Repo()
    repo.get_valor_indice = lambda id_valor: {"id_indice_financiero": 1, "valor_indice": Decimal("80.00000000"), "fecha_publicacion": None}
    result = PreviewIndexacionCuotasV2Service(repo).execute(cmd())
    det = result.data["detalles"][0]
    assert det["estado_elegibilidad"] == "EXCLUIDA"
    assert det["motivo_exclusion"] == "AJUSTE_NEGATIVO_NO_SOPORTADO"
    assert det["ajuste_nuevo"] == Decimal("0.00")
    assert det["snapshot_despues"]["ajuste_objetivo_calculado"] == "-200.00"


def test_preview_persistido_requiere_headers_y_persiste():
    repo = Repo()
    service = PreviewIndexacionCuotasV2Service(repo)
    assert not service.execute(cmd(persistir=True)).success
    result = service.execute(
        cmd(persistir=True),
        CoreEFHeaders(
            x_op_id=UUID("550e8400-e29b-41d4-a716-446655440000"),
            x_usuario_id=1,
            x_sucursal_id=1,
            x_instalacion_id=1,
        ),
    )
    assert result.success
    assert result.data["modo"] == "PERSISTIDA"
    assert result.data["id_corrida_indexacion_financiera"] == 99
    assert repo.created[0][0]["estado_corrida"] == "PREVISUALIZADA"
