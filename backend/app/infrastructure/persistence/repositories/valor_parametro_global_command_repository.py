from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


class ValorParametroGlobalCommandRepository:
    """Persistencia específica update-only de #412, sin fronteras transaccionales."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def validate_context(self, id_sucursal: int, id_instalacion: int) -> dict | None:
        row = (
            self.session.execute(
                text("""
            SELECT i.uid_global
              FROM public.sucursal s
              JOIN public.instalacion i ON i.id_sucursal = s.id_sucursal
             WHERE s.id_sucursal = :id_sucursal
               AND i.id_instalacion = :id_instalacion
        """),
                {"id_sucursal": id_sucursal, "id_instalacion": id_instalacion},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def find_target(self, codigo_parametro: str) -> tuple[str, int | None]:
        rows = (
            self.session.execute(
                text("""
            SELECT p.exponible_api_administrativa, p.es_sensible,
                   p.editable_administrativamente, t.codigo_tipo_dato,
                   a.codigo_alcance, v.id_valor_parametro
              FROM public.parametro_sistema p
              LEFT JOIN public.tipo_dato_parametro t
                ON t.id_tipo_dato_parametro = p.id_tipo_dato_parametro
              LEFT JOIN public.alcance_parametro a
                ON a.id_alcance_parametro = p.id_alcance_parametro
              LEFT JOIN public.valor_parametro v
                ON v.id_parametro_sistema = p.id_parametro_sistema
               AND v.id_sucursal IS NULL AND v.id_instalacion IS NULL
               AND v.es_valor_vigente = true AND v.deleted_at IS NULL
             WHERE p.codigo_parametro = :codigo
        """),
                {"codigo": codigo_parametro},
            )
            .mappings()
            .all()
        )
        if not rows:
            return "NOT_FOUND", None
        first = rows[0]
        if not first["exponible_api_administrativa"] or first["es_sensible"]:
            return "NOT_FOUND", None
        if (
            not first["editable_administrativamente"]
            or first["codigo_tipo_dato"] != "ENTERO"
            or first["codigo_alcance"] != "GLOBAL"
        ):
            return "CONFLICT", None
        targets = [
            row["id_valor_parametro"]
            for row in rows
            if row["id_valor_parametro"] is not None
        ]
        if len(targets) != 1:
            return "CONFLICT", None
        return "OK", targets[0]

    def lock_target(self, id_valor_parametro: int) -> dict[str, Any] | None:
        row = (
            self.session.execute(
                text("""
            SELECT v.id_valor_parametro, v.uid_global,
                   v.valor_parametro AS valor_raw, v.version_registro,
                   v.updated_at, v.id_instalacion_origen,
                   v.id_instalacion_ultima_modificacion, v.op_id_alta,
                   v.op_id_ultima_modificacion, v.id_sucursal, v.id_instalacion,
                   v.es_valor_vigente, v.deleted_at,
                   p.exponible_api_administrativa, p.es_sensible,
                   p.editable_administrativamente, t.codigo_tipo_dato,
                   a.codigo_alcance
              FROM public.valor_parametro v
              JOIN public.parametro_sistema p
                ON p.id_parametro_sistema = v.id_parametro_sistema
              JOIN public.tipo_dato_parametro t
                ON t.id_tipo_dato_parametro = p.id_tipo_dato_parametro
              JOIN public.alcance_parametro a
                ON a.id_alcance_parametro = p.id_alcance_parametro
             WHERE v.id_valor_parametro = :id
             FOR UPDATE OF v
        """),
                {"id": id_valor_parametro},
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None

    def cas_update(
        self,
        *,
        id_valor_parametro: int,
        valor_parametro: str,
        op_id,
        id_instalacion: int,
        if_match_version: int,
    ) -> dict | None:
        row = (
            self.session.execute(
                text("""
            UPDATE public.valor_parametro
               SET valor_parametro = :valor_parametro,
                   op_id_ultima_modificacion = :op_id,
                   id_instalacion_ultima_modificacion = :id_instalacion
             WHERE id_valor_parametro = :id_valor_parametro
               AND version_registro = :if_match_version
             RETURNING id_valor_parametro, uid_global,
                       valor_parametro AS valor_raw, version_registro, updated_at,
                       id_instalacion_origen, id_instalacion_ultima_modificacion,
                       op_id_alta, op_id_ultima_modificacion
        """),
                {
                    "id_valor_parametro": id_valor_parametro,
                    "valor_parametro": valor_parametro,
                    "op_id": op_id,
                    "id_instalacion": id_instalacion,
                    "if_match_version": if_match_version,
                },
            )
            .mappings()
            .one_or_none()
        )
        return dict(row) if row is not None else None
