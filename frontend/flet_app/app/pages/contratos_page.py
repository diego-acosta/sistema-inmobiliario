import flet as ft


class ContratosPage:
    def build(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Contratos", size=28, weight=ft.FontWeight.W_700),
                ft.Text("Modulo Contratos pendiente de UI"),
            ],
            spacing=12,
        )
