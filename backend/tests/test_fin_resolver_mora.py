"""
Tests para el resolver centralizado de parámetros de mora.
Verifica prioridad: origen > concepto > default global.
"""
import pytest
from decimal import Decimal

from app.domain.financiero.parametros_mora import (
    DIAS_GRACIA_MORA_DEFAULT,
    TASA_DIARIA_MORA_DEFAULT,
)
from app.domain.financiero.resolver_mora import ResolucionMora, resolver_mora_params

from tests.test_disponibilidades_create import HEADERS
from tests.test_fin_event_contrato_alquiler import (
    _activar,
    _crear_condicion,
    _crear_contrato_borrador,
    _crear_locatario_principal,
)

# ── reglas de prueba ──────────────────────────────────────────────────────────

_TASA_CONCEPTO = Decimal("0.002")
_TASA_ORIGEN = Decimal("0.003")
_DIAS_CONCEPTO = 3
_DIAS_ORIGEN = 0

_REGLA_CONCEPTO = ResolucionMora(tasa_diaria=_TASA_CONCEPTO, dias_gracia=_DIAS_CONCEPTO)
_REGLA_ORIGEN = ResolucionMora(tasa_diaria=_TASA_ORIGEN, dias_gracia=_DIAS_ORIGEN)

_REGLAS = {
    "CANON_LOCATIVO": _REGLA_CONCEPTO,
    "CONTRATO_ALQUILER:999": _REGLA_ORIGEN,
}


# ── unit tests: resolver_mora_params ─────────────────────────────────────────

def test_sin_regla_usa_default() -> None:
    """Sin reglas ni contexto → devuelve tasa y días de gracia globales."""
    r = resolver_mora_params()
    assert r.tasa_diaria == TASA_DIARIA_MORA_DEFAULT
    assert r.dias_gracia == DIAS_GRACIA_MORA_DEFAULT


def test_sin_contexto_usa_default_aunque_haya_reglas() -> None:
    """Con reglas pero sin contexto → no puede matchear → devuelve default."""
    r = resolver_mora_params(reglas=_REGLAS)
    assert r.tasa_diaria == TASA_DIARIA_MORA_DEFAULT


def test_regla_por_concepto_overridea_default() -> None:
    """codigo_concepto presente en reglas → usa regla de concepto."""
    r = resolver_mora_params(codigo_concepto="CANON_LOCATIVO", reglas=_REGLAS)
    assert r.tasa_diaria == _TASA_CONCEPTO
    assert r.dias_gracia == _DIAS_CONCEPTO


def test_regla_por_origen_overridea_concepto() -> None:
    """origen presente en reglas Y concepto presente → origen tiene prioridad."""
    r = resolver_mora_params(
        tipo_origen="CONTRATO_ALQUILER",
        id_origen=999,
        codigo_concepto="CANON_LOCATIVO",
        reglas=_REGLAS,
    )
    assert r.tasa_diaria == _TASA_ORIGEN
    assert r.dias_gracia == _DIAS_ORIGEN


def test_origen_sin_regla_cae_a_concepto() -> None:
    """Origen no tiene regla específica pero concepto sí → usa concepto."""
    r = resolver_mora_params(
        tipo_origen="CONTRATO_ALQUILER",
        id_origen=1,  # no tiene regla
        codigo_concepto="CANON_LOCATIVO",
        reglas=_REGLAS,
    )
    assert r.tasa_diaria == _TASA_CONCEPTO


def test_origen_sin_regla_y_concepto_sin_regla_usa_default() -> None:
    """Ni origen ni concepto tienen regla → default."""
    r = resolver_mora_params(
        tipo_origen="VENTA",
        id_origen=1,
        codigo_concepto="CAPITAL_VENTA",
        reglas=_REGLAS,
    )
    assert r.tasa_diaria == TASA_DIARIA_MORA_DEFAULT


def test_resolucion_mora_es_inmutable() -> None:
    """ResolucionMora es frozen dataclass — no modificable."""
    r = resolver_mora_params()
    with pytest.raises((AttributeError, TypeError)):
        r.tasa_diaria = Decimal("0.999")  # type: ignore[misc]


# ── unit tests: cálculo con ResolucionMora personalizada ─────────────────────

def test_calcular_mora_con_resolucion_custom() -> None:
    """
    Verificar que pasar una ResolucionMora custom a _calcular_mora_dinamica
    produce el resultado esperado con esa tasa.
    """
    from datetime import date
    from app.infrastructure.persistence.repositories.financiero_repository import (
        _calcular_mora_dinamica,
    )

    resolucion_custom = ResolucionMora(tasa_diaria=Decimal("0.002"), dias_gracia=0)
    resultado = _calcular_mora_dinamica(
        saldo_pendiente=10000,
        fecha_vencimiento=date(2026, 5, 1),
        fecha_corte=date(2026, 5, 11),  # 10 días
        resolucion=resolucion_custom,
    )

    # mora = 10000 * 0.002 * 10 = 200
    assert resultado["mora_calculada"] == pytest.approx(200.00)
    assert resultado["tasa_diaria_mora"] == pytest.approx(0.002)
    assert resultado["dias_atraso"] == 10


def test_calcular_mora_sin_resolucion_usa_default() -> None:
    """Sin resolucion → usa default."""
    from datetime import date
    from app.infrastructure.persistence.repositories.financiero_repository import (
        _calcular_mora_dinamica,
    )

    resultado = _calcular_mora_dinamica(
        saldo_pendiente=10000,
        fecha_vencimiento=date(2026, 5, 1),
        fecha_corte=date(2026, 5, 11),  # 10 días, pero hay 5 de gracia
        # dias_atraso_efectivos = 10 - 5 = 5
    )

    assert resultado["tasa_diaria_mora"] == pytest.approx(float(TASA_DIARIA_MORA_DEFAULT))
    # mora = 10000 * 0.001 * 5 = 50 (10 días - 5 días gracia)
    assert resultado["mora_calculada"] == pytest.approx(50.00)
    assert resultado["dias_atraso"] == 5


# ── integración: todos los endpoints usan la resolución global por defecto ────

def test_estado_cuenta_persona_usa_tasa_default(client, db_session) -> None:
    """
    El endpoint estado-cuenta devuelve tasa_diaria_mora = TASA_DIARIA_MORA_DEFAULT.
    Verifica que el resolver está en el camino de la consulta.
    Obligación con vencimiento 2026-05-15, fecha_corte=2026-05-25 (10d - 5 gracia = 5d mora).
    mora = saldo * TASA_DIARIA_MORA_DEFAULT * 5
    """
    contrato = _crear_contrato_borrador(
        client, codigo="RESOL-EC-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        dia_vencimiento_canon=15,
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 10000.00, "2026-05-01")
    id_persona = _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    resp = client.get(
        f"/api/v1/financiero/personas/{id_persona}/estado-cuenta",
        headers=HEADERS,
        params={"fecha_corte": "2026-05-25"},
    )

    assert resp.status_code == 200
    ob = resp.json()["data"]["obligaciones"][0]
    assert ob["tasa_diaria_mora"] == pytest.approx(float(TASA_DIARIA_MORA_DEFAULT))
    assert ob["dias_atraso"] == 5
    mora_esperada = 10000 * float(TASA_DIARIA_MORA_DEFAULT) * 5
    assert ob["mora_calculada"] == pytest.approx(mora_esperada)


def test_simular_pago_usa_tasa_default(client, db_session) -> None:
    """
    El endpoint simular-pago usa la tasa del resolver para punitorio simulado.
    En pago/simulacion, dias_gracia es umbral: superada la gracia, calcula
    desde fecha_vencimiento. Del 2026-05-15 al 2026-05-25 son 10 dias.
    """
    contrato = _crear_contrato_borrador(
        client, codigo="RESOL-SIM-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
        dia_vencimiento_canon=15,
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 10000.00, "2026-05-01")
    id_persona = _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    resp = client.post(
        f"/api/v1/financiero/personas/{id_persona}/simular-pago",
        headers=HEADERS,
        json={"monto": 99999.00, "fecha_corte": "2026-05-25"},
    )

    assert resp.status_code == 200
    ob = resp.json()["data"]["detalle"][0]
    mora_esperada = 10000 * float(TASA_DIARIA_MORA_DEFAULT) * 10
    assert ob["mora_calculada"] == pytest.approx(mora_esperada)
