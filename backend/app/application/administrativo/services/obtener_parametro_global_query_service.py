from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from app.infrastructure.persistence.repositories.parametro_sistema_repository import (
    ParametroSistemaRepository,
)


class ParametroGlobalNotFoundError(Exception):
    """Definición inexistente, no exponible o sensible."""


class ParametroGlobalConflictError(Exception):
    """Definición exponible no sensible incompatible con valor GLOBAL."""


class ParametroGlobalInconsistencyError(Exception):
    """Estructura o valor persistido inconsistente para la consulta."""


@dataclass(frozen=True)
class ObtenerParametroGlobalQueryService:
    repository: ParametroSistemaRepository

    def obtener(self, codigo_parametro: str) -> dict[str, Any]:
        rows = self.repository.get_definicion_con_valor_global_marcado_vigente(
            codigo_parametro
        )
        if not rows:
            raise ParametroGlobalNotFoundError()

        first = rows[0]
        if not first["exponible_api_administrativa"] or first["es_sensible"]:
            raise ParametroGlobalNotFoundError()

        tipo_incompleto = any(
            first[field] is None
            for field in (
                "id_tipo_dato_parametro",
                "codigo_tipo_dato",
                "nombre_tipo_dato",
            )
        )
        alcance_incompleto = any(
            first[field] is None
            for field in (
                "id_alcance_parametro",
                "codigo_alcance",
                "nombre_alcance",
            )
        )
        if tipo_incompleto or alcance_incompleto:
            raise ParametroGlobalInconsistencyError()

        if first["codigo_alcance"] != "GLOBAL":
            raise ParametroGlobalConflictError()

        if first["codigo_tipo_dato"] != "ENTERO":
            raise ParametroGlobalInconsistencyError()

        value_rows = [row for row in rows if row["id_valor_parametro"] is not None]
        if len(value_rows) > 1:
            raise ParametroGlobalInconsistencyError()

        definicion = {
            "id_parametro_sistema": first["id_parametro_sistema"],
            "codigo_parametro": first["codigo_parametro"],
            "nombre_parametro": first["nombre_parametro"],
            "descripcion": first["descripcion"],
            "tipo": {
                "id_tipo_dato_parametro": first["id_tipo_dato_parametro"],
                "codigo_tipo_dato": first["codigo_tipo_dato"],
                "nombre_tipo_dato": first["nombre_tipo_dato"],
                "descripcion_tipo_dato": first["descripcion_tipo_dato"],
            },
            "alcance": {
                "id_alcance_parametro": first["id_alcance_parametro"],
                "codigo_alcance": first["codigo_alcance"],
                "nombre_alcance": first["nombre_alcance"],
                "descripcion_alcance": first["descripcion_alcance"],
            },
        }

        if not value_rows:
            return {
                "definicion": definicion,
                "estado_valor": "SIN_VALOR",
                "valor_marcado_vigente": None,
            }

        row = value_rows[0]
        valor_raw = row["valor_raw"]
        if not isinstance(valor_raw, str) or not re.fullmatch(r"-?[0-9]+", valor_raw):
            raise ParametroGlobalInconsistencyError()
        valor_tipado = int(valor_raw)

        return {
            "definicion": definicion,
            "estado_valor": "CON_VALOR_MARCADO_VIGENTE",
            "valor_marcado_vigente": {
                "id_valor_parametro": row["id_valor_parametro"],
                "uid_global": str(row["uid_global"]),
                "valor_raw": valor_raw,
                "valor_tipado": valor_tipado,
                "version_registro": row["version_registro"],
                "es_valor_vigente": row["es_valor_vigente"],
                "fecha_desde": row["fecha_desde"],
                "fecha_hasta": row["fecha_hasta"],
                "created_at": row["valor_created_at"],
                "updated_at": row["valor_updated_at"],
            },
        }
