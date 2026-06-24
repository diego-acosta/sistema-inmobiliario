from __future__ import annotations

from collections.abc import Callable
from threading import Thread
import traceback

import flet as ft


def loading_state(message: str = "Cargando...") -> ft.Control:
    """Return a reusable centered loading panel for backend-bound screens."""
    return ft.Container(
        content=ft.Column(
            controls=[
                ft.ProgressRing(width=28, height=28, stroke_width=3),
                ft.Text(message, text_align=ft.TextAlign.CENTER),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=12,
            tight=True,
        ),
        alignment=ft.alignment.center,
        padding=24,
        expand=True,
    )


class DeferredLoadingContainer(ft.Container):
    """Container that paints a loading state before running a blocking loader.

    This keeps the first incremental step small: existing synchronous backend calls
    stay unchanged, but they run after the control is mounted and the loading state
    is visible. The loader must return the final Flet control to display.
    """

    def __init__(
        self,
        loader: Callable[[], ft.Control],
        *,
        message: str = "Cargando...",
        error_builder: Callable[[str], ft.Control] | None = None,
    ) -> None:
        super().__init__(content=loading_state(message), expand=True)
        self._loader = loader
        self._error_builder = error_builder
        self._started = False

    def did_mount(self) -> None:
        if self._started:
            return
        self._started = True
        Thread(target=self._load, daemon=True).start()

    def _load(self) -> None:
        try:
            self.content = self._loader()
        except Exception as exc:  # defensive UI boundary: never expose traceback.
            message = str(exc) or "No se pudieron cargar los datos."
            self.content = (
                self._error_builder(message)
                if self._error_builder is not None
                else ft.Text(
                    "No se pudieron cargar los datos.", color=ft.Colors.RED_800
                )
            )
            traceback.print_exc()
        self.update()
