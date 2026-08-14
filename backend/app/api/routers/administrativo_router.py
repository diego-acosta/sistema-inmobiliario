from typing import Annotated

from app.api.authentication import get_authenticated_principal
from app.api.core_ef_headers import (
    CoreEFHeaders,
    CoreEFHeaderValidationError,
    parse_core_ef_headers,
    parse_authenticated_core_ef_headers,
)
from app.api.administrative_authorization import require_administrative_permission
from app.api.dependencies import get_db
from app.api.schemas.administrativo import (
    AuthenticatedPrincipalData,
    AuthenticatedPrincipalResponse,
    ActualizarValorParametroGlobalRequest,
    ActualizarValorParametroGlobalResponse,
    CatalogoMaestroBajaResponse,
    CatalogoMaestroCreateRequest,
    CatalogoMaestroCreateResponse,
    CatalogoMaestroData,
    CatalogoMaestroDetailResponse,
    CatalogoMaestroListData,
    CatalogoMaestroListResponse,
    CatalogoMaestroUpdateRequest,
    CatalogoMaestroUpdateResponse,
    CatalogoMaestroWriteData,
    ErrorResponse,
    ItemCatalogoBajaResponse,
    ItemCatalogoCreateRequest,
    ItemCatalogoCreateResponse,
    ItemCatalogoData,
    ItemCatalogoEstadoRequest,
    ItemCatalogoEstadoResponse,
    ItemCatalogoListData,
    ItemCatalogoListResponse,
    ItemCatalogoUpdateRequest,
    ItemCatalogoUpdateResponse,
    ItemCatalogoWriteData,
    LoginData,
    LoginRequest,
    LoginResponse,
    ParametroGlobalValorResponse,
    ParametroSistemaAlcanceData,
    ParametroSistemaData,
    ParametroSistemaListData,
    ParametroSistemaListResponse,
    ParametroSistemaTipoData,
    PermisoData,
    PermisoListResponse,
    RolSeguridadData,
    RolSeguridadDetailResponse,
    RolSeguridadListResponse,
    RolSeguridadPermisosResponse,
    UsuarioAlcanceOperativoData,
    UsuarioAlcanceOperativoResponse,
    UsuarioRolSeguridadBajaResponse,
    UsuarioRolSeguridadCreateRequest,
    UsuarioRolSeguridadCreateResponse,
    UsuarioRolSeguridadData,
    UsuarioRolSeguridadListResponse,
    UsuarioSistemaBajaResponse,
    UsuarioSistemaCreateRequest,
    UsuarioSistemaCreateResponse,
    UsuarioSistemaData,
    UsuarioSistemaDetailResponse,
    UsuarioSistemaListResponse,
    UsuarioSucursalCreateRequest,
    UsuarioSucursalCreateResponse,
    UsuarioSucursalData,
    UsuarioSucursalListResponse,
)
from app.application.administrativo.authentication import (
    AuthenticatedPrincipal,
    AuthenticationService,
    AuthenticationTechnicalError,
    AuthenticationUnavailable,
    InvalidCredentials,
    InvalidSession,
    SessionTechnicalError,
    parse_bearer_header,
)
from app.application.administrativo.services.obtener_parametro_global_query_service import (
    ObtenerParametroGlobalQueryService,
    ParametroGlobalConflictError,
    ParametroGlobalInconsistencyError,
    ParametroGlobalNotFoundError,
)
from app.application.administrativo.services.actualizar_valor_parametro_global_service import (
    ActualizarValorParametroGlobalService,
    ParametroCommandError,
)
from app.config.settings import get_settings
from app.infrastructure.persistence.repositories.catalogo_maestro_repository import (
    CatalogoMaestroConcurrencyError,
    CatalogoMaestroDuplicateCodeError,
    CatalogoMaestroIdempotencyConflictError,
    CatalogoMaestroRepository,
)
from app.infrastructure.persistence.repositories.item_catalogo_repository import (
    ItemCatalogoConcurrencyError,
    ItemCatalogoDuplicateCodeError,
    ItemCatalogoIdempotencyConflictError,
    ItemCatalogoInvalidStateTransitionError,
    ItemCatalogoRepository,
)
from app.infrastructure.persistence.repositories.parametro_sistema_repository import (
    ParametroSistemaRepository,
)
from app.infrastructure.persistence.repositories.rol_seguridad_repository import (
    RolSeguridadRepository,
)
from app.infrastructure.persistence.repositories.usuario_rol_seguridad_repository import (  # noqa: E501
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
from app.infrastructure.persistence.repositories.usuario_sucursal_repository import (
    UsuarioSucursalDuplicateActiveError,
    UsuarioSucursalIdempotencyConflictError,
    UsuarioSucursalRepository,
)
from fastapi import APIRouter, Depends, Header, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

router = APIRouter(tags=["Administrativo"])


@router.get(
    "/api/v1/administrativo/seguridad/me",
    response_model=AuthenticatedPrincipalResponse,
    responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def obtener_principal_autenticado(
    response: Response,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_authenticated_principal)],
) -> AuthenticatedPrincipalResponse:
    # CORE-EF: QUERY_READLIKE; Authorization autentica y no hay headers write.
    response.headers["Cache-Control"] = "no-store"
    return AuthenticatedPrincipalResponse(
        data=AuthenticatedPrincipalData(
            **{
                field: getattr(principal, field)
                for field in AuthenticatedPrincipalData.model_fields
            }
        )
    )


@router.post(
    "/api/v1/administrativo/seguridad/login",
    response_model=LoginResponse,
    responses={
        401: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {
                "application/json": {"schema": LoginRequest.model_json_schema()}
            },
        }
    },
)
async def login_administrativo(
    request: Request, response: Response, db: Session = Depends(get_db)
) -> LoginResponse | JSONResponse:
    # CORE-EF: COMMAND_WRITE_TECNICO preautenticado, local y no sincronizable.
    try:
        payload = await request.json()
        credentials = LoginRequest.model_validate(payload)
    except (ValueError, TypeError, ValidationError):
        # Este endpoint procesa su body de forma acotada para impedir que FastAPI
        # incluya login/password o el body recibido en detail[].input.
        return _auth_error(
            422, "VALIDATION_ERROR", "La solicitud de login no es válida."
        )
    try:
        result = AuthenticationService(db, get_settings()).login(
            credentials.login, credentials.password
        )
    except InvalidCredentials:
        return _auth_error(
            401, "INVALID_CREDENTIALS", "Las credenciales no son válidas."
        )
    except AuthenticationUnavailable:
        return _auth_error(
            503,
            "AUTHENTICATION_UNAVAILABLE",
            "Autenticación temporalmente no disponible.",
        )
    except AuthenticationTechnicalError:
        return _auth_error(
            500,
            "AUTHENTICATION_TECHNICAL_ERROR",
            "No fue posible completar la autenticación.",
        )
    response.headers["Cache-Control"] = "no-store"
    return LoginResponse(
        data=LoginData(
            access_token=result.access_token,
            expires_at=result.expires_at,
            session_id=str(result.session_id),
        )
    )


@router.post(
    "/api/v1/administrativo/seguridad/logout",
    status_code=204,
    response_model=None,
    response_class=Response,
    responses={401: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def logout_administrativo(
    response: Response,
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
) -> Response | JSONResponse:
    # CORE-EF: COMMAND_WRITE_TECNICO local; Bearer es identidad e idempotency key natural.
    try:
        token = parse_bearer_header(authorization)
        AuthenticationService(db, get_settings()).logout(token)
    except InvalidSession:
        return _auth_error(401, "INVALID_SESSION", "La sesión no es válida.")
    except SessionTechnicalError:
        return _auth_error(
            500, "SESSION_TECHNICAL_ERROR", "No fue posible cerrar la sesión."
        )
    response.headers["Cache-Control"] = "no-store"
    response.status_code = 204
    return response


def _auth_error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ErrorResponse(
            error_code=code, error_message=message, details={}
        ).model_dump(),
        headers={"Cache-Control": "no-store"},
    )


def _item_write_error(exc: Exception) -> JSONResponse:
    if isinstance(exc, ItemCatalogoIdempotencyConflictError):
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    if isinstance(exc, ItemCatalogoConcurrencyError):
        return _error(409, "CONCURRENCY_ERROR", str(exc))
    if isinstance(exc, ItemCatalogoDuplicateCodeError):
        return _error(409, "DUPLICATE_CODE", str(exc))
    if isinstance(exc, ItemCatalogoInvalidStateTransitionError):
        return _error(409, "INVALID_STATE_TRANSITION", str(exc))
    return _error(
        500,
        "TECHNICAL_INCONSISTENCY",
        "No se pudo procesar el ítem del catálogo.",
        {},
    )


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


def _parse_core_write_or_error(
    *,
    x_op_id: str | None,
    x_usuario_id: str | None,
    x_sucursal_id: str | None,
    x_instalacion_id: str | None,
    if_match_version: str | None = None,
    require_if_match_version: bool = False,
) -> CoreEFHeaders | JSONResponse:
    try:
        return parse_core_ef_headers(
            x_op_id=x_op_id,
            x_usuario_id=x_usuario_id,
            x_sucursal_id=x_sucursal_id,
            x_instalacion_id=x_instalacion_id,
            if_match_version=if_match_version,
            require_if_match_version=require_if_match_version,
        )
    except CoreEFHeaderValidationError as exc:
        return _error(
            400,
            "VALIDATION_ERROR",
            exc.message,
            {"header": exc.header_name, "reason": exc.reason},
        )


@router.post(
    "/api/v1/administrativo/catalogos",
    status_code=201,
    response_model=CatalogoMaestroCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_catalogo_maestro(
    request: CatalogoMaestroCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> CatalogoMaestroCreateResponse | JSONResponse:
    # CORE-EF: COMMAND_WRITE_NEGOCIO; create versioned aggregate plus outbox.
    core = _parse_core_write_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core
    try:
        catalogo = CatalogoMaestroRepository(db).create(request.model_dump(), core)
    except CatalogoMaestroIdempotencyConflictError as exc:
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    except CatalogoMaestroDuplicateCodeError as exc:
        return _error(409, "DUPLICATE_CODE", str(exc))
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo crear el catálogo maestro.",
            {"error": str(exc)},
        )
    return CatalogoMaestroCreateResponse(data=CatalogoMaestroWriteData(**catalogo))


@router.put(
    "/api/v1/administrativo/catalogos/{id_catalogo_maestro}",
    response_model=CatalogoMaestroUpdateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_catalogo_maestro(
    id_catalogo_maestro: int,
    request: CatalogoMaestroUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> CatalogoMaestroUpdateResponse | JSONResponse:
    # CORE-EF: COMMAND_WRITE_NEGOCIO; conditional version update plus outbox.
    core = _parse_core_write_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core, JSONResponse):
        return core
    try:
        catalogo = CatalogoMaestroRepository(db).update(
            id_catalogo_maestro,
            request.model_dump(),
            core=core,
            if_match_version=core.if_match_version or 0,
        )
    except CatalogoMaestroIdempotencyConflictError as exc:
        return _error(409, "IDEMPOTENT_DUPLICATE", str(exc))
    except CatalogoMaestroConcurrencyError as exc:
        return _error(409, "CONCURRENCY_ERROR", str(exc))
    except CatalogoMaestroDuplicateCodeError as exc:
        return _error(409, "DUPLICATE_CODE", str(exc))
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo modificar el catálogo maestro.",
            {"error": str(exc)},
        )
    if catalogo is None:
        return _error(404, "NOT_FOUND", "Catálogo maestro no encontrado.")
    return CatalogoMaestroUpdateResponse(data=CatalogoMaestroWriteData(**catalogo))


@router.patch(
    "/api/v1/administrativo/catalogos/{id_catalogo_maestro}/baja",
    response_model=CatalogoMaestroBajaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def baja_catalogo_maestro(
    id_catalogo_maestro: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> CatalogoMaestroBajaResponse | JSONResponse:
    # CORE-EF: COMMAND_WRITE_NEGOCIO; soft delete, conditional version and outbox.
    core = _parse_core_write_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core, JSONResponse):
        return core
    try:
        catalogo = CatalogoMaestroRepository(db).baja_logica(
            id_catalogo_maestro, core=core, if_match_version=core.if_match_version or 0
        )
    except CatalogoMaestroConcurrencyError as exc:
        return _error(409, "CONCURRENCY_ERROR", str(exc))
    except Exception as exc:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo dar de baja el catálogo maestro.",
            {"error": str(exc)},
        )
    if catalogo is None:
        return _error(404, "NOT_FOUND", "Catálogo maestro no encontrado.")
    return CatalogoMaestroBajaResponse(data=CatalogoMaestroWriteData(**catalogo))


@router.post(
    "/api/v1/administrativo/catalogos/{id_catalogo_maestro}/items",
    status_code=201,
    response_model=ItemCatalogoCreateResponse,
)
def create_item_catalogo(
    id_catalogo_maestro: int,
    request: ItemCatalogoCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ItemCatalogoCreateResponse | JSONResponse:
    # CORE-EF: COMMAND_WRITE_NEGOCIO; alta idempotente y outbox transaccional.
    core = _parse_core_write_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core, JSONResponse):
        return core
    try:
        item = ItemCatalogoRepository(db).create(
            id_catalogo_maestro, request.model_dump(), core
        )
    except Exception as exc:
        return _item_write_error(exc)
    if item is None:
        return _error(404, "NOT_FOUND", "Catálogo maestro no encontrado.")
    return ItemCatalogoCreateResponse(data=ItemCatalogoWriteData(**item))


def _change_item(
    id_catalogo_maestro: int,
    id_item_catalogo: int,
    payload: dict,
    action: str,
    db: Session,
    x_op_id: str | None,
    x_usuario_id: str | None,
    x_sucursal_id: str | None,
    x_instalacion_id: str | None,
    if_match_version: str | None,
):
    core = _parse_core_write_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core, JSONResponse):
        return core
    try:
        item = ItemCatalogoRepository(db).change(
            id_catalogo_maestro,
            id_item_catalogo,
            payload,
            core,
            core.if_match_version or 0,
            action,
        )
    except Exception as exc:
        return _item_write_error(exc)
    if item is None:
        return _error(
            404, "NOT_FOUND", "Ítem o catálogo maestro no encontrado o no vigente."
        )
    return item


@router.put(
    "/api/v1/administrativo/catalogos/{id_catalogo_maestro}/items/{id_item_catalogo}",
    response_model=ItemCatalogoUpdateResponse,
)
def update_item_catalogo(
    id_catalogo_maestro: int,
    id_item_catalogo: int,
    request: ItemCatalogoUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ItemCatalogoUpdateResponse | JSONResponse:
    result = _change_item(
        id_catalogo_maestro,
        id_item_catalogo,
        request.model_dump(),
        "update",
        db,
        x_op_id,
        x_usuario_id,
        x_sucursal_id,
        x_instalacion_id,
        if_match_version,
    )
    return (
        result
        if isinstance(result, JSONResponse)
        else ItemCatalogoUpdateResponse(data=ItemCatalogoWriteData(**result))
    )


@router.patch(
    "/api/v1/administrativo/catalogos/{id_catalogo_maestro}/items/{id_item_catalogo}/estado",
    response_model=ItemCatalogoEstadoResponse,
)
def change_item_catalogo_estado(
    id_catalogo_maestro: int,
    id_item_catalogo: int,
    request: ItemCatalogoEstadoRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ItemCatalogoEstadoResponse | JSONResponse:
    result = _change_item(
        id_catalogo_maestro,
        id_item_catalogo,
        request.model_dump(),
        "estado",
        db,
        x_op_id,
        x_usuario_id,
        x_sucursal_id,
        x_instalacion_id,
        if_match_version,
    )
    return (
        result
        if isinstance(result, JSONResponse)
        else ItemCatalogoEstadoResponse(data=ItemCatalogoWriteData(**result))
    )


@router.patch(
    "/api/v1/administrativo/catalogos/{id_catalogo_maestro}/items/{id_item_catalogo}/baja",
    response_model=ItemCatalogoBajaResponse,
)
def baja_item_catalogo(
    id_catalogo_maestro: int,
    id_item_catalogo: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ItemCatalogoBajaResponse | JSONResponse:
    result = _change_item(
        id_catalogo_maestro,
        id_item_catalogo,
        {},
        "baja",
        db,
        x_op_id,
        x_usuario_id,
        x_sucursal_id,
        x_instalacion_id,
        if_match_version,
    )
    return (
        result
        if isinstance(result, JSONResponse)
        else ItemCatalogoBajaResponse(data=ItemCatalogoWriteData(**result))
    )


def _parametro_global_response(response: JSONResponse) -> JSONResponse:
    response.headers["Cache-Control"] = "no-store"
    return response


def _parametro_global_error(
    status_code: int, code: str, message: str, details: dict | None = None
) -> JSONResponse:
    return _parametro_global_response(_error(status_code, code, message, details))


ASCII_LEDGER_WHITESPACE = " \t\n\r\f\v"


def _validate_command_codigo(codigo: str) -> None:
    if not 1 <= len(codigo) <= 100 or not codigo.strip(ASCII_LEDGER_WHITESPACE):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "type": "value_error",
                    "loc": ["path", "codigo_parametro"],
                    "msg": "Value error, código de parámetro inválido",
                }
            ],
        )


@router.patch(
    "/api/v1/administrativo/configuracion/parametros/{codigo_parametro:path}/valor-global",
    response_model=ActualizarValorParametroGlobalResponse,
    responses={
        400: {"model": ErrorResponse},
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        412: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def actualizar_parametro_global(
    codigo_parametro: str,
    request: ActualizarValorParametroGlobalRequest,
    principal: Annotated[
        AuthenticatedPrincipal,
        Depends(
            require_administrative_permission("ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR")
        ),
    ],
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ActualizarValorParametroGlobalResponse | JSONResponse:
    # CORE-EF: COMMAND_WRITE_NEGOCIO. La identidad humana es sólo el principal.
    _validate_command_codigo(codigo_parametro)
    try:
        core = parse_authenticated_core_ef_headers(
            x_op_id, x_sucursal_id, x_instalacion_id, if_match_version
        )
    except CoreEFHeaderValidationError as exc:
        return _parametro_global_error(
            400,
            "VALIDATION_ERROR",
            exc.message,
            {"header": exc.header_name, "reason": exc.reason},
        )
    try:
        snapshot = ActualizarValorParametroGlobalService(db).execute(
            codigo_parametro=codigo_parametro,
            valor_tipado=request.valor_tipado,
            headers=core,
            id_usuario=principal.id_usuario,
        )
        db.commit()
    except ParametroCommandError as exc:
        db.rollback()
        messages = {
            "inconsistencia_contexto_tecnico": "El contexto técnico declarado es inconsistente.",
            "parametro_no_encontrado": "No existe un parámetro del sistema para el criterio indicado.",
            "conflicto_parametro": "Existe un conflicto con el parámetro solicitado.",
            "CONCURRENCY_ERROR": "La versión del recurso no coincide.",
            "inconsistencia_parametro": "La definición o el valor del parámetro resulta inconsistente.",
        }
        return _parametro_global_error(
            exc.status,
            exc.code,
            messages.get(exc.code, "No fue posible completar la operación."),
            {},
        )
    except Exception:
        db.rollback()
        return _parametro_global_error(
            500, "TECHNICAL_INCONSISTENCY", "No fue posible completar la operación.", {}
        )
    return _parametro_global_response(JSONResponse(content=snapshot))


@router.get(
    "/api/v1/administrativo/configuracion/parametros/{codigo_parametro}/valor-global",
    response_model=ParametroGlobalValorResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_parametro_global_marcado_vigente(
    codigo_parametro: str,
    db: Session = Depends(get_db),
) -> ParametroGlobalValorResponse | JSONResponse:
    # CORE-EF: QUERY_READLIKE. Ruta administrativa no pública; no usa headers
    # write, no bloquea, no muta, no emite outbox ni realiza commit.
    try:
        data = ObtenerParametroGlobalQueryService(
            ParametroSistemaRepository(db)
        ).obtener(codigo_parametro)
    except ParametroGlobalNotFoundError:
        return _parametro_global_error(
            404,
            "parametro_no_encontrado",
            "No existe un parámetro del sistema para el criterio indicado.",
            {},
        )
    except ParametroGlobalConflictError:
        return _parametro_global_error(
            409,
            "conflicto_parametro",
            "Existe un conflicto con el alcance del parámetro.",
            {},
        )
    except ParametroGlobalInconsistencyError:
        return _parametro_global_error(
            500,
            "inconsistencia_parametro",
            "La definición o el valor del parámetro resulta inconsistente.",
            {},
        )
    except Exception:
        return _parametro_global_error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo consultar el valor global del parámetro.",
            {},
        )
    return _parametro_global_response(
        JSONResponse(
            content=ParametroGlobalValorResponse(data=data).model_dump(mode="json")
        )
    )


@router.get(
    "/api/v1/administrativo/configuracion/parametros",
    response_model=ParametroSistemaListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_parametros_sistema(
    db: Session = Depends(get_db),
) -> ParametroSistemaListResponse | JSONResponse:
    # CORE-EF: QUERY_READLIKE. No usa headers write ni genera efectos persistentes.
    try:
        rows = ParametroSistemaRepository(db).list_definiciones()
    except Exception:
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo consultar el inventario de parámetros.",
            {},
        )

    items = [
        ParametroSistemaData(
            id_parametro_sistema=row["id_parametro_sistema"],
            codigo_parametro=row["codigo_parametro"],
            nombre_parametro=row["nombre_parametro"],
            descripcion=row["descripcion"],
            tipo=ParametroSistemaTipoData(
                id_tipo_dato_parametro=row["id_tipo_dato_parametro"],
                codigo_tipo_dato=row["codigo_tipo_dato"],
                nombre_tipo_dato=row["nombre_tipo_dato"],
            ),
            alcance=ParametroSistemaAlcanceData(
                id_alcance_parametro=row["id_alcance_parametro"],
                codigo_alcance=row["codigo_alcance"],
                nombre_alcance=row["nombre_alcance"],
            ),
        )
        for row in rows
    ]
    return ParametroSistemaListResponse(
        data=ParametroSistemaListData(items=items, total=len(items))
    )


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


def _validar_fecha_vigencia(
    request: UsuarioSucursalCreateRequest,
) -> JSONResponse | None:
    if request.fecha_hasta is not None and request.fecha_desde is not None:
        if request.fecha_hasta < request.fecha_desde:
            return _error(
                400,
                "VALIDATION_ERROR",
                "fecha_hasta no puede ser menor que fecha_desde.",
            )
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
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudieron listar sucursales del usuario.",
            {"error": str(exc)},
        )
    if sucursales is None:
        return _error(404, "NOT_FOUND", "Usuario del sistema no encontrado.")
    return UsuarioSucursalListResponse(
        data=[UsuarioSucursalData(**item) for item in sucursales]
    )


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
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo obtener el alcance operativo del usuario.",
            {"error": str(exc)},
        )
    data_sucursales = [UsuarioSucursalData(**item) for item in sucursales]
    predeterminada = next(
        (item for item in data_sucursales if item.es_sucursal_predeterminada), None
    )
    return UsuarioAlcanceOperativoResponse(
        data=UsuarioAlcanceOperativoData(
            usuario=UsuarioSistemaData(**usuario),
            sucursales_asignadas=data_sucursales,
            sucursal_predeterminada=predeterminada,
            puede_operar=any(item.puede_operar for item in data_sucursales),
            puede_consultar=any(item.puede_consultar for item in data_sucursales),
            puede_administrar=any(item.puede_administrar for item in data_sucursales),
            estado_vigencia="ACTIVO" if data_sucursales else "SIN_ALCANCE",
        )
    )


@router.post(
    "/api/v1/administrativo/usuarios/{id_usuario}/sucursales",
    status_code=201,
    response_model=UsuarioSucursalCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
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
    core = _parse_core_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
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
        return _error(
            500,
            "TECHNICAL_INCONSISTENCY",
            "No se pudo asignar sucursal al usuario.",
            {"error": str(exc)},
        )
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
