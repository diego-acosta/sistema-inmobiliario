from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.application.common.results import AppResult
from app.application.inmuebles.commands.create_inmueble import CreateInmuebleCommand
from app.application.inmuebles.commands.manage_dato_catastral_registral import (
    CreateDatoCatastralRegistralCommand,
)
from app.application.inmuebles.services.create_inmueble_service import CreateInmuebleService
from app.application.inmuebles.services.dato_catastral_registral_service import (
    DatoCatastralRegistralService,
)


@dataclass(slots=True)
class ImportacionInmuebleItem:
    fila: int
    inmueble: Any
    dato_catastral_registral: Any | None = None


class _SinCommitRepositoryAdapter:
    def __init__(self, repository: Any) -> None:
        self.repository = repository

    def __getattr__(self, name: str) -> Any:
        return getattr(self.repository, name)

    def create_inmueble(self, payload: Any) -> dict[str, Any]:
        return self.repository.create_inmueble_sin_commit(payload)

    def create_dato_catastral_registral(self, payload: Any) -> dict[str, Any]:
        return self.repository.create_dato_catastral_registral_sin_commit(payload)


class ConfirmImportacionInmueblesService:
    """Confirmación batch transaccional de importación de inmuebles.

    CORE-EF: COMMAND_WRITE_NEGOCIO.
    - Headers: un único X-Op-Id para toda la operación batch.
    - If-Match-Version: NO APLICA; sólo crea registros nuevos.
    - Idempotencia: retry idéntico por códigos con el mismo X-Op-Id devuelve
      los ids ya persistidos sin crear duplicados.
    - Outbox/locks: NO APLICA en este PR.
    - Transacción: una única transacción física controlada por este servicio.
    """

    def __init__(self, repository: Any) -> None:
        self.repository = repository
        adapter = _SinCommitRepositoryAdapter(repository)
        self.inmueble_service = CreateInmuebleService(repository=adapter)
        self.dato_service = DatoCatastralRegistralService(repository=adapter)

    def execute(
        self, context: Any, items: list[ImportacionInmuebleItem]
    ) -> AppResult[dict[str, Any]]:
        duplicated_row = self._duplicated_row(items)
        if duplicated_row is not None:
            return AppResult.fail(
                "CODIGO_INMUEBLE_DUPLICADO", f"FILA_{duplicated_row}"
            )

        normalized_codes = self._normalized_codes(items)
        retry_result = self._idempotent_retry_result(context, items, normalized_codes)
        if retry_result is not None:
            return retry_result

        existing = self.repository.find_existing_by_codes(normalized_codes)
        if existing:
            codigo = str(existing[0].get("codigo") or "")
            row = next(
                (
                    item.fila
                    for item in items
                    if str(item.inmueble.codigo_inmueble).strip().lower()
                    == codigo.strip().lower()
                ),
                None,
            )
            row_errors = [f"FILA_{row}"] if row is not None else []
            return AppResult.fail("CODIGO_INMUEBLE_YA_EXISTE", *row_errors)

        created_items: list[dict[str, Any]] = []
        try:
            for item in items:
                inmueble_req = item.inmueble
                inmueble_result = self.inmueble_service.execute(
                    CreateInmuebleCommand(
                        context=context,
                        id_desarrollo=inmueble_req.id_desarrollo,
                        codigo_inmueble=inmueble_req.codigo_inmueble,
                        nombre_inmueble=inmueble_req.nombre_inmueble,
                        calle=inmueble_req.calle,
                        altura=inmueble_req.altura,
                        superficie=inmueble_req.superficie,
                        estado_administrativo=inmueble_req.estado_administrativo,
                        estado_juridico=inmueble_req.estado_juridico,
                        observaciones=inmueble_req.observaciones,
                    )
                )
                if not inmueble_result.success or inmueble_result.data is None:
                    self.repository.rollback()
                    return AppResult.fail(*inmueble_result.errors, f"FILA_{item.fila}")

                id_inmueble = inmueble_result.data["id_inmueble"]
                created_row = {
                    "fila": item.fila,
                    "codigo_inmueble": inmueble_result.data["codigo_inmueble"],
                    "id_inmueble": id_inmueble,
                    "id_dato_catastral_registral": None,
                }

                if item.dato_catastral_registral is not None:
                    dato_req = item.dato_catastral_registral
                    dato_result = self.dato_service.create(
                        CreateDatoCatastralRegistralCommand(
                            context=context,
                            id_inmueble=id_inmueble,
                            **dato_req.model_dump(),
                        )
                    )
                    if not dato_result.success or dato_result.data is None:
                        self.repository.rollback()
                        return AppResult.fail(*dato_result.errors, f"FILA_{item.fila}")
                    created_row["id_dato_catastral_registral"] = dato_result.data[
                        "id_dato_catastral_registral"
                    ]

                created_items.append(created_row)

            self.repository.commit()
        except Exception:
            self.repository.rollback()
            raise

        return AppResult.ok({"creados": len(created_items), "items": created_items})

    def _idempotent_retry_result(
        self, context: Any, items: list[ImportacionInmuebleItem], normalized_codes: list[str]
    ) -> AppResult[dict[str, Any]] | None:
        op_id = getattr(context, "op_id", None)
        if op_id is None:
            return None

        imported = self.repository.find_imported_by_codes_and_op_id(
            normalized_codes, op_id
        )
        if not imported:
            return None

        by_code = {self._normalize_code(row["codigo"]): row for row in imported}
        all_items_imported = all(
            self._normalize_code(item.inmueble.codigo_inmueble) in by_code
            for item in items
        )
        if not all_items_imported:
            return AppResult.fail("IMPORTACION_BATCH_RETRY_PARCIAL")

        result_items: list[dict[str, Any]] = []
        for item in items:
            row = by_code[self._normalize_code(item.inmueble.codigo_inmueble)]
            id_dato = row.get("id_dato_catastral_registral")
            if item.dato_catastral_registral is not None and id_dato is None:
                return AppResult.fail("IMPORTACION_BATCH_RETRY_PARCIAL")
            result_items.append(
                {
                    "fila": item.fila,
                    "codigo_inmueble": row["codigo"],
                    "id_inmueble": row["id_inmueble"],
                    "id_dato_catastral_registral": id_dato,
                }
            )

        return AppResult.ok({"creados": len(result_items), "items": result_items})

    @classmethod
    def _duplicated_row(cls, items: list[ImportacionInmuebleItem]) -> int | None:
        seen: set[str] = set()
        for item in items:
            code = cls._normalize_code(item.inmueble.codigo_inmueble)
            if code in seen:
                return item.fila
            seen.add(code)
        return None

    @classmethod
    def _normalized_codes(cls, items: list[ImportacionInmuebleItem]) -> list[str]:
        return [cls._normalize_code(item.inmueble.codigo_inmueble) for item in items]

    @staticmethod
    def _normalize_code(codigo: Any) -> str:
        return str(codigo).strip().lower()
