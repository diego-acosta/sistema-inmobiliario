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
    CatalogoMaestroData,
    CatalogoMaestroDetailResponse,
    CatalogoMaestroListData,
    CatalogoMaestroListResponse,
    ErrorResponse,
    ItemCatalogoData,
    ItemCatalogoListData,
    ItemCatalogoListResponse,
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
    UsuarioSucursalCreateRequest,
    UsuarioSucursalCreateResponse,
    UsuarioSucursalData,
    UsuarioSucursalListResponse,
    UsuarioAlcanceOperativoData,
    UsuarioAlcanceOperativoResponse,
)
from app.infrastructure.persistence.repositories.catalogo_maestro_repository import (
    CatalogoMaestroRepository,
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
from app.infrastructure.persistence.repositories.usuario_sucursal_repository import (
    UsuarioSucursalDuplicateActiveError,
    UsuarioSucursalIdempotencyConflictError,
    UsuarioSucursalRepository,
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


def _normalize_query(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


@router.get(
    "/api/v1/administrativo/catalogos",
    response_model=CatalogoMaestroListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_catalogos_maestros(
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> CatalogoMaestroListResponse | JSONResponse:
    # CORE-EF: QUERY_READLIKE. Headers write, If-Match-Version, idempotencia,
    # outbox, lock, versionado y transacción write: NO APLICA.
    try:
        result = CatalogoMaestroRepository(db).list_catalogos(
            q=_normalize_query(q), page=page, page_size=page_size
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudieron listar catálogos maestros.",
            {"error": str(exc)},
        )
    return CatalogoMaestroListResponse(
        data=CatalogoMaestroListData(
            items=[CatalogoMaestroData(**item) for item in result["items"]],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
        )
    )


@router.get(
    "/api/v1/administrativo/catalogos/{id_catalogo_maestro}",
    response_model=CatalogoMaestroDetailResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_catalogo_maestro(
    id_catalogo_maestro: int,
    db: Session = Depends(get_db),
) -> CatalogoMaestroDetailResponse | JSONResponse:
    # CORE-EF: QUERY_READLIKE sin efectos persistentes ni headers write.
    try:
        catalogo = CatalogoMaestroRepository(db).get_catalogo(id_catalogo_maestro)
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo obtener el catálogo maestro.",
            {"error": str(exc)},
        )
    if catalogo is None:
        return _error(404, "NOT_FOUND", "Catálogo maestro no encontrado.")
    return CatalogoMaestroDetailResponse(data=CatalogoMaestroData(**catalogo))


@router.get(
    "/api/v1/administrativo/catalogos/{id_catalogo_maestro}/items",
    response_model=ItemCatalogoListResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def list_items_catalogo(
    id_catalogo_maestro: int,
    q: str | None = Query(default=None),
    estado_item_catalogo: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
) -> ItemCatalogoListResponse | JSONResponse:
    # CORE-EF: QUERY_READLIKE. Filtro estado_item_catalogo literal; NULL se preserva.
    try:
        result = CatalogoMaestroRepository(db).list_items(
            id_catalogo_maestro=id_catalogo_maestro,
            q=_normalize_query(q),
            estado_item_catalogo=estado_item_catalogo,
            page=page,
            page_size=page_size,
        )
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudieron listar ítems del catálogo maestro.",
            {"error": str(exc)},
        )
    if result is None:
        return _error(404, "NOT_FOUND", "Catálogo maestro no encontrado.")
    return ItemCatalogoListResponse(
        data=ItemCatalogoListData(
            items=[ItemCatalogoData(**item) for item in result["items"]],
            total=result["total"],
            page=result["page"],
            page_size=result["page_size"],
        )
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


def _validar_fecha_vigencia(request: UsuarioSucursalCreateRequest) -> JSONResponse | None:
    if request.fecha_hasta is not None and request.fecha_desde is not None:
        if request.fecha_hasta < request.fecha_desde:
            return _error(400, "VALIDATION_ERROR", "fecha_hasta no puede ser menor que fecha_desde.")
    return None


@router.get(
    "/api/v1/administrativo/usuarios/{id_usuario}/sucursales",
    response_model=UsuarioSucursalListResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def list_sucursales_by_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
) -> UsuarioSucursalListResponse | JSONResponse:
    try:
        sucursales = UsuarioSucursalRepository(db).list_by_usuario(id_usuario)
    except Exception as exc:
        return _error(500, "TECHNICAL_INCONSISTENCY", "No se pudieron listar sucursales del usuario.", {"error": str(exc)})
    if sucursales is None:
        return _error(404, "NOT_FOUND", "Usuario del sistema no encontrado.")
    return UsuarioSucursalListResponse(data=[UsuarioSucursalData(**item) for item in sucursales])


@router.get(
    "/api/v1/administrativo/usuarios/{id_usuario}/alcance-operativo",
    response_model=UsuarioAlcanceOperativoResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_alcance_operativo_usuario(
    id_usuario: int,
    db: Session = Depends(get_db),
) -> UsuarioAlcanceOperativoResponse | JSONResponse:
    try:
        usuario = UsuarioSistemaRepository(db).get(id_usuario)
        if usuario is None:
            return _error(404, "NOT_FOUND", "Usuario del sistema no encontrado.")
        sucursales = UsuarioSucursalRepository(db).list_by_usuario(id_usuario) or []
    except Exception as exc:
        return _error(500, "TECHNICAL_INCONSISTENCY", "No se pudo obtener el alcance operativo del usuario.", {"error": str(exc)})
    data_sucursales = [UsuarioSucursalData(**item) for item in sucursales]
    predeterminada = next((item for item in data_sucursales if item.es_sucursal_predeterminada), None)
    return UsuarioAlcanceOperativoResponse(data=UsuarioAlcanceOperativoData(
        usuario=UsuarioSistemaData(**usuario),
        sucursales_asignadas=data_sucursales,
        sucursal_predeterminada=predeterminada,
        puede_operar=any(item.puede_operar for item in data_sucursales),
        puede_consultar=any(item.puede_consultar for item in data_sucursales),
        puede_administrar=any(item.puede_administrar for item in data_sucursales),
        estado_vigencia="ACTIVO" if data_sucursales else "SIN_ALCANCE",
    ))


@router.post(
    "/api/v1/administrativo/usuarios/{id_usuario}/sucursales",
    status_code=201,
    response_model=UsuarioSucursalCreateResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def assign_sucursal_to_usuario(
    id_usuario: int,
    request: UsuarioSucursalCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> UsuarioSucursalCreateResponse | JSONResponse:
    core = _parse_core_or_error(x_op_id=x_op_id, x_usuario_id=x_usuario_id, x_sucursal_id=x_sucursal_id, x_instalacion_id=x_instalacion_id)
    if isinstance(core, JSONResponse):
        return core
    fecha_error = _validar_fecha_vigencia(request)
    if fecha_error is not None:
        return fecha_error
    payload = request.model_dump()
    repo = UsuarioSucursalRepository(db)
    try:
        if not repo.exists_usuario(id_usuario):
            return _error(404, "NOT_FOUND", "Usuario del sistema no encontrado.")
        if not repo.exists_sucursal(request.id_sucursal):
            return _error(404, "NOT_FOUND", "Sucursal no encontrada.")
        vinculo = repo.create(id_usuario, payload, core)
    except UsuarioSucursalIdempotencyConflictError as exc:
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    except UsuarioSucursalDuplicateActiveError as exc:
        return _error(409, "TECHNICAL_INCONSISTENCY", str(exc))
    except Exception as exc:
        return _error(500, "TECHNICAL_INCONSISTENCY", "No se pudo asignar sucursal al usuario.", {"error": str(exc)})
    if vinculo is None:
        return _error(404, "NOT_FOUND", "Usuario o sucursal no encontrado.")
    return UsuarioSucursalCreateResponse(data=UsuarioSucursalData(**vinculo))


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
