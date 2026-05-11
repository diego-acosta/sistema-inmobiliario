import flet as ft


def detail_section(title: str, controls: list[ft.Control]) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text(title, size=18, weight=ft.FontWeight.W_600),
                ft.Divider(height=1),
                *controls,
            ],
            spacing=10,
        ),
        padding=16,
        border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
        border_radius=6,
    )


def key_value_grid(items: list[tuple[str, object]]) -> ft.Control:
    rows: list[ft.Control] = []
    for label, value in items:
        rows.append(
            ft.Row(
                controls=[
                    ft.Text(label, width=190, color=ft.Colors.BLUE_GREY_700),
                    ft.Text(_format_value(value), selectable=True),
                ],
                vertical_alignment=ft.CrossAxisAlignment.START,
            )
        )
    return ft.Column(controls=rows, spacing=6)


def _format_value(value: object) -> str:
    if value is None:
        return "-"
    return str(value)
