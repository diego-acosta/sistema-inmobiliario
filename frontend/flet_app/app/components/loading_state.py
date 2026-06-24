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
        padding=24,
        expand=True,
    )


def safe_update(control: ft.Control) -> None:
    """Update a control only when Flet has already mounted it on a page."""
    if getattr(control, "page", None) is None:
        return
    try:
        control.update()
    except AssertionError:
        # The user may have navigated away between the page check and update().
        return


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
        self._mounted = False

    def did_mount(self) -> None:
        self._mounted = True
        if self._started:
            return
        self._started = True
        Thread(target=self._load, daemon=True).start()

    def will_unmount(self) -> None:
        self._mounted = False

    def _load(self) -> None:
        try:
            content = self._loader()
        except Exception as exc:  # defensive UI boundary: never expose traceback.
            message = str(exc) or "No se pudieron cargar los datos."
            content = (
                self._error_builder(message)
                if self._error_builder is not None
                else ft.Text(
                    "No se pudieron cargar los datos.", color=ft.Colors.RED_800
                )
            )
            traceback.print_exc()

        if not self._mounted or self.page is None:
            return
        self.content = content
        safe_update(self)


class DeferredControlLoader(ft.Container):
    """Mount an existing control immediately and populate it in the background."""

    def __init__(
        self,
        control: ft.Control,
        loader: Callable[[], None],
        *,
        message: str = "Cargando...",
    ) -> None:
        self._control = control
        self._loader = loader
        self._started = False
        self._mounted = False
        if hasattr(control, "controls"):
            control.controls = [loading_state(message)]
        super().__init__(content=control, expand=True)

    def did_mount(self) -> None:
        self._mounted = True
        if self._started:
            return
        self._started = True
        Thread(target=self._load, daemon=True).start()

    def will_unmount(self) -> None:
        self._mounted = False

    def _load(self) -> None:
        try:
            self._loader()
        except Exception:
            traceback.print_exc()
        if self._mounted and self._control.page is not None:
            safe_update(self._control)
