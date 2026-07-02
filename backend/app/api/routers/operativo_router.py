from fastapi import APIRouter, Depends, Header, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.core_ef_headers import (
    CoreEFHeaderValidationError,
    CoreEFHeaders,
    parse_core_ef_headers,
)
from app.api.dependencies import get_db
from app.api.schemas.operativo import (
    ErrorResponse,
    InstalacionCreateRequest,
    InstalacionCreateResponse,
    InstalacionData,
    InstalacionDetailResponse,
    InstalacionListResponse,
    SucursalCreateRequest,
    SucursalCreateResponse,
    SucursalData,
    SucursalDetailResponse,
    SucursalListResponse,
)
from app.infrastructure.persistence.repositories.instalacion_repository import (
    InstalacionDuplicateActiveError,
    InstalacionIdempotencyConflictError,
    InstalacionRepository,
    InstalacionSucursalNotFoundError,
)
from app.infrastructure.persistence.repositories.sucursal_repository import (
    SucursalDuplicateActiveError,
    SucursalIdempotencyConflictError,
    SucursalRepository,
)

router = APIRouter(tags=["Operativo"])


def _error(
    status_code: int, code: str, message: str, details: dict | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error_code=code,
            error_message=message,
            details=details or {},
        ).model_dump(),
    )


def _parse_core_or_error(
    *,
    x_op_id: str | None,
    x_usuario_id: str | None,
    x_sucursal_id: str | None,
    x_instalacion_id: str | None,
) -> CoreEFHeaders | JSONResponse:
    try:
        return parse_core_ef_headers(
            x_op_id=x_op_id,
            x_usuario_id=x_usuario_id,
            x_sucursal_id=x_sucursal_id,
            x_instalacion_id=x_instalacion_id,
        )
    except CoreEFHeaderValidationError as exc:
        return _error(
            400,
            "VALIDATION_ERROR",
            exc.message,
            {"header": exc.header_name, "reason": exc.reason},
        )


@router.post(
    "/api/v1/operativo/sucursales",
    response_model=SucursalCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_sucursal(
    request: SucursalCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> SucursalCreateResponse | JSONResponse:
    core = _parse_core_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core

    try:
        sucursal = SucursalRepository(db).create(request.model_dump(), core)
    except SucursalIdempotencyConflictError as exc:
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    except SucursalDuplicateActiveError as exc:
        return _error(409, "TECHNICAL_INCONSISTENCY", str(exc))
    except IntegrityError as exc:
        return _error(
            409,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo crear la sucursal por una restricción de integridad.",
            {"error": str(exc.orig)},
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo crear la sucursal.",
            {"error": str(exc)},
        )
    return SucursalCreateResponse(data=SucursalData(**sucursal))


@router.get(
    "/api/v1/operativo/sucursales",
    response_model=SucursalListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_sucursales(
    estado_sucursal: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> SucursalListResponse | JSONResponse:
    try:
        sucursales = SucursalRepository(db).list(
            estado_sucursal=estado_sucursal.strip().upper() if estado_sucursal else None
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo listar sucursales.",
            {"error": str(exc)},
        )
    return SucursalListResponse(
        data=[SucursalData(**sucursal) for sucursal in sucursales]
    )


@router.get(
    "/api/v1/operativo/sucursales/{id_sucursal}",
    response_model=SucursalDetailResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_sucursal(
    id_sucursal: int,
    db: Session = Depends(get_db),
) -> SucursalDetailResponse | JSONResponse:
    try:
        sucursal = SucursalRepository(db).get(id_sucursal)
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo obtener la sucursal.",
            {"error": str(exc)},
        )
    if sucursal is None:
        return _error(404, "NOT_FOUND", "Sucursal no encontrada.")
    return SucursalDetailResponse(data=SucursalData(**sucursal))


@router.post(
    "/api/v1/operativo/instalaciones",
    response_model=InstalacionCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_instalacion(
    request: InstalacionCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> InstalacionCreateResponse | JSONResponse:
    core = _parse_core_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core

    try:
        instalacion = InstalacionRepository(db).create(request.model_dump(), core)
    except InstalacionSucursalNotFoundError as exc:
        return _error(404, "NOT_FOUND", str(exc))
    except InstalacionIdempotencyConflictError as exc:
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    except InstalacionDuplicateActiveError as exc:
        return _error(409, "TECHNICAL_INCONSISTENCY", str(exc))
    except IntegrityError as exc:
        return _error(
            409,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo crear la instalación por una restricción de integridad.",
            {"error": str(exc.orig)},
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo crear la instalación.",
            {"error": str(exc)},
        )
    return InstalacionCreateResponse(data=InstalacionData(**instalacion))


@router.get(
    "/api/v1/operativo/instalaciones",
    response_model=InstalacionListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_instalaciones(
    id_sucursal: int | None = Query(default=None),
    estado_instalacion: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> InstalacionListResponse | JSONResponse:
    try:
        instalaciones = InstalacionRepository(db).list(
            id_sucursal=id_sucursal,
            estado_instalacion=(
                estado_instalacion.strip().upper() if estado_instalacion else None
            ),
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo listar instalaciones.",
            {"error": str(exc)},
        )
    return InstalacionListResponse(
        data=[InstalacionData(**instalacion) for instalacion in instalaciones]
    )


@router.get(
    "/api/v1/operativo/instalaciones/{id_instalacion}",
    response_model=InstalacionDetailResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_instalacion(
    id_instalacion: int,
    db: Session = Depends(get_db),
) -> InstalacionDetailResponse | JSONResponse:
    try:
        instalacion = InstalacionRepository(db).get(id_instalacion)
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo obtener la instalación.",
            {"error": str(exc)},
        )
    if instalacion is None:
        return _error(404, "NOT_FOUND", "Instalación no encontrada.")
    return InstalacionDetailResponse(data=InstalacionData(**instalacion))
