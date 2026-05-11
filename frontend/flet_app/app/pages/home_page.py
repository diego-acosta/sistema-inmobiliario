import flet as ft


class HomePage:
    def __init__(self, on_navigate) -> None:
        self.on_navigate = on_navigate

    def build(self) -> ft.Control:
        cards = [
            ("Partes", "Consulta de partes, roles y estado financiero.", "partes"),
            ("Inmuebles", "Ficha inmobiliaria integral.", "inmuebles"),
            ("Contratos", "Contratos de alquiler.", "contratos"),
            ("Ventas", "Ventas y condiciones comerciales.", "ventas"),
            ("Finanzas", "Estado de cuenta por parte.", "finanzas"),
        ]
        return ft.Column(
            controls=[
                ft.Text("Sistema Inmobiliario", size=32, weight=ft.FontWeight.W_700),
                ft.Text(
                    "V1 de consulta operativa. Las pantallas disponibles son de lectura, excepto flujos financieros que se habilitaran en bloques posteriores.",
                    color=ft.Colors.BLUE_GREY_700,
                ),
                ft.ResponsiveRow(
                    controls=[
                        ft.Container(
                            col={"sm": 12, "md": 6, "lg": 4},
                            content=ft.Container(
                                content=ft.Column(
                                    controls=[
                                        ft.Text(title, size=18, weight=ft.FontWeight.W_600),
                                        ft.Text(description, color=ft.Colors.BLUE_GREY_700),
                                        ft.ElevatedButton(
                                            "Abrir",
                                            on_click=lambda _, route=route: self.on_navigate(route),
                                        ),
                                    ],
                                    spacing=8,
                                ),
                                padding=16,
                                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                                border_radius=6,
                            ),
                        )
                        for title, description, route in cards
                    ],
                    spacing=12,
                    run_spacing=12,
                ),
            ],
            spacing=20,
            scroll=ft.ScrollMode.AUTO,
        )
