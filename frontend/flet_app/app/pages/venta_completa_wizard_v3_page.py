from __future__ import annotations

from typing import Callable

import flet as ft

from app.api_client import ApiClient
from app.components.loading_state import DeferredLoadingContainer
from prototypes.venta_completa_wizard_v3_prototype import VentaCompletaWizardV3Prototype


class VentaCompletaWizardV3Page:
    """Pantalla real que integra el Wizard Venta Completa V3 validado."""

    def __init__(
        self, page: ft.Page, api: ApiClient, on_navigate: Callable[..., None]
    ) -> None:
        self.page = page
        self.api = api
        self.on_navigate = on_navigate
        self.last_confirmed_sale_id: int | None = None
        self.wizard = VentaCompletaWizardV3Prototype(
            page,
            api=api,
            embedded=True,
            on_close=self._close,
            on_confirmed=self._on_confirmed,
        )

    def build(self) -> ft.Control:
        return DeferredLoadingContainer(
            self.wizard.build,
            message="Cargando Wizard Venta Completa...",
        )

    def _close(self) -> None:
        self.on_navigate("ventas")

    def _on_confirmed(self, id_venta: int | None) -> None:
        self.last_confirmed_sale_id = id_venta
