from dataclasses import dataclass
from uuid import UUID

from fastapi import Header


@dataclass(frozen=True)
class CoreEFHeaders:
    x_op_id: UUID
    x_usuario_id: int
    x_sucursal_id: int
    x_instalacion_id: int
    if_match_version: int | None = None


class CoreEFHeaderValidationError(ValueError):
    def __init__(self, *, header_name: str, reason: str) -> None:
        self.header_name = header_name
        self.reason = reason
        super().__init__(f"Header {reason}: {header_name}.")

    @property
    def message(self) -> str:
        return f"Header {self.reason}: {self.header_name}."


def _missing_header_error(header_name: str) -> CoreEFHeaderValidationError:
    return CoreEFHeaderValidationError(header_name=header_name, reason="requerido faltante")


def _invalid_header_error(header_name: str) -> CoreEFHeaderValidationError:
    return CoreEFHeaderValidationError(header_name=header_name, reason="inválido")


def _parse_required_int(header_name: str, header_value: str | None) -> int:
    if header_value is None:
        raise _missing_header_error(header_name)
    try:
        return int(header_value)
    except ValueError as exc:
        raise _invalid_header_error(header_name) from exc


def _parse_if_match(if_match_version: str | None, required: bool) -> int | None:
    if if_match_version is None:
        if required:
            raise _missing_header_error("If-Match-Version")
        return None
    try:
        return int(if_match_version)
    except ValueError as exc:
        raise _invalid_header_error("If-Match-Version") from exc


def parse_core_ef_headers(
    x_op_id: str | None,
    x_usuario_id: str | None,
    x_sucursal_id: str | None,
    x_instalacion_id: str | None,
    if_match_version: str | None = None,
    *,
    require_if_match_version: bool = False,
) -> CoreEFHeaders:
    if x_op_id is None:
        raise _missing_header_error("X-Op-Id")
    try:
        parsed_x_op_id = UUID(x_op_id)
    except ValueError as exc:
        raise _invalid_header_error("X-Op-Id") from exc

    return CoreEFHeaders(
        x_op_id=parsed_x_op_id,
        x_usuario_id=_parse_required_int("X-Usuario-Id", x_usuario_id),
        x_sucursal_id=_parse_required_int("X-Sucursal-Id", x_sucursal_id),
        x_instalacion_id=_parse_required_int("X-Instalacion-Id", x_instalacion_id),
        if_match_version=_parse_if_match(if_match_version, require_if_match_version),
    )


def get_core_ef_headers_write(
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> CoreEFHeaders:
    return parse_core_ef_headers(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
