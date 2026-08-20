from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from app.application.administrativo.parametro_entero import parse_parametro_entero
from app.infrastructure.persistence.repositories.calendario_comercial_query_repository import (
    CalendarioComercialQueryRepository,
)


CODIGOS_CALENDARIO = frozenset(
    {
        "DIA_CIERRE_COMERCIAL",
        "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS",
    }
)


class ConfiguracionCalendarioComercialIncompleta(Exception):
    """No existe configuración aplicable por una causa funcional legítima."""

    code = "CONFIGURACION_CALENDARIO_COMERCIAL_INCOMPLETA"


class ConfiguracionCalendarioComercialInconsistente(Exception):
    """La persistencia del agregado no permite construir un snapshot seguro."""

    code = "CONFIGURACION_CALENDARIO_COMERCIAL_INCONSISTENTE"


@dataclass(frozen=True)
class ConfiguracionCalendarioComercialSnapshot:
    dia_cierre_comercial: int
    dia_vencimiento_predeterminado_cuotas: int
    version_agregada: int
    fecha_desde: datetime
    fecha_hasta: datetime | None


@dataclass(frozen=True)
class ObtenerConfiguracionCalendarioComercialQueryService:
    repository: CalendarioComercialQueryRepository

    def obtener(
        self, fecha_efectiva: date
    ) -> ConfiguracionCalendarioComercialSnapshot:
        if not isinstance(fecha_efectiva, date) or isinstance(fecha_efectiva, datetime):
            raise TypeError("fecha_efectiva debe ser date")

        rows = self.repository.obtener_snapshot_fisico()
        definiciones = [row for row in rows if row["clase"] == "DEFINICION"]
        valores = [row for row in rows if row["clase"] == "VALOR"]
        raices = [row for row in rows if row["clase"] == "RAIZ"]

        if len(definiciones) != 2 or {
            row["codigo_parametro"] for row in definiciones
        } != CODIGOS_CALENDARIO:
            raise ConfiguracionCalendarioComercialInconsistente()
        if any(
            row["codigo_tipo_dato"] != "ENTERO"
            or row["codigo_alcance"] != "GLOBAL"
            or not row["exponible_api_administrativa"]
            or row["es_sensible"]
            or not row["editable_administrativamente"]
            for row in definiciones
        ):
            raise ConfiguracionCalendarioComercialInconsistente()

        valores_activos = [row for row in valores if row["deleted_at"] is None]
        raices_activas = [row for row in raices if row["deleted_at"] is None]
        if not valores and not raices:
            raise ConfiguracionCalendarioComercialIncompleta()
        if len(raices_activas) != 1:
            raise ConfiguracionCalendarioComercialInconsistente()
        if not valores_activos:
            raise ConfiguracionCalendarioComercialInconsistente()

        por_intervalo: dict[tuple[datetime, datetime | None], dict[str, int]] = {}
        for row in valores_activos:
            fecha_desde = row["fecha_desde"]
            fecha_hasta = row["fecha_hasta"]
            if fecha_desde is None or (
                fecha_hasta is not None and fecha_desde >= fecha_hasta
            ):
                raise ConfiguracionCalendarioComercialInconsistente()
            try:
                valor = parse_parametro_entero(row["valor_parametro"])
            except (TypeError, ValueError) as exc:
                raise ConfiguracionCalendarioComercialInconsistente() from exc
            if not 1 <= valor <= 31:
                raise ConfiguracionCalendarioComercialInconsistente()
            intervalo = (fecha_desde, fecha_hasta)
            pareja = por_intervalo.setdefault(intervalo, {})
            codigo = row["codigo_parametro"]
            if codigo in pareja:
                raise ConfiguracionCalendarioComercialInconsistente()
            pareja[codigo] = valor

        if any(set(pareja) != CODIGOS_CALENDARIO for pareja in por_intervalo.values()):
            raise ConfiguracionCalendarioComercialInconsistente()

        intervalos_ordenados = sorted(por_intervalo, key=lambda intervalo: intervalo[0])
        for anterior, actual in zip(
            intervalos_ordenados, intervalos_ordenados[1:], strict=False
        ):
            fecha_hasta_anterior = anterior[1]
            if fecha_hasta_anterior is None or actual[0] < fecha_hasta_anterior:
                raise ConfiguracionCalendarioComercialInconsistente()

        instante = datetime.combine(fecha_efectiva, datetime.min.time())
        aplicables = [
            (intervalo, pareja)
            for intervalo, pareja in por_intervalo.items()
            if intervalo[0] <= instante
            and (intervalo[1] is None or instante < intervalo[1])
        ]
        if len(aplicables) > 1:
            raise ConfiguracionCalendarioComercialInconsistente()
        if not aplicables:
            primera_vigencia = min(intervalo[0] for intervalo in por_intervalo)
            if instante < primera_vigencia:
                raise ConfiguracionCalendarioComercialIncompleta()
            raise ConfiguracionCalendarioComercialInconsistente()

        (fecha_desde, fecha_hasta), pareja = aplicables[0]
        raiz = raices_activas[0]
        return ConfiguracionCalendarioComercialSnapshot(
            dia_cierre_comercial=pareja["DIA_CIERRE_COMERCIAL"],
            dia_vencimiento_predeterminado_cuotas=pareja[
                "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS"
            ],
            version_agregada=raiz["version_agregada"],
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
