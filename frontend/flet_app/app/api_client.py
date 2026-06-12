from dataclasses import dataclass
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import httpx

from app.config import get_api_base_url


@dataclass(slots=True)
class ApiResult:
    success: bool
    data: Any = None
    error_message: str | None = None
    status_code: int | None = None
    error_code: str | None = None
    error_details: Any = None


class ApiClient:
    def __init__(self, base_url: str | None = None, timeout: float = 10.0) -> None:
        self.base_url = (base_url or get_api_base_url()).rstrip("/")
        self.timeout = timeout

    def get_personas(
        self,
        *,
        q: str | None = None,
        tipo_persona: str | None = None,
        estado_persona: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ApiResult:
        params = {
            "q": q or None,
            "tipo_persona": tipo_persona or None,
            "estado_persona": estado_persona or None,
            "limit": limit,
            "offset": offset,
        }
        return self._get("/api/v1/personas", params=params)

    def get_persona_detalle_integral(self, id_persona: int) -> ApiResult:
        return self._get(f"/api/v1/personas/{id_persona}/detalle-integral")

    def buscar_personas(
        self,
        *,
        q: str | None = None,
        tipo_persona: str | None = None,
        estado_persona: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ApiResult:
        return self.get_personas(
            q=q,
            tipo_persona=tipo_persona,
            estado_persona=estado_persona,
            limit=limit,
            offset=offset,
        )

    def get_estado_cuenta_persona(
        self,
        id_persona: int,
        *,
        estado: str | None = None,
        tipo_origen: str | None = None,
        id_origen: int | None = None,
        vencidas: bool | None = None,
        fecha_vencimiento_desde: str | None = None,
        fecha_vencimiento_hasta: str | None = None,
        fecha_corte: str | None = None,
    ) -> ApiResult:
        return self._get(
            f"/api/v1/financiero/personas/{id_persona}/estado-cuenta",
            params={
                "estado": estado or None,
                "tipo_origen": tipo_origen or None,
                "id_origen": id_origen,
                "vencidas": vencidas,
                "fecha_vencimiento_desde": fecha_vencimiento_desde or None,
                "fecha_vencimiento_hasta": fecha_vencimiento_hasta or None,
                "fecha_corte": fecha_corte or None,
            },
        )

    def simular_pago_persona(
        self,
        id_persona: int,
        monto: float,
        fecha_corte: str | None = None,
    ) -> ApiResult:
        return self._post(
            f"/api/v1/financiero/personas/{id_persona}/simular-pago",
            json={
                "monto": monto,
                "fecha_corte": fecha_corte or date.today().isoformat(),
            },
        )

    def registrar_pago_persona(
        self,
        id_persona: int,
        monto: float,
        fecha_pago: str,
        alcance_pago: str,
        id_obligacion_financiera: int | None = None,
        id_relacion_generadora: int | None = None,
        op_id: str | None = None,
    ) -> ApiResult:
        x_op_id = self._valid_or_new_uuid(op_id)
        return self._post(
            "/api/v1/financiero/pagos",
            params={"id_persona": id_persona},
            headers={"X-Op-Id": x_op_id},
            json={
                "monto": monto,
                "fecha_pago": fecha_pago,
                "alcance_pago": alcance_pago,
                "id_obligacion_financiera": id_obligacion_financiera,
                "id_relacion_generadora": id_relacion_generadora,
            },
        )

    def get_inmuebles(
        self,
        *,
        q: str | None = None,
        estado_administrativo: str | None = None,
        estado_juridico: str | None = None,
        disponibilidad_actual: str | None = None,
        ocupacion_actual: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ApiResult:
        return self._get(
            "/api/v1/inmuebles",
            params={
                "q": q or None,
                "estado_administrativo": estado_administrativo or None,
                "estado_juridico": estado_juridico or None,
                "disponibilidad_actual": disponibilidad_actual or None,
                "ocupacion_actual": ocupacion_actual or None,
                "limit": limit,
                "offset": offset,
            },
        )

    def get_inmueble_detalle_integral(self, id_inmueble: int) -> ApiResult:
        return self._get(f"/api/v1/inmuebles/{id_inmueble}/detalle-integral")

    def listar_inmuebles(
        self,
        *,
        q: str | None = None,
        estado_administrativo: str | None = None,
        estado_juridico: str | None = None,
        disponibilidad_actual: str | None = None,
        ocupacion_actual: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ApiResult:
        return self.get_inmuebles(
            q=q,
            estado_administrativo=estado_administrativo,
            estado_juridico=estado_juridico,
            disponibilidad_actual=disponibilidad_actual,
            ocupacion_actual=ocupacion_actual,
            limit=limit,
            offset=offset,
        )

    def get_unidades_funcionales(
        self,
        *,
        q: str | None = None,
        id_inmueble: int | None = None,
        estado_administrativo: str | None = None,
        estado_operativo: str | None = None,
        disponibilidad_actual: str | None = None,
        ocupacion_actual: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ApiResult:
        return self._get(
            "/api/v1/unidades-funcionales",
            params={
                "q": q or None,
                "id_inmueble": id_inmueble,
                "estado_administrativo": estado_administrativo or None,
                "estado_operativo": estado_operativo or None,
                "disponibilidad_actual": disponibilidad_actual or None,
                "ocupacion_actual": ocupacion_actual or None,
                "limit": limit,
                "offset": offset,
            },
        )

    def get_unidad_funcional_detalle_integral(
        self, id_unidad_funcional: int
    ) -> ApiResult:
        return self._get(
            f"/api/v1/unidades-funcionales/{id_unidad_funcional}/detalle-integral"
        )

    def listar_unidades_funcionales(
        self,
        *,
        q: str | None = None,
        id_inmueble: int | None = None,
        estado_administrativo: str | None = None,
        estado_operativo: str | None = None,
        disponibilidad_actual: str | None = None,
        ocupacion_actual: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ApiResult:
        return self.get_unidades_funcionales(
            q=q,
            id_inmueble=id_inmueble,
            estado_administrativo=estado_administrativo,
            estado_operativo=estado_operativo,
            disponibilidad_actual=disponibilidad_actual,
            ocupacion_actual=ocupacion_actual,
            limit=limit,
            offset=offset,
        )

    def get_contratos_alquiler(
        self,
        *,
        q: str | None = None,
        estado_contrato: str | None = None,
        id_persona: int | None = None,
        rol_codigo: str | None = None,
        id_inmueble: int | None = None,
        id_unidad_funcional: int | None = None,
        con_saldo: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ApiResult:
        return self._get(
            "/api/v1/contratos-alquiler",
            params={
                "q": q or None,
                "estado_contrato": estado_contrato or None,
                "id_persona": id_persona,
                "rol_codigo": rol_codigo or None,
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": id_unidad_funcional,
                "con_saldo": con_saldo,
                "limit": limit,
                "offset": offset,
            },
        )

    def get_contrato_alquiler_detalle_integral(
        self, id_contrato_alquiler: int
    ) -> ApiResult:
        return self._get(
            f"/api/v1/contratos-alquiler/{id_contrato_alquiler}/detalle-integral"
        )

    def get_ventas(
        self,
        *,
        q: str | None = None,
        estado_venta: str | None = None,
        id_persona: int | None = None,
        rol_codigo: str | None = None,
        id_inmueble: int | None = None,
        id_unidad_funcional: int | None = None,
        tipo_plan_financiero: str | None = None,
        con_saldo: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ApiResult:
        return self._get(
            "/api/v1/ventas",
            params={
                "q": q or None,
                "estado_venta": estado_venta or None,
                "id_persona": id_persona,
                "rol_codigo": rol_codigo or None,
                "id_inmueble": id_inmueble,
                "id_unidad_funcional": id_unidad_funcional,
                "tipo_plan_financiero": tipo_plan_financiero or None,
                "con_saldo": con_saldo,
                "limit": limit,
                "offset": offset,
            },
        )

    def get_reservas_venta(
        self,
        *,
        codigo_reserva: str | None = None,
        estado_reserva: str | None = None,
        fecha_desde: str | None = None,
        fecha_hasta: str | None = None,
        vigente: bool | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ApiResult:
        return self._get(
            "/api/v1/reservas-venta",
            params={
                "codigo_reserva": codigo_reserva or None,
                "estado_reserva": estado_reserva or None,
                "fecha_desde": fecha_desde or None,
                "fecha_hasta": fecha_hasta or None,
                "vigente": vigente,
                "limit": limit,
                "offset": offset,
            },
        )

    def get_venta_detalle_integral(self, id_venta: int) -> ApiResult:
        return self._get(f"/api/v1/ventas/{id_venta}/detalle-integral")

    def preview_plan_pago_venta_v2_sin_venta(
        self, payload: dict[str, Any]
    ) -> ApiResult:
        return self._post(
            "/api/v1/ventas/plan-pago-v2/preview",
            json=payload,
        )

    def preview_plan_pago_venta_v2_por_bloques(
        self, id_venta: int, payload: dict[str, Any]
    ) -> ApiResult:
        return self._post(
            f"/api/v1/ventas/{id_venta}/plan-pago-v2/preview",
            json=payload,
        )

    def generar_plan_pago_venta_v2_por_bloques(
        self, id_venta: int, payload: dict[str, Any]
    ) -> ApiResult:
        return self._post(
            f"/api/v1/ventas/{id_venta}/plan-pago-v2/generar",
            headers={
                "X-Op-Id": str(uuid4()),
                "X-Usuario-Id": "1",
                "X-Sucursal-Id": "1",
                "X-Instalacion-Id": "1",
            },
            json=payload,
        )

    def confirmar_venta_directa_completa(
        self,
        payload: dict[str, Any],
        op_id: str | None = None,
    ) -> ApiResult:
        x_op_id = self._valid_or_new_uuid(op_id)
        return self._post(
            "/api/v1/ventas/directa/confirmar-venta-completa",
            headers={
                "X-Op-Id": x_op_id,
                "X-Usuario-Id": "1",
                "X-Sucursal-Id": "1",
                "X-Instalacion-Id": "1",
            },
            json=payload,
        )

    def confirmar_venta_completa_desde_reserva(
        self,
        id_reserva_venta: int,
        if_match_version: int,
        payload: dict[str, Any],
        op_id: str | None = None,
    ) -> ApiResult:
        x_op_id = self._valid_or_new_uuid(op_id)
        return self._post(
            f"/api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa",
            headers={
                "X-Op-Id": x_op_id,
                "X-Usuario-Id": "1",
                "X-Sucursal-Id": "1",
                "X-Instalacion-Id": "1",
                "If-Match-Version": str(if_match_version),
            },
            json=payload,
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> ApiResult:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, params=self._clean_params(params or {}))
        except httpx.ConnectError:
            return ApiResult(
                success=False,
                error_message=(
                    f"No se pudo conectar con el backend en {self.base_url}."
                ),
            )
        except httpx.TimeoutException:
            return ApiResult(
                success=False,
                error_message="La consulta al backend excedio el tiempo de espera.",
            )
        except httpx.HTTPError as exc:
            return ApiResult(success=False, error_message=str(exc))

        if response.status_code >= 400:
            error_payload = self._parse_error(response)
            return ApiResult(
                success=False,
                error_message=error_payload["message"],
                status_code=response.status_code,
                error_code=error_payload["code"],
                error_details=error_payload["details"],
            )

        try:
            payload = response.json()
        except ValueError:
            return ApiResult(
                success=False,
                error_message="El backend devolvio una respuesta no JSON.",
                status_code=response.status_code,
            )

        if not isinstance(payload, dict) or "data" not in payload:
            return ApiResult(
                success=False,
                error_message="El backend devolvio un formato JSON inesperado.",
                status_code=response.status_code,
            )

        return ApiResult(
            success=True,
            data=payload.get("data"),
            status_code=response.status_code,
        )

    def _post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> ApiResult:
        url = f"{self.base_url}{path}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    url,
                    params=self._clean_params(params or {}),
                    headers=headers,
                    json=self._clean_params(json or {}),
                )
        except httpx.ConnectError:
            return ApiResult(
                success=False,
                error_message=(
                    f"No se pudo conectar con el backend en {self.base_url}."
                ),
            )
        except httpx.TimeoutException:
            return ApiResult(
                success=False,
                error_message="La consulta al backend excedio el tiempo de espera.",
            )
        except httpx.HTTPError as exc:
            return ApiResult(success=False, error_message=str(exc))

        if response.status_code >= 400:
            error_payload = self._parse_error(response)
            return ApiResult(
                success=False,
                error_message=error_payload["message"],
                status_code=response.status_code,
                error_code=error_payload["code"],
                error_details=error_payload["details"],
            )

        try:
            payload = response.json()
        except ValueError:
            return ApiResult(
                success=False,
                error_message="El backend devolvio una respuesta no JSON.",
                status_code=response.status_code,
            )

        if not isinstance(payload, dict) or "data" not in payload:
            return ApiResult(
                success=False,
                error_message="El backend devolvio un formato JSON inesperado.",
                status_code=response.status_code,
            )

        return ApiResult(
            success=True,
            data=payload.get("data"),
            status_code=response.status_code,
        )

    def _format_error(self, response: httpx.Response) -> str:
        return self._parse_error(response)["message"]

    def _parse_error(self, response: httpx.Response) -> dict[str, Any]:
        default = f"Error HTTP {response.status_code}."
        try:
            payload = response.json()
        except ValueError:
            return {"code": None, "message": default, "details": None}

        if not isinstance(payload, dict):
            return {"code": None, "message": default, "details": None}

        code = payload.get("error_code")
        message = payload.get("error_message") or default
        details = payload.get("details")
        parts = [f"HTTP {response.status_code}"]
        if code:
            parts.append(str(code))
        parts.append(str(message))

        detail_text = self._format_details(details)
        if detail_text:
            parts.append(detail_text)

        return {
            "code": str(code) if code else None,
            "message": " | ".join(parts),
            "details": details,
        }

    def _format_details(self, details: Any) -> str:
        if details is None:
            return ""
        if isinstance(details, dict):
            errors = details.get("errors")
            extra = {key: value for key, value in details.items() if key != "errors"}
            parts: list[str] = []
            if errors:
                if isinstance(errors, list):
                    parts.append("errors=" + ", ".join(str(error) for error in errors))
                else:
                    parts.append(f"errors={errors}")
            if extra:
                parts.append(f"details={extra}")
            return " | ".join(parts)
        return f"details={details}"

    def _clean_params(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in params.items()
            if value is not None and value != ""
        }

    def _valid_or_new_uuid(self, value: str | None) -> str:
        if value:
            try:
                return str(UUID(value))
            except ValueError:
                pass
        return str(uuid4())
