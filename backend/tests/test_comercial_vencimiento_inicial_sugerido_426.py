from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from unittest.mock import patch

import pytest
from app.application.administrativo.services.obtener_configuracion_calendario_comercial_query_service import (
    ConfiguracionCalendarioComercialIncompleta,
    ConfiguracionCalendarioComercialInconsistente,
)
from app.application.comercial.services.resolver_primer_vencimiento_sugerido_service import (
    PrimerVencimientoSugeridoFueraDeRango,
    ResolverPrimerVencimientoSugeridoService,
)
from sqlalchemy import text

ENDPOINT = "/api/v1/ventas/vencimiento-inicial-sugerido"
CIERRE = "DIA_CIERRE_COMERCIAL"
VENCIMIENTO = "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS"


@dataclass(frozen=True)
class _Calendario:
    dia_cierre_comercial: int
    dia_vencimiento_predeterminado_cuotas: int


class _Query:
    def __init__(self, calendario: _Calendario):
        self.calendario = calendario
        self.fecha_efectiva = None

    def obtener(self, fecha_efectiva: date):
        self.fecha_efectiva = fecha_efectiva
        return self.calendario


@pytest.mark.parametrize(
    ("fecha_venta", "cierre", "dia_vencimiento", "esperada"),
    [
        (date(2026, 5, 9), 10, 15, date(2026, 6, 15)),
        (date(2026, 5, 10), 10, 15, date(2026, 6, 15)),
        (date(2026, 5, 11), 10, 15, date(2026, 7, 15)),
        (date(2026, 11, 10), 10, 1, date(2026, 12, 1)),
        (date(2026, 12, 10), 10, 28, date(2027, 1, 28)),
        (date(2026, 12, 11), 10, 15, date(2027, 2, 15)),
        (date(2027, 1, 10), 10, 31, date(2027, 2, 28)),
        (date(2028, 1, 10), 10, 31, date(2028, 2, 29)),
        (date(2026, 3, 10), 10, 31, date(2026, 4, 30)),
        (date(2026, 5, 10), 10, 31, date(2026, 6, 30)),
        (date(2026, 8, 10), 10, 31, date(2026, 9, 30)),
        (date(2026, 10, 10), 10, 31, date(2026, 11, 30)),
    ],
)
def test_resolver_aplica_cierre_cambio_de_anio_y_clamp(
    fecha_venta, cierre, dia_vencimiento, esperada
):
    query = _Query(_Calendario(cierre, dia_vencimiento))
    result = ResolverPrimerVencimientoSugeridoService(query).resolver(fecha_venta)

    assert result.fecha_primer_vencimiento_sugerida == esperada
    assert query.fecha_efectiva == fecha_venta


@pytest.mark.parametrize(
    ("fecha_venta", "cierre"),
    [
        (date(9999, 12, 1), 1),
        (date(9999, 11, 11), 10),
    ],
)
def test_resolver_rechaza_mes_destino_fuera_de_rango(fecha_venta, cierre):
    query = _Query(_Calendario(cierre, 15))

    with pytest.raises(PrimerVencimientoSugeridoFueraDeRango):
        ResolverPrimerVencimientoSugeridoService(query).resolver(fecha_venta)


def test_resolver_admite_diciembre_de_date_max():
    query = _Query(_Calendario(1, 31))

    result = ResolverPrimerVencimientoSugeridoService(query).resolver(
        date(9999, 11, 1)
    )

    assert result.fecha_primer_vencimiento_sugerida == date(9999, 12, 31)


def _root(db_session):
    db_session.execute(
        text(
            "INSERT INTO configuracion_calendario_comercial("
            "id_configuracion_calendario_comercial, version_registro) "
            "VALUES (426000001, 1)"
        )
    )


def _period(db_session, start: str, end: str | None, cierre: int, vencimiento: int):
    for code, value in ((CIERRE, cierre), (VENCIMIENTO, vencimiento)):
        db_session.execute(
            text("""
                INSERT INTO valor_parametro(
                    id_parametro_sistema, valor_parametro, es_valor_vigente,
                    fecha_desde, fecha_hasta
                )
                SELECT id_parametro_sistema, :value, false, :start, :end
                  FROM parametro_sistema
                 WHERE codigo_parametro = :code
            """),
            {"code": code, "value": str(value), "start": start, "end": end},
        )


def test_api_resuelve_vigencia_por_fecha_venta(client, db_session):
    _root(db_session)
    _period(db_session, "2026-01-01", "2026-07-01", 10, 15)
    _period(db_session, "2026-07-01", None, 20, 31)

    response = client.get(ENDPOINT, params={"fecha_venta": "2026-07-20"})

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "data": {"fecha_primer_vencimiento_sugerida": "2026-08-31"},
    }


def test_api_mes_corto(client, db_session):
    _root(db_session)
    _period(db_session, "2026-01-01", None, 20, 31)

    response = client.get(ENDPOINT, params={"fecha_venta": "2027-01-20"})

    assert response.status_code == 200
    assert response.json()["data"]["fecha_primer_vencimiento_sugerida"] == "2027-02-28"


@pytest.mark.parametrize("fecha_venta", ["", "no-es-fecha", "2026-02-30"])
def test_api_rechaza_fecha_invalida(client, fecha_venta):
    response = client.get(ENDPOINT, params={"fecha_venta": fecha_venta})
    assert response.status_code == 422


@pytest.mark.parametrize("fecha_venta", ["9999-12-01", "9999-11-11"])
def test_api_rechaza_mes_destino_fuera_de_rango(client, fecha_venta):
    with patch(
        "app.api.routers.comercial_router."
        "ObtenerConfiguracionCalendarioComercialQueryService.obtener",
        return_value=_Calendario(10, 15),
    ):
        response = client.get(ENDPOINT, params={"fecha_venta": fecha_venta})

    assert response.status_code == 422
    assert (
        response.json()["error_code"]
        == "PRIMER_VENCIMIENTO_SUGERIDO_FUERA_DE_RANGO"
    )


def test_api_calendario_incompleto_es_precondicion(client):
    response = client.get(ENDPOINT, params={"fecha_venta": "2026-05-10"})

    assert response.status_code == 409
    assert response.json()["error_code"] == "CONFIGURACION_CALENDARIO_COMERCIAL_INCOMPLETA"


def test_api_inconsistencia_es_error_tecnico_controlado(client):
    with patch(
        "app.api.routers.comercial_router."
        "ObtenerConfiguracionCalendarioComercialQueryService.obtener",
        side_effect=ConfiguracionCalendarioComercialInconsistente,
    ):
        response = client.get(ENDPOINT, params={"fecha_venta": "2026-05-10"})

    assert response.status_code == 500
    assert (
        response.json()["error_code"]
        == "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"
    )


def test_resolver_no_degrada_errores_administrativos():
    for error in (
        ConfiguracionCalendarioComercialIncompleta,
        ConfiguracionCalendarioComercialInconsistente,
    ):
        query = _Query(_Calendario(10, 15))
        with (
            patch.object(query, "obtener", side_effect=error),
            pytest.raises(error),
        ):
            ResolverPrimerVencimientoSugeridoService(query).resolver(
                date(2026, 5, 10)
            )
