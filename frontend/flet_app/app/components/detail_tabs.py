from collections.abc import Sequence
import inspect

import flet as ft

TabContent = tuple[str, Sequence[ft.Control]]


def detail_tabs(items: Sequence[TabContent], selected_index: int = 0) -> ft.Control:
    if _supports_classic_tabs():
        return ft.Tabs(
            selected_index=selected_index,
            expand=True,
            tabs=[
                ft.Tab(
                    text=title,
                    content=_tab_content(controls),
                )
                for title, controls in items
            ],
        )

    return ft.Column(
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[ft.Text(title, weight=ft.FontWeight.W_600)]
                    + _controls_list(controls),
                    spacing=12,
                ),
                padding=8,
                border=ft.border.all(1, ft.Colors.BLUE_GREY_100),
                border_radius=6,
            )
            for title, controls in items
        ],
        spacing=12,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )


def _supports_classic_tabs() -> bool:
    tabs_params = inspect.signature(ft.Tabs).parameters
    tab_params = inspect.signature(ft.Tab).parameters
    return "tabs" in tabs_params and "text" in tab_params


def _tab_content(controls: Sequence[ft.Control]) -> ft.Control:
    return ft.Container(
        content=ft.Column(
            controls=_controls_list(controls),
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        padding=8,
        expand=True,
    )


def _controls_list(controls: Sequence[ft.Control]) -> list[ft.Control]:
    result = list(controls)
    return result or [ft.Text("Sin datos.")]
