from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from os import getenv
from pathlib import Path
from typing import Any

from dotenv import dotenv_values
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


BASE_DIR = Path(__file__).resolve().parents[1]
LEGACY_SUFFIX = "_legacy"


@dataclass
class ForeignKeyRow:
    source_schema: str
    source_table: str
    source_columns: list[str]
    constraint_name: str
    target_schema: str
    target_table: str
    target_columns: list[str]

    @property
    def is_current_to_legacy(self) -> bool:
        return not self.source_table.endswith(LEGACY_SUFFIX)

    @property
    def severity(self) -> str:
        return "CRITICO" if self.is_current_to_legacy else "MEDIO"


@dataclass
class LegacyReferenceSummary:
    schema: str
    legacy_table: str
    incoming_fk_count: int
    referenced_by: list[str]
    severity: str


@dataclass
class NamingConflict:
    schema: str
    current_table: str
    legacy_table: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Inspecciona la base PostgreSQL configurada para detectar "
            "inconsistencias legacy en claves foraneas."
        )
    )
    parser.add_argument(
        "--db-url",
        help="URL de conexion PostgreSQL explicita. Tiene prioridad sobre .env.",
    )
    parser.add_argument(
        "--env-file",
        help=(
            "Archivo .env a usar. Si no se informa, replica la logica del backend: "
            "ENV=test usa .env.test; en otro caso usa .env."
        ),
    )
    parser.add_argument(
        "--json-out",
        help="Ruta opcional para exportar el reporte en JSON.",
    )
    parser.add_argument(
        "--md-out",
        help="Ruta opcional para exportar el reporte en Markdown.",
    )
    return parser.parse_args()


def resolve_env_file(explicit_env_file: str | None) -> Path:
    if explicit_env_file:
        env_path = Path(explicit_env_file)
        return env_path if env_path.is_absolute() else (BASE_DIR / env_path)

    env = getenv("ENV", "dev").strip().lower()
    return BASE_DIR / (".env.test" if env == "test" else ".env")


def resolve_database_url(db_url: str | None, env_file: Path) -> tuple[str, dict[str, Any]]:
    metadata: dict[str, Any] = {
        "database_url_source": "argument" if db_url else "env_file",
        "env_file": str(env_file),
    }

    if db_url:
        return db_url, metadata

    if not env_file.exists():
        raise ValueError(f"No existe el archivo de entorno: {env_file}")

    env_values = dotenv_values(env_file)
    database_url = env_values.get("DATABASE_URL")
    if not database_url:
        raise ValueError(f"DATABASE_URL no esta definida en: {env_file}")
    return database_url, metadata


def fetch_legacy_foreign_keys(connection: Any) -> list[ForeignKeyRow]:
    query = text(
        """
        SELECT
            src_ns.nspname AS source_schema,
            src.relname AS source_table,
            con.conname AS constraint_name,
            tgt_ns.nspname AS target_schema,
            tgt.relname AS target_table,
            array_agg(src_att.attname ORDER BY src_cols.ord) AS source_columns,
            array_agg(tgt_att.attname ORDER BY tgt_cols.ord) AS target_columns
        FROM pg_constraint con
        JOIN pg_class src ON src.oid = con.conrelid
        JOIN pg_namespace src_ns ON src_ns.oid = src.relnamespace
        JOIN pg_class tgt ON tgt.oid = con.confrelid
        JOIN pg_namespace tgt_ns ON tgt_ns.oid = tgt.relnamespace
        JOIN unnest(con.conkey) WITH ORDINALITY AS src_cols(attnum, ord) ON TRUE
        JOIN pg_attribute src_att
          ON src_att.attrelid = con.conrelid
         AND src_att.attnum = src_cols.attnum
        JOIN unnest(con.confkey) WITH ORDINALITY AS tgt_cols(attnum, ord)
          ON tgt_cols.ord = src_cols.ord
        JOIN pg_attribute tgt_att
          ON tgt_att.attrelid = con.confrelid
         AND tgt_att.attnum = tgt_cols.attnum
        WHERE con.contype = 'f'
          AND tgt.relname LIKE :legacy_pattern
        GROUP BY
            src_ns.nspname,
            src.relname,
            con.conname,
            tgt_ns.nspname,
            tgt.relname
        ORDER BY
            src_ns.nspname,
            src.relname,
            con.conname
        """
    )
    rows = connection.execute(
        query, {"legacy_pattern": f"%{LEGACY_SUFFIX}"}
    ).mappings()
    return [
        ForeignKeyRow(
            source_schema=row["source_schema"],
            source_table=row["source_table"],
            source_columns=list(row["source_columns"]),
            constraint_name=row["constraint_name"],
            target_schema=row["target_schema"],
            target_table=row["target_table"],
            target_columns=list(row["target_columns"]),
        )
        for row in rows
    ]


def fetch_legacy_tables(connection: Any) -> list[tuple[str, str]]:
    query = text(
        """
        SELECT n.nspname AS schema_name, c.relname AS table_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r'
          AND c.relname LIKE :legacy_pattern
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        ORDER BY n.nspname, c.relname
        """
    )
    rows = connection.execute(
        query, {"legacy_pattern": f"%{LEGACY_SUFFIX}"}
    ).mappings()
    return [(row["schema_name"], row["table_name"]) for row in rows]


def fetch_current_tables(connection: Any) -> set[tuple[str, str]]:
    query = text(
        """
        SELECT n.nspname AS schema_name, c.relname AS table_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        WHERE c.relkind = 'r'
          AND c.relname NOT LIKE :legacy_pattern
          AND n.nspname NOT IN ('pg_catalog', 'information_schema')
        """
    )
    rows = connection.execute(
        query, {"legacy_pattern": f"%{LEGACY_SUFFIX}"}
    ).mappings()
    return {(row["schema_name"], row["table_name"]) for row in rows}


def build_legacy_reference_summary(
    legacy_tables: list[tuple[str, str]], legacy_foreign_keys: list[ForeignKeyRow]
) -> list[LegacyReferenceSummary]:
    incoming: dict[tuple[str, str], list[str]] = defaultdict(list)
    for fk in legacy_foreign_keys:
        key = (fk.target_schema, fk.target_table)
        incoming[key].append(
            f"{fk.source_schema}.{fk.source_table} ({fk.constraint_name})"
        )

    summaries: list[LegacyReferenceSummary] = []
    for schema_name, table_name in legacy_tables:
        refs = sorted(incoming.get((schema_name, table_name), []))
        summaries.append(
            LegacyReferenceSummary(
                schema=schema_name,
                legacy_table=table_name,
                incoming_fk_count=len(refs),
                referenced_by=refs,
                severity="MEDIO" if refs else "BAJO",
            )
        )
    return summaries


def build_naming_conflicts(
    legacy_tables: list[tuple[str, str]], current_tables: set[tuple[str, str]]
) -> list[NamingConflict]:
    conflicts: list[NamingConflict] = []
    for schema_name, legacy_table in legacy_tables:
        if not legacy_table.endswith(LEGACY_SUFFIX):
            continue
        current_name = legacy_table[: -len(LEGACY_SUFFIX)]
        if (schema_name, current_name) in current_tables:
            conflicts.append(
                NamingConflict(
                    schema=schema_name,
                    current_table=current_name,
                    legacy_table=legacy_table,
                )
            )
    return sorted(conflicts, key=lambda item: (item.schema, item.current_table))


def build_priority_alerts(
    legacy_foreign_keys: list[ForeignKeyRow],
    legacy_reference_summary: list[LegacyReferenceSummary],
    naming_conflicts: list[NamingConflict],
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []

    for fk in legacy_foreign_keys:
        if fk.is_current_to_legacy:
            alerts.append(
                {
                    "severity": "CRITICO",
                    "message": (
                        f"La tabla actual {fk.source_schema}.{fk.source_table} depende "
                        f"de {fk.target_schema}.{fk.target_table} mediante "
                        f"{fk.constraint_name}."
                    ),
                }
            )

    for summary in legacy_reference_summary:
        if summary.incoming_fk_count > 0:
            alerts.append(
                {
                    "severity": "MEDIO",
                    "message": (
                        f"La tabla legacy {summary.schema}.{summary.legacy_table} "
                        f"sigue recibiendo {summary.incoming_fk_count} FK(s)."
                    ),
                }
            )
        else:
            alerts.append(
                {
                    "severity": "BAJO",
                    "message": (
                        f"La tabla legacy {summary.schema}.{summary.legacy_table} "
                        "existe sin referencias activas."
                    ),
                }
            )

    for conflict in naming_conflicts:
        alerts.append(
            {
                "severity": "MEDIO",
                "message": (
                    f"Coexisten {conflict.schema}.{conflict.current_table} y "
                    f"{conflict.schema}.{conflict.legacy_table}; revisar posibles "
                    "desalineaciones entre modelo actual y legacy."
                ),
            }
        )

    severity_order = {"CRITICO": 0, "MEDIO": 1, "BAJO": 2}
    return sorted(alerts, key=lambda item: (severity_order[item["severity"]], item["message"]))


def report_to_dict(
    database_url_source: dict[str, Any],
    database_name: str,
    legacy_foreign_keys: list[ForeignKeyRow],
    current_to_legacy: list[ForeignKeyRow],
    legacy_reference_summary: list[LegacyReferenceSummary],
    naming_conflicts: list[NamingConflict],
    alerts: list[dict[str, str]],
) -> dict[str, Any]:
    def serialize_foreign_key(item: ForeignKeyRow) -> dict[str, Any]:
        payload = asdict(item)
        payload["severity"] = item.severity
        payload["is_current_to_legacy"] = item.is_current_to_legacy
        return payload

    return {
        "metadata": {
            **database_url_source,
            "database_name": database_name,
        },
        "summary": {
            "legacy_fk_count": len(legacy_foreign_keys),
            "current_to_legacy_fk_count": len(current_to_legacy),
            "legacy_tables_detected": len(legacy_reference_summary),
            "naming_conflicts_detected": len(naming_conflicts),
            "critical_alert_count": sum(
                1 for alert in alerts if alert["severity"] == "CRITICO"
            ),
        },
        "legacy_foreign_keys": [
            serialize_foreign_key(item) for item in legacy_foreign_keys
        ],
        "current_to_legacy_dependencies": [
            serialize_foreign_key(item) for item in current_to_legacy
        ],
        "legacy_reference_summary": [
            asdict(item) for item in legacy_reference_summary
        ],
        "naming_conflicts": [asdict(item) for item in naming_conflicts],
        "priority_alerts": alerts,
    }


def format_console_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    summary = report["summary"]
    metadata = report["metadata"]

    lines.append("=== Resumen general ===")
    lines.append(f"Base: {metadata['database_name']}")
    lines.append(f"Origen DATABASE_URL: {metadata['database_url_source']}")
    lines.append(f"Archivo de entorno: {metadata['env_file']}")
    lines.append(f"FKs hacia _legacy: {summary['legacy_fk_count']}")
    lines.append(
        "Tablas actuales que dependen de _legacy: "
        f"{summary['current_to_legacy_fk_count']}"
    )
    lines.append(f"Tablas _legacy detectadas: {summary['legacy_tables_detected']}")
    lines.append(
        f"Conflictos de naming detectados: {summary['naming_conflicts_detected']}"
    )
    lines.append("")

    lines.append("=== FKs hacia _legacy ===")
    if report["legacy_foreign_keys"]:
        for fk in report["legacy_foreign_keys"]:
            lines.append(
                "- "
                f"{fk['source_schema']}.{fk['source_table']} "
                f"({', '.join(fk['source_columns'])}) -> "
                f"{fk['target_schema']}.{fk['target_table']} "
                f"({', '.join(fk['target_columns'])}) "
                f"[{fk['constraint_name']}] "
                f"SEVERIDAD={fk['severity']}"
            )
    else:
        lines.append("- Sin hallazgos.")
    lines.append("")

    lines.append("=== Tablas actuales que dependen de _legacy ===")
    if report["current_to_legacy_dependencies"]:
        for fk in report["current_to_legacy_dependencies"]:
            lines.append(
                "- "
                f"{fk['source_schema']}.{fk['source_table']} depende de "
                f"{fk['target_schema']}.{fk['target_table']} "
                f"via {fk['constraint_name']}"
            )
    else:
        lines.append("- Sin hallazgos.")
    lines.append("")

    lines.append("=== Tablas _legacy todavia activas por referencia ===")
    for summary_item in report["legacy_reference_summary"]:
        refs = summary_item["referenced_by"]
        lines.append(
            "- "
            f"{summary_item['schema']}.{summary_item['legacy_table']}: "
            f"{summary_item['incoming_fk_count']} FK(s) entrante(s), "
            f"SEVERIDAD={summary_item['severity']}"
        )
        if refs:
            for ref in refs:
                lines.append(f"  referencia desde: {ref}")
    if not report["legacy_reference_summary"]:
        lines.append("- Sin tablas _legacy detectadas.")
    lines.append("")

    lines.append("=== Posibles conflictos de naming ===")
    if report["naming_conflicts"]:
        for item in report["naming_conflicts"]:
            lines.append(
                "- "
                f"{item['schema']}.{item['current_table']} <-> "
                f"{item['schema']}.{item['legacy_table']}"
            )
    else:
        lines.append("- Sin conflictos detectados por sufijo _legacy.")
    lines.append("")

    lines.append("=== Alertas prioritarias ===")
    if report["priority_alerts"]:
        for alert in report["priority_alerts"]:
            lines.append(f"- [{alert['severity']}] {alert['message']}")
    else:
        lines.append("- Sin alertas.")

    return "\n".join(lines)


def format_markdown_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    metadata = report["metadata"]

    lines: list[str] = [
        "# Legacy Inconsistencies Report",
        "",
        "## Resumen general",
        "",
        f"- Base: `{metadata['database_name']}`",
        f"- Origen DATABASE_URL: `{metadata['database_url_source']}`",
        f"- Archivo de entorno: `{metadata['env_file']}`",
        f"- FKs hacia `_legacy`: `{summary['legacy_fk_count']}`",
        (
            "- Tablas actuales que dependen de `_legacy`: "
            f"`{summary['current_to_legacy_fk_count']}`"
        ),
        f"- Tablas `_legacy` detectadas: `{summary['legacy_tables_detected']}`",
        (
            "- Conflictos de naming detectados: "
            f"`{summary['naming_conflicts_detected']}`"
        ),
        "",
        "## FKs hacia `_legacy`",
        "",
    ]

    if report["legacy_foreign_keys"]:
        for fk in report["legacy_foreign_keys"]:
            lines.append(
                "- "
                f"`{fk['source_schema']}.{fk['source_table']}` "
                f"({', '.join(fk['source_columns'])}) -> "
                f"`{fk['target_schema']}.{fk['target_table']}` "
                f"({', '.join(fk['target_columns'])}) "
                f"[`{fk['constraint_name']}`] `{fk['severity']}`"
            )
    else:
        lines.append("- Sin hallazgos.")

    lines.extend(["", "## Tablas actuales que dependen de `_legacy`", ""])
    if report["current_to_legacy_dependencies"]:
        for fk in report["current_to_legacy_dependencies"]:
            lines.append(
                "- "
                f"`{fk['source_schema']}.{fk['source_table']}` depende de "
                f"`{fk['target_schema']}.{fk['target_table']}` via "
                f"`{fk['constraint_name']}`"
            )
    else:
        lines.append("- Sin hallazgos.")

    lines.extend(["", "## Tablas `_legacy` todavia activas por referencia", ""])
    if report["legacy_reference_summary"]:
        for summary_item in report["legacy_reference_summary"]:
            lines.append(
                "- "
                f"`{summary_item['schema']}.{summary_item['legacy_table']}`: "
                f"`{summary_item['incoming_fk_count']}` FK(s), "
                f"`{summary_item['severity']}`"
            )
            for ref in summary_item["referenced_by"]:
                lines.append(f"  referencia desde `{ref}`")
    else:
        lines.append("- Sin tablas `_legacy` detectadas.")

    lines.extend(["", "## Posibles conflictos de naming", ""])
    if report["naming_conflicts"]:
        for item in report["naming_conflicts"]:
            lines.append(
                "- "
                f"`{item['schema']}.{item['current_table']}` <-> "
                f"`{item['schema']}.{item['legacy_table']}`"
            )
    else:
        lines.append("- Sin conflictos detectados por sufijo `_legacy`.")

    lines.extend(["", "## Alertas prioritarias", ""])
    if report["priority_alerts"]:
        for alert in report["priority_alerts"]:
            lines.append(f"- **{alert['severity']}** {alert['message']}")
    else:
        lines.append("- Sin alertas.")

    return "\n".join(lines)


def write_output(path_str: str, content: str) -> None:
    output_path = Path(path_str)
    if not output_path.is_absolute():
        output_path = BASE_DIR / output_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")


def main() -> int:
    args = parse_args()
    env_file = resolve_env_file(args.env_file)

    try:
        database_url, metadata = resolve_database_url(args.db_url, env_file)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    try:
        engine = create_engine(database_url, future=True, pool_pre_ping=True)
        with engine.connect() as connection:
            database_name = connection.execute(text("select current_database()")).scalar_one()
            legacy_foreign_keys = fetch_legacy_foreign_keys(connection)
            legacy_tables = fetch_legacy_tables(connection)
            current_tables = fetch_current_tables(connection)
    except SQLAlchemyError as exc:
        print("ERROR: no se pudo conectar o inspeccionar la base.", file=sys.stderr)
        print(str(exc), file=sys.stderr)
        return 1

    current_to_legacy = [
        fk for fk in legacy_foreign_keys if fk.is_current_to_legacy
    ]
    legacy_reference_summary = build_legacy_reference_summary(
        legacy_tables, legacy_foreign_keys
    )
    naming_conflicts = build_naming_conflicts(legacy_tables, current_tables)
    alerts = build_priority_alerts(
        legacy_foreign_keys, legacy_reference_summary, naming_conflicts
    )

    report = report_to_dict(
        database_url_source=metadata,
        database_name=database_name,
        legacy_foreign_keys=legacy_foreign_keys,
        current_to_legacy=current_to_legacy,
        legacy_reference_summary=legacy_reference_summary,
        naming_conflicts=naming_conflicts,
        alerts=alerts,
    )

    console_report = format_console_report(report)
    print(console_report)

    if args.json_out:
        write_output(
            args.json_out,
            json.dumps(report, indent=2, ensure_ascii=False),
        )

    if args.md_out:
        write_output(args.md_out, format_markdown_report(report))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
