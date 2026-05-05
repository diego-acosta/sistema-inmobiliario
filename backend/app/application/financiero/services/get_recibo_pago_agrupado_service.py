from dataclasses import dataclass

from app.application.common.results import AppResult


@dataclass(slots=True)
class GetReciboPagoAgrupadoService:
    repository: object

    def execute(self, *, codigo_pago_grupo: str) -> AppResult[dict]:
        data = self.repository.get_recibo_pago_agrupado(
            codigo_pago_grupo=codigo_pago_grupo
        )
        if data is None:
            return AppResult.fail("NOT_FOUND_PAGO_GRUPO")
        return AppResult.ok(data)
