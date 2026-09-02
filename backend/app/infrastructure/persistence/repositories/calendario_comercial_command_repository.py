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

    def lock_roots(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.session.execute(
                text("""
                SELECT id_configuracion_calendario_comercial, uid_global,
                       version_registro, deleted_at
                  FROM configuracion_calendario_comercial
                 ORDER BY id_configuracion_calendario_comercial
                 FOR UPDATE
                """)
            ).mappings()
        ]

    def lock_definitions(self) -> tuple[bool, dict[str, int]]:
        definitions = (
            self.session.execute(
                text("""
                SELECT p.id_parametro_sistema, p.codigo_parametro,
                       p.exponible_api_administrativa, p.es_sensible,
                       p.editable_administrativamente, t.codigo_tipo_dato,
                       a.codigo_alcance
                  FROM parametro_sistema p
                  JOIN tipo_dato_parametro t USING(id_tipo_dato_parametro)
                  JOIN alcance_parametro a USING(id_alcance_parametro)
                 WHERE p.codigo_parametro IN
                   ('DIA_CIERRE_COMERCIAL',
                    'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
                 ORDER BY p.codigo_parametro
                 FOR UPDATE OF p
                """)
            ).mappings().all()
        )
        valid = len(definitions) == len(CODIGOS) and all(
            row["codigo_tipo_dato"] == "ENTERO"
            and row["codigo_alcance"] == "GLOBAL"
            and row["exponible_api_administrativa"]
            and not row["es_sensible"]
            and row["editable_administrativamente"]
            for row in definitions
        )
        return valid, {
            row["codigo_parametro"]: row["id_parametro_sistema"]
            for row in definitions
        }

    def lock_history(self, *, include_deleted: bool = False) -> list[dict[str, Any]]:
        deleted_filter = "" if include_deleted else "AND v.deleted_at IS NULL"
        return [
            dict(row)
            for row in self.session.execute(
                text(f"""
                SELECT v.id_valor_parametro, v.uid_global, v.version_registro,
                       v.valor_parametro, v.fecha_desde, v.fecha_hasta,
                       v.es_valor_vigente, v.deleted_at, p.codigo_parametro
                  FROM valor_parametro v
                  JOIN parametro_sistema p USING(id_parametro_sistema)
                 WHERE p.codigo_parametro IN
                   ('DIA_CIERRE_COMERCIAL',
                    'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
                   AND v.id_sucursal IS NULL AND v.id_instalacion IS NULL
                   {deleted_filter}
                 ORDER BY p.codigo_parametro, v.fecha_desde,
                          v.id_valor_parametro
                 FOR UPDATE OF v
                """)
            ).mappings()
        ]

    def inspect_bootstrap_state(self) -> tuple[bool, dict[str, int]]:
        roots = self.lock_roots()
        valid_definitions, ids = self.lock_definitions()
        history = self.lock_history(include_deleted=True)
        return valid_definitions and not roots and not history, ids

    def create(
        self,
        *,
        definitions: dict[str, int],
        values: dict[str, int],
        vigente_desde: date,
        op_id: UUID,
        id_instalacion: int,
    ) -> dict[str, Any]:
        root = (
            self.session.execute(
                text("""
                INSERT INTO configuracion_calendario_comercial(
                    id_instalacion_origen,id_instalacion_ultima_modificacion,
                    op_id_alta,op_id_ultima_modificacion)
                VALUES (:inst,:inst,:op,:op)
                RETURNING id_configuracion_calendario_comercial,
                          uid_global,version_registro
            """),
                {"inst": id_instalacion, "op": op_id},
            )
            .mappings()
            .one()
        )
        created_values: dict[str, dict[str, Any]] = {}
        for code, parameter_id in definitions.items():
            # valor_parametro exige op_id_alta único por fila; se derivan IDs
            # determinísticos del command, sin perder su procedencia.
            child_op_id = uuid5(op_id, code)
            row = (
                self.session.execute(
                    text("""
                INSERT INTO valor_parametro(
                    id_parametro_sistema,valor_parametro,es_valor_vigente,
                    fecha_desde,fecha_hasta,id_instalacion_origen,
                    id_instalacion_ultima_modificacion,op_id_alta,
                    op_id_ultima_modificacion)
                VALUES (:pid,:value,true,:start,NULL,:inst,:inst,:op,:op)
                RETURNING uid_global, version_registro, fecha_desde, fecha_hasta
            """),
                    {
                        "pid": parameter_id,
                        "value": str(values[code]),
                        "start": vigente_desde,
                        "inst": id_instalacion,
                        "op": child_op_id,
                    },
                )
                .mappings()
                .one()
            )
            created_values[code] = {"codigo_parametro": code, **dict(row)}
        return {"root": dict(root), "values": created_values}

    def lock_active_root(self) -> dict[str, Any] | None:
        rows = self.lock_roots()
        return rows[0] if len(rows) == 1 and rows[0]["deleted_at"] is None else None

    def lock_and_inspect_history(self) -> tuple[dict[str, int], list[dict[str, Any]]]:
        valid, definitions = self.lock_definitions()
        if not valid:
            return {}, []
        return definitions, self.lock_history()

    def program(
        self,
        *,
        root_id: int,
        definitions: dict[str, int],
        previous: list[dict[str, Any]],
        values: dict[str, int],
        vigente_desde: date,
        op_id: UUID,
        id_instalacion: int,
    ) -> dict[str, Any]:
        previous_by_code = {row["codigo_parametro"]: row for row in previous}
        for row in previous:
            self.session.execute(
                text("""
                UPDATE valor_parametro SET fecha_hasta=:start,
                       es_valor_vigente=false,
                       id_instalacion_ultima_modificacion=:inst,
                       op_id_ultima_modificacion=:op
                 WHERE id_valor_parametro=:id
            """),
                {
                    "start": vigente_desde,
                    "inst": id_instalacion,
                    "op": op_id,
                    "id": row["id_valor_parametro"],
                },
            )
        created: dict[str, dict[str, Any]] = {}
        for code, parameter_id in definitions.items():
            row = (
                self.session.execute(
                    text("""
                INSERT INTO valor_parametro(
                    id_parametro_sistema,valor_parametro,es_valor_vigente,
                    fecha_desde,fecha_hasta,id_instalacion_origen,
                    id_instalacion_ultima_modificacion,op_id_alta,
                    op_id_ultima_modificacion)
                VALUES (:pid,:value,true,:start,NULL,:inst,:inst,:op,:op)
                RETURNING uid_global,version_registro,fecha_desde,fecha_hasta
            """),
                    {
                        "pid": parameter_id,
                        "value": str(values[code]),
                        "start": vigente_desde,
                        "inst": id_instalacion,
                        "op": uuid5(op_id, code),
                    },
                )
                .mappings()
                .one()
            )
            created[code] = {"codigo_parametro": code, **dict(row)}
        root = (
            self.session.execute(
                text("""
            UPDATE configuracion_calendario_comercial
               SET id_instalacion_ultima_modificacion=:inst,
                   op_id_ultima_modificacion=:op
             WHERE id_configuracion_calendario_comercial=:id
             RETURNING id_configuracion_calendario_comercial,uid_global,
                       version_registro
        """),
                {"inst": id_instalacion, "op": op_id, "id": root_id},
            )
            .mappings()
            .one()
        )
        return {"root": dict(root), "values": created, "previous": previous_by_code}
