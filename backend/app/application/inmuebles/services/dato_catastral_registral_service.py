from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

from app.application.common.results import AppResult
from app.application.inmuebles.commands.manage_dato_catastral_registral import (
    BajaDatoCatastralRegistralCommand,
    CreateDatoCatastralRegistralCommand,
    UpdateDatoCatastralRegistralCommand,
)

ESTADOS_DATO = {"ACTIVO", "INACTIVO", "HISTORICO"}


@dataclass(slots=True)
class DatoCatastralRegistralPayload:
    id_inmueble: int
    values: dict[str, Any]
    version_registro_actual: int | None
    version_registro_nueva: int
    now: datetime
    id_instalacion: int
    op_id: UUID | None
    id_dato_catastral_registral: int | None = None


class Repository(Protocol):
    def inmueble_exists(self, id_inmueble: int) -> bool: ...
    def list_datos_catastrales_registrales(self, id_inmueble: int) -> list[dict[str, Any]]: ...
    def create_dato_catastral_registral(self, payload: DatoCatastralRegistralPayload) -> dict[str, Any]: ...
    def get_dato_catastral_registral(self, id_inmueble: int, id_dato: int) -> dict[str, Any] | None: ...
    def update_dato_catastral_registral(self, payload: DatoCatastralRegistralPayload) -> dict[str, Any] | None: ...
    def baja_dato_catastral_registral(self, payload: DatoCatastralRegistralPayload) -> dict[str, Any] | None: ...


def _command_values(command: Any) -> dict[str, Any]:
    excluded = {"context", "id_inmueble", "id_dato_catastral_registral", "if_match_version"}
    return {k: v for k, v in asdict(command).items() if k not in excluded}


def _validate_values(values: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if values.get("estado_dato") not in ESTADOS_DATO:
        errors.append("INVALID_ESTADO_DATO")
    for field in ("superficie_titulo", "superficie_mensura"):
        value = values.get(field)
        if value is not None and value <= 0:
            errors.append("INVALID_SUPERFICIE")
    if values.get("fecha_desde") and values.get("fecha_hasta") and values["fecha_hasta"] < values["fecha_desde"]:
        errors.append("INVALID_DATE_RANGE")
    return errors


def _context_values(command: Any) -> tuple[int | None, UUID | None]:
    return getattr(command.context, "id_instalacion", None), getattr(command.context, "op_id", None)


class DatoCatastralRegistralService:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def list(self, id_inmueble: int) -> AppResult[list[dict[str, Any]]]:
        if not self.repository.inmueble_exists(id_inmueble):
            return AppResult.fail("NOT_FOUND_INMUEBLE")
        return AppResult.ok(self.repository.list_datos_catastrales_registrales(id_inmueble))

    def create(self, command: CreateDatoCatastralRegistralCommand) -> AppResult[dict[str, Any]]:
        if not self.repository.inmueble_exists(command.id_inmueble):
            return AppResult.fail("NOT_FOUND_INMUEBLE")
        values = _command_values(command)
        errors = _validate_values(values)
        if errors:
            return AppResult.fail(*errors)
        id_instalacion, op_id = _context_values(command)
        if id_instalacion is None:
            return AppResult.fail("APPLICATION_ERROR")
        payload = DatoCatastralRegistralPayload(command.id_inmueble, values, None, 1, datetime.now(UTC), id_instalacion, op_id)
        return AppResult.ok(self.repository.create_dato_catastral_registral(payload))

    def update(self, command: UpdateDatoCatastralRegistralCommand) -> AppResult[dict[str, Any]]:
        current = self.repository.get_dato_catastral_registral(command.id_inmueble, command.id_dato_catastral_registral)
        if current is None:
            if not self.repository.inmueble_exists(command.id_inmueble):
                return AppResult.fail("NOT_FOUND_INMUEBLE")
            return AppResult.fail("NOT_FOUND_DATO_CATASTRAL_REGISTRAL")
        if command.if_match_version != current["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")
        values = _command_values(command)
        errors = _validate_values(values)
        if errors:
            return AppResult.fail(*errors)
        id_instalacion, op_id = _context_values(command)
        if id_instalacion is None:
            return AppResult.fail("APPLICATION_ERROR")
        payload = DatoCatastralRegistralPayload(command.id_inmueble, values, current["version_registro"], current["version_registro"] + 1, datetime.now(UTC), id_instalacion, op_id, command.id_dato_catastral_registral)
        updated = self.repository.update_dato_catastral_registral(payload)
        if updated is None:
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(updated)

    def baja(self, command: BajaDatoCatastralRegistralCommand) -> AppResult[dict[str, Any]]:
        current = self.repository.get_dato_catastral_registral(command.id_inmueble, command.id_dato_catastral_registral)
        if current is None:
            if not self.repository.inmueble_exists(command.id_inmueble):
                return AppResult.fail("NOT_FOUND_INMUEBLE")
            return AppResult.fail("NOT_FOUND_DATO_CATASTRAL_REGISTRAL")
        if command.if_match_version != current["version_registro"]:
            return AppResult.fail("CONCURRENCY_ERROR")
        id_instalacion, op_id = _context_values(command)
        if id_instalacion is None:
            return AppResult.fail("APPLICATION_ERROR")
        payload = DatoCatastralRegistralPayload(command.id_inmueble, {}, current["version_registro"], current["version_registro"] + 1, datetime.now(UTC), id_instalacion, op_id, command.id_dato_catastral_registral)
        deleted = self.repository.baja_dato_catastral_registral(payload)
        if deleted is None:
            return AppResult.fail("CONCURRENCY_ERROR")
        return AppResult.ok(deleted)
