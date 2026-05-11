from typing import Any, Callable

import flet as ft


ColumnDef = tuple[str, str]


def entity_table(
    *,
    columns: list[ColumnDef],
    rows: list[dict[str, Any]],
    actions: Callable[[dict[str, Any]], list[ft.Control]] | None = None,
) -> ft.Control:
    table_columns = [ft.DataColumn(ft.Text(label)) for label, _ in columns]
    if actions is not None:
        table_columns.append(ft.DataColumn(ft.Text("Acciones")))

    table_rows: list[ft.DataRow] = []
    for row in rows:
        cells = [ft.DataCell(ft.Text(_cell(row.get(key)))) for _, key in columns]
        if actions is not None:
            cells.append(ft.DataCell(ft.Row(actions(row), spacing=6)))
        table_rows.append(ft.DataRow(cells=cells))

    return ft.Row(
        controls=[
            ft.DataTable(
                columns=table_columns,
                rows=table_rows,
                heading_row_color=ft.Colors.BLUE_GREY_50,
                data_row_min_height=44,
                data_row_max_height=64,
            )
        ],
        scroll=ft.ScrollMode.AUTO,
    )


def _cell(value: object) -> str:
    if value is None:
        return "-"
    if isinstance(value, dict):
        return value.get("numero_documento") or value.get("valor_contacto") or "-"
    return str(value)
