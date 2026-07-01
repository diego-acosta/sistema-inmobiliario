from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.core_ef_headers import (
    CoreEFHeaderValidationError,
    CoreEFHeaders,
    parse_core_ef_headers,
)
from app.api.dependencies import get_db
from app.api.schemas.administrativo import (
    ErrorResponse,
    PermisoData,
    PermisoListResponse,
    RolSeguridadData,
    RolSeguridadDetailResponse,
    RolSeguridadListResponse,
    RolSeguridadPermisosResponse,
    UsuarioSistemaBajaResponse,
    UsuarioSistemaCreateRequest,
    UsuarioSistemaCreateResponse,
    UsuarioSistemaData,
    UsuarioSistemaDetailResponse,
    UsuarioSistemaListResponse,
    UsuarioRolSeguridadBajaResponse,
    UsuarioRolSeguridadCreateRequest,
    UsuarioRolSeguridadCreateResponse,
    UsuarioRolSeguridadData,
    UsuarioRolSeguridadListResponse,
)
from app.infrastructure.persistence.repositories.rol_seguridad_repository import (
    RolSeguridadRepository,
)
from app.infrastructure.persistence.repositories.usuario_rol_seguridad_repository import (
    UsuarioRolSeguridadConcurrencyError,
    UsuarioRolSeguridadDuplicateActiveError,
    UsuarioRolSeguridadIdempotencyConflictError,
    UsuarioRolSeguridadRepository,
)
from app.infrastructure.persistence.repositories.usuario_sistema_repository import (
    UsuarioConcurrencyError,
    UsuarioIdempotencyConflictError,
    UsuarioSistemaRepository,
)

router = APIRouter(tags=["Administrativo"])


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


@router.get(
    "/api/v1/administrativo/roles-seguridad",
    response_model=RolSeguridadListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_roles_seguridad(
    db: Session = Depends(get_db),
) -> RolSeguridadListResponse | JSONResponse:
    try:
        roles = RolSeguridadRepository(db).list_roles_seguridad()
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo listar roles de seguridad.",
            {"error": str(exc)},
        )
    return RolSeguridadListResponse(data=[RolSeguridadData(**rol) for rol in roles])


@router.get(
    "/api/v1/administrativo/roles-seguridad/{id_rol_seguridad}",
    response_model=RolSeguridadDetailResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_rol_seguridad(
    id_rol_seguridad: int,
    db: Session = Depends(get_db),
) -> RolSeguridadDetailResponse | JSONResponse:
    try:
        rol = RolSeguridadRepository(db).get_rol_seguridad(id_rol_seguridad)
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo obtener el rol de seguridad.",
            {"error": str(exc)},
        )
    if rol is None:
        return _error(404, "NOT_FOUND", "Rol de seguridad no encontrado.")
    return RolSeguridadDetailResponse(data=RolSeguridadData(**rol))


@router.get(
    "/api/v1/administrativo/permisos",
    response_model=PermisoListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_permisos(
    db: Session = Depends(get_db),
) -> PermisoListResponse | JSONResponse:
    try:
        permisos = RolSeguridadRepository(db).list_permisos()
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo listar permisos.",
            {"error": str(exc)},
        )
    return PermisoListResponse(data=[PermisoData(**permiso) for permiso in permisos])


@router.get(
    "/api/v1/administrativo/roles-seguridad/{id_rol_seguridad}/permisos",
    response_model=RolSeguridadPermisosResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def list_permisos_by_rol_seguridad(
    id_rol_seguridad: int,
    db: Session = Depends(get_db),
) -> RolSeguridadPermisosResponse | JSONResponse:
    try:
        permisos = RolSeguridadRepository(db).list_permisos_by_rol_seguridad(
            id_rol_seguridad
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudieron listar permisos del rol de seguridad.",
            {"error": str(exc)},
        )
    if permisos is None:
        return _error(404, "NOT_FOUND", "Rol de seguridad no encontrado.")
    return RolSeguridadPermisosResponse(
        data=[PermisoData(**permiso) for permiso in permisos]
    )


@router.post(
    "/api/v1/administrativo/usuarios",
    status_code=201,
    response_model=UsuarioSistemaCreateResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def create_usuario_sistema(
    request: UsuarioSistemaCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> UsuarioSistemaCreateResponse | JSONResponse:
    core = _parse_core_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core

    try:
        usuario = UsuarioSistemaRepository(db).create(request.model_dump(), core)
    except UsuarioIdempotencyConflictError as exc:
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    except IntegrityError:
        return _error(
            409,
            "TECHNICAL_INCONSISTENCY",
            "Ya existe un usuario con ese código o login.",
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo crear el usuario del sistema.",
            {"error": str(exc)},
        )

    return UsuarioSistemaCreateResponse(data=UsuarioSistemaData(**usuario))


@router.get(
    "/api/v1/administrativo/usuarios",
    response_model=UsuarioSistemaListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_usuarios_sistema(
    incluir_bajas: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> UsuarioSistemaListResponse | JSONResponse:
    try:
        usuarios = UsuarioSistemaRepository(db).list(incluir_bajas=incluir_bajas)
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo listar usuarios del sistema.",
            {"error": str(exc)},
        )
    return UsuarioSistemaListResponse(
        data=[UsuarioSistemaData(**usuario) for usuario in usuarios]
    )


@router.get(
    "/api/v1/administrativo/usuarios/{id_usuario}",
    response_model=UsuarioSistemaDetailResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_usuario_sistema(
    id_usuario: int,
    db: Session = Depends(get_db),
) -> UsuarioSistemaDetailResponse | JSONResponse:
    try:
        usuario = UsuarioSistemaRepository(db).get(id_usuario)
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo obtener el usuario del sistema.",
            {"error": str(exc)},
        )
    if usuario is None:
        return _error(404, "NOT_FOUND", "Usuario del sistema no encontrado.")
    return UsuarioSistemaDetailResponse(data=UsuarioSistemaData(**usuario))


@router.get(
    "/api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad",
    response_model=UsuarioRolSeguridadListResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def list_roles_seguridad_by_usuario(
    id_usuario: int,
    incluir_bajas: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> UsuarioRolSeguridadListResponse | JSONResponse:
    try:
        asignaciones = UsuarioRolSeguridadRepository(db).list_by_usuario(
            id_usuario, incluir_bajas=incluir_bajas
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudieron listar roles de seguridad del usuario.",
            {"error": str(exc)},
        )
    if asignaciones is None:
        return _error(404, "NOT_FOUND", "Usuario del sistema no encontrado.")
    return UsuarioRolSeguridadListResponse(
        data=[UsuarioRolSeguridadData(**item) for item in asignaciones]
    )


@router.post(
    "/api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad",
    status_code=201,
    response_model=UsuarioRolSeguridadCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def assign_rol_seguridad_to_usuario(
    id_usuario: int,
    request: UsuarioRolSeguridadCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> UsuarioRolSeguridadCreateResponse | JSONResponse:
    core = _parse_core_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core

    repo = UsuarioRolSeguridadRepository(db)
    try:
        if not repo.exists_usuario(id_usuario):
            return _error(404, "NOT_FOUND", "Usuario del sistema no encontrado.")
        if not repo.exists_rol_seguridad(request.id_rol_seguridad):
            return _error(404, "NOT_FOUND", "Rol de seguridad no encontrado.")
        asignacion = repo.create(id_usuario, request.model_dump(), core)
    except UsuarioRolSeguridadIdempotencyConflictError as exc:
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    except UsuarioRolSeguridadDuplicateActiveError as exc:
        return _error(409, "TECHNICAL_INCONSISTENCY", str(exc))
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo asignar el rol de seguridad al usuario.",
            {"error": str(exc)},
        )
    return UsuarioRolSeguridadCreateResponse(data=UsuarioRolSeguridadData(**asignacion))


@router.patch(
    "/api/v1/administrativo/usuarios/{id_usuario}/roles-seguridad/{id_asignacion}/baja",
    response_model=UsuarioRolSeguridadBajaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def baja_rol_seguridad_usuario(
    id_usuario: int,
    id_asignacion: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> UsuarioRolSeguridadBajaResponse | JSONResponse:
    try:
        core = parse_core_ef_headers(
            x_op_id=x_op_id,
            x_usuario_id=x_usuario_id,
            x_sucursal_id=x_sucursal_id,
            x_instalacion_id=x_instalacion_id,
            if_match_version=if_match_version,
            require_if_match_version=True,
        )
    except CoreEFHeaderValidationError as exc:
        return _error(
            400,
            "VALIDATION_ERROR",
            exc.message,
            {"header": exc.header_name, "reason": exc.reason},
        )

    try:
        asignacion = UsuarioRolSeguridadRepository(db).baja_logica(
            id_usuario,
            id_asignacion,
            core=core,
            if_match_version=core.if_match_version or 0,
        )
    except UsuarioRolSeguridadConcurrencyError as exc:
        return _error(409, "CONCURRENCY_ERROR", str(exc))
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo dar de baja la asignación de rol de seguridad.",
            {"error": str(exc)},
        )
    if asignacion is None:
        return _error(404, "NOT_FOUND", "Asignación de rol de seguridad no encontrada.")
    return UsuarioRolSeguridadBajaResponse(data=UsuarioRolSeguridadData(**asignacion))


@router.get(
    "/api/v1/administrativo/roles-seguridad/{id_rol_seguridad}/usuarios",
    response_model=UsuarioRolSeguridadListResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def list_usuarios_by_rol_seguridad(
    id_rol_seguridad: int,
    incluir_bajas: bool = Query(default=False),
    db: Session = Depends(get_db),
) -> UsuarioRolSeguridadListResponse | JSONResponse:
    try:
        asignaciones = UsuarioRolSeguridadRepository(db).list_by_rol_seguridad(
            id_rol_seguridad, incluir_bajas=incluir_bajas
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudieron listar usuarios del rol de seguridad.",
            {"error": str(exc)},
        )
    if asignaciones is None:
        return _error(404, "NOT_FOUND", "Rol de seguridad no encontrado.")
    return UsuarioRolSeguridadListResponse(
        data=[UsuarioRolSeguridadData(**item) for item in asignaciones]
    )


@router.patch(
    "/api/v1/administrativo/usuarios/{id_usuario}/baja",
    response_model=UsuarioSistemaBajaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def baja_usuario_sistema(
    id_usuario: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> UsuarioSistemaBajaResponse | JSONResponse:
    try:
        core = parse_core_ef_headers(
            x_op_id=x_op_id,
            x_usuario_id=x_usuario_id,
            x_sucursal_id=x_sucursal_id,
            x_instalacion_id=x_instalacion_id,
            if_match_version=if_match_version,
            require_if_match_version=True,
        )
    except CoreEFHeaderValidationError as exc:
        return _error(
            400,
            "VALIDATION_ERROR",
            exc.message,
            {"header": exc.header_name, "reason": exc.reason},
        )

    try:
        usuario = UsuarioSistemaRepository(db).baja_logica(
            id_usuario,
            core=core,
            if_match_version=core.if_match_version or 0,
        )
    except UsuarioConcurrencyError as exc:
        return _error(409, "CONCURRENCY_ERROR", str(exc))
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo dar de baja el usuario del sistema.",
            {"error": str(exc)},
        )
    if usuario is None:
        return _error(404, "NOT_FOUND", "Usuario del sistema no encontrado.")
    return UsuarioSistemaBajaResponse(data=UsuarioSistemaData(**usuario))
