from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID, uuid5

from sqlalchemy import text
from sqlalchemy.orm import Session


CODIGOS = (
    "DIA_CIERRE_COMERCIAL",
    "DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS",
)


class CalendarioComercialCommandRepository:
    """Persistencia del bootstrap agregado; la transacción pertenece al caller."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def validate_context(self, id_sucursal: int, id_instalacion: int) -> UUID | None:
        return self.session.execute(
            text("""
                SELECT i.uid_global
                  FROM sucursal s JOIN instalacion i
                    ON i.id_sucursal=s.id_sucursal
                 WHERE s.id_sucursal=:s AND i.id_instalacion=:i
            """),
            {"s": id_sucursal, "i": id_instalacion},
        ).scalar_one_or_none()

    def lock_global(self) -> None:
        # Dos mitades constantes del SHA-256 de CALENDARIO_COMERCIAL/GLOBAL.
        self.session.execute(text("SELECT pg_advisory_xact_lock(759942885, 986974765)"))

    def inspect_bootstrap_state(self) -> tuple[bool, dict[str, int]]:
        definitions = self.session.execute(
            text("""
                SELECT p.id_parametro_sistema, p.codigo_parametro,
                       p.exponible_api_administrativa, p.es_sensible,
                       p.editable_administrativamente, t.codigo_tipo_dato,
                       a.codigo_alcance
                  FROM parametro_sistema p
                  JOIN tipo_dato_parametro t USING(id_tipo_dato_parametro)
                  JOIN alcance_parametro a USING(id_alcance_parametro)
                 WHERE p.codigo_parametro IN (
                    'DIA_CIERRE_COMERCIAL',
                    'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
                 ORDER BY p.codigo_parametro
                 FOR UPDATE OF p
            """),
        ).mappings().all()
        valid_definitions = len(definitions) == 2 and all(
            row["codigo_tipo_dato"] == "ENTERO"
            and row["codigo_alcance"] == "GLOBAL"
            and row["exponible_api_administrativa"]
            and not row["es_sensible"]
            and row["editable_administrativamente"]
            for row in definitions
        )
        root_count = self.session.execute(
            text("SELECT count(*) FROM configuracion_calendario_comercial")
        ).scalar_one()
        value_count = self.session.execute(
            text("""
                SELECT count(*) FROM valor_parametro v JOIN parametro_sistema p
                  USING(id_parametro_sistema)
                 WHERE p.codigo_parametro IN (
                    'DIA_CIERRE_COMERCIAL',
                    'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
            """)
        ).scalar_one()
        ids = {row["codigo_parametro"]: row["id_parametro_sistema"] for row in definitions}
        return valid_definitions and root_count == 0 and value_count == 0, ids

    def create(self, *, definitions: dict[str, int], values: dict[str, int], vigente_desde: date,
               op_id: UUID, id_instalacion: int) -> dict[str, Any]:
        root = self.session.execute(
            text("""
                INSERT INTO configuracion_calendario_comercial(
                    id_instalacion_origen,id_instalacion_ultima_modificacion,
                    op_id_alta,op_id_ultima_modificacion)
                VALUES (:inst,:inst,:op,:op)
                RETURNING id_configuracion_calendario_comercial,
                          uid_global,version_registro
            """), {"inst": id_instalacion, "op": op_id}
        ).mappings().one()
        created_values: dict[str, dict[str, Any]] = {}
        for code, parameter_id in definitions.items():
            # valor_parametro exige op_id_alta único por fila; se derivan IDs
            # determinísticos del command, sin perder su procedencia.
            child_op_id = uuid5(op_id, code)
            row = self.session.execute(text("""
                INSERT INTO valor_parametro(
                    id_parametro_sistema,valor_parametro,es_valor_vigente,
                    fecha_desde,fecha_hasta,id_instalacion_origen,
                    id_instalacion_ultima_modificacion,op_id_alta,
                    op_id_ultima_modificacion)
                VALUES (:pid,:value,true,:start,NULL,:inst,:inst,:op,:op)
                RETURNING uid_global, version_registro, fecha_desde, fecha_hasta
            """), {"pid": parameter_id, "value": str(values[code]),
                     "start": vigente_desde, "inst": id_instalacion,
                     "op": child_op_id}).mappings().one()
            created_values[code] = {"codigo_parametro": code, **dict(row)}
        return {"root": dict(root), "values": created_values}
