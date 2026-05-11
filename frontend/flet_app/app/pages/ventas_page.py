import flet as ft


class VentasPage:
    def build(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Ventas", size=28, weight=ft.FontWeight.W_700),
                ft.Text("Modulo Ventas pendiente de UI"),
            ],
            spacing=12,
        )
