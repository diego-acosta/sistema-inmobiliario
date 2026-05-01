"""
Tests de integración para generación de cronograma locativo mensual.
La activación del contrato dispara HandleContratoAlquilerActivadoEventService,
que crea N obligaciones_financieras (una por período mensual) con CANON_LOCATIVO.
"""
from datetime import date

import pytest
from sqlalchemy import text

from app.application.common.commands import CommandContext
from app.application.financiero.services.handle_contrato_alquiler_activado_event_service import (
    HandleContratoAlquilerActivadoEventService,
    generate_monthly_periods,
    get_condicion_vigente_para_periodo,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from app.infrastructure.persistence.repositories.locativo_repository import (
    LocativoRepository,
)
from tests.test_contratos_alquiler_create import _payload_base
from tests.test_disponibilidades_create import HEADERS
from tests.test_reservas_venta_create import _crear_inmueble

URL_CONTRATOS = "/api/v1/contratos-alquiler"
URL_ACTIVAR = "/api/v1/contratos-alquiler/{id}/activar"
URL_CONDICIONES = "/api/v1/contratos-alquiler/{id}/condiciones-economicas-alquiler"


# ── helpers ───────────────────────────────────────────────────────────────────

def _crear_contrato_borrador(client, *, codigo: str, fecha_inicio: str, fecha_fin: str) -> dict:
    id_inmueble = _crear_inmueble(client, codigo=f"INM-{codigo}")
    response = client.post(
        URL_CONTRATOS,
        headers=HEADERS,
        json=_payload_base(
            codigo_contrato=codigo,
            objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
        ),
    )
    assert response.status_code == 201
    return response.json()["data"]


def _crear_condicion(
    client,
    id_contrato: int,
    monto: float,
    fecha_desde: str,
    *,
    moneda: str = "ARS",
    fecha_hasta: str | None = None,
) -> dict:
    response = client.post(
        URL_CONDICIONES.format(id=id_contrato),
        headers=HEADERS,
        json={
            "monto_base": monto,
            "moneda": moneda,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "periodicidad": None,
            "observaciones": None,
        },
    )
    assert response.status_code == 201
    return response.json()["data"]


def _activar(client, id_contrato: int, version: int) -> dict:
    response = client.patch(
        URL_ACTIVAR.format(id=id_contrato),
        headers={**HEADERS, "If-Match-Version": str(version)},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _get_obligaciones_de_relacion(db_session, id_relacion_generadora: int) -> list:
    rows = db_session.execute(
        text(
            """
            SELECT
                id_obligacion_financiera,
                periodo_desde,
                periodo_hasta,
                importe_total,
                estado_obligacion
            FROM obligacion_financiera
            WHERE id_relacion_generadora = :id
              AND deleted_at IS NULL
            ORDER BY periodo_desde ASC
            """
        ),
        {"id": id_relacion_generadora},
    ).mappings().all()
    return [dict(r) for r in rows]


def _get_relacion_for_contrato(db_session, id_contrato_alquiler: int) -> int:
    row = db_session.execute(
        text(
            """
            SELECT id_relacion_generadora
            FROM relacion_generadora
            WHERE tipo_origen = 'contrato_alquiler'
              AND id_origen = :id
              AND deleted_at IS NULL
            ORDER BY id_relacion_generadora DESC
            LIMIT 1
            """
        ),
        {"id": id_contrato_alquiler},
    ).mappings().one()
    return row["id_relacion_generadora"]


# ── unit tests: generate_monthly_periods ─────────────────────────────────────

def test_generate_monthly_periods_3_meses_completos() -> None:
    periods = generate_monthly_periods(date(2026, 5, 1), date(2026, 7, 31))
    assert len(periods) == 3
    assert periods[0] == (date(2026, 5, 1), date(2026, 5, 31))
    assert periods[1] == (date(2026, 6, 1), date(2026, 6, 30))
    assert periods[2] == (date(2026, 7, 1), date(2026, 7, 31))


def test_generate_monthly_periods_ultimo_periodo_cortado() -> None:
    periods = generate_monthly_periods(date(2026, 5, 1), date(2026, 6, 15))
    assert len(periods) == 2
    assert periods[1] == (date(2026, 6, 1), date(2026, 6, 15))


def test_generate_monthly_periods_un_solo_mes_parcial() -> None:
    periods = generate_monthly_periods(date(2026, 5, 10), date(2026, 5, 20))
    assert len(periods) == 1
    assert periods[0] == (date(2026, 5, 10), date(2026, 5, 20))


def test_generate_monthly_periods_sin_huecos_ni_solapamiento() -> None:
    periods = generate_monthly_periods(date(2026, 1, 1), date(2026, 3, 15))
    # Verificar continuidad: el inicio de cada período sigue al fin del anterior + 1 día
    for i in range(1, len(periods)):
        prev_hasta = periods[i - 1][1]
        curr_desde = periods[i][0]
        from datetime import timedelta
        assert curr_desde == prev_hasta + timedelta(days=1), (
            f"Hueco entre período {i-1} y {i}: {prev_hasta} → {curr_desde}"
        )
    # Último período termina en fecha_fin exacta
    assert periods[-1][1] == date(2026, 3, 15)


# ── integración: cronograma generado al activar ───────────────────────────────

def test_cronograma_genera_3_obligaciones_para_contrato_de_3_meses(client, db_session) -> None:
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-3M-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 50000.00, "2026-05-01")
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 3
    for ob in obligaciones:
        assert float(ob["importe_total"]) == 50000.00
        assert ob["estado_obligacion"] == "EMITIDA"

    # Períodos correctos
    assert obligaciones[0]["periodo_desde"] == date(2026, 5, 1)
    assert obligaciones[0]["periodo_hasta"] == date(2026, 5, 31)
    assert obligaciones[1]["periodo_desde"] == date(2026, 6, 1)
    assert obligaciones[1]["periodo_hasta"] == date(2026, 6, 30)
    assert obligaciones[2]["periodo_desde"] == date(2026, 7, 1)
    assert obligaciones[2]["periodo_hasta"] == date(2026, 7, 31)


def test_cronograma_ultimo_periodo_cortado_en_fecha_fin(client, db_session) -> None:
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-CORT-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-15",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 30000.00, "2026-05-01")
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 2
    # Primer período: mes completo
    assert obligaciones[0]["periodo_desde"] == date(2026, 5, 1)
    assert obligaciones[0]["periodo_hasta"] == date(2026, 5, 31)
    # Segundo período: cortado en fecha_fin
    assert obligaciones[1]["periodo_desde"] == date(2026, 6, 1)
    assert obligaciones[1]["periodo_hasta"] == date(2026, 6, 15)


def test_cronograma_idempotencia_no_duplica(client, db_session) -> None:
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-IDEM-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 20000.00, "2026-05-01")
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    assert len(_get_obligaciones_de_relacion(db_session, id_rg)) == 3

    # Llamar al handler directamente una segunda vez
    loc_repo = LocativoRepository(db_session)
    fin_repo = FinancieroRepository(db_session)
    handler = HandleContratoAlquilerActivadoEventService(
        locativo_repository=loc_repo,
        financiero_repository=fin_repo,
    )
    context = CommandContext()
    result = handler.execute(contrato["id_contrato_alquiler"], context)

    assert result.success
    assert result.data["generadas"] == 0
    assert result.data["razon"] == "ya_generado"
    # Cuenta no cambió
    assert len(_get_obligaciones_de_relacion(db_session, id_rg)) == 3


def test_cronograma_sin_condicion_no_genera_obligaciones(client, db_session) -> None:
    # Contrato sin condicion_economica → handler sale con 0 generadas sin error
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-NOCOND-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    # NO creamos condicion
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    # No debe existir relacion_generadora ni obligaciones para este contrato
    row = db_session.execute(
        text(
            "SELECT COUNT(*) FROM relacion_generadora WHERE tipo_origen = 'contrato_alquiler' AND id_origen = :id"
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).scalar()
    assert row == 0


# ── unit tests: get_condicion_vigente_para_periodo ────────────────────────────

def test_condicion_vigente_retorna_la_vigente() -> None:
    condiciones = [{"fecha_desde": date(2026, 5, 1), "fecha_hasta": None, "monto_base": 1000}]
    result = get_condicion_vigente_para_periodo(condiciones, date(2026, 6, 1))
    assert result is not None
    assert result["monto_base"] == 1000


def test_condicion_vigente_retorna_none_si_empieza_despues() -> None:
    condiciones = [{"fecha_desde": date(2026, 8, 1), "fecha_hasta": None, "monto_base": 1000}]
    result = get_condicion_vigente_para_periodo(condiciones, date(2026, 6, 1))
    assert result is None


def test_condicion_vigente_excluida_por_fecha_hasta() -> None:
    condiciones = [{"fecha_desde": date(2026, 5, 1), "fecha_hasta": date(2026, 5, 31), "monto_base": 1000}]
    assert get_condicion_vigente_para_periodo(condiciones, date(2026, 6, 1)) is None


def test_condicion_vigente_incluida_cuando_fecha_hasta_igual_a_periodo() -> None:
    condiciones = [{"fecha_desde": date(2026, 5, 1), "fecha_hasta": date(2026, 6, 1), "monto_base": 1000}]
    assert get_condicion_vigente_para_periodo(condiciones, date(2026, 6, 1)) is not None


def test_condicion_vigente_elige_mas_reciente_si_varias_aplican() -> None:
    condiciones = [
        {"fecha_desde": date(2026, 1, 1), "fecha_hasta": None, "monto_base": 1000},
        {"fecha_desde": date(2026, 5, 1), "fecha_hasta": None, "monto_base": 2000},
    ]
    result = get_condicion_vigente_para_periodo(condiciones, date(2026, 6, 1))
    assert result["monto_base"] == 2000


# ── integración: condición vigente por período ────────────────────────────────

def test_cronograma_usa_condicion_vigente_por_periodo(client, db_session) -> None:
    """Dos condiciones con importes distintos deben aplicar al período correcto."""
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-2COND-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-08-31",
    )
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 50000.00, "2026-05-01",
        fecha_hasta="2026-06-30",
    )
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 70000.00, "2026-07-01",
    )
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 4
    assert float(obligaciones[0]["importe_total"]) == 50000.00  # mayo
    assert float(obligaciones[1]["importe_total"]) == 50000.00  # junio
    assert float(obligaciones[2]["importe_total"]) == 70000.00  # julio
    assert float(obligaciones[3]["importe_total"]) == 70000.00  # agosto


def test_cronograma_omite_periodos_sin_condicion_aplicable(client, db_session) -> None:
    """Períodos sin condición vigente se omiten; los que sí tienen se crean."""
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-OMIT-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    # Condición arranca en julio → mayo y junio quedan sin condición
    _crear_condicion(client, contrato["id_contrato_alquiler"], 30000.00, "2026-07-01")
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 1
    assert obligaciones[0]["periodo_desde"] == date(2026, 7, 1)
    assert obligaciones[0]["periodo_hasta"] == date(2026, 7, 31)
    assert float(obligaciones[0]["importe_total"]) == 30000.00


def test_cronograma_sin_condicion_aplicable_no_crea_relacion_generadora(client, db_session) -> None:
    """Si ningún período tiene condición vigente, no se crea relacion_generadora."""
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-NOREL-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
    )
    # Condición empieza después del fin del contrato
    _crear_condicion(client, contrato["id_contrato_alquiler"], 10000.00, "2026-08-01")
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    count = db_session.execute(
        text(
            "SELECT COUNT(*) FROM relacion_generadora "
            "WHERE tipo_origen = 'contrato_alquiler' AND id_origen = :id"
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).scalar()
    assert count == 0
