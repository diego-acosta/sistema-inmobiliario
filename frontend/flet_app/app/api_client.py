from dataclasses import dataclass
from typing import Any

import httpx

from app.config import get_api_base_url


@dataclass(slots=True)
class ApiResult:
    success: bool
    data: Any = None
    error_message: str | None = None
    status_code: int | None = None


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
            return ApiResult(
                success=False,
                error_message=self._format_error(response),
                status_code=response.status_code,
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
        default = f"Error HTTP {response.status_code}."
        try:
            payload = response.json()
        except ValueError:
            return default

        if not isinstance(payload, dict):
            return default

        code = payload.get("error_code")
        message = payload.get("error_message") or default
        return f"{code}: {message}" if code else message

    def _clean_params(self, params: dict[str, Any]) -> dict[str, Any]:
        return {
            key: value
            for key, value in params.items()
            if value is not None and value != ""
        }
