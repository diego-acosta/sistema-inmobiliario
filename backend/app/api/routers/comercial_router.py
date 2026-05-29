from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.core_ef_headers import (
    CoreEFHeaderValidationError,
    CoreEFHeaders,
    parse_core_ef_headers,
)
from app.api.dependencies import get_db
from app.api.schemas.comercial import (
    CesionListData,
    CesionListResponse,
    CesionData,
    ConfirmVentaDirectaCompletaRequest,
    ConfirmVentaDirectaCompletaResponse,
    ConfirmVentaCompletaDesdeReservaRequest,
    ConfirmVentaCompletaDesdeReservaResponse,
    ConfirmVentaData,
    ConfirmVentaRequest,
    ConfirmVentaResponse,
    CreateCesionRequest,
    CreateCesionResponse,
    CreateEscrituracionRequest,
    CreateEscrituracionResponse,
    CreateInstrumentoCompraventaRequest,
    CreateInstrumentoCompraventaResponse,
    DefineCondicionesComercialesVentaData,
    DefineCondicionesComercialesVentaRequest,
    DefineCondicionesComercialesVentaResponse,
    ErrorResponse,
    EscrituracionData,
    EscrituracionListData,
    EscrituracionListResponse,
    GeneratePlanPagoVentaAnticipoMasCuotasIgualesRequest,
    GeneratePlanPagoVentaAnticipoMasCuotasIgualesResponse,
    GeneratePlanPagoVentaV2PorBloquesRequest,
    GeneratePlanPagoVentaV2PorBloquesResponse,
    GenerateVentaFromReservaVentaData,
    GenerateVentaFromReservaVentaRequest,
    GenerateVentaFromReservaVentaResponse,
    GeneratePlanPagoVentaCuotasIgualesSimpleRequest,
    GeneratePlanPagoVentaCuotasIgualesSimpleResponse,
    PreviewPlanPagoVentaV2PorBloquesRequest,
    PreviewPlanPagoVentaV2PorBloquesResponse,
    InstrumentoCompraventaData,
    InstrumentoCompraventaListData,
    InstrumentoCompraventaListResponse,
    InstrumentoCompraventaObjetoData,
    ReservaVentaActivateData,
    ReservaVentaActivateResponse,
    ReservaVentaBajaData,
    ReservaVentaBajaResponse,
    ReservaVentaCancelData,
    ReservaVentaCancelResponse,
    ReservaVentaExpireData,
    ReservaVentaExpireResponse,
    ReservaVentaConfirmData,
    ReservaVentaConfirmResponse,
    ReservaVentaCreateData,
    ReservaVentaObjetoCreateData,
    ReservaVentaCreateRequest,
    ReservaVentaCreateResponse,
    ReservaVentaDetailData,
    ReservaVentaDetailResponse,
    ReservaVentaListData,
    ReservaVentaListItemData,
    ReservaVentaListResponse,
    ReservaVentaUpdateData,
    ReservaVentaUpdateRequest,
    ReservaVentaUpdateResponse,
    VentaDetailData,
    VentaDetailResponse,
    VentaDetalleIntegralData,
    VentaDetalleIntegralResponse,
    VentaListData,
    VentaListItemData,
    VentaListResponse,
    VentaObjetoData,
)
from app.application.comercial.commands.activate_reserva_venta import (
    ActivateReservaVentaCommand,
)
from app.application.comercial.commands.cancel_reserva_venta import (
    CancelReservaVentaCommand,
)
from app.application.comercial.commands.confirm_reserva_venta import (
    ConfirmReservaVentaCommand,
)
from app.application.comercial.commands.confirm_venta import ConfirmVentaCommand
from app.application.comercial.commands.confirm_venta_completa_desde_reserva import (
    ConfirmVentaCompletaCondicionCuotaInput,
    ConfirmVentaCompletaCondicionObjetoInput,
    ConfirmVentaCompletaCondicionesComercialesInput,
    ConfirmVentaCompletaConfirmacionInput,
    ConfirmVentaCompletaDesdeReservaCommand,
    ConfirmVentaCompletaGenerarVentaInput,
    ConfirmVentaCompletaPlanPagoBloqueInput,
    ConfirmVentaCompletaPlanPagoV2Input,
)
from app.application.comercial.commands.confirm_venta_directa_completa import (
    ConfirmVentaDirectaCompletaCommand,
    ConfirmVentaDirectaCompletaCompradorInput,
    ConfirmVentaDirectaCompletaCondicionCuotaInput,
    ConfirmVentaDirectaCompletaCondicionesComercialesInput,
    ConfirmVentaDirectaCompletaConfirmacionInput,
    ConfirmVentaDirectaCompletaGenerarVentaInput,
    ConfirmVentaDirectaCompletaObjetoInput,
    ConfirmVentaDirectaCompletaPlanPagoBloqueInput,
    ConfirmVentaDirectaCompletaPlanPagoV2Input,
)
from app.application.comercial.commands.create_cesion import CreateCesionCommand
from app.application.comercial.commands.create_escrituracion import (
    CreateEscrituracionCommand,
)
from app.application.comercial.commands.create_instrumento_compraventa import (
    CreateInstrumentoCompraventaCommand,
    CreateInstrumentoCompraventaObjetoCommand,
)
from app.application.comercial.commands.create_reserva_venta import (
    CreateReservaVentaCommand,
    CreateReservaVentaObjetoCommand,
    CreateReservaVentaParticipacionCommand,
)
from app.application.comercial.commands.delete_reserva_venta import (
    DeleteReservaVentaCommand,
)
from app.application.comercial.commands.define_condiciones_comerciales_venta import (
    DefineCondicionesComercialesVentaCommand,
    DefineCondicionesComercialesVentaCuotaCommand,
    DefineCondicionesComercialesVentaObjetoCommand,
)
from app.application.comercial.commands.expire_reserva_venta import (
    ExpireReservaVentaCommand,
)
from app.application.comercial.commands.generate_venta_from_reserva_venta import (
    GenerateVentaFromReservaVentaCommand,
)
from app.application.comercial.commands.generate_plan_pago_venta_cuotas_iguales_simple import (
    GeneratePlanPagoVentaCuotasIgualesSimpleCommand,
)
from app.application.comercial.commands.generate_plan_pago_venta_anticipo_mas_cuotas_iguales import (
    GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand,
)
from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    GeneratePlanPagoVentaV2PorBloquesCommand,
    PlanPagoVentaBloqueInput,
)
from app.application.comercial.commands.update_reserva_venta import (
    UpdateReservaVentaCommand,
)
from app.application.comercial.services.activate_reserva_venta_service import (
    ActivateReservaVentaService,
)
from app.application.comercial.services.cancel_reserva_venta_service import (
    CancelReservaVentaService,
)
from app.application.comercial.services.confirm_reserva_venta_service import (
    ConfirmReservaVentaService,
)
from app.application.comercial.services.confirm_venta_service import ConfirmVentaService
from app.application.comercial.services.confirm_venta_completa_desde_reserva_service import (
    ConfirmVentaCompletaDesdeReservaService,
)
from app.application.comercial.services.confirm_venta_directa_completa_service import (
    ConfirmVentaDirectaCompletaService,
)
from app.application.comercial.services.create_cesion_service import (
    CreateCesionService,
)
from app.application.comercial.services.create_escrituracion_service import (
    CreateEscrituracionService,
)
from app.application.comercial.services.create_instrumento_compraventa_service import (
    CreateInstrumentoCompraventaService,
)
from app.application.comercial.services.create_reserva_venta_service import (
    CreateReservaVentaService,
)
from app.application.comercial.services.delete_reserva_venta_service import (
    DeleteReservaVentaService,
)
from app.application.comercial.services.define_condiciones_comerciales_venta_service import (
    DefineCondicionesComercialesVentaService,
)
from app.application.comercial.services.expire_reserva_venta_service import (
    ExpireReservaVentaService,
)
from app.application.comercial.services.generate_venta_from_reserva_venta_service import (
    GenerateVentaFromReservaVentaService,
)
from app.application.comercial.services.generate_plan_pago_venta_cuotas_iguales_simple_service import (
    GeneratePlanPagoVentaCuotasIgualesSimpleService,
)
from app.application.comercial.services.generate_plan_pago_venta_anticipo_mas_cuotas_iguales_service import (
    GeneratePlanPagoVentaAnticipoMasCuotasIgualesService,
)
from app.application.comercial.services.build_plan_pago_venta_v2_por_bloques_preview_service import (
    BuildPlanPagoVentaV2PorBloquesPreviewService,
    METODO_PLAN_POR_BLOQUES,
)
from app.application.comercial.services.generate_plan_pago_venta_v2_por_bloques_service import (
    GeneratePlanPagoVentaV2PorBloquesService,
)
from app.application.comercial.services.get_reserva_venta_service import (
    GetReservaVentaService,
)
from app.application.comercial.services.list_reservas_venta_service import (
    ListReservasVentaService,
)
from app.application.comercial.services.list_ventas_service import ListVentasService
from app.application.comercial.services.list_instrumentos_compraventa_service import (
    ListInstrumentosCompraventaService,
)
from app.application.comercial.services.list_cesiones_service import (
    ListCesionesService,
)
from app.application.comercial.services.list_escrituraciones_service import (
    ListEscrituracionesService,
)
from app.application.comercial.services.update_reserva_venta_service import (
    UpdateReservaVentaService,
)
from app.application.comercial.services.get_venta_service import GetVentaService
from app.application.comercial.services.get_venta_detalle_integral_service import (
    GetVentaDetalleIntegralService,
)
from app.application.common.commands import CommandContext
from app.infrastructure.persistence.repositories.indice_financiero_repository import (
    IndiceFinancieroRepository,
)
from app.infrastructure.persistence.repositories.comercial_repository import (
    ComercialRepository,
)
from app.infrastructure.persistence.repositories.plan_pago_venta_v2_repository import (
    PlanPagoVentaV2Repository,
)


router = APIRouter(tags=["Comercial"])

_CORE_EF_REQUIRED_HEADERS_OPENAPI = {
    "parameters": [
        {"name": "X-Op-Id", "in": "header", "required": True, "schema": {"type": "string"}},
        {"name": "X-Usuario-Id", "in": "header", "required": True, "schema": {"type": "string"}},
        {"name": "X-Sucursal-Id", "in": "header", "required": True, "schema": {"type": "string"}},
        {"name": "X-Instalacion-Id", "in": "header", "required": True, "schema": {"type": "string"}},
    ]
}
_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI = {
    "parameters": [
        *_CORE_EF_REQUIRED_HEADERS_OPENAPI["parameters"],
        {"name": "If-Match-Version", "in": "header", "required": True, "schema": {"type": "string"}},
    ]
}


@dataclass(slots=True)
class ComercialCommandContext(CommandContext):
    id_instalacion: int | None = None
    op_id: UUID | None = None


def _core_ef_error_response(exc: CoreEFHeaderValidationError) -> JSONResponse:
    error = ErrorResponse(
        error_code="VALIDATION_ERROR",
        error_message=exc.message,
        details={"header": exc.header_name},
    )
    return JSONResponse(status_code=400, content=error.model_dump())


def _parse_core_ef_headers_or_error(
    *, x_op_id: str | None, x_usuario_id: str | None, x_sucursal_id: str | None, x_instalacion_id: str | None
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
) -> CoreEFHeaders | JSONResponse:
    try:
        return parse_core_ef_headers(
            x_op_id=x_op_id,
            x_usuario_id=x_usuario_id,
            x_sucursal_id=x_sucursal_id,
            x_instalacion_id=x_instalacion_id,
            if_match_version=if_match_version,
            require_if_match_version=True,
        )
    except CoreEFHeaderValidationError as exc:
        return _core_ef_error_response(exc)


def _build_comercial_command_context(core_ef_headers: CoreEFHeaders, if_match_version: str | None = None) -> ComercialCommandContext:
    metadata: dict[str, str] = {
        "x_op_id": str(core_ef_headers.x_op_id),
        "x_sucursal_id": str(core_ef_headers.x_sucursal_id),
        "x_instalacion_id": str(core_ef_headers.x_instalacion_id),
    }
    if if_match_version is not None:
        metadata["if_match_version"] = if_match_version
    return ComercialCommandContext(
        id_instalacion=core_ef_headers.x_instalacion_id,
        op_id=core_ef_headers.x_op_id,
        request_id=core_ef_headers.x_op_id,
        actor_id=str(core_ef_headers.x_usuario_id),
        metadata=metadata,
    )


@router.post(
    "/api/v1/reservas-venta",
    status_code=201,
    response_model=ReservaVentaCreateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_reserva_venta(
    request: ReservaVentaCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ReservaVentaCreateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers)

    command = CreateReservaVentaCommand(
        context=context,
        codigo_reserva=request.codigo_reserva,
        fecha_reserva=request.fecha_reserva,
        fecha_vencimiento=request.fecha_vencimiento,
        observaciones=request.observaciones,
        objetos=[
            CreateReservaVentaObjetoCommand(
                id_inmueble=item.id_inmueble,
                id_unidad_funcional=item.id_unidad_funcional,
                observaciones=item.observaciones,
            )
            for item in request.objetos
        ],
        participaciones=[
            CreateReservaVentaParticipacionCommand(
                id_persona=item.id_persona,
                id_rol_participacion=item.id_rol_participacion,
                fecha_desde=item.fecha_desde,
                fecha_hasta=item.fecha_hasta,
                observaciones=item.observaciones,
            )
            for item in request.participaciones
        ],
    )

    repository = ComercialRepository(db)
    service = CreateReservaVentaService(repository=repository)

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
            for error in (
                "NOT_FOUND_INMUEBLE",
                "NOT_FOUND_UNIDAD_FUNCIONAL",
                "NOT_FOUND_PERSONA",
                "NOT_FOUND_ROL_PARTICIPACION",
            )
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El objeto inmobiliario, la persona o el rol indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "EXACTLY_ONE_OBJECT_PARENT_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Cada objeto debe informar exactamente uno entre id_inmueble e id_unidad_funcional.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_DATE_RANGE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="fecha_vencimiento no puede ser menor que fecha_reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_PARTICIPACION_DATE_RANGE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="fecha_hasta no puede ser anterior a fecha_desde en las participaciones.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "OBJETOS_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Debe informarse al menos un objeto para crear la reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "PARTICIPACIONES_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Debe informarse al menos una participacion para crear la reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_REQUIRED_FIELDS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="codigo_reserva es requerido.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "DUPLICATE_OBJECT" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No puede repetirse el mismo objeto dentro de una misma reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "OBJECT_NOT_AVAILABLE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado no esta disponible para reservar.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado ya participa en una venta activa incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_RESERVA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado ya participa en una reserva vigente incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())
        if "CONFLICTING_JERARQUIA_INMOBILIARIA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Existe un conflicto jerarquico entre inmueble y unidad funcional para reservar.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear la reserva de venta.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            ReservaVentaObjetoCreateData(**objeto).model_dump()
            for objeto in result.data["objetos"]
        ],
    }
    return ReservaVentaCreateResponse(data=ReservaVentaCreateData(**data))


@router.put(
    "/api/v1/reservas-venta/{id_reserva_venta}",
    response_model=ReservaVentaUpdateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_reserva_venta(
    id_reserva_venta: int,
    request: ReservaVentaUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ReservaVentaUpdateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers, if_match_version)

    command = UpdateReservaVentaCommand(
        context=context,
        id_reserva_venta=id_reserva_venta,
        if_match_version=core_ef_headers.if_match_version,
        codigo_reserva=request.codigo_reserva,
        fecha_reserva=request.fecha_reserva,
        fecha_vencimiento=request.fecha_vencimiento,
        observaciones=request.observaciones,
    )

    repository = ComercialRepository(db)
    service = UpdateReservaVentaService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_RESERVA_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La reserva indicada no existe.",
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

        if "INVALID_REQUIRED_FIELDS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="codigo_reserva es requerido.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_DATE_RANGE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="fecha_vencimiento debe ser mayor o igual a fecha_reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_RESERVA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una reserva en estado borrador, activa o confirmada puede actualizarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "RESERVA_WITH_LINKED_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva no puede actualizarse porque ya esta vinculada a una venta.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "DUPLICATE_CODIGO_RESERVA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Ya existe una reserva con el mismo codigo_reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())


        if "X-Instalacion-Id es requerido." in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="X-Instalacion-Id es requerido.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo actualizar la reserva de venta.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            ReservaVentaObjetoCreateData(**objeto).model_dump()
            for objeto in result.data["objetos"]
        ],
    }
    return ReservaVentaUpdateResponse(data=ReservaVentaUpdateData(**data))


@router.patch(
    "/api/v1/reservas-venta/{id_reserva_venta}/baja",
    response_model=ReservaVentaBajaResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_reserva_venta(
    id_reserva_venta: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ReservaVentaBajaResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers, if_match_version)

    command = DeleteReservaVentaCommand(
        context=context,
        id_reserva_venta=id_reserva_venta,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = ComercialRepository(db)
    service = DeleteReservaVentaService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_RESERVA_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La reserva indicada no existe.",
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

        if "INVALID_RESERVA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una reserva en estado borrador o activa puede darse de baja.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "RESERVA_WITH_LINKED_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva no puede darse de baja porque ya esta vinculada a una venta.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())


        if "X-Instalacion-Id es requerido." in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="X-Instalacion-Id es requerido.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo dar de baja la reserva de venta.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ReservaVentaBajaResponse(data=ReservaVentaBajaData(**result.data))


@router.get(
    "/api/v1/reservas-venta/{id_reserva_venta}",
    response_model=ReservaVentaDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_reserva_venta(
    id_reserva_venta: int,
    db: Session = Depends(get_db),
) -> ReservaVentaDetailResponse | JSONResponse:
    repository = ComercialRepository(db)
    service = GetReservaVentaService(repository=repository)

    try:
        result = service.execute(id_reserva_venta)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="La reserva indicada no existe.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            ReservaVentaObjetoCreateData(**objeto).model_dump()
            for objeto in result.data["objetos"]
        ],
    }
    return ReservaVentaDetailResponse(data=ReservaVentaDetailData(**data))


@router.get(
    "/api/v1/reservas-venta",
    response_model=ReservaVentaListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_reservas_venta(
    codigo_reserva: str | None = Query(default=None),
    estado_reserva: str | None = Query(default=None),
    fecha_desde: datetime | None = Query(default=None),
    fecha_hasta: datetime | None = Query(default=None),
    vigente: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ReservaVentaListResponse | JSONResponse:
    repository = ComercialRepository(db)
    service = ListReservasVentaService(repository=repository)

    try:
        result = service.execute(
            codigo_reserva=codigo_reserva,
            estado_reserva=estado_reserva,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            vigente=vigente,
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
            error_message="No se pudieron obtener las reservas de venta.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        "items": [
            {
                **item,
                "objetos": [
                    ReservaVentaObjetoCreateData(**objeto).model_dump()
                    for objeto in item["objetos"]
                ],
            }
            for item in result.data["items"]
        ],
        "total": result.data["total"],
    }
    return ReservaVentaListResponse(
        data=ReservaVentaListData(
            items=[ReservaVentaListItemData(**item) for item in data["items"]],
            total=data["total"],
        )
    )


@router.post(
    "/api/v1/reservas-venta/{id_reserva_venta}/activar",
    response_model=ReservaVentaActivateResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def activate_reserva_venta(
    id_reserva_venta: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ReservaVentaActivateResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers, if_match_version)

    command = ActivateReservaVentaCommand(
        context=context,
        id_reserva_venta=id_reserva_venta,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = ComercialRepository(db)
    service = ActivateReservaVentaService(repository=repository)

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
            for error in (
                "NOT_FOUND_RESERVA_VENTA",
                "NOT_FOUND_INMUEBLE",
                "NOT_FOUND_UNIDAD_FUNCIONAL",
            )
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La reserva o el objeto inmobiliario indicado no existe.",
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

        if "INVALID_RESERVA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una reserva en estado borrador puede activarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "RESERVA_WITHOUT_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva no posee objetos inmobiliarios asociados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "OBJECT_NOT_AVAILABLE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado no esta disponible para activar la reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado ya participa en una venta activa incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_RESERVA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado ya participa en una reserva vigente incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())
        if "CONFLICTING_JERARQUIA_INMOBILIARIA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Existe un conflicto jerarquico entre inmueble y unidad funcional para activar la reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo activar la reserva de venta.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            ReservaVentaObjetoCreateData(**objeto).model_dump()
            for objeto in result.data["objetos"]
        ],
    }
    return ReservaVentaActivateResponse(data=ReservaVentaActivateData(**data))


@router.post(
    "/api/v1/reservas-venta/{id_reserva_venta}/cancelar",
    response_model=ReservaVentaCancelResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def cancel_reserva_venta(
    id_reserva_venta: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ReservaVentaCancelResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers, if_match_version)

    command = CancelReservaVentaCommand(
        context=context,
        id_reserva_venta=id_reserva_venta,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = ComercialRepository(db)
    service = CancelReservaVentaService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_RESERVA_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La reserva indicada no existe.",
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

        if "INVALID_RESERVA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una reserva en estado borrador, activa o confirmada puede cancelarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva ya participa en una venta activa vinculada.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "RESERVA_WITHOUT_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva no posee objetos inmobiliarios asociados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_RESERVA_BLOCK" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva confirmada no mantiene un bloqueo de disponibilidad consistente para cancelarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo cancelar la reserva de venta.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            ReservaVentaObjetoCreateData(**objeto).model_dump()
            for objeto in result.data["objetos"]
        ],
    }
    return ReservaVentaCancelResponse(data=ReservaVentaCancelData(**data))


@router.post(
    "/api/v1/reservas-venta/{id_reserva_venta}/vencer",
    response_model=ReservaVentaExpireResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def expire_reserva_venta(
    id_reserva_venta: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ReservaVentaExpireResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers, if_match_version)

    command = ExpireReservaVentaCommand(
        context=context,
        id_reserva_venta=id_reserva_venta,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = ComercialRepository(db)
    service = ExpireReservaVentaService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_RESERVA_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La reserva indicada no existe.",
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

        if "INVALID_RESERVA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una reserva en estado activa o confirmada puede vencerse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "RESERVA_WITHOUT_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva no posee objetos inmobiliarios asociados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_RESERVA_BLOCK" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva confirmada no mantiene un bloqueo de disponibilidad consistente para vencerse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo vencer la reserva de venta.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            ReservaVentaObjetoCreateData(**objeto).model_dump()
            for objeto in result.data["objetos"]
        ],
    }
    return ReservaVentaExpireResponse(data=ReservaVentaExpireData(**data))


@router.post(
    "/api/v1/reservas-venta/{id_reserva_venta}/confirmar",
    response_model=ReservaVentaConfirmResponse,
    openapi_extra=_CORE_EF_REQUIRED_HEADERS_WITH_IF_MATCH_VERSION_OPENAPI,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def confirm_reserva_venta(
    id_reserva_venta: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ReservaVentaConfirmResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers, if_match_version)

    command = ConfirmReservaVentaCommand(
        context=context,
        id_reserva_venta=id_reserva_venta,
        if_match_version=core_ef_headers.if_match_version,
    )

    repository = ComercialRepository(db)
    service = ConfirmReservaVentaService(repository=repository)

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
            for error in (
                "NOT_FOUND_RESERVA_VENTA",
                "NOT_FOUND_INMUEBLE",
                "NOT_FOUND_UNIDAD_FUNCIONAL",
            )
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La reserva o el objeto inmobiliario indicado no existe.",
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

        if "RESERVA_ALREADY_CONFIRMED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva ya se encuentra confirmada.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_RESERVA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una reserva en estado activa puede confirmarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "RESERVA_WITHOUT_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva no posee objetos inmobiliarios asociados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "OBJECT_NOT_AVAILABLE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado no esta disponible para confirmar la reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado ya participa en una venta activa incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_RESERVA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado ya participa en una reserva vigente incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())
        if "CONFLICTING_JERARQUIA_INMOBILIARIA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Existe un conflicto jerarquico entre inmueble y unidad funcional para confirmar la reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo confirmar la reserva de venta.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            ReservaVentaObjetoCreateData(**objeto).model_dump()
            for objeto in result.data["objetos"]
        ],
    }
    return ReservaVentaConfirmResponse(data=ReservaVentaConfirmData(**data))


@router.post(
    "/api/v1/reservas-venta/{id_reserva_venta}/confirmar-venta-completa",
    response_model=ConfirmVentaCompletaDesdeReservaResponse,
    # Nota: no usar openapi_extra con headers CORE-EF aqui porque FastAPI ya
    # genera estos parametros desde Header(...) y se duplicaria name+in.
    # Se mantiene Header(default=None) para preservar el contrato runtime:
    # faltante/invalido => 400 VALIDATION_ERROR (no 422 nativo).
    responses={
        400: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def confirmar_venta_completa_desde_reserva(
    id_reserva_venta: int,
    request: ConfirmVentaCompletaDesdeReservaRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ConfirmVentaCompletaDesdeReservaResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(
        core_ef_headers,
        if_match_version=if_match_version,
    )

    command = ConfirmVentaCompletaDesdeReservaCommand(
        context=context,
        id_reserva_venta=id_reserva_venta,
        if_match_version_reserva=core_ef_headers.if_match_version,
        generar_venta=ConfirmVentaCompletaGenerarVentaInput(
            codigo_venta=request.generar_venta.codigo_venta,
            fecha_venta=request.generar_venta.fecha_venta,
            monto_total=request.generar_venta.monto_total,
            observaciones=request.generar_venta.observaciones,
        ),
        condiciones_comerciales=ConfirmVentaCompletaCondicionesComercialesInput(
            monto_total=request.condiciones_comerciales.monto_total,
            tipo_plan_financiero=request.condiciones_comerciales.tipo_plan_financiero,
            moneda=request.condiciones_comerciales.moneda,
            importe_anticipo=request.condiciones_comerciales.importe_anticipo,
            fecha_vencimiento_anticipo=request.condiciones_comerciales.fecha_vencimiento_anticipo,
            importe_saldo=request.condiciones_comerciales.importe_saldo,
            fecha_vencimiento_saldo=request.condiciones_comerciales.fecha_vencimiento_saldo,
            cuotas=[
                ConfirmVentaCompletaCondicionCuotaInput(
                    numero_cuota=item.numero_cuota,
                    importe_cuota=item.importe_cuota,
                    fecha_vencimiento=item.fecha_vencimiento,
                    moneda=item.moneda,
                    observaciones=item.observaciones,
                )
                for item in request.condiciones_comerciales.cuotas
            ],
            objetos=[
                ConfirmVentaCompletaCondicionObjetoInput(
                    id_inmueble=item.id_inmueble,
                    id_unidad_funcional=item.id_unidad_funcional,
                    precio_asignado=item.precio_asignado,
                )
                for item in request.condiciones_comerciales.objetos
            ],
        ),
        plan_pago_v2=ConfirmVentaCompletaPlanPagoV2Input(
            tipo_pago=request.plan_pago_v2.tipo_pago,
            monto_total_plan=request.plan_pago_v2.monto_total_plan,
            moneda=request.plan_pago_v2.moneda,
            bloques=[
                ConfirmVentaCompletaPlanPagoBloqueInput(
                    tipo_bloque=item.tipo_bloque,
                    etiqueta_bloque=item.etiqueta_bloque,
                    importe_total_bloque=item.importe_total_bloque,
                    fecha_vencimiento=item.fecha_vencimiento,
                    cantidad_cuotas=item.cantidad_cuotas,
                    importe_cuota=item.importe_cuota,
                    fecha_primer_vencimiento=item.fecha_primer_vencimiento,
                    periodicidad=item.periodicidad,
                    regla_redondeo=item.regla_redondeo,
                    observaciones=item.observaciones,
                )
                for item in request.plan_pago_v2.bloques
            ],
            observaciones=request.plan_pago_v2.observaciones,
        ),
        confirmacion=ConfirmVentaCompletaConfirmacionInput(
            observaciones=request.confirmacion.observaciones,
        ),
    )

    service = ConfirmVentaCompletaDesdeReservaService(
        comercial_repository=ComercialRepository(db),
        plan_pago_v2_service=GeneratePlanPagoVentaV2PorBloquesService(
            repository=PlanPagoVentaV2Repository(db)
        ),
    )

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "CONCURRENCY_ERROR" in result.errors:
            error = ErrorResponse(
                error_code="CONCURRENCY_ERROR",
                error_message="If-Match-Version es requerido y debe coincidir con version_registro de reserva_venta.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        if "MONTO_TOTAL_PLAN_MISMATCH" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="monto_total de condiciones_comerciales debe coincidir con monto_total_plan.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if any(error.startswith("NOT_FOUND") for error in result.errors):
            error = ErrorResponse(
                error_code=result.errors[0],
                error_message="No se encontro el recurso requerido para confirmar la venta completa desde la reserva.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo confirmar la venta completa desde la reserva.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ConfirmVentaCompletaDesdeReservaResponse(**result.data)


@router.post(
    "/api/v1/ventas/directa/confirmar-venta-completa",
    response_model=ConfirmVentaDirectaCompletaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def confirmar_venta_directa_completa(
    request: ConfirmVentaDirectaCompletaRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ConfirmVentaDirectaCompletaResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers)

    command = ConfirmVentaDirectaCompletaCommand(
        context=context,
        generar_venta=ConfirmVentaDirectaCompletaGenerarVentaInput(
            codigo_venta=request.generar_venta.codigo_venta,
            fecha_venta=request.generar_venta.fecha_venta,
            monto_total=request.generar_venta.monto_total,
            observaciones=request.generar_venta.observaciones,
        ),
        objetos=[
            ConfirmVentaDirectaCompletaObjetoInput(
                id_inmueble=item.id_inmueble,
                id_unidad_funcional=item.id_unidad_funcional,
                precio_asignado=item.precio_asignado,
                observaciones=item.observaciones,
            )
            for item in request.objetos
        ],
        compradores=[
            ConfirmVentaDirectaCompletaCompradorInput(
                id_persona=item.id_persona,
                id_rol_participacion=item.id_rol_participacion,
                fecha_desde=item.fecha_desde,
                fecha_hasta=item.fecha_hasta,
                observaciones=item.observaciones,
            )
            for item in request.compradores
        ],
        condiciones_comerciales=ConfirmVentaDirectaCompletaCondicionesComercialesInput(
            monto_total=request.condiciones_comerciales.monto_total,
            tipo_plan_financiero=request.condiciones_comerciales.tipo_plan_financiero,
            moneda=request.condiciones_comerciales.moneda,
            importe_anticipo=request.condiciones_comerciales.importe_anticipo,
            fecha_vencimiento_anticipo=request.condiciones_comerciales.fecha_vencimiento_anticipo,
            importe_saldo=request.condiciones_comerciales.importe_saldo,
            fecha_vencimiento_saldo=request.condiciones_comerciales.fecha_vencimiento_saldo,
            cuotas=[
                ConfirmVentaDirectaCompletaCondicionCuotaInput(
                    numero_cuota=item.numero_cuota,
                    importe_cuota=item.importe_cuota,
                    fecha_vencimiento=item.fecha_vencimiento,
                    moneda=item.moneda,
                    observaciones=item.observaciones,
                )
                for item in request.condiciones_comerciales.cuotas
            ],
        ),
        plan_pago_v2=ConfirmVentaDirectaCompletaPlanPagoV2Input(
            tipo_pago=request.plan_pago_v2.tipo_pago,
            monto_total_plan=request.plan_pago_v2.monto_total_plan,
            moneda=request.plan_pago_v2.moneda,
            bloques=[
                ConfirmVentaDirectaCompletaPlanPagoBloqueInput(
                    tipo_bloque=item.tipo_bloque,
                    etiqueta_bloque=item.etiqueta_bloque,
                    importe_total_bloque=item.importe_total_bloque,
                    fecha_vencimiento=item.fecha_vencimiento,
                    cantidad_cuotas=item.cantidad_cuotas,
                    importe_cuota=item.importe_cuota,
                    fecha_primer_vencimiento=item.fecha_primer_vencimiento,
                    periodicidad=item.periodicidad,
                    regla_redondeo=item.regla_redondeo,
                    observaciones=item.observaciones,
                )
                for item in request.plan_pago_v2.bloques
            ],
            observaciones=request.plan_pago_v2.observaciones,
        ),
        confirmacion=ConfirmVentaDirectaCompletaConfirmacionInput(
            observaciones=request.confirmacion.observaciones,
        ),
    )

    service = ConfirmVentaDirectaCompletaService(
        comercial_repository=ComercialRepository(db),
        plan_pago_v2_service=GeneratePlanPagoVentaV2PorBloquesService(
            repository=PlanPagoVentaV2Repository(db)
        ),
    )

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "MONTO_TOTAL_PLAN_MISMATCH" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="monto_total de condiciones_comerciales debe coincidir con monto_total_plan.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if any(error.startswith("NOT_FOUND") for error in result.errors):
            error = ErrorResponse(
                error_code=result.errors[0],
                error_message="No se encontro el recurso requerido para confirmar la venta directa completa.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo confirmar la venta directa completa.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ConfirmVentaDirectaCompletaResponse(**result.data)


@router.post(
    "/api/v1/reservas-venta/{id_reserva_venta}/generar-venta",
    status_code=201,
    response_model=GenerateVentaFromReservaVentaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def generate_venta_from_reserva_venta(
    id_reserva_venta: int,
    request: GenerateVentaFromReservaVentaRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> GenerateVentaFromReservaVentaResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers, if_match_version)

    command = GenerateVentaFromReservaVentaCommand(
        context=context,
        id_reserva_venta=id_reserva_venta,
        if_match_version=core_ef_headers.if_match_version,
        codigo_venta=request.codigo_venta,
        fecha_venta=request.fecha_venta,
        monto_total=request.monto_total,
        observaciones=request.observaciones,
    )

    repository = ComercialRepository(db)
    service = GenerateVentaFromReservaVentaService(repository=repository)

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
            for error in (
                "NOT_FOUND_RESERVA_VENTA",
                "NOT_FOUND_INMUEBLE",
                "NOT_FOUND_UNIDAD_FUNCIONAL",
            )
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La reserva o el objeto inmobiliario indicado no existe.",
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

        if "RESERVA_ALREADY_CONVERTED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva ya fue convertida en una venta.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_REQUIRED_FIELDS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="codigo_venta es requerido.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_RESERVA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una reserva en estado confirmada puede generar una venta.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "RESERVA_WITHOUT_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva no posee objetos inmobiliarios asociados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_RESERVA_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva presenta un detalle multiobjeto inconsistente.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "DUPLICATE_CODIGO_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="codigo_venta ya existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_RESERVA_BLOCK" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva confirmada no mantiene un bloqueo de disponibilidad consistente.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado ya participa en una venta activa incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_RESERVA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Existe una reserva vigente incompatible sobre alguno de los objetos.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo generar la venta desde la reserva.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            VentaObjetoData(**objeto).model_dump() for objeto in result.data["objetos"]
        ],
    }
    return GenerateVentaFromReservaVentaResponse(
        data=GenerateVentaFromReservaVentaData(**data)
    )


@router.get(
    "/api/v1/ventas",
    response_model=VentaListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_ventas(
    q: str | None = Query(default=None),
    estado_venta: str | None = Query(default=None),
    id_persona: int | None = Query(default=None),
    rol_codigo: str | None = Query(default=None),
    id_inmueble: int | None = Query(default=None),
    id_unidad_funcional: int | None = Query(default=None),
    tipo_plan_financiero: str | None = Query(default=None),
    fecha_venta_desde: datetime | None = Query(default=None),
    fecha_venta_hasta: datetime | None = Query(default=None),
    con_saldo: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> VentaListResponse | JSONResponse:
    repository = ComercialRepository(db)
    service = ListVentasService(repository=repository)

    try:
        result = service.execute(
            q=q,
            estado_venta=estado_venta,
            id_persona=id_persona,
            rol_codigo=rol_codigo,
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
            tipo_plan_financiero=tipo_plan_financiero,
            fecha_venta_desde=fecha_venta_desde,
            fecha_venta_hasta=fecha_venta_hasta,
            con_saldo=con_saldo,
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
            error_message="No se pudieron obtener las ventas.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return VentaListResponse(
        data=VentaListData(
            items=[VentaListItemData(**item) for item in result.data["items"]],
            total=result.data["total"],
            limit=result.data.get("limit"),
            offset=result.data.get("offset"),
        )
    )


@router.get(
    "/api/v1/ventas/{id_venta}",
    response_model=VentaDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_venta(
    id_venta: int,
    db: Session = Depends(get_db),
) -> VentaDetailResponse | JSONResponse:
    repository = ComercialRepository(db)
    service = GetVentaService(repository=repository)

    try:
        result = service.execute(id_venta)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="La venta indicada no existe.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return VentaDetailResponse(data=VentaDetailData(**result.data))


@router.get(
    "/api/v1/ventas/{id_venta}/detalle-integral",
    response_model=VentaDetalleIntegralResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_venta_detalle_integral(
    id_venta: int,
    db: Session = Depends(get_db),
) -> VentaDetalleIntegralResponse | JSONResponse:
    repository = ComercialRepository(db)
    service = GetVentaDetalleIntegralService(repository=repository)

    try:
        result = service.execute(id_venta)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="La venta indicada no existe.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return VentaDetalleIntegralResponse(data=VentaDetalleIntegralData(**result.data))


@router.post(
    "/api/v1/ventas/{id_venta}/definir-condiciones-comerciales",
    response_model=DefineCondicionesComercialesVentaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def define_condiciones_comerciales_venta(
    id_venta: int,
    request: DefineCondicionesComercialesVentaRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> DefineCondicionesComercialesVentaResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers, if_match_version)

    command = DefineCondicionesComercialesVentaCommand(
        context=context,
        id_venta=id_venta,
        if_match_version=core_ef_headers.if_match_version,
        monto_total=request.monto_total,
        tipo_plan_financiero=request.tipo_plan_financiero,
        moneda=request.moneda,
        importe_anticipo=request.importe_anticipo,
        fecha_vencimiento_anticipo=request.fecha_vencimiento_anticipo,
        importe_saldo=request.importe_saldo,
        fecha_vencimiento_saldo=request.fecha_vencimiento_saldo,
        cuotas=[
            DefineCondicionesComercialesVentaCuotaCommand(
                numero_cuota=item.numero_cuota,
                importe_cuota=item.importe_cuota,
                fecha_vencimiento=item.fecha_vencimiento,
                moneda=item.moneda,
                observaciones=item.observaciones,
            )
            for item in request.cuotas
        ],
        objetos=[
            DefineCondicionesComercialesVentaObjetoCommand(
                id_inmueble=item.id_inmueble,
                id_unidad_funcional=item.id_unidad_funcional,
                precio_asignado=item.precio_asignado,
            )
            for item in request.objetos
        ],
    )

    repository = ComercialRepository(db)
    service = DefineCondicionesComercialesVentaService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La venta indicada no existe.",
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

        if "INVALID_VENTA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una venta en estado borrador puede definir condiciones comerciales.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "VENTA_WITHOUT_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta no posee objetos inmobiliarios asociados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "EXACTLY_ONE_OBJECT_PARENT_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Cada objeto debe informar exactamente uno entre id_inmueble e id_unidad_funcional.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "DUPLICATE_OBJECT" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No puede repetirse el mismo objeto dentro de una misma venta.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_PRECIO_ASIGNADO" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="precio_asignado debe ser mayor que cero para cada objeto.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "MISSING_VENTA_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Deben informarse todos los objetos vigentes de la venta, sin faltantes ni extras.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_MONTO_TOTAL" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La suma de precio_asignado debe coincidir exactamente con monto_total.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_TIPO_PLAN_FINANCIERO" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="tipo_plan_financiero debe ser CONTADO, ANTICIPO_Y_SALDO o CUOTAS_FIJAS.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_MONEDA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="moneda es requerida para las condiciones comerciales.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if any(error.startswith("INVALID_PLAN_CUOTAS_FIJAS") for error in result.errors):
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El plan CUOTAS_FIJAS requiere cuotas secuenciales desde 1, importes positivos, moneda consistente, fechas de vencimiento y suma exacta contra monto_total.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if (
            "INVALID_PLAN_ANTICIPO_Y_SALDO" in result.errors
            or "INVALID_PLAN_ANTICIPO_Y_SALDO_TOTAL" in result.errors
        ):
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El plan ANTICIPO_Y_SALDO requiere anticipo y saldo positivos, fechas de vencimiento y suma exacta contra monto_total.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_VENTA_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta presenta un detalle multiobjeto inconsistente.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())


        if "X-Instalacion-Id es requerido." in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="X-Instalacion-Id es requerido.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron definir las condiciones comerciales de la venta.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            VentaObjetoData(**objeto).model_dump() for objeto in result.data["objetos"]
        ],
    }
    return DefineCondicionesComercialesVentaResponse(
        data=DefineCondicionesComercialesVentaData(**data)
    )


def _build_plan_pago_v2_por_bloques_command(
    *,
    id_venta: int,
    request: GeneratePlanPagoVentaV2PorBloquesRequest,
    context: CommandContext,
) -> GeneratePlanPagoVentaV2PorBloquesCommand:
    return GeneratePlanPagoVentaV2PorBloquesCommand(
        context=context,
        id_venta=id_venta,
        tipo_pago=request.tipo_pago,
        monto_total_plan=request.monto_total_plan,
        moneda=request.moneda,
        bloques=[
            PlanPagoVentaBloqueInput(
                tipo_bloque=bloque.tipo_bloque,
                etiqueta_bloque=bloque.etiqueta_bloque,
                importe_total_bloque=bloque.importe_total_bloque,
                fecha_vencimiento=bloque.fecha_vencimiento,
                cantidad_cuotas=bloque.cantidad_cuotas,
                importe_cuota=bloque.importe_cuota,
                fecha_primer_vencimiento=bloque.fecha_primer_vencimiento,
                periodicidad=bloque.periodicidad,
                regla_redondeo=bloque.regla_redondeo,
                metodo_liquidacion=bloque.metodo_liquidacion,
                tasa_interes_directo_periodica=bloque.tasa_interes_directo_periodica,
                cantidad_periodos=bloque.cantidad_periodos,
                base_calculo_interes=bloque.base_calculo_interes,
                id_indice_financiero=bloque.id_indice_financiero,
                fecha_base_indice=bloque.fecha_base_indice,
                valor_base_indice=bloque.valor_base_indice,
                modo_indexacion=bloque.modo_indexacion,
                base_calculo_indexacion=bloque.base_calculo_indexacion,
                tipo_generacion_indexada=bloque.tipo_generacion_indexada,
                politica_valor_no_disponible=bloque.politica_valor_no_disponible,
                conserva_capital_original=bloque.conserva_capital_original,
                genera_ajuste_por_diferencia=bloque.genera_ajuste_por_diferencia,
                observaciones=bloque.observaciones,
            )
            for bloque in request.bloques
        ],
        observaciones=request.observaciones,
    )


def _plan_pago_v2_preview_response_data(
    *,
    command: GeneratePlanPagoVentaV2PorBloquesCommand,
    preview: dict,
) -> dict:
    return {
        "id_venta": command.id_venta,
        "metodo_plan_pago": METODO_PLAN_POR_BLOQUES,
        "tipo_pago": command.tipo_pago.strip().upper(),
        "moneda": command.moneda.strip().upper(),
        "monto_total_plan": command.monto_total_plan,
        "total_calculado": preview["total_calculado"],
        "total_con_interes": preview["total_con_interes"],
        "total_con_indexacion": preview["total_con_indexacion"],
        "total_ajuste_indexacion": preview["total_ajuste_indexacion"],
        "diferencia": preview["diferencia"],
        "redondeos": preview["redondeos"],
        "bloques": [
            {
                "numero_bloque": bloque.numero_bloque,
                "tipo_bloque": bloque.tipo_bloque,
                "etiqueta_bloque": bloque.etiqueta_bloque,
                "cantidad_cuotas": bloque.input.cantidad_cuotas,
                "importe_total_bloque": bloque.importe_total_bloque,
                "importe_cuota": bloque.importe_cuota,
                "fecha_vencimiento": bloque.input.fecha_vencimiento,
                "fecha_primer_vencimiento": bloque.input.fecha_primer_vencimiento,
                "periodicidad": bloque.input.periodicidad,
                "regla_redondeo": bloque.input.regla_redondeo,
                "metodo_liquidacion": bloque.input.metodo_liquidacion,
                "tasa_interes_directo_periodica": bloque.input.tasa_interes_directo_periodica,
                "cantidad_periodos": bloque.input.cantidad_periodos,
                "base_calculo_interes": bloque.input.base_calculo_interes,
                "id_indice_financiero": bloque.input.id_indice_financiero,
                "fecha_base_indice": bloque.input.fecha_base_indice,
                "valor_base_indice": bloque.input.valor_base_indice,
                "modo_indexacion": bloque.input.modo_indexacion,
                "base_calculo_indexacion": bloque.input.base_calculo_indexacion,
                "tipo_generacion_indexada": bloque.input.tipo_generacion_indexada,
                "politica_valor_no_disponible": bloque.input.politica_valor_no_disponible,
                "conserva_capital_original": bloque.input.conserva_capital_original,
                "genera_ajuste_por_diferencia": bloque.input.genera_ajuste_por_diferencia,
                "total_con_indexacion": bloque.total_con_indexacion,
                "total_ajuste_indexacion": bloque.total_ajuste_indexacion,
                "cantidad_cuotas_con_indice": bloque.cantidad_cuotas_con_indice,
                "cantidad_cuotas_proyectadas_sin_indice": bloque.cantidad_cuotas_proyectadas_sin_indice,
                "concepto_financiero_codigo": bloque.concepto_financiero_codigo,
            }
            for bloque in preview["bloques"]
        ],
        "obligaciones": [
            {
                "numero_obligacion": obligacion.numero_obligacion,
                "numero_bloque": obligacion.bloque.numero_bloque,
                "tipo_bloque": obligacion.bloque.tipo_bloque,
                "tipo_item_cronograma": obligacion.tipo_item_cronograma,
                "etiqueta_obligacion": obligacion.etiqueta_obligacion,
                "item_numero": obligacion.item_numero,
                "fecha_vencimiento": obligacion.fecha_vencimiento,
                "importe_total": obligacion.importe_total,
                "moneda": command.moneda.strip().upper(),
                "concepto_financiero_codigo": obligacion.concepto_financiero_codigo,
                "estado_preview_indexacion": obligacion.estado_preview_indexacion,
                "id_indice_financiero": obligacion.id_indice_financiero,
                "id_indice_financiero_valor": obligacion.id_indice_financiero_valor,
                "fecha_valor_indice": obligacion.fecha_valor_indice,
                "valor_base_indice": obligacion.valor_base_indice,
                "valor_aplicado_indice": obligacion.valor_aplicado_indice,
                "coeficiente_indexacion": obligacion.coeficiente_indexacion,
                "capital_cuota": obligacion.capital_cuota,
                "ajuste_indexacion_cuota": obligacion.ajuste_indexacion_cuota,
            }
            for obligacion in preview["obligaciones"]
        ],
    }


@router.post(
    "/api/v1/ventas/{id_venta}/plan-pago-v2/preview",
    response_model=PreviewPlanPagoVentaV2PorBloquesResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def preview_plan_pago_venta_v2_por_bloques(
    id_venta: int,
    request: PreviewPlanPagoVentaV2PorBloquesRequest,
    db: Session = Depends(get_db),
) -> PreviewPlanPagoVentaV2PorBloquesResponse | JSONResponse:
    command = _build_plan_pago_v2_por_bloques_command(
        id_venta=id_venta,
        request=request,
        context=CommandContext(),
    )
    service = BuildPlanPagoVentaV2PorBloquesPreviewService(
        indice_financiero_query=IndiceFinancieroRepository(db)
    )

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
            error_message="No se pudo previsualizar el plan de pago V2 por bloques.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PreviewPlanPagoVentaV2PorBloquesResponse(
        data=_plan_pago_v2_preview_response_data(command=command, preview=result.data)
    )


@router.post(
    "/api/v1/ventas/{id_venta}/plan-pago-v2/generar",
    response_model=GeneratePlanPagoVentaV2PorBloquesResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def generate_plan_pago_venta_v2_por_bloques(
    id_venta: int,
    request: GeneratePlanPagoVentaV2PorBloquesRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> GeneratePlanPagoVentaV2PorBloquesResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers)
    command = _build_plan_pago_v2_por_bloques_command(
        id_venta=id_venta,
        request=request,
        context=context,
    )
    service = GeneratePlanPagoVentaV2PorBloquesService(
        repository=PlanPagoVentaV2Repository(db)
    )

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La venta indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if any(
            error.startswith("PLAN_PAGO_VENTA_VIVO_INCOMPATIBLE")
            or error.startswith("PLAN_PAGO_VENTA_BLOQUE_INCOMPATIBLE")
            or error.startswith("PLAN_PAGO_VENTA_BLOQUE_INDEXACION_INCOMPATIBLE")
            or error.startswith("OBLIGACION_PLAN_PAGO_VENTA_BLOQUE_INCOMPATIBLE")
            for error in result.errors
        ):
            error = ErrorResponse(
                error_code="CONFLICT",
                error_message="La venta ya posee un plan de pago vivo incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        if (
            "COMPRADOR_VENTA_NO_RESUELTO" in result.errors
            or "COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO" in result.errors
        ):
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta debe tener exactamente un comprador financiero resoluble.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if any(error.startswith("NOT_FOUND_CONCEPTO") for error in result.errors):
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No existe un concepto financiero requerido para generar el cronograma.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo generar el plan de pago V2 por bloques.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return GeneratePlanPagoVentaV2PorBloquesResponse(data=result.data)


@router.post(
    "/api/v1/ventas/{id_venta}/plan-pago-v2/cuotas-iguales-simple",
    response_model=GeneratePlanPagoVentaCuotasIgualesSimpleResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def generate_plan_pago_venta_cuotas_iguales_simple(
    id_venta: int,
    request: GeneratePlanPagoVentaCuotasIgualesSimpleRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> GeneratePlanPagoVentaCuotasIgualesSimpleResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers)
    command = GeneratePlanPagoVentaCuotasIgualesSimpleCommand(
        context=context,
        id_venta=id_venta,
        monto_total_plan=request.monto_total_plan,
        moneda=request.moneda,
        cantidad_cuotas=request.cantidad_cuotas,
        fecha_primer_vencimiento=request.fecha_primer_vencimiento,
        periodicidad=request.periodicidad,
        regla_redondeo=request.regla_redondeo,
    )
    service = GeneratePlanPagoVentaCuotasIgualesSimpleService(
        repository=PlanPagoVentaV2Repository(db)
    )

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La venta indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "PLAN_PAGO_VENTA_VIVO_INCOMPATIBLE" in result.errors:
            error = ErrorResponse(
                error_code="CONFLICT",
                error_message="La venta ya posee un plan de pago vivo incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        if (
            "COMPRADOR_VENTA_NO_RESUELTO" in result.errors
            or "COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO" in result.errors
        ):
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta debe tener exactamente un comprador financiero resoluble.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if any(error.startswith("NOT_FOUND_CONCEPTO") for error in result.errors):
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No existe un concepto financiero requerido para generar el cronograma.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo generar el plan de pago V2 de cuotas iguales.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return GeneratePlanPagoVentaCuotasIgualesSimpleResponse(data=result.data)


@router.post(
    "/api/v1/ventas/{id_venta}/plan-pago-v2/anticipo-mas-cuotas-iguales",
    response_model=GeneratePlanPagoVentaAnticipoMasCuotasIgualesResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def generate_plan_pago_venta_anticipo_mas_cuotas_iguales(
    id_venta: int,
    request: GeneratePlanPagoVentaAnticipoMasCuotasIgualesRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> GeneratePlanPagoVentaAnticipoMasCuotasIgualesResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers)
    command = GeneratePlanPagoVentaAnticipoMasCuotasIgualesCommand(
        context=context,
        id_venta=id_venta,
        monto_total_plan=request.monto_total_plan,
        moneda=request.moneda,
        importe_anticipo=request.importe_anticipo,
        fecha_vencimiento_anticipo=request.fecha_vencimiento_anticipo,
        cantidad_cuotas=request.cantidad_cuotas,
        fecha_primer_vencimiento=request.fecha_primer_vencimiento,
        periodicidad=request.periodicidad,
        regla_redondeo=request.regla_redondeo,
    )
    service = GeneratePlanPagoVentaAnticipoMasCuotasIgualesService(
        repository=PlanPagoVentaV2Repository(db)
    )

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La venta indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "PLAN_PAGO_VENTA_VIVO_INCOMPATIBLE" in result.errors:
            error = ErrorResponse(
                error_code="CONFLICT",
                error_message="La venta ya posee un plan de pago vivo incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        if (
            "COMPRADOR_VENTA_NO_RESUELTO" in result.errors
            or "COMPRADOR_VENTA_MULTIPLE_NO_SOPORTADO" in result.errors
        ):
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta debe tener exactamente un comprador financiero resoluble.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if any(error.startswith("NOT_FOUND_CONCEPTO") for error in result.errors):
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No existe un concepto financiero requerido para generar el cronograma.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo generar el plan de pago V2 de anticipo mas cuotas iguales.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return GeneratePlanPagoVentaAnticipoMasCuotasIgualesResponse(data=result.data)


@router.patch(
    "/api/v1/ventas/{id_venta}/confirmar",
    response_model=ConfirmVentaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def confirm_venta(
    id_venta: int,
    request: ConfirmVentaRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ConfirmVentaResponse | JSONResponse:
    core_ef_headers = _parse_core_ef_headers_with_if_match_or_error(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
        if_match_version=if_match_version,
    )
    if isinstance(core_ef_headers, JSONResponse):
        return core_ef_headers

    context = _build_comercial_command_context(core_ef_headers, if_match_version=if_match_version)

    command = ConfirmVentaCommand(
        context=context,
        id_venta=id_venta,
        if_match_version=core_ef_headers.if_match_version,
        observaciones=request.observaciones,
    )

    repository = ComercialRepository(db)
    service = ConfirmVentaService(repository=repository)

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
            for error in (
                "NOT_FOUND_VENTA",
                "NOT_FOUND_RESERVA_VENTA",
                "NOT_FOUND_INMUEBLE",
                "NOT_FOUND_UNIDAD_FUNCIONAL",
            )
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La venta o la reserva vinculada indicada no existe.",
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

        if "INVALID_VENTA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una venta en estado borrador o activa puede confirmarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "VENTA_WITHOUT_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta no posee objetos inmobiliarios asociados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_VENTA_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta presenta un detalle multiobjeto inconsistente.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INCOMPLETE_VENTA_CONDITIONS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta debe tener condiciones comerciales completas antes de confirmarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado ya participa en una venta activa incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "OBJECT_NOT_AVAILABLE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="El objeto inmobiliario indicado no esta disponible para confirmar la venta.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_LINKED_RESERVA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La reserva vinculada no se encuentra en un estado compatible para confirmar la venta.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo confirmar la venta.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            VentaObjetoData(**objeto).model_dump() for objeto in result.data["objetos"]
        ],
    }
    return ConfirmVentaResponse(data=ConfirmVentaData(**data))


@router.get(
    "/api/v1/ventas/{id_venta}/instrumentos-compraventa",
    response_model=InstrumentoCompraventaListResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_instrumentos_compraventa(
    id_venta: int,
    tipo_instrumento: str | None = Query(default=None),
    estado_instrumento: str | None = Query(default=None),
    fecha_desde: datetime | None = Query(default=None),
    fecha_hasta: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> InstrumentoCompraventaListResponse | JSONResponse:
    repository = ComercialRepository(db)
    service = ListInstrumentosCompraventaService(repository=repository)

    try:
        result = service.execute(
            id_venta,
            tipo_instrumento=tipo_instrumento,
            estado_instrumento=estado_instrumento,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="La venta indicada no existe.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return InstrumentoCompraventaListResponse(
        data=InstrumentoCompraventaListData(
            items=[
                InstrumentoCompraventaData(**item) for item in result.data["items"]
            ],
            total=result.data["total"],
        )
    )


@router.post(
    "/api/v1/ventas/{id_venta}/instrumentos-compraventa",
    status_code=201,
    response_model=CreateInstrumentoCompraventaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_instrumento_compraventa(
    id_venta: int,
    request: CreateInstrumentoCompraventaRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> CreateInstrumentoCompraventaResponse | JSONResponse:
    id_instalacion: int | None = None
    op_id: UUID | None = None

    if x_instalacion_id is not None:
        try:
            id_instalacion = int(x_instalacion_id)
        except ValueError:
            id_instalacion = None

    if x_op_id:
        try:
            op_id = UUID(x_op_id)
        except ValueError:
            op_id = None

    context_kwargs = {
        "actor_id": x_usuario_id,
        "metadata": {
            "x_op_id": x_op_id,
            "x_sucursal_id": x_sucursal_id,
            "x_instalacion_id": x_instalacion_id,
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = ComercialCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreateInstrumentoCompraventaCommand(
        context=context,
        id_venta=id_venta,
        tipo_instrumento=request.tipo_instrumento,
        numero_instrumento=request.numero_instrumento,
        fecha_instrumento=request.fecha_instrumento,
        estado_instrumento=request.estado_instrumento,
        observaciones=request.observaciones,
        objetos=[
            CreateInstrumentoCompraventaObjetoCommand(
                id_inmueble=item.id_inmueble,
                id_unidad_funcional=item.id_unidad_funcional,
                observaciones=item.observaciones,
            )
            for item in request.objetos
        ],
    )

    repository = ComercialRepository(db)
    service = CreateInstrumentoCompraventaService(repository=repository)

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
            for error in ("NOT_FOUND_VENTA", "NOT_FOUND_INMUEBLE", "NOT_FOUND_UNIDAD_FUNCIONAL")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La venta o el objeto inmobiliario indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "INVALID_VENTA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una venta en estado confirmada puede emitir instrumentos de compraventa.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "VENTA_WITHOUT_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta no posee objetos inmobiliarios asociados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_VENTA_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta presenta un detalle multiobjeto inconsistente.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INCOMPLETE_VENTA_CONDITIONS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta debe tener condiciones comerciales completas antes de emitir instrumentos.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_REQUIRED_FIELDS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="tipo_instrumento es requerido.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_ESTADO_INSTRUMENTO" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="estado_instrumento es invalido para instrumento_compraventa.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "EXACTLY_ONE_OBJECT_PARENT_REQUIRED" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Cada objeto debe informar exactamente uno entre id_inmueble e id_unidad_funcional.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "DUPLICATE_OBJECT" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No puede repetirse el mismo objeto dentro de un mismo instrumento.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_INSTRUMENT_ASSOCIATION" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Los objetos del instrumento deben pertenecer a la venta indicada.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())


        if "X-Instalacion-Id es requerido." in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="X-Instalacion-Id es requerido.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo registrar el instrumento de compraventa.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    data = {
        **result.data,
        "objetos": [
            InstrumentoCompraventaObjetoData(**objeto).model_dump()
            for objeto in result.data["objetos"]
        ],
    }
    return CreateInstrumentoCompraventaResponse(
        data=InstrumentoCompraventaData(**data)
    )


@router.get(
    "/api/v1/ventas/{id_venta}/cesiones",
    response_model=CesionListResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_cesiones(
    id_venta: int,
    tipo_cesion: str | None = Query(default=None),
    fecha_desde: datetime | None = Query(default=None),
    fecha_hasta: datetime | None = Query(default=None),
    db: Session = Depends(get_db),
) -> CesionListResponse | JSONResponse:
    repository = ComercialRepository(db)
    service = ListCesionesService(repository=repository)

    try:
        result = service.execute(
            id_venta,
            tipo_cesion=tipo_cesion,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="La venta indicada no existe.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return CesionListResponse(
        data=CesionListData(
            items=[CesionData(**item) for item in result.data["items"]],
            total=result.data["total"],
        )
    )


@router.post(
    "/api/v1/ventas/{id_venta}/cesiones",
    status_code=201,
    response_model=CreateCesionResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_cesion(
    id_venta: int,
    request: CreateCesionRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> CreateCesionResponse | JSONResponse:
    id_instalacion: int | None = None
    op_id: UUID | None = None

    if x_instalacion_id is not None:
        try:
            id_instalacion = int(x_instalacion_id)
        except ValueError:
            id_instalacion = None

    if x_op_id:
        try:
            op_id = UUID(x_op_id)
        except ValueError:
            op_id = None

    context_kwargs = {
        "actor_id": x_usuario_id,
        "metadata": {
            "x_op_id": x_op_id,
            "x_sucursal_id": x_sucursal_id,
            "x_instalacion_id": x_instalacion_id,
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = ComercialCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreateCesionCommand(
        context=context,
        id_venta=id_venta,
        fecha_cesion=request.fecha_cesion,
        tipo_cesion=request.tipo_cesion,
        observaciones=request.observaciones,
    )

    repository = ComercialRepository(db)
    service = CreateCesionService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La venta indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "INVALID_VENTA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una venta en estado confirmada puede registrar cesiones.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "VENTA_WITHOUT_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta no posee objetos inmobiliarios asociados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_VENTA_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta presenta un detalle multiobjeto inconsistente.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INCOMPLETE_VENTA_CONDITIONS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta debe tener condiciones comerciales completas antes de registrar cesiones.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_RESCISION" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta posee una rescision activa incompatible con una nueva cesion.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_ESCRITURACION" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta posee una escrituracion activa incompatible con una nueva cesion.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_CESION" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta ya posee una cesion activa incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_OCUPACION" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Existe una ocupacion vigente incompatible con la continuidad comercial de la venta.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())


        if "X-Instalacion-Id es requerido." in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="X-Instalacion-Id es requerido.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo registrar la cesion.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return CreateCesionResponse(data=CesionData(**result.data))


@router.get(
    "/api/v1/ventas/{id_venta}/escrituraciones",
    response_model=EscrituracionListResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_escrituraciones(
    id_venta: int,
    fecha_desde: datetime | None = Query(default=None),
    fecha_hasta: datetime | None = Query(default=None),
    numero_escritura: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> EscrituracionListResponse | JSONResponse:
    repository = ComercialRepository(db)
    service = ListEscrituracionesService(repository=repository)

    try:
        result = service.execute(
            id_venta,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            numero_escritura=numero_escritura,
        )
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="La venta indicada no existe.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return EscrituracionListResponse(
        data=EscrituracionListData(
            items=[EscrituracionData(**item) for item in result.data["items"]],
            total=result.data["total"],
        )
    )


@router.post(
    "/api/v1/ventas/{id_venta}/escrituraciones",
    status_code=201,
    response_model=CreateEscrituracionResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_escrituracion(
    id_venta: int,
    request: CreateEscrituracionRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> CreateEscrituracionResponse | JSONResponse:
    id_instalacion: int | None = None
    op_id: UUID | None = None

    if x_instalacion_id is not None:
        try:
            id_instalacion = int(x_instalacion_id)
        except ValueError:
            id_instalacion = None

    if x_op_id:
        try:
            op_id = UUID(x_op_id)
        except ValueError:
            op_id = None

    context_kwargs = {
        "actor_id": x_usuario_id,
        "metadata": {
            "x_op_id": x_op_id,
            "x_sucursal_id": x_sucursal_id,
            "x_instalacion_id": x_instalacion_id,
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = ComercialCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreateEscrituracionCommand(
        context=context,
        id_venta=id_venta,
        fecha_escrituracion=request.fecha_escrituracion,
        numero_escritura=request.numero_escritura,
        observaciones=request.observaciones,
    )

    repository = ComercialRepository(db)
    service = CreateEscrituracionService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_VENTA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La venta indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "INVALID_VENTA_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo una venta en estado confirmada puede registrar escrituraciones.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "VENTA_WITHOUT_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta no posee objetos inmobiliarios asociados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "INVALID_VENTA_OBJECTS" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta presenta un detalle multiobjeto inconsistente.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_RESCISION" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta posee una rescision activa incompatible con una nueva escrituracion.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if "CONFLICTING_ESCRITURACION" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="La venta ya posee una escrituracion activa incompatible.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())


        if "X-Instalacion-Id es requerido." in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="X-Instalacion-Id es requerido.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo registrar la escrituracion.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return CreateEscrituracionResponse(data=EscrituracionData(**result.data))
