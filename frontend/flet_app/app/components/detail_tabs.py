from collections.abc import Sequence

import flet as ft


TabContent = tuple[str, Sequence[ft.Control]]


def detail_tabs(items: Sequence[TabContent]) -> ft.Control:
    return ft.Tabs(
        selected_index=0,
        expand=True,
        tabs=[
            ft.Tab(
                text=title,
                content=ft.Container(
                    content=ft.Column(
                        controls=_controls_list(controls),
                        spacing=12,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                    padding=8,
                    expand=True,
                ),
            )
            for title, controls in items
        ],
    )


def _controls_list(controls: Sequence[ft.Control]) -> list[ft.Control]:
    result = list(controls)
    return result or [ft.Text("Sin datos.")]
