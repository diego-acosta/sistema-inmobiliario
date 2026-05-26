from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.core_ef_headers import (
    CoreEFHeaderValidationError,
    CoreEFHeaders,
    parse_core_ef_headers,
)
from app.api.schemas.inmuebles import (
    ActivoIntegracionTraceResponse,
    ActivoIntegracionVentaItem,
    DisponibilidadBajaData,
    DisponibilidadBajaResponse,
    DisponibilidadCerrarData,
    DisponibilidadCerrarRequest,
    DisponibilidadCerrarResponse,
    DisponibilidadCreateData,
    DisponibilidadCreateRequest,
    DisponibilidadCreateResponse,
    DisponibilidadListItem,
    DisponibilidadListResponse,
    DisponibilidadReemplazarVigenteRequest,
    DisponibilidadUpdateData,
    DisponibilidadUpdateRequest,
    DisponibilidadUpdateResponse,
    ErrorResponse,
    OcupacionBajaData,
    OcupacionBajaResponse,
    OcupacionCerrarData,
    OcupacionCerrarRequest,
    OcupacionCerrarResponse,
    OcupacionCreateData,
    OcupacionCreateRequest,
    OcupacionCreateResponse,
    OcupacionReemplazarVigenteRequest,
    OcupacionListItem,
    OcupacionListResponse,
    OcupacionUpdateData,
    OcupacionUpdateRequest,
    OcupacionUpdateResponse,
    InmuebleAsociarDesarrolloData,
    InmuebleAsociarDesarrolloRequest,
    InmuebleAsociarDesarrolloResponse,
    InmuebleBajaData,
    InmuebleBajaResponse,
    InmuebleCreateData,
    InmuebleCreateRequest,
    InmuebleCreateResponse,
    InmuebleDesasociarDesarrolloData,
    InmuebleDesasociarDesarrolloResponse,
    InmuebleDetailData,
    InmuebleDetailResponse,
    InmuebleDetalleIntegralResponse,
    InmuebleListItem,
    InmuebleListResponse,
    InmuebleServicioCreateData,
    InmuebleServicioCreateRequest,
    InmuebleServicioCreateResponse,
    InmuebleServicioListItem,
    InmuebleServicioListResponse,
    InmuebleUpdateData,
    InmuebleUpdateRequest,
    InmuebleUpdateResponse,
    UnidadFuncionalCreateData,
    UnidadFuncionalCreateRequest,
    UnidadFuncionalCreateResponse,
    UnidadFuncionalBajaData,
    UnidadFuncionalBajaResponse,
    UnidadFuncionalDetailData,
    UnidadFuncionalDetailResponse,
    UnidadFuncionalDetalleIntegralResponse,
    UnidadFuncionalListItem,
    UnidadFuncionalListResponse,
    UnidadFuncionalServicioCreateData,
    UnidadFuncionalServicioCreateRequest,
    UnidadFuncionalServicioCreateResponse,
    UnidadFuncionalServicioListItem,
    UnidadFuncionalServicioListResponse,
    UnidadFuncionalUpdateData,
    UnidadFuncionalUpdateRequest,
    UnidadFuncionalUpdateResponse,
)
from app.application.common.commands import CommandContext
from app.application.inmuebles.commands.create_disponibilidad import (
    CreateDisponibilidadCommand,
)
from app.application.inmuebles.commands.replace_disponibilidad_vigente import (
    ReplaceDisponibilidadVigenteCommand,
)
from app.application.inmuebles.commands.replace_ocupacion_vigente import (
    ReplaceOcupacionVigenteCommand,
)
from app.application.inmuebles.commands.create_ocupacion import (
    CreateOcupacionCommand,
)
from app.application.inmuebles.commands.close_ocupacion import (
    CloseOcupacionCommand,
)
from app.application.inmuebles.commands.close_disponibilidad import (
    CloseDisponibilidadCommand,
)
from app.application.inmuebles.commands.delete_disponibilidad import (
    DeleteDisponibilidadCommand,
)
from app.application.inmuebles.commands.delete_ocupacion import (
    DeleteOcupacionCommand,
)
from app.application.inmuebles.commands.associate_inmueble_desarrollo import (
    AssociateInmuebleDesarrolloCommand,
)
from app.application.inmuebles.commands.create_inmueble import CreateInmuebleCommand
from app.application.inmuebles.commands.create_inmueble_servicio import (
    CreateInmuebleServicioCommand,
)
from app.application.inmuebles.commands.create_unidad_funcional import (
    CreateUnidadFuncionalCommand,
)
from app.application.inmuebles.commands.create_unidad_funcional_servicio import (
    CreateUnidadFuncionalServicioCommand,
)
from app.application.inmuebles.commands.delete_inmueble import DeleteInmuebleCommand
from app.application.inmuebles.commands.delete_unidad_funcional import (
    DeleteUnidadFuncionalCommand,
)
from app.application.inmuebles.commands.disassociate_inmueble_desarrollo import (
    DisassociateInmuebleDesarrolloCommand,
)
from app.application.inmuebles.commands.update_inmueble import UpdateInmuebleCommand
from app.application.inmuebles.commands.update_disponibilidad import (
    UpdateDisponibilidadCommand,
)
from app.application.inmuebles.commands.update_ocupacion import (
    UpdateOcupacionCommand,
)
from app.application.inmuebles.commands.update_unidad_funcional import (
    UpdateUnidadFuncionalCommand,
)
from app.application.inmuebles.services.create_disponibilidad_service import (
    CreateDisponibilidadService,
)
from app.application.inmuebles.services.replace_disponibilidad_vigente_service import (
    ReplaceDisponibilidadVigenteService,
)
from app.application.inmuebles.services.replace_ocupacion_vigente_service import (
    ReplaceOcupacionVigenteService,
)
from app.application.inmuebles.services.create_ocupacion_service import (
    CreateOcupacionService,
)
from app.application.inmuebles.services.close_ocupacion_service import (
    CloseOcupacionService,
)
from app.application.inmuebles.services.close_disponibilidad_service import (
    CloseDisponibilidadService,
)
from app.application.inmuebles.services.delete_disponibilidad_service import (
    DeleteDisponibilidadService,
)
from app.application.inmuebles.services.delete_ocupacion_service import (
    DeleteOcupacionService,
)
from app.application.inmuebles.services.associate_inmueble_desarrollo_service import (
    AssociateInmuebleDesarrolloService,
)
from app.application.inmuebles.services.create_inmueble_service import (
    CreateInmuebleService,
)
from app.application.inmuebles.services.create_inmueble_servicio_service import (
    CreateInmuebleServicioService,
)
from app.application.inmuebles.services.create_unidad_funcional_service import (
    CreateUnidadFuncionalService,
)
from app.application.inmuebles.services.create_unidad_funcional_servicio_service import (
    CreateUnidadFuncionalServicioService,
)
from app.application.inmuebles.services.delete_inmueble_service import (
    DeleteInmuebleService,
)
from app.application.inmuebles.services.delete_unidad_funcional_service import (
    DeleteUnidadFuncionalService,
)
from app.application.inmuebles.services.disassociate_inmueble_desarrollo_service import (
    DisassociateInmuebleDesarrolloService,
)
from app.application.inmuebles.services.get_inmueble_disponibilidades_service import (
    GetInmuebleDisponibilidadesService,
)
from app.application.inmuebles.services.get_inmueble_detalle_integral_service import (
    GetInmuebleDetalleIntegralService,
)
from app.application.inmuebles.services.get_inmueble_integracion_trazabilidad_service import (
    GetInmuebleIntegracionTrazabilidadService,
)
from app.application.inmuebles.services.get_inmueble_ocupaciones_service import (
    GetInmuebleOcupacionesService,
)
from app.application.inmuebles.services.get_inmueble_service import (
    GetInmuebleService,
)
from app.application.inmuebles.services.get_inmueble_servicios_service import (
    GetInmuebleServiciosService,
)
from app.application.inmuebles.services.get_inmuebles_service import (
    GetInmueblesService,
)
from app.application.inmuebles.services.get_unidad_funcional_disponibilidades_service import (
    GetUnidadFuncionalDisponibilidadesService,
)
from app.application.inmuebles.services.get_unidad_funcional_detalle_integral_service import (
    GetUnidadFuncionalDetalleIntegralService,
)
from app.application.inmuebles.services.get_unidad_funcional_integracion_trazabilidad_service import (
    GetUnidadFuncionalIntegracionTrazabilidadService,
)
from app.application.inmuebles.services.get_unidad_funcional_ocupaciones_service import (
    GetUnidadFuncionalOcupacionesService,
)
from app.application.inmuebles.services.get_unidad_funcional_service import (
    GetUnidadFuncionalService,
)
from app.application.inmuebles.services.get_unidad_funcional_servicios_service import (
    GetUnidadFuncionalServiciosService,
)
from app.application.inmuebles.services.get_unidades_funcionales_global_service import (
    GetUnidadesFuncionalesGlobalService,
)
from app.application.inmuebles.services.get_unidades_funcionales_service import (
    GetUnidadesFuncionalesService,
)
from app.application.inmuebles.services.update_inmueble_service import (
    UpdateInmuebleService,
)
from app.application.inmuebles.services.update_disponibilidad_service import (
    UpdateDisponibilidadService,
)
from app.application.inmuebles.services.update_ocupacion_service import (
    UpdateOcupacionService,
)
from app.application.inmuebles.services.update_unidad_funcional_service import (
    UpdateUnidadFuncionalService,
)
from app.infrastructure.persistence.repositories.inmueble_repository import (
    InmuebleRepository,
)


router = APIRouter(tags=["Inmobiliario"])

_CORE_EF_REQUIRED_HEADERS_OPENAPI = {
    "parameters": [
        {
            "name": "X-Op-Id",
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
        },
        {
            "name": "X-Usuario-Id",
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
        },
        {
            "name": "X-Sucursal-Id",
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
        },
        {
            "name": "X-Instalacion-Id",
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
        },
    ]
}
_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI = {
    "parameters": [
        *_CORE_EF_REQUIRED_HEADERS_OPENAPI["parameters"],
        {
            "name": "If-Match-Version",
            "in": "header",
            "required": True,
            "schema": {"type": "string"},
        },
    ]
}


class InmuebleCommandContext(CommandContext):
    __slots__ = ("id_instalacion", "op_id")

    def __init__(
        self,
        *,
        id_instalacion: int | None,
        op_id: UUID | None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.id_instalacion = id_instalacion
        self.op_id = op_id


def _core_ef_error_response(exc: CoreEFHeaderValidationError) -> JSONResponse:
    error = ErrorResponse(
        error_code="VALIDATION_ERROR",
        error_message=exc.message,
        details={"header": exc.header_name},
    )
    return JSONResponse(status_code=400, content=error.model_dump())


def _parse_core_ef_headers_or_error(
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
            if_match_version=None,
        )
    except CoreEFHeaderValidationError as exc:
        return _core_ef_error_response(exc)


def _parse_core_ef_headers_with_if_match_or_error(
    *,
    x_op_id: str | None,
    x_usuario_id: str | None,
    x_sucursal_id: str | None,
    x_instalacion_id: str | None,
    if_match_version: str | None,
    require_if_match_version: bool,
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
        return _core_ef_error_response(exc)


def _build_inmueble_command_context(
    core_ef_headers: CoreEFHeaders,
) -> InmuebleCommandContext:
    return InmuebleCommandContext(
        id_instalacion=core_ef_headers.x_instalacion_id,
        op_id=core_ef_headers.x_op_id,
        request_id=core_ef_headers.x_op_id,
        actor_id=str(core_ef_headers.x_usuario_id),
        metadata={
            "x_op_id": str(core_ef_headers.x_op_id),
            "x_sucursal_id": str(core_ef_headers.x_sucursal_id),
            "x_instalacion_id": str(core_ef_headers.x_instalacion_id),
        },
    )


@router.post(
    "/api/v1/inmuebles",
    status_code=201,
    response_model=InmuebleCreateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_inmueble(
    request: InmuebleCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> InmuebleCreateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = CreateInmuebleCommand(
        context=context,
        id_desarrollo=request.id_desarrollo,
        codigo_inmueble=request.codigo_inmueble,
        nombre_inmueble=request.nombre_inmueble,
        superficie=request.superficie,
        estado_administrativo=request.estado_administrativo,
        estado_juridico=request.estado_juridico,
        observaciones=request.observaciones,
    )

    repository = InmuebleRepository(db)
    service = CreateInmuebleService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear el inmueble.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return InmuebleCreateResponse(data=InmuebleCreateData(**result.data))


@router.post(
    "/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
    status_code=201,
    response_model=UnidadFuncionalCreateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_unidad_funcional(
    id_inmueble: int,
    request: UnidadFuncionalCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> UnidadFuncionalCreateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = CreateUnidadFuncionalCommand(
        context=context,
        id_inmueble=id_inmueble,
        codigo_unidad=request.codigo_unidad,
        nombre_unidad=request.nombre_unidad,
        superficie=request.superficie,
        estado_administrativo=request.estado_administrativo,
        estado_operativo=request.estado_operativo,
        observaciones=request.observaciones,
    )

    repository = InmuebleRepository(db)
    service = CreateUnidadFuncionalService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_INMUEBLE" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El inmueble indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear la unidad funcional.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return UnidadFuncionalCreateResponse(
        data=UnidadFuncionalCreateData(**result.data)
    )


@router.post(
    "/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios",
    status_code=201,
    response_model=UnidadFuncionalServicioCreateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_unidad_funcional_servicio(
    id_unidad_funcional: int,
    request: UnidadFuncionalServicioCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> UnidadFuncionalServicioCreateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = CreateUnidadFuncionalServicioCommand(
        context=context,
        id_unidad_funcional=id_unidad_funcional,
        id_servicio=request.id_servicio,
        estado=request.estado,
    )

    repository = InmuebleRepository(db)
    service = CreateUnidadFuncionalServicioService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(
            error in result.errors
            for error in ("NOT_FOUND_UNIDAD_FUNCIONAL", "NOT_FOUND_SERVICIO")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La unidad funcional o el servicio indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "DUPLICATE_UNIDAD_FUNCIONAL_SERVICIO" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Ya existe una asociacion activa entre la unidad funcional y el servicio.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear el servicio de la unidad funcional.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return UnidadFuncionalServicioCreateResponse(
        data=UnidadFuncionalServicioCreateData(**result.data)
    )


@router.get(
    "/api/v1/unidades-funcionales/{id_unidad_funcional}/servicios",
    response_model=UnidadFuncionalServicioListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_unidad_funcional_servicios(
    id_unidad_funcional: int,
    db: Session = Depends(get_db),
) -> UnidadFuncionalServicioListResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetUnidadFuncionalServiciosService(repository=repository)

    try:
        result = service.execute(id_unidad_funcional)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener los servicios de la unidad funcional.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return UnidadFuncionalServicioListResponse(
        data=[UnidadFuncionalServicioListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/inmuebles/{id_inmueble}/trazabilidad-integracion",
    response_model=ActivoIntegracionTraceResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_inmueble_trazabilidad_integracion(
    id_inmueble: int,
    db: Session = Depends(get_db),
) -> ActivoIntegracionTraceResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetInmuebleIntegracionTrazabilidadService(repository=repository)

    try:
        result = service.execute(id_inmueble)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo obtener la trazabilidad de integracion del inmueble.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ActivoIntegracionTraceResponse(
        data=[ActivoIntegracionVentaItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/unidades-funcionales/{id_unidad_funcional}/trazabilidad-integracion",
    response_model=ActivoIntegracionTraceResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_unidad_funcional_trazabilidad_integracion(
    id_unidad_funcional: int,
    db: Session = Depends(get_db),
) -> ActivoIntegracionTraceResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetUnidadFuncionalIntegracionTrazabilidadService(
        repository=repository
    )

    try:
        result = service.execute(id_unidad_funcional)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo obtener la trazabilidad de integracion de la unidad funcional.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ActivoIntegracionTraceResponse(
        data=[ActivoIntegracionVentaItem(**item) for item in result.data]
    )


@router.post(
    "/api/v1/disponibilidades",
    status_code=201,
    response_model=DisponibilidadCreateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_disponibilidad(
    request: DisponibilidadCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> DisponibilidadCreateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = CreateDisponibilidadCommand(
        context=context,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        estado_disponibilidad=request.estado_disponibilidad,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        motivo=request.motivo,
        observaciones=request.observaciones,
    )

    repository = InmuebleRepository(db)
    service = CreateDisponibilidadService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(
            error in result.errors
            for error in ("NOT_FOUND_INMUEBLE", "NOT_FOUND_UNIDAD_FUNCIONAL")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El inmueble o la unidad funcional indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "EXACTLY_ONE_PARENT_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_DATE_RANGE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="fecha_hasta no puede ser menor que fecha_desde.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear la disponibilidad.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DisponibilidadCreateResponse(
        data=DisponibilidadCreateData(**result.data)
    )


@router.post(
    "/api/v1/disponibilidades/reemplazar-vigente",
    status_code=201,
    response_model=DisponibilidadCreateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def replace_disponibilidad_vigente(
    request: DisponibilidadReemplazarVigenteRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> DisponibilidadCreateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = ReplaceDisponibilidadVigenteCommand(
        context=context,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        estado_disponibilidad=request.estado_disponibilidad,
        fecha_desde=request.fecha_desde,
        motivo=request.motivo,
        observaciones=request.observaciones,
    )

    repository = InmuebleRepository(db)
    service = ReplaceDisponibilidadVigenteService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(
            error in result.errors
            for error in ("NOT_FOUND_INMUEBLE", "NOT_FOUND_UNIDAD_FUNCIONAL")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El inmueble o la unidad funcional indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "EXACTLY_ONE_PARENT_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "NO_OPEN_DISPONIBILIDAD" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No existe una disponibilidad vigente para la entidad indicada.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "MULTIPLE_OPEN_DISPONIBILIDAD" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La entidad indicada tiene mas de una disponibilidad vigente. Estado inconsistente.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_REPLACEMENT_DATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La nueva disponibilidad no puede comenzar antes que la disponibilidad vigente actual.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "DISPONIBILIDAD_OVERLAP" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El reemplazo de disponibilidad viola las reglas vigentes de solapamiento.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo reemplazar la disponibilidad vigente.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DisponibilidadCreateResponse(
        data=DisponibilidadCreateData(**result.data)
    )


@router.post(
    "/api/v1/ocupaciones/reemplazar-vigente",
    status_code=201,
    response_model=OcupacionCreateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def replace_ocupacion_vigente(
    request: OcupacionReemplazarVigenteRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> OcupacionCreateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = ReplaceOcupacionVigenteCommand(
        context=context,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        tipo_ocupacion=request.tipo_ocupacion,
        fecha_desde=request.fecha_desde,
        descripcion=request.descripcion,
        observaciones=request.observaciones,
    )

    repository = InmuebleRepository(db)
    service = ReplaceOcupacionVigenteService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(
            error in result.errors
            for error in ("NOT_FOUND_INMUEBLE", "NOT_FOUND_UNIDAD_FUNCIONAL")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El inmueble o la unidad funcional indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "EXACTLY_ONE_PARENT_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "NO_OPEN_OCUPACION" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No existe una ocupacion vigente aplicable para la entidad indicada.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "MULTIPLE_OPEN_OCUPACION" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La entidad indicada tiene mas de una ocupacion vigente aplicable. Estado inconsistente.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_REPLACEMENT_DATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La nueva ocupacion no puede comenzar antes que la ocupacion vigente actual.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "OCUPACION_OVERLAP" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El reemplazo de ocupacion viola las reglas vigentes de solapamiento.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo reemplazar la ocupacion vigente.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return OcupacionCreateResponse(data=OcupacionCreateData(**result.data))


@router.post(
    "/api/v1/ocupaciones",
    status_code=201,
    response_model=OcupacionCreateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_ocupacion(
    request: OcupacionCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> OcupacionCreateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = CreateOcupacionCommand(
        context=context,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        tipo_ocupacion=request.tipo_ocupacion,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        descripcion=request.descripcion,
        observaciones=request.observaciones,
    )

    repository = InmuebleRepository(db)
    service = CreateOcupacionService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(
            error in result.errors
            for error in ("NOT_FOUND_INMUEBLE", "NOT_FOUND_UNIDAD_FUNCIONAL")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El inmueble o la unidad funcional indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "EXACTLY_ONE_PARENT_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_DATE_RANGE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="fecha_hasta no puede ser menor que fecha_desde.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear la ocupacion.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return OcupacionCreateResponse(data=OcupacionCreateData(**result.data))


@router.patch(
    "/api/v1/ocupaciones/{id_ocupacion}/cerrar",
    response_model=OcupacionCerrarResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def close_ocupacion(
    id_ocupacion: int,
    request: OcupacionCerrarRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> OcupacionCerrarResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = CloseOcupacionCommand(
        context=context,
        id_ocupacion=id_ocupacion,
        fecha_hasta=request.fecha_hasta,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = InmuebleRepository(db)
    service = CloseOcupacionService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_OCUPACION" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La ocupacion indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        if "INVALID_DATE_RANGE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="fecha_hasta no puede ser menor que fecha_desde.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "OCUPACION_ALREADY_CLOSED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La ocupacion ya se encuentra cerrada.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "OCUPACION_OVERLAP" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El cierre de ocupacion viola las reglas vigentes de solapamiento.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo cerrar la ocupacion.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return OcupacionCerrarResponse(data=OcupacionCerrarData(**result.data))


@router.patch(
    "/api/v1/ocupaciones/{id_ocupacion}/baja",
    response_model=OcupacionBajaResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_ocupacion(
    id_ocupacion: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> OcupacionBajaResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = DeleteOcupacionCommand(
        context=context,
        id_ocupacion=id_ocupacion,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = InmuebleRepository(db)
    service = DeleteOcupacionService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_OCUPACION" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La ocupacion indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo dar de baja la ocupacion.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return OcupacionBajaResponse(data=OcupacionBajaData(**result.data))


@router.put(
    "/api/v1/ocupaciones/{id_ocupacion}",
    response_model=OcupacionUpdateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_ocupacion(
    id_ocupacion: int,
    request: OcupacionUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> OcupacionUpdateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = UpdateOcupacionCommand(
        context=context,
        id_ocupacion=id_ocupacion,
        if_match_version=core_ef_headers.if_match_version,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        tipo_ocupacion=request.tipo_ocupacion,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        descripcion=request.descripcion,
        observaciones=request.observaciones,
    )

    repository = InmuebleRepository(db)
    service = UpdateOcupacionService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(
            error in result.errors
            for error in ("NOT_FOUND_OCUPACION", "NOT_FOUND_INMUEBLE", "NOT_FOUND_UNIDAD_FUNCIONAL")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La ocupacion, el inmueble o la unidad funcional indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        if "EXACTLY_ONE_PARENT_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_DATE_RANGE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="fecha_hasta no puede ser menor que fecha_desde.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "OCUPACION_ALREADY_CLOSED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La ocupacion ya se encuentra cerrada y no puede editarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "USE_CLOSE_ENDPOINT" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Para cerrar una ocupacion vigente debe usarse PATCH /api/v1/ocupaciones/{id_ocupacion}/cerrar.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "OCUPACION_OVERLAP" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La actualizacion de ocupacion viola las reglas vigentes de solapamiento.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo actualizar la ocupacion.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return OcupacionUpdateResponse(data=OcupacionUpdateData(**result.data))


@router.put(
    "/api/v1/disponibilidades/{id_disponibilidad}",
    response_model=DisponibilidadUpdateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_disponibilidad(
    id_disponibilidad: int,
    request: DisponibilidadUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> DisponibilidadUpdateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = UpdateDisponibilidadCommand(
        context=context,
        id_disponibilidad=id_disponibilidad,
        if_match_version=core_ef_headers.if_match_version,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        estado_disponibilidad=request.estado_disponibilidad,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        motivo=request.motivo,
        observaciones=request.observaciones,
    )

    repository = InmuebleRepository(db)
    service = UpdateDisponibilidadService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(
            error in result.errors
            for error in ("NOT_FOUND_DISPONIBILIDAD", "NOT_FOUND_INMUEBLE", "NOT_FOUND_UNIDAD_FUNCIONAL")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La disponibilidad, el inmueble o la unidad funcional indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        if "EXACTLY_ONE_PARENT_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Debe informarse exactamente uno entre id_inmueble e id_unidad_funcional.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_DATE_RANGE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="fecha_hasta no puede ser menor que fecha_desde.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "DISPONIBILIDAD_ALREADY_CLOSED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La disponibilidad ya se encuentra cerrada y no puede editarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "USE_CLOSE_ENDPOINT" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Para cerrar una disponibilidad vigente debe usarse PATCH /api/v1/disponibilidades/{id_disponibilidad}/cerrar.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "DISPONIBILIDAD_OVERLAP" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La actualizacion de disponibilidad viola las reglas vigentes de solapamiento.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo actualizar la disponibilidad.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DisponibilidadUpdateResponse(
        data=DisponibilidadUpdateData(**result.data)
    )


@router.patch(
    "/api/v1/disponibilidades/{id_disponibilidad}/cerrar",
    response_model=DisponibilidadCerrarResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def close_disponibilidad(
    id_disponibilidad: int,
    request: DisponibilidadCerrarRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> DisponibilidadCerrarResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = CloseDisponibilidadCommand(
        context=context,
        id_disponibilidad=id_disponibilidad,
        fecha_hasta=request.fecha_hasta,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = InmuebleRepository(db)
    service = CloseDisponibilidadService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_DISPONIBILIDAD" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La disponibilidad indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        if "INVALID_DATE_RANGE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="fecha_hasta no puede ser menor que fecha_desde.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "DISPONIBILIDAD_ALREADY_CLOSED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La disponibilidad ya se encuentra cerrada.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "DISPONIBILIDAD_OVERLAP" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El cierre de disponibilidad viola las reglas vigentes de solapamiento.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo cerrar la disponibilidad.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DisponibilidadCerrarResponse(
        data=DisponibilidadCerrarData(**result.data)
    )


@router.patch(
    "/api/v1/disponibilidades/{id_disponibilidad}/baja",
    response_model=DisponibilidadBajaResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_disponibilidad(
    id_disponibilidad: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> DisponibilidadBajaResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = DeleteDisponibilidadCommand(
        context=context,
        id_disponibilidad=id_disponibilidad,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = InmuebleRepository(db)
    service = DeleteDisponibilidadService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_DISPONIBILIDAD" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La disponibilidad indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        if "INVALID_DISPONIBILIDAD_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La baja de disponibilidad viola reglas estructurales del registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo dar de baja la disponibilidad.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DisponibilidadBajaResponse(data=DisponibilidadBajaData(**result.data))


@router.get(
    "/api/v1/inmuebles/{id_inmueble}/disponibilidades",
    response_model=DisponibilidadListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_inmueble_disponibilidades(
    id_inmueble: int,
    db: Session = Depends(get_db),
) -> DisponibilidadListResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetInmuebleDisponibilidadesService(repository=repository)

    try:
        result = service.execute(id_inmueble)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las disponibilidades del inmueble.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DisponibilidadListResponse(
        data=[DisponibilidadListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/unidades-funcionales/{id_unidad_funcional}/disponibilidades",
    response_model=DisponibilidadListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_unidad_funcional_disponibilidades(
    id_unidad_funcional: int,
    db: Session = Depends(get_db),
) -> DisponibilidadListResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetUnidadFuncionalDisponibilidadesService(repository=repository)

    try:
        result = service.execute(id_unidad_funcional)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las disponibilidades de la unidad funcional.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DisponibilidadListResponse(
        data=[DisponibilidadListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/inmuebles/{id_inmueble}/ocupaciones",
    response_model=OcupacionListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_inmueble_ocupaciones(
    id_inmueble: int,
    db: Session = Depends(get_db),
) -> OcupacionListResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetInmuebleOcupacionesService(repository=repository)

    try:
        result = service.execute(id_inmueble)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las ocupaciones del inmueble.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return OcupacionListResponse(
        data=[OcupacionListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/unidades-funcionales/{id_unidad_funcional}/ocupaciones",
    response_model=OcupacionListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_unidad_funcional_ocupaciones(
    id_unidad_funcional: int,
    db: Session = Depends(get_db),
) -> OcupacionListResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetUnidadFuncionalOcupacionesService(repository=repository)

    try:
        result = service.execute(id_unidad_funcional)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las ocupaciones de la unidad funcional.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return OcupacionListResponse(
        data=[OcupacionListItem(**item) for item in result.data]
    )


@router.post(
    "/api/v1/inmuebles/{id_inmueble}/servicios",
    status_code=201,
    response_model=InmuebleServicioCreateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_inmueble_servicio(
    id_inmueble: int,
    request: InmuebleServicioCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> InmuebleServicioCreateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = CreateInmuebleServicioCommand(
        context=context,
        id_inmueble=id_inmueble,
        id_servicio=request.id_servicio,
        estado=request.estado,
    )

    repository = InmuebleRepository(db)
    service = CreateInmuebleServicioService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(
            error in result.errors for error in ("NOT_FOUND_INMUEBLE", "NOT_FOUND_SERVICIO")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El inmueble o el servicio indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "DUPLICATE_INMUEBLE_SERVICIO" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Ya existe una asociacion activa entre el inmueble y el servicio.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear el servicio del inmueble.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return InmuebleServicioCreateResponse(
        data=InmuebleServicioCreateData(**result.data)
    )


@router.get(
    "/api/v1/inmuebles/{id_inmueble}/servicios",
    response_model=InmuebleServicioListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_inmueble_servicios(
    id_inmueble: int,
    db: Session = Depends(get_db),
) -> InmuebleServicioListResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetInmuebleServiciosService(repository=repository)

    try:
        result = service.execute(id_inmueble)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener los servicios del inmueble.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return InmuebleServicioListResponse(
        data=[InmuebleServicioListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/inmuebles/{id_inmueble}/unidades-funcionales",
    response_model=UnidadFuncionalListResponse,
    response_model_exclude_none=True,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_unidades_funcionales(
    id_inmueble: int,
    db: Session = Depends(get_db),
) -> UnidadFuncionalListResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetUnidadesFuncionalesService(repository=repository)

    try:
        result = service.execute(id_inmueble)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las unidades funcionales.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return UnidadFuncionalListResponse(
        data=[UnidadFuncionalListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/unidades-funcionales",
    response_model=UnidadFuncionalListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_unidades_funcionales_global(
    q: str | None = None,
    id_inmueble: int | None = None,
    estado_administrativo: str | None = None,
    estado_operativo: str | None = None,
    disponibilidad_actual: str | None = None,
    ocupacion_actual: str | None = None,
    id_servicio: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> UnidadFuncionalListResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetUnidadesFuncionalesGlobalService(repository=repository)

    try:
        result = service.execute(
            q=q,
            id_inmueble=id_inmueble,
            estado_administrativo=estado_administrativo,
            estado_operativo=estado_operativo,
            disponibilidad_actual=disponibilidad_actual,
            ocupacion_actual=ocupacion_actual,
            id_servicio=id_servicio,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las unidades funcionales.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    items = [UnidadFuncionalListItem(**item) for item in result.data["items"]]
    return UnidadFuncionalListResponse(
        data=items,
        items=items,
        total=result.data["total"],
        limit=result.data["limit"],
        offset=result.data["offset"],
    )


@router.get(
    "/api/v1/unidades-funcionales/{id_unidad_funcional}/detalle-integral",
    response_model=UnidadFuncionalDetalleIntegralResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_unidad_funcional_detalle_integral(
    id_unidad_funcional: int,
    db: Session = Depends(get_db),
) -> UnidadFuncionalDetalleIntegralResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetUnidadFuncionalDetalleIntegralService(repository=repository)

    try:
        result = service.execute(id_unidad_funcional)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="La unidad funcional indicada no existe.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return UnidadFuncionalDetalleIntegralResponse(data=result.data)


@router.get(
    "/api/v1/unidades-funcionales/{id_unidad_funcional}",
    response_model=UnidadFuncionalDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_unidad_funcional(
    id_unidad_funcional: int,
    db: Session = Depends(get_db),
) -> UnidadFuncionalDetailResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetUnidadFuncionalService(repository=repository)

    try:
        result = service.execute(id_unidad_funcional)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error_code = "NOT_FOUND" if "NOT_FOUND" in result.errors else "APPLICATION_ERROR"
        error_message = (
            "La unidad funcional indicada no existe."
            if error_code == "NOT_FOUND"
            else "No se pudo obtener la unidad funcional."
        )
        status_code = 404 if error_code == "NOT_FOUND" else 400
        error = ErrorResponse(
            error_code=error_code,
            error_message=error_message,
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=status_code, content=error.model_dump())

    return UnidadFuncionalDetailResponse(data=UnidadFuncionalDetailData(**result.data))


@router.put(
    "/api/v1/unidades-funcionales/{id_unidad_funcional}",
    response_model=UnidadFuncionalUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
)
def update_unidad_funcional(
    id_unidad_funcional: int,
    request: UnidadFuncionalUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> UnidadFuncionalUpdateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = UpdateUnidadFuncionalCommand(
        context=context,
        id_unidad_funcional=id_unidad_funcional,
        if_match_version=core_ef_headers.if_match_version,
        codigo_unidad=request.codigo_unidad,
        nombre_unidad=request.nombre_unidad,
        superficie=request.superficie,
        estado_administrativo=request.estado_administrativo,
        estado_operativo=request.estado_operativo,
        observaciones=request.observaciones,
    )

    repository = InmuebleRepository(db)
    service = UpdateUnidadFuncionalService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_UNIDAD_FUNCIONAL" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La unidad funcional indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo actualizar la unidad funcional.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return UnidadFuncionalUpdateResponse(
        data=UnidadFuncionalUpdateData(**result.data)
    )


@router.patch(
    "/api/v1/unidades-funcionales/{id_unidad_funcional}/baja",
    response_model=UnidadFuncionalBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
)
def delete_unidad_funcional(
    id_unidad_funcional: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> UnidadFuncionalBajaResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = DeleteUnidadFuncionalCommand(
        context=context,
        id_unidad_funcional=id_unidad_funcional,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = InmuebleRepository(db)
    service = DeleteUnidadFuncionalService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_UNIDAD_FUNCIONAL" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La unidad funcional indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo dar de baja la unidad funcional.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return UnidadFuncionalBajaResponse(data=UnidadFuncionalBajaData(**result.data))


@router.get(
    "/api/v1/inmuebles/{id_inmueble}/detalle-integral",
    response_model=InmuebleDetalleIntegralResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_inmueble_detalle_integral(
    id_inmueble: int,
    db: Session = Depends(get_db),
) -> InmuebleDetalleIntegralResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetInmuebleDetalleIntegralService(repository=repository)

    try:
        result = service.execute(id_inmueble)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="El inmueble indicado no existe.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return InmuebleDetalleIntegralResponse(data=result.data)


@router.get(
    "/api/v1/inmuebles/{id_inmueble}",
    response_model=InmuebleDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_inmueble(
    id_inmueble: int,
    db: Session = Depends(get_db),
) -> InmuebleDetailResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetInmuebleService(repository=repository)

    try:
        result = service.execute(id_inmueble)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error_code = "NOT_FOUND" if "NOT_FOUND" in result.errors else "APPLICATION_ERROR"
        error_message = (
            "El inmueble indicado no existe."
            if error_code == "NOT_FOUND"
            else "No se pudo obtener el inmueble."
        )
        status_code = 404 if error_code == "NOT_FOUND" else 400
        error = ErrorResponse(
            error_code=error_code,
            error_message=error_message,
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=status_code, content=error.model_dump())

    return InmuebleDetailResponse(data=InmuebleDetailData(**result.data))


@router.get(
    "/api/v1/inmuebles",
    response_model=InmuebleListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_inmuebles(
    q: str | None = None,
    estado_administrativo: str | None = None,
    estado_juridico: str | None = None,
    id_desarrollo: int | None = None,
    disponibilidad_actual: str | None = None,
    ocupacion_actual: str | None = None,
    id_servicio: int | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> InmuebleListResponse | JSONResponse:
    repository = InmuebleRepository(db)
    service = GetInmueblesService(repository=repository)

    try:
        result = service.execute(
            q=q,
            estado_administrativo=estado_administrativo,
            estado_juridico=estado_juridico,
            id_desarrollo=id_desarrollo,
            disponibilidad_actual=disponibilidad_actual,
            ocupacion_actual=ocupacion_actual,
            id_servicio=id_servicio,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener los inmuebles.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    items = [InmuebleListItem(**item) for item in result.data["items"]]
    return InmuebleListResponse(
        data=items,
        items=items,
        total=result.data["total"],
        limit=result.data["limit"],
        offset=result.data["offset"],
    )


@router.put(
    "/api/v1/inmuebles/{id_inmueble}",
    response_model=InmuebleUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
)
def update_inmueble(
    id_inmueble: int,
    request: InmuebleUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> InmuebleUpdateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = UpdateInmuebleCommand(
        context=context,
        id_inmueble=id_inmueble,
        if_match_version=core_ef_headers.if_match_version,
        id_desarrollo=request.id_desarrollo,
        codigo_inmueble=request.codigo_inmueble,
        nombre_inmueble=request.nombre_inmueble,
        superficie=request.superficie,
        estado_administrativo=request.estado_administrativo,
        estado_juridico=request.estado_juridico,
        observaciones=request.observaciones,
    )

    repository = InmuebleRepository(db)
    service = UpdateInmuebleService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(error in result.errors for error in ("NOT_FOUND_INMUEBLE", "NOT_FOUND_DESARROLLO")):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El inmueble o el desarrollo indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo actualizar el inmueble.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return InmuebleUpdateResponse(data=InmuebleUpdateData(**result.data))


@router.patch(
    "/api/v1/inmuebles/{id_inmueble}/baja",
    response_model=InmuebleBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
)
def delete_inmueble(
    id_inmueble: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> InmuebleBajaResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = DeleteInmuebleCommand(
        context=context,
        id_inmueble=id_inmueble,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = InmuebleRepository(db)
    service = DeleteInmuebleService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_INMUEBLE" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El inmueble indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo dar de baja el inmueble.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return InmuebleBajaResponse(data=InmuebleBajaData(**result.data))


@router.patch(
    "/api/v1/inmuebles/{id_inmueble}/asociar-desarrollo",
    response_model=InmuebleAsociarDesarrolloResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def associate_inmueble_desarrollo(
    id_inmueble: int,
    request: InmuebleAsociarDesarrolloRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> InmuebleAsociarDesarrolloResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = AssociateInmuebleDesarrolloCommand(
        context=context,
        id_inmueble=id_inmueble,
        id_desarrollo=request.id_desarrollo,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = InmuebleRepository(db)
    service = AssociateInmuebleDesarrolloService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(
            error in result.errors
            for error in ("NOT_FOUND_INMUEBLE", "NOT_FOUND_DESARROLLO")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El inmueble o el desarrollo indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo asociar el inmueble al desarrollo.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return InmuebleAsociarDesarrolloResponse(
        data=InmuebleAsociarDesarrolloData(**result.data)
    )


@router.patch(
    "/api/v1/inmuebles/{id_inmueble}/desasociar-desarrollo",
    response_model=InmuebleDesasociarDesarrolloResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def disassociate_inmueble_desarrollo(
    id_inmueble: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> InmuebleDesasociarDesarrolloResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
        require_if_match_version=True,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_inmueble_command_context(core_ef_headers)

    command = DisassociateInmuebleDesarrolloCommand(
        context=context,
        id_inmueble=id_inmueble,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = InmuebleRepository(db)
    service = DisassociateInmuebleDesarrolloService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_INMUEBLE" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El inmueble indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo desasociar el inmueble del desarrollo.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return InmuebleDesasociarDesarrolloResponse(
        data=InmuebleDesasociarDesarrolloData(**result.data)
    )
