"""
Tests de integración para generación de cronograma locativo mensual.
La activación del contrato dispara HandleContratoAlquilerActivadoEventService,
que crea N obligaciones_financieras (una por período mensual) con CANON_LOCATIVO.
"""
from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy import text

from app.application.common.commands import CommandContext
from app.application.financiero.services.cronograma_locativo_builder import (
    calcular_fecha_vencimiento_canon,
    generate_monthly_periods,
    get_condicion_vigente_para_periodo,
)
from app.application.financiero.services.handle_contrato_alquiler_activado_event_service import (
    HandleContratoAlquilerActivadoEventService,
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

def _crear_contrato_borrador(
    client,
    *,
    codigo: str,
    fecha_inicio: str,
    fecha_fin: str,
    dia_vencimiento_canon: int | None = None,
) -> dict:
    id_inmueble = _crear_inmueble(client, codigo=f"INM-{codigo}")
    payload = _payload_base(
        codigo_contrato=codigo,
        objetos=[{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
    )
    if dia_vencimiento_canon is not None:
        payload["dia_vencimiento_canon"] = dia_vencimiento_canon
    response = client.post(URL_CONTRATOS, headers=HEADERS, json=payload)
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


def _crear_locatario_principal(client, db_session, id_contrato: int) -> int:
    persona_response = client.post(
        "/api/v1/personas",
        headers=HEADERS,
        json={
            "tipo_persona": "FISICA",
            "nombre": "Locatario",
            "apellido": f"Principal {id_contrato}",
            "razon_social": None,
            "estado_persona": "ACTIVA",
            "observaciones": "Locatario principal para cronograma locativo",
        },
    )
    assert persona_response.status_code == 201
    id_persona = persona_response.json()["data"]["id_persona"]

    id_rol = db_session.execute(
        text(
            """
            INSERT INTO rol_participacion (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                codigo_rol, nombre_rol, descripcion, estado_rol
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                'LOCATARIO_PRINCIPAL', 'Locatario principal',
                'Rol locativo principal para cronograma financiero', 'ACTIVO'
            )
            ON CONFLICT (codigo_rol) DO UPDATE
            SET updated_at = EXCLUDED.updated_at
            RETURNING id_rol_participacion
            """
        ),
        {"op_id": HEADERS["X-Op-Id"]},
    ).scalar_one()

    db_session.execute(
        text(
            """
            INSERT INTO relacion_persona_rol (
                uid_global, version_registro, created_at, updated_at,
                id_instalacion_origen, id_instalacion_ultima_modificacion,
                op_id_alta, op_id_ultima_modificacion,
                id_persona, id_rol_participacion,
                tipo_relacion, id_relacion, fecha_desde, fecha_hasta,
                observaciones
            )
            VALUES (
                gen_random_uuid(), 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                1, 1, :op_id, :op_id,
                :id_persona, :id_rol,
                'contrato_alquiler', :id_contrato,
                TIMESTAMP '2026-05-01 00:00:00', NULL,
                'Locatario principal vigente'
            )
            """
        ),
        {
            "op_id": HEADERS["X-Op-Id"],
            "id_persona": id_persona,
            "id_rol": id_rol,
            "id_contrato": id_contrato,
        },
    )
    return id_persona


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
                fecha_vencimiento,
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


def _get_obligados_de_relacion(db_session, id_relacion_generadora: int) -> list:
    rows = db_session.execute(
        text(
            """
            SELECT oo.id_persona, oo.rol_obligado, oo.porcentaje_responsabilidad
            FROM obligacion_obligado oo
            JOIN obligacion_financiera o
              ON o.id_obligacion_financiera = oo.id_obligacion_financiera
            WHERE o.id_relacion_generadora = :id
              AND o.deleted_at IS NULL
              AND oo.deleted_at IS NULL
            ORDER BY o.periodo_desde ASC, oo.id_obligacion_obligado ASC
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


def _ensure_idempotencia_sql_cronograma(db_session) -> None:
    db_session.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_relacion_generadora_origen_activo
                ON public.relacion_generadora (tipo_origen, id_origen)
                WHERE deleted_at IS NULL
            """
        )
    )
    db_session.execute(
        text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_obligacion_financiera_cronograma_periodo_activo
                ON public.obligacion_financiera (id_relacion_generadora, periodo_desde, periodo_hasta)
                WHERE deleted_at IS NULL
            """
        )
    )


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


def test_calcular_fecha_vencimiento_canon_usa_dia_de_contrato() -> None:
    """dia_vencimiento_canon=10 en contrato_alquiler → vence el 10 del mes."""
    vencimiento = calcular_fecha_vencimiento_canon(
        date(2026, 5, 1),
        dia_vencimiento_canon=10,
    )

    assert vencimiento == date(2026, 5, 10)


def test_calcular_fecha_vencimiento_canon_ajusta_al_ultimo_dia_del_mes() -> None:
    """dia=31 en febrero → último día real del mes (28 en año no bisiesto)."""
    vencimiento = calcular_fecha_vencimiento_canon(
        date(2026, 2, 1),
        dia_vencimiento_canon=31,
    )

    assert vencimiento == date(2026, 2, 28)


def test_calcular_fecha_vencimiento_canon_ajusta_al_ultimo_dia_mes_bisiesto() -> None:
    """dia=31 en febrero bisiesto → 29."""
    vencimiento = calcular_fecha_vencimiento_canon(
        date(2028, 2, 1),
        dia_vencimiento_canon=31,
    )

    assert vencimiento == date(2028, 2, 29)


def test_calcular_fecha_vencimiento_canon_fallback_periodo_desde() -> None:
    """dia_vencimiento_canon=None → fallback técnico: fecha_vencimiento = periodo_desde."""
    vencimiento = calcular_fecha_vencimiento_canon(
        date(2026, 5, 1),
        dia_vencimiento_canon=None,
    )

    assert vencimiento == date(2026, 5, 1)


def test_calcular_fecha_vencimiento_canon_no_devuelve_fecha_anterior_al_periodo() -> None:
    """Si el día calculado quedara antes de periodo_desde, se usa periodo_desde."""
    vencimiento = calcular_fecha_vencimiento_canon(
        date(2026, 5, 10),
        dia_vencimiento_canon=5,
    )

    assert vencimiento == date(2026, 5, 10)


# ── integración: cronograma generado al activar ───────────────────────────────

def test_cronograma_genera_3_obligaciones_para_contrato_de_3_meses(client, db_session) -> None:
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-3M-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 50000.00, "2026-05-01")
    id_locatario = _crear_locatario_principal(
        client,
        db_session,
        contrato["id_contrato_alquiler"],
    )
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)
    obligados = _get_obligados_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 3
    assert len(obligados) == 3
    for ob in obligaciones:
        assert float(ob["importe_total"]) == 50000.00
        assert ob["estado_obligacion"] == "EMITIDA"
        assert ob["fecha_vencimiento"] == ob["periodo_desde"]
    for obligado in obligados:
        assert obligado["id_persona"] == id_locatario
        assert obligado["rol_obligado"] == "LOCATARIO_PRINCIPAL"
        assert float(obligado["porcentaje_responsabilidad"]) == 100.00

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
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
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
    _ensure_idempotencia_sql_cronograma(db_session)
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-IDEM-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 20000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
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
    relaciones = db_session.execute(
        text(
            """
            SELECT COUNT(*)
            FROM relacion_generadora
            WHERE tipo_origen = 'contrato_alquiler'
              AND id_origen = :id
              AND deleted_at IS NULL
            """
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).scalar()
    assert relaciones == 1
    assert len(_get_obligaciones_de_relacion(db_session, id_rg)) == 3


def test_cronograma_constraints_sql_rechazan_duplicado_directo(client, db_session) -> None:
    _ensure_idempotencia_sql_cronograma(db_session)
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-UQ-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 20000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    """
                    INSERT INTO relacion_generadora (tipo_origen, id_origen)
                    VALUES ('contrato_alquiler', :id_contrato)
                    """
                ),
                {"id_contrato": contrato["id_contrato_alquiler"]},
            )

    with pytest.raises(IntegrityError):
        with db_session.begin_nested():
            db_session.execute(
                text(
                    """
                    INSERT INTO obligacion_financiera (
                        id_relacion_generadora,
                        fecha_emision,
                        fecha_vencimiento,
                        periodo_desde,
                        periodo_hasta,
                        importe_total,
                        saldo_pendiente,
                        estado_obligacion
                    )
                    VALUES (
                        :id_rg,
                        :periodo_desde,
                        :periodo_desde,
                        :periodo_desde,
                        :periodo_hasta,
                        20000.00,
                        20000.00,
                        'EMITIDA'
                    )
                    """
                ),
                {
                    "id_rg": id_rg,
                    "periodo_desde": obligaciones[0]["periodo_desde"],
                    "periodo_hasta": obligaciones[0]["periodo_hasta"],
                },
            )


def test_cronograma_con_condicion_sin_locatario_principal_falla(db_session, client) -> None:
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-SIN-LOC-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 20000.00, "2026-05-01")

    handler = HandleContratoAlquilerActivadoEventService(
        locativo_repository=LocativoRepository(db_session),
        financiero_repository=FinancieroRepository(db_session),
    )
    result = handler.execute(contrato["id_contrato_alquiler"], CommandContext())

    assert not result.success
    assert "SIN_LOCATARIO_PRINCIPAL" in result.errors
    count = db_session.execute(
        text(
            "SELECT COUNT(*) FROM relacion_generadora "
            "WHERE tipo_origen = 'contrato_alquiler' AND id_origen = :id"
        ),
        {"id": contrato["id_contrato_alquiler"]},
    ).scalar()
    assert count == 0


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
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
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
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
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


# ── integración: dia_vencimiento_canon ───────────────────────────────────────

def test_cronograma_usa_dia_vencimiento_canon_del_contrato(client, db_session) -> None:
    """dia_vencimiento_canon=10 → fecha_vencimiento = día 10 de cada periodo_desde."""
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-DVC-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-07-31",
        dia_vencimiento_canon=10,
    )
    assert contrato["dia_vencimiento_canon"] == 10

    _crear_condicion(client, contrato["id_contrato_alquiler"], 60000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 3
    assert obligaciones[0]["fecha_vencimiento"] == date(2026, 5, 10)
    assert obligaciones[1]["fecha_vencimiento"] == date(2026, 6, 10)
    assert obligaciones[2]["fecha_vencimiento"] == date(2026, 7, 10)


def test_cronograma_dia_vencimiento_31_en_febrero_usa_ultimo_dia(client, db_session) -> None:
    """dia=31 en febrero → último día real del mes."""
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-DVC-FEB-001",
        fecha_inicio="2026-02-01", fecha_fin="2026-02-28",
        dia_vencimiento_canon=31,
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 40000.00, "2026-02-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 1
    assert obligaciones[0]["fecha_vencimiento"] == date(2026, 2, 28)


def test_cronograma_sin_dia_vencimiento_usa_periodo_desde(client, db_session) -> None:
    """Sin dia_vencimiento_canon → fallback técnico: fecha_vencimiento = periodo_desde."""
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-DVC-NULL-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-30",
    )
    assert contrato["dia_vencimiento_canon"] is None

    _crear_condicion(client, contrato["id_contrato_alquiler"], 25000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 2
    for ob in obligaciones:
        assert ob["fecha_vencimiento"] == ob["periodo_desde"]


# ── unit tests: prorrateo ─────────────────────────────────────────────────────

def test_get_segmentos_sin_cambio_devuelve_un_segmento() -> None:
    """Sin cambio de condición dentro del período → un solo segmento."""
    from app.application.financiero.services.cronograma_locativo_builder import (
        get_segmentos_para_periodo,
    )
    condiciones = [{"fecha_desde": date(2026, 5, 1), "fecha_hasta": None, "monto_base": 10000}]
    segs = get_segmentos_para_periodo(condiciones, date(2026, 5, 1), date(2026, 5, 31))
    assert len(segs) == 1
    assert segs[0][0] == date(2026, 5, 1)
    assert segs[0][1] == date(2026, 5, 31)


def test_get_segmentos_cambio_a_mitad_genera_dos() -> None:
    """Condición B empieza el día 16 → dos segmentos (1-15) y (16-31)."""
    from app.application.financiero.services.cronograma_locativo_builder import (
        get_segmentos_para_periodo,
    )
    condiciones = [
        {"fecha_desde": date(2026, 5, 1), "fecha_hasta": date(2026, 5, 15), "monto_base": 10000},
        {"fecha_desde": date(2026, 5, 16), "fecha_hasta": None, "monto_base": 15000},
    ]
    segs = get_segmentos_para_periodo(condiciones, date(2026, 5, 1), date(2026, 5, 31))
    assert len(segs) == 2
    assert segs[0] == (date(2026, 5, 1), date(2026, 5, 15), condiciones[0])
    assert segs[1] == (date(2026, 5, 16), date(2026, 5, 31), condiciones[1])


def test_calcular_importes_un_segmento_devuelve_monto_completo() -> None:
    """Con un solo segmento → monto_base completo, sin prorrateo."""
    from app.application.financiero.services.cronograma_locativo_builder import (
        calcular_importes_prorateados,
    )
    condicion = {"fecha_desde": date(2026, 5, 1), "fecha_hasta": None, "monto_base": 10000}
    segs = [(date(2026, 5, 1), date(2026, 5, 31), condicion)]
    importes = calcular_importes_prorateados(segs, date(2026, 5, 1))
    assert len(importes) == 1
    assert importes[0] == pytest.approx(10000.00)


def test_calcular_importes_dos_segmentos_mismo_monto_suman_total() -> None:
    """
    Dos segmentos con igual monto_base, mismo mes (31 días).
    Residuo asegura suma exacta = monto_base.
    """
    from app.application.financiero.services.cronograma_locativo_builder import (
        calcular_importes_prorateados,
    )
    condicion = {"monto_base": 10000}
    segs = [
        (date(2026, 1, 1), date(2026, 1, 15), condicion),
        (date(2026, 1, 16), date(2026, 1, 31), condicion),
    ]
    importes = calcular_importes_prorateados(segs, date(2026, 1, 1))
    assert len(importes) == 2
    assert round(sum(importes), 2) == pytest.approx(10000.00)
    # 10000 * 15/31 = 4838.71, 10000 * 16/31 = 5161.29, suma = 10000.00
    assert importes[0] == pytest.approx(10000 * 15 / 31, abs=0.01)


def test_calcular_importes_tres_segmentos_mismo_monto_suman_total() -> None:
    """Tres segmentos con igual monto_base → residuo al último, suma exacta."""
    from app.application.financiero.services.cronograma_locativo_builder import (
        calcular_importes_prorateados,
    )
    condicion = {"monto_base": 9999}  # impar para forzar residuo
    # enero: 10+10+11 = 31 días
    segs = [
        (date(2026, 1, 1), date(2026, 1, 10), condicion),
        (date(2026, 1, 11), date(2026, 1, 20), condicion),
        (date(2026, 1, 21), date(2026, 1, 31), condicion),
    ]
    importes = calcular_importes_prorateados(segs, date(2026, 1, 1))
    assert len(importes) == 3
    assert round(sum(importes), 2) == pytest.approx(9999.00)


def test_calcular_importes_distintos_montos_proporcionales() -> None:
    """Con diferentes monto_base → cada segmento proporcional a su propio monto."""
    from app.application.financiero.services.cronograma_locativo_builder import (
        calcular_importes_prorateados,
    )
    cond_a = {"monto_base": 10000}
    cond_b = {"monto_base": 15000}
    # Mayo (31 días), 15 + 16
    segs = [
        (date(2026, 5, 1), date(2026, 5, 15), cond_a),
        (date(2026, 5, 16), date(2026, 5, 31), cond_b),
    ]
    importes = calcular_importes_prorateados(segs, date(2026, 5, 1))
    assert len(importes) == 2
    assert importes[0] == pytest.approx(10000 * 15 / 31, abs=0.01)
    assert importes[1] == pytest.approx(15000 * 16 / 31, abs=0.01)


# ── integración: prorrateo en cronograma ─────────────────────────────────────

def test_cronograma_prorrateo_cambio_a_mitad_de_mes(client, db_session) -> None:
    """
    Condición A desde Mayo 1, B desde Mayo 16.
    Cronograma de Mayo debe generar 2 obligaciones prorateadas.
    """
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-PROR-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
    )
    # Condición A: mayo 1-15
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 10000.00, "2026-05-01",
        fecha_hasta="2026-05-15",
    )
    # Condición B: mayo 16-31
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 15000.00, "2026-05-16",
    )
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 2
    assert obligaciones[0]["periodo_desde"] == date(2026, 5, 1)
    assert obligaciones[0]["periodo_hasta"] == date(2026, 5, 15)
    assert obligaciones[1]["periodo_desde"] == date(2026, 5, 16)
    assert obligaciones[1]["periodo_hasta"] == date(2026, 5, 31)
    # Importes proporcionales (31 días)
    assert float(obligaciones[0]["importe_total"]) == pytest.approx(10000 * 15 / 31, abs=0.01)
    assert float(obligaciones[1]["importe_total"]) == pytest.approx(15000 * 16 / 31, abs=0.01)


def test_cronograma_prorrateo_multiples_cambios_genera_n_segmentos(client, db_session) -> None:
    """Tres condiciones en un mes → 3 obligaciones."""
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-PROR-MULT-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
    )
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 9000.00, "2026-05-01", fecha_hasta="2026-05-10",
    )
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 10000.00, "2026-05-11", fecha_hasta="2026-05-20",
    )
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 12000.00, "2026-05-21",
    )
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 3
    assert obligaciones[0]["periodo_desde"] == date(2026, 5, 1)
    assert obligaciones[1]["periodo_desde"] == date(2026, 5, 11)
    assert obligaciones[2]["periodo_desde"] == date(2026, 5, 21)


def test_cronograma_prorrateo_mismo_monto_suma_exacta(client, db_session) -> None:
    """
    Dos condiciones con igual monto (10000) en mayo (31d: 15+16).
    Suma debe ser exactamente 10000 (residuo aplicado al último).
    """
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-PROR-SUM-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-05-31",
    )
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 10000.00, "2026-05-01", fecha_hasta="2026-05-15",
    )
    _crear_condicion(
        client, contrato["id_contrato_alquiler"], 10000.00, "2026-05-16",
    )
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 2
    total = sum(float(ob["importe_total"]) for ob in obligaciones)
    assert total == pytest.approx(10000.00)


def test_cronograma_sin_cambio_condicion_comportamiento_original(client, db_session) -> None:
    """Sin cambios de condición dentro del período → importe = monto_base completo."""
    contrato = _crear_contrato_borrador(
        client, codigo="CRON-PROR-ORI-001",
        fecha_inicio="2026-05-01", fecha_fin="2026-06-30",
    )
    _crear_condicion(client, contrato["id_contrato_alquiler"], 20000.00, "2026-05-01")
    _crear_locatario_principal(client, db_session, contrato["id_contrato_alquiler"])
    _activar(client, contrato["id_contrato_alquiler"], contrato["version_registro"])

    id_rg = _get_relacion_for_contrato(db_session, contrato["id_contrato_alquiler"])
    obligaciones = _get_obligaciones_de_relacion(db_session, id_rg)

    assert len(obligaciones) == 2
    for ob in obligaciones:
        assert float(ob["importe_total"]) == pytest.approx(20000.00)


def test_contrato_create_rechaza_dia_vencimiento_fuera_de_rango(client) -> None:
    """dia_vencimiento_canon=0 o >31 debe ser rechazado por validación Pydantic (422)."""
    id_inmueble = _crear_inmueble(client, codigo="INM-DVC-RANGE-001")
    for dia_invalido in (0, 32, -1):
        response = client.post(
            URL_CONTRATOS,
            headers=HEADERS,
            json={
                "codigo_contrato": f"DVC-RANGE-{dia_invalido}",
                "fecha_inicio": "2026-05-01",
                "fecha_fin": "2026-07-31",
                "observaciones": None,
                "objetos": [{"id_inmueble": id_inmueble, "id_unidad_funcional": None, "observaciones": None}],
                "dia_vencimiento_canon": dia_invalido,
            },
        )
        assert response.status_code == 422, f"Esperaba 422 para dia={dia_invalido}"
