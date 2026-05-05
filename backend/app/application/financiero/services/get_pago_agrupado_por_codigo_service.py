from dataclasses import dataclass

from app.application.common.result import Result


@dataclass(slots=True)
class GetPagoAgrupadoPorCodigoService:
    repository: object

    def execute(self, *, codigo_pago_grupo: str) -> Result:
        data = self.repository.get_pago_agrupado_by_codigo(codigo_pago_grupo=codigo_pago_grupo)
        if data is None:
            return Result(success=False, data=None, errors=["NOT_FOUND_PAGO_GRUPO"])
        return Result(success=True, data=data, errors=[])
