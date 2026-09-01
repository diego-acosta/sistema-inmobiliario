from __future__ import annotations

from typing import Any
from uuid import uuid5

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.infrastructure.persistence.repositories.calendario_comercial_command_repository import (
    CODIGOS,
)


class CalendarioComercialSyncCasLost(RuntimeError):
    """El snapshot cambió entre el lock/lectura y el CAS remoto."""


class CalendarioComercialSyncRepository:
    """Persistencia receptora de calendario; nunca confirma la transacción."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def lock_global(self) -> None:
        self.session.execute(text("SELECT pg_advisory_xact_lock(759942885, 986974765)"))

    def lock_definitions(self) -> tuple[str, dict[str, int]]:
        rows = (
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
            )
            .mappings()
            .all()
        )
        if len(rows) != len(CODIGOS):
            return "MISSING", {}
        if not all(
            row["codigo_tipo_dato"] == "ENTERO"
            and row["codigo_alcance"] == "GLOBAL"
            and row["exponible_api_administrativa"]
            and not row["es_sensible"]
            and row["editable_administrativamente"]
            for row in rows
        ):
            return "INCOMPATIBLE", {}
        return "READY", {
            row["codigo_parametro"]: row["id_parametro_sistema"] for row in rows
        }

    def lock_roots(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.session.execute(
                text("""
                SELECT id_configuracion_calendario_comercial, uid_global,
                       version_registro, deleted_at, op_id_alta,
                       op_id_ultima_modificacion
                  FROM configuracion_calendario_comercial
                 ORDER BY id_configuracion_calendario_comercial
                 FOR UPDATE
                """)
            )
            .mappings()
            .all()
        ]

    def lock_history(self) -> list[dict[str, Any]]:
        return [
            dict(row)
            for row in self.session.execute(
                text("""
                SELECT v.id_valor_parametro, v.id_parametro_sistema,
                       v.uid_global, v.version_registro, v.valor_parametro,
                       v.es_valor_vigente, v.fecha_desde, v.fecha_hasta,
                       v.deleted_at, p.codigo_parametro
                  FROM valor_parametro v
                  JOIN parametro_sistema p USING(id_parametro_sistema)
                 WHERE p.codigo_parametro IN
                   ('DIA_CIERRE_COMERCIAL',
                    'DIA_VENCIMIENTO_PREDETERMINADO_CUOTAS')
                   AND v.id_sucursal IS NULL AND v.id_instalacion IS NULL
                 ORDER BY p.codigo_parametro, v.fecha_desde,
                          v.id_valor_parametro
                 FOR UPDATE OF v
                """)
            )
            .mappings()
            .all()
        ]

    def child_uid_owners(self, uids: set[str]) -> dict[str, dict[str, Any]]:
        if not uids:
            return {}
        rows = (
            self.session.execute(
                text("""
                SELECT v.uid_global, v.id_valor_parametro, p.codigo_parametro
                  FROM valor_parametro v
                  JOIN parametro_sistema p USING(id_parametro_sistema)
                 WHERE v.uid_global = ANY(CAST(:uids AS uuid[]))
                """),
                {"uids": sorted(uids)},
            )
            .mappings()
            .all()
        )
        return {str(row["uid_global"]): dict(row) for row in rows}

    def create_remote(
        self,
        *,
        definitions: dict[str, int],
        envelope: dict[str, Any],
    ) -> None:
        self.session.execute(
            text("""
            INSERT INTO configuracion_calendario_comercial(
                uid_global, version_registro, op_id_alta,
                op_id_ultima_modificacion)
            VALUES (CAST(:uid AS uuid), 1, CAST(:op AS uuid), CAST(:op AS uuid))
            """),
            {"uid": envelope["aggregate_uid"], "op": envelope["op_id"]},
        )
        for code in CODIGOS:
            value = envelope["values"][code]
            self.session.execute(
                text("""
                INSERT INTO valor_parametro(
                    id_parametro_sistema, uid_global, valor_parametro,
                    es_valor_vigente, fecha_desde, fecha_hasta,
                    version_registro, op_id_alta, op_id_ultima_modificacion)
                VALUES (
                    :parameter_id, CAST(:uid AS uuid), :value, true,
                    CAST(:start AS timestamp), NULL, 1,
                    CAST(:child_op AS uuid), CAST(:child_op AS uuid)
                )
                """),
                {
                    "parameter_id": definitions[code],
                    "uid": value["uid_global"],
                    "value": str(value["value"]),
                    "start": envelope["vigente_desde"],
                    "child_op": str(uuid5(envelope["op_id_uuid"], code)),
                },
            )

    def apply_programming(
        self,
        *,
        root_id: int,
        definitions: dict[str, int],
        previous_by_code: dict[str, dict[str, Any]],
        envelope: dict[str, Any],
    ) -> int:
        for code in CODIGOS:
            previous = previous_by_code[code]
            updated_version = self.session.execute(
                text("""
                UPDATE valor_parametro
                   SET fecha_hasta=CAST(:end AS timestamp),
                       es_valor_vigente=false,
                       op_id_ultima_modificacion=CAST(:op AS uuid)
                 WHERE id_valor_parametro=:id
                   AND version_registro=:expected_version
                 RETURNING version_registro
                """),
                {
                    "end": envelope["vigente_desde"],
                    "op": envelope["op_id"],
                    "id": previous["id_valor_parametro"],
                    "expected_version": previous["version_registro"],
                },
            ).scalar_one_or_none()
            if updated_version != envelope["previous_values"][code]["version_registro"]:
                raise CalendarioComercialSyncCasLost("CALENDARIO_SYNC_CAS_LOST")

        for code in CODIGOS:
            value = envelope["values"][code]
            self.session.execute(
                text("""
                INSERT INTO valor_parametro(
                    id_parametro_sistema, uid_global, valor_parametro,
                    es_valor_vigente, fecha_desde, fecha_hasta,
                    version_registro, op_id_alta, op_id_ultima_modificacion)
                VALUES (
                    :parameter_id, CAST(:uid AS uuid), :value, true,
                    CAST(:start AS timestamp), NULL, 1,
                    CAST(:child_op AS uuid), CAST(:child_op AS uuid)
                )
                """),
                {
                    "parameter_id": definitions[code],
                    "uid": value["uid_global"],
                    "value": str(value["value"]),
                    "start": envelope["vigente_desde"],
                    "child_op": str(uuid5(envelope["op_id_uuid"], code)),
                },
            )

        return self.session.execute(
            text("""
            UPDATE configuracion_calendario_comercial
               SET op_id_ultima_modificacion=CAST(:op AS uuid)
             WHERE id_configuracion_calendario_comercial=:id
               AND version_registro=:expected_version
             RETURNING version_registro
            """),
            {
                "op": envelope["op_id"],
                "id": root_id,
                "expected_version": envelope["version_agregada_anterior"],
            },
        ).scalar_one_or_none()
