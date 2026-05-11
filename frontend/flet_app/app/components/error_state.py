import flet as ft


def error_state(message: str, on_retry=None) -> ft.Control:
    controls: list[ft.Control] = [
        ft.Icon(ft.Icons.ERROR_OUTLINE, color=ft.Colors.RED_600),
        ft.Text(message, color=ft.Colors.RED_700),
    ]
    if on_retry is not None:
        controls.append(ft.ElevatedButton("Reintentar", on_click=on_retry))
    return ft.Container(
        content=ft.Row(controls=controls, spacing=10),
        bgcolor=ft.Colors.RED_50,
        border=ft.border.all(1, ft.Colors.RED_100),
        border_radius=6,
        padding=12,
    )
