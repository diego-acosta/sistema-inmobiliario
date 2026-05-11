import flet as ft


class FinanzasPage:
    def build(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Finanzas", size=28, weight=ft.FontWeight.W_700),
                ft.Text("Modulo Finanzas pendiente de UI"),
            ],
            spacing=12,
        )
