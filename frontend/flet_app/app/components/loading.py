import flet as ft


def loading_view(message: str = "Cargando...") -> ft.Control:
    return ft.Row(
        controls=[
            ft.ProgressRing(width=18, height=18, stroke_width=2),
            ft.Text(message),
        ],
        spacing=12,
        vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
