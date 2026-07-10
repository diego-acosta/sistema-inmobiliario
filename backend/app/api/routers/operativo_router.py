from fastapi import APIRouter, Depends, Header, Path, Query, status
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
    CajaAperturaCreateRequest,
    CajaAperturaCerrarRequest,
    CajaAperturaData,
    CajaAperturaListResponse,
    CajaAperturaResponse,
    CajaAperturaVigenteResponse,
    CajaOperativaCreateRequest,
    CajaOperativaCreateResponse,
    CajaOperativaData,
    CajaOperativaDetailResponse,
    CajaOperativaListResponse,
    ErrorResponse,
    InstalacionCreateRequest,
    InstalacionCreateResponse,
    InstalacionData,
    InstalacionDetailResponse,
    InstalacionListResponse,
    ConfiguracionLocalRequest,
    ConfiguracionLocalResponse,
    ConfiguracionLocalData,
    ConfiguracionLocalListResponse,
    SucursalCreateRequest,
    SucursalCreateResponse,
    SucursalData,
    SucursalDetailResponse,
    SucursalListResponse,
)
from app.infrastructure.persistence.repositories.caja_apertura_repository import (
    CajaAperturaConcurrencyError,
    CajaAperturaDuplicateOpenError,
    CajaAperturaIdempotencyConflictError,
    CajaAperturaNotFoundError,
    CajaAperturaRepository,
    CajaAperturaValidationError,
)
from app.infrastructure.persistence.repositories.caja_operativa_repository import (
    CajaOperativaDuplicateActiveError,
    CajaOperativaIdempotencyConflictError,
    CajaOperativaNotFoundError,
    CajaOperativaRepository,
    CajaOperativaValidationError,
)
from app.infrastructure.persistence.repositories.configuracion_local_repository import (
    ConfiguracionLocalConcurrencyError,
    ConfiguracionLocalDuplicateActiveError,
    ConfiguracionLocalIdempotencyConflictError,
    ConfiguracionLocalNotFoundError,
    ConfiguracionLocalRepository,
    ConfiguracionLocalValidationError,
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


@router.get(
    "/api/v1/operativo/configuracion-local",
    response_model=ConfiguracionLocalListResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_configuracion_local(
    id_sucursal: int = Query(...),
    id_instalacion: int = Query(...),
    db: Session = Depends(get_db),
) -> ConfiguracionLocalListResponse | JSONResponse:
    try:
        configuraciones = ConfiguracionLocalRepository(db).list(
            id_sucursal=id_sucursal,
            id_instalacion=id_instalacion,
        )
    except ConfiguracionLocalNotFoundError as exc:
        return _error(404, "NOT_FOUND", str(exc))
    except ConfiguracionLocalValidationError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc))
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo consultar la configuración local.",
            {"error": str(exc)},
        )
    return ConfiguracionLocalListResponse(
        data=[ConfiguracionLocalData(**item) for item in configuraciones]
    )


@router.post(
    "/api/v1/operativo/configuracion-local",
    response_model=ConfiguracionLocalResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_configuracion_local(
    request: ConfiguracionLocalRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ConfiguracionLocalResponse | JSONResponse:
    core = _parse_core_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core
    try:
        created = ConfiguracionLocalRepository(db).create(request.model_dump(), core)
    except ConfiguracionLocalNotFoundError as exc:
        return _error(404, "NOT_FOUND", str(exc))
    except ConfiguracionLocalValidationError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc))
    except ConfiguracionLocalIdempotencyConflictError as exc:
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    except ConfiguracionLocalDuplicateActiveError as exc:
        return _error(409, "TECHNICAL_INCONSISTENCY", str(exc))
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo crear la configuración local.",
            {"error": str(exc)},
        )
    return ConfiguracionLocalResponse(data=ConfiguracionLocalData(**created))


@router.put(
    "/api/v1/operativo/configuracion-local/{id_configuracion_local}",
    response_model=ConfiguracionLocalResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        412: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_configuracion_local(
    request: ConfiguracionLocalRequest,
    id_configuracion_local: int = Path(...),
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ConfiguracionLocalResponse | JSONResponse:
    core = _parse_core_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core
    if if_match_version is None:
        return _error(
            400,
            "VALIDATION_ERROR",
            "If-Match-Version es requerido.",
            {"header": "If-Match-Version"},
        )
    try:
        version = int(if_match_version)
    except ValueError:
        return _error(
            400,
            "VALIDATION_ERROR",
            "If-Match-Version inválido.",
            {"header": "If-Match-Version"},
        )
    try:
        updated = ConfiguracionLocalRepository(db).update(
            id_configuracion_local, request.model_dump(), core, version
        )
    except ConfiguracionLocalNotFoundError as exc:
        return _error(404, "NOT_FOUND", str(exc))
    except ConfiguracionLocalValidationError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc))
    except ConfiguracionLocalConcurrencyError as exc:
        return _error(
            412, "CONCURRENCY_ERROR", str(exc), {"header": "If-Match-Version"}
        )
    except ConfiguracionLocalDuplicateActiveError as exc:
        return _error(409, "TECHNICAL_INCONSISTENCY", str(exc))
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo actualizar la configuración local.",
            {"error": str(exc)},
        )
    return ConfiguracionLocalResponse(data=ConfiguracionLocalData(**updated))


@router.post(
    "/api/v1/operativo/cajas",
    response_model=CajaOperativaCreateResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_caja_operativa(
    request: CajaOperativaCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> CajaOperativaCreateResponse | JSONResponse:
    core = _parse_core_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core
    try:
        caja = CajaOperativaRepository(db).create(request.model_dump(), core)
    except CajaOperativaNotFoundError as exc:
        return _error(404, "NOT_FOUND", str(exc))
    except CajaOperativaValidationError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc))
    except CajaOperativaIdempotencyConflictError as exc:
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    except CajaOperativaDuplicateActiveError as exc:
        return _error(409, "TECHNICAL_INCONSISTENCY", str(exc))
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo crear la caja operativa.",
            {"error": str(exc)},
        )
    return CajaOperativaCreateResponse(data=CajaOperativaData(**caja))


@router.get(
    "/api/v1/operativo/cajas",
    response_model=CajaOperativaListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_cajas_operativas(
    id_sucursal: int | None = Query(default=None),
    id_instalacion: int | None = Query(default=None),
    estado_caja: str | None = Query(default=None),
    tipo_caja: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> CajaOperativaListResponse | JSONResponse:
    try:
        cajas = CajaOperativaRepository(db).list(
            id_sucursal=id_sucursal,
            id_instalacion=id_instalacion,
            estado_caja=estado_caja.strip().upper() if estado_caja else None,
            tipo_caja=tipo_caja.strip().upper() if tipo_caja else None,
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo listar cajas operativas.",
            {"error": str(exc)},
        )
    return CajaOperativaListResponse(data=[CajaOperativaData(**caja) for caja in cajas])


@router.post(
    "/api/v1/operativo/cajas/{id_caja}/aperturas",
    response_model=CajaAperturaResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def abrir_caja_operativa(
    request: CajaAperturaCreateRequest,
    id_caja: int = Path(...),
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> CajaAperturaResponse | JSONResponse:
    core = _parse_core_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core
    try:
        apertura = CajaAperturaRepository(db).create(id_caja, request.model_dump(), core)
    except CajaAperturaNotFoundError as exc:
        return _error(404, "NOT_FOUND", str(exc))
    except CajaAperturaValidationError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc))
    except CajaAperturaIdempotencyConflictError as exc:
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    except CajaAperturaDuplicateOpenError as exc:
        return _error(409, "TECHNICAL_INCONSISTENCY", str(exc))
    except Exception as exc:
        return _error(500, "TECHNICAL_INCONSISTENCY", "No se pudo abrir la caja operativa.", {"error": str(exc)})
    return CajaAperturaResponse(data=CajaAperturaData(**apertura))


@router.patch(
    "/api/v1/operativo/cajas/aperturas/{id_apertura_caja}/cerrar",
    response_model=CajaAperturaResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 412: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def cerrar_caja_operativa(
    request: CajaAperturaCerrarRequest,
    id_apertura_caja: int = Path(...),
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> CajaAperturaResponse | JSONResponse:
    core = _parse_core_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core
    if if_match_version is None:
        return _error(400, "VALIDATION_ERROR", "If-Match-Version es requerido.", {"header": "If-Match-Version"})
    try:
        version = int(if_match_version)
    except ValueError:
        return _error(400, "VALIDATION_ERROR", "If-Match-Version inválido.", {"header": "If-Match-Version"})
    try:
        cierre = CajaAperturaRepository(db).cerrar(id_apertura_caja, request.model_dump(), core, version)
    except CajaAperturaNotFoundError as exc:
        return _error(404, "NOT_FOUND", str(exc))
    except CajaAperturaValidationError as exc:
        return _error(400, "VALIDATION_ERROR", str(exc))
    except CajaAperturaConcurrencyError as exc:
        return _error(412, "CONCURRENCY_ERROR", str(exc), {"header": "If-Match-Version"})
    except CajaAperturaDuplicateOpenError as exc:
        return _error(409, "TECHNICAL_INCONSISTENCY", str(exc))
    except Exception as exc:
        return _error(500, "TECHNICAL_INCONSISTENCY", "No se pudo cerrar la caja operativa.", {"error": str(exc)})
    return CajaAperturaResponse(data=CajaAperturaData(**cierre))


@router.get(
    "/api/v1/operativo/cajas/{id_caja}/apertura-vigente",
    response_model=CajaAperturaVigenteResponse,
    responses={500: {"model": ErrorResponse}},
)
def get_apertura_vigente_caja(
    id_caja: int,
    db: Session = Depends(get_db),
) -> CajaAperturaVigenteResponse | JSONResponse:
    try:
        apertura = CajaAperturaRepository(db).get_vigente_by_caja(id_caja)
    except Exception as exc:
        return _error(500, "TECHNICAL_INCONSISTENCY", "No se pudo consultar la apertura vigente.", {"error": str(exc)})
    return CajaAperturaVigenteResponse(data=CajaAperturaData(**apertura) if apertura else None)


@router.get(
    "/api/v1/operativo/cajas/aperturas-vigentes",
    response_model=CajaAperturaListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_aperturas_vigentes(
    id_sucursal: int | None = Query(default=None),
    id_instalacion: int | None = Query(default=None),
    abiertas_desde_antes_de: str | None = Query(default=None),
    solo_abiertas_de_dias_anteriores: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> CajaAperturaListResponse | JSONResponse:
    from datetime import datetime
    try:
        desde = datetime.fromisoformat(abiertas_desde_antes_de.replace("Z", "+00:00")) if abiertas_desde_antes_de else None
        aperturas = CajaAperturaRepository(db).list_vigentes(
            id_sucursal=id_sucursal,
            id_instalacion=id_instalacion,
            abiertas_desde_antes_de=desde,
            solo_abiertas_de_dias_anteriores=solo_abiertas_de_dias_anteriores,
        )
    except Exception as exc:
        return _error(500, "TECHNICAL_INCONSISTENCY", "No se pudo listar aperturas vigentes.", {"error": str(exc)})
    return CajaAperturaListResponse(data=[CajaAperturaData(**apertura) for apertura in aperturas])


@router.get(
    "/api/v1/operativo/cajas/{id_caja}",
    response_model=CajaOperativaDetailResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_caja_operativa(
    id_caja: int,
    db: Session = Depends(get_db),
) -> CajaOperativaDetailResponse | JSONResponse:
    try:
        caja = CajaOperativaRepository(db).get(id_caja)
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo obtener la caja operativa.",
            {"error": str(exc)},
        )
    if caja is None:
        return _error(404, "NOT_FOUND", "Caja operativa no encontrada.")
    return CajaOperativaDetailResponse(data=CajaOperativaData(**caja))
