from typing import Any, Protocol

from app.application.common.results import AppResult


class PlanPagoVentaV2ReadRepository(Protocol):
    def get_venta_minima(self, id_venta: int) -> dict[str, Any] | None: ...

    def get_plan_pago_venta_v2_integral(
        self, id_venta: int
    ) -> dict[str, Any] | None: ...


class GetPlanPagoVentaV2IntegralService:
    def __init__(self, repository: PlanPagoVentaV2ReadRepository) -> None:
        self.repository = repository

    def execute(self, id_venta: int) -> AppResult[dict[str, Any]]:
        venta = self.repository.get_venta_minima(id_venta)
        if venta is None:
            return AppResult.fail("NOT_FOUND_VENTA")

        plan_pago = self.repository.get_plan_pago_venta_v2_integral(id_venta)
        if plan_pago is None:
            return AppResult.fail("NOT_FOUND_PLAN_PAGO_V2")

        return AppResult.ok(plan_pago)
