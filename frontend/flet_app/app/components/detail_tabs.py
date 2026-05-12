from collections.abc import Sequence

import flet as ft


TabContent = tuple[str, Sequence[ft.Control]]


def detail_tabs(items: Sequence[TabContent]) -> ft.Control:
    views = [
        ft.Container(
            content=ft.Column(
                controls=list(controls),
                spacing=14,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
            padding=ft.padding.only(top=12),
            expand=True,
        )
        for _, controls in items
    ]
    return ft.Tabs(
        content=ft.Column(
            controls=[
                ft.TabBar(tabs=[ft.Tab(label=title) for title, _ in items]),
                ft.TabBarView(controls=views, expand=True),
            ],
            expand=True,
        ),
        length=len(items),
        selected_index=0,
        expand=True,
        animation_duration=120,
    )
