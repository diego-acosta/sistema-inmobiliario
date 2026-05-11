import flet as ft

from app.api_client import ApiClient
from app.config import get_api_base_url
from app.router import AppRouter, Route
from app.pages.contratos_page import ContratosPage
from app.pages.finanzas_page import FinanzasPage
from app.pages.home_page import HomePage
from app.pages.inmuebles_page import InmueblesPage
from app.pages.parte_detail_page import ParteDetailPage
from app.pages.partes_list_page import PartesListPage
from app.pages.ventas_page import VentasPage


class AppShell:
    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.router = AppRouter()
        self.api = ApiClient()
        self.content = ft.Container(expand=True, padding=24)
        self.rail = self._build_rail()

    def run(self) -> None:
        self.page.title = "Sistema Inmobiliario"
        self.page.window_width = 1280
        self.page.window_height = 820
        self.page.padding = 0
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.add(
            ft.Row(
                controls=[
                    ft.Container(
                        content=ft.Column(
                            controls=[
                                ft.Container(
                                    content=ft.Text(
                                        "Sistema\nInmobiliario",
                                        size=18,
                                        weight=ft.FontWeight.W_700,
                                    ),
                                    padding=16,
                                ),
                                ft.Container(
                                    content=self.rail,
                                    expand=True,
                                    alignment=ft.alignment.top_left,
                                ),
                                ft.Container(
                                    content=ft.Text(
                                        get_api_base_url(),
                                        size=11,
                                        color=ft.Colors.BLUE_GREY_500,
                                    ),
                                    padding=16,
                                ),
                            ],
                            expand=True,
                        ),
                        width=220,
                        bgcolor=ft.Colors.BLUE_GREY_50,
                    ),
                    ft.VerticalDivider(width=1),
                    self.content,
                ],
                expand=True,
                spacing=0,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        )
        self.navigate("home")

    def navigate(self, name: str, **params) -> None:
        route = self.router.go(name, **params)
        self._sync_rail(route)
        self.content.content = self._render_route(route)
        self.page.update()

    def _build_rail(self) -> ft.NavigationRail:
        return ft.NavigationRail(
            selected_index=0,
            label_type=ft.NavigationRailLabelType.ALL,
            destinations=[
                ft.NavigationRailDestination(
                    icon=ft.Icons.HOME_OUTLINED,
                    selected_icon=ft.Icons.HOME,
                    label="Inicio",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.GROUP_OUTLINED,
                    selected_icon=ft.Icons.GROUP,
                    label="Partes",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.APARTMENT_OUTLINED,
                    selected_icon=ft.Icons.APARTMENT,
                    label="Inmuebles",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.DESCRIPTION_OUTLINED,
                    selected_icon=ft.Icons.DESCRIPTION,
                    label="Contratos",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                    selected_icon=ft.Icons.RECEIPT_LONG,
                    label="Ventas",
                ),
                ft.NavigationRailDestination(
                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET_OUTLINED,
                    selected_icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                    label="Finanzas",
                ),
            ],
            on_change=self._on_nav_change,
        )

    def _on_nav_change(self, event: ft.ControlEvent) -> None:
        routes = ["home", "partes", "inmuebles", "contratos", "ventas", "finanzas"]
        self.navigate(routes[event.control.selected_index])

    def _sync_rail(self, route: Route) -> None:
        index_by_route = {
            "home": 0,
            "partes": 1,
            "parte_detail": 1,
            "inmuebles": 2,
            "contratos": 3,
            "ventas": 4,
            "finanzas": 5,
        }
        self.rail.selected_index = index_by_route.get(route.name, 0)

    def _render_route(self, route: Route) -> ft.Control:
        if route.name == "home":
            return HomePage(on_navigate=self.navigate).build()
        if route.name == "partes":
            return PartesListPage(api=self.api, on_navigate=self.navigate).build()
        if route.name == "parte_detail":
            id_persona = int((route.params or {})["id_persona"])
            return ParteDetailPage(
                api=self.api,
                id_persona=id_persona,
                on_navigate=self.navigate,
            ).build()
        if route.name == "inmuebles":
            return InmueblesPage().build()
        if route.name == "contratos":
            return ContratosPage().build()
        if route.name == "ventas":
            return VentasPage().build()
        if route.name == "finanzas":
            return FinanzasPage().build()
        return HomePage(on_navigate=self.navigate).build()
