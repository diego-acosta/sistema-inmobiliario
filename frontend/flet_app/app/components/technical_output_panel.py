from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import flet as ft


def format_technical_output(sections: Sequence[tuple[str, Any]]) -> str:
    """Build a readable single text block for technical/debug output."""
    blocks: list[str] = []
    for title, value in sections:
        blocks.append(f"{title}:")
        blocks.append(_format_value(value))
    return "\n\n".join(blocks)


def build_technical_output_panel(
    technical_text: str,
    *,
    height: int = 300,
    copy_button_text: str = "Copiar modo técnico",
) -> ft.Control:
    """Compact read-only panel with bounded height for technical/debug output."""

    def copy_to_clipboard(event: ft.ControlEvent) -> None:
        page = getattr(event.control, "page", None)
        set_clipboard = getattr(page, "set_clipboard", None)
        if callable(set_clipboard):
            set_clipboard(technical_text)

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Modo técnico", weight=ft.FontWeight.W_700),
                        ft.Container(expand=True),
                        ft.TextButton(
                            copy_button_text,
                            icon=ft.Icons.CONTENT_COPY,
                            on_click=copy_to_clipboard,
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.TextField(
                    value=technical_text,
                    multiline=True,
                    read_only=True,
                    min_lines=8,
                    max_lines=14,
                    height=height,
                    text_style=ft.TextStyle(font_family="monospace"),
                    border_color=ft.Colors.BLUE_GREY_100,
                    bgcolor=ft.Colors.BLUE_GREY_50,
                ),
            ],
            spacing=8,
        ),
        padding=12,
        bgcolor=ft.Colors.BLUE_GREY_50,
        border_radius=8,
    )


def _format_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (Mapping, list, tuple)) or value is None:
        import json

        return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return str(value)
