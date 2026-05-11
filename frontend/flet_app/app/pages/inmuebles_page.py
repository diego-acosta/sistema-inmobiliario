import flet as ft


class InmueblesPage:
    def build(self) -> ft.Control:
        return ft.Column(
            controls=[
                ft.Text("Inmuebles", size=28, weight=ft.FontWeight.W_700),
                ft.Text("Modulo Inmuebles pendiente de UI"),
            ],
            spacing=12,
        )
