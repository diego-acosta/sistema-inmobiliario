from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.financiero import (
    AplicacionItemData,
    ComposicionCreateItem,
    ConceptoFinancieroData,
    ConceptoFinancieroListData,
    ConceptoFinancieroListResponse,
    DeudaComposicionItem,
    DeudaConsolidadoData,
    DeudaConsolidadoRelacionItem,
    DeudaConsolidadoResumen,
    DeudaConsolidadoResponse,
    DeudaConsolidadoTipoOrigenResumen,
    DeudaItem,
    DeudaListData,
    DeudaListResponse,
    ErrorResponse,
    EstadoCuentaData,
    EstadoCuentaPersonaData,
    EstadoCuentaPersonaObligacionItem,
    EstadoCuentaPersonaResumen,
    EstadoCuentaPersonaResponse,
    EstadoCuentaResponse,
    PagoObligacionResultado,
    RegistrarPagoPersonaData,
    RegistrarPagoPersonaRequest,
    RegistrarPagoPersonaResponse,
    SimularPagoObligacionItem,
    SimularPagoPersonaData,
    SimularPagoPersonaRequest,
    SimularPagoPersonaResponse,
    ImputacionCreateRequest,
    ImputacionData,
    ImputacionResponse,
    InboxEventRequest,
    MoraGenerarData,
    MoraGenerarRequest,
    MoraGenerarResponse,
    ObligacionFinancieraCreateRequest,
    ObligacionFinancieraData,
    ObligacionFinancieraResponse,
    RelacionGeneradoraCreateRequest,
    RelacionGeneradoraData,
    RelacionGeneradoraListData,
    RelacionGeneradoraListResponse,
    RelacionGeneradoraResponse,
)
from app.application.common.commands import CommandContext
from app.application.financiero.commands.create_relacion_generadora import (
    CreateRelacionGeneradoraCommand,
)
from app.application.financiero.commands.generar_mora_financiera import (
    GenerarMoraFinancieraCommand,
)
from app.application.financiero.services.create_relacion_generadora_service import (
    CreateRelacionGeneradoraService,
)
from app.application.financiero.services.get_relacion_generadora_service import (
    GetRelacionGeneradoraService,
)
from app.application.financiero.commands.create_imputacion_financiera import (
    CreateImputacionFinancieraCommand,
)
from app.application.financiero.commands.create_obligacion_financiera import (
    ComposicionInput,
    CreateObligacionFinancieraCommand,
)
from app.application.financiero.services.create_imputacion_financiera_service import (
    CreateImputacionFinancieraService,
)
from app.application.financiero.services.create_obligacion_financiera_service import (
    CreateObligacionFinancieraService,
)
from app.application.financiero.services.get_obligacion_financiera_service import (
    GetObligacionFinancieraService,
)
from app.application.financiero.services.get_estado_cuenta_financiero_service import (
    GetEstadoCuentaFinancieroService,
)
from app.application.financiero.services.get_deuda_consolidado_service import (
    GetDeudaConsolidadoService,
)
from app.application.financiero.services.get_estado_cuenta_persona_service import (
    GetEstadoCuentaPersonaService,
)
from app.application.financiero.services.simular_pago_persona_service import (
    SimularPagoPersonaService,
)
from app.application.financiero.services.registrar_pago_persona_service import (
    RegistrarPagoPersonaService,
)
from app.application.financiero.services.generar_mora_financiera_service import (
    GenerarMoraFinancieraService,
)
from app.application.financiero.services.list_conceptos_financieros_service import (
    ListConceptosFinancierosService,
)
from app.application.financiero.services.list_deuda_consolidada_service import (
    ListDeudaConsolidadaService,
)
from app.application.financiero.services.inbox_event_dispatcher import (
    InboxEventDispatcher,
)
from app.application.financiero.services.list_relaciones_generadoras_service import (
    ListRelacionesGeneradorasService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)


router = APIRouter(tags=["Financiero"])


@dataclass(slots=True)
class FinancieroCommandContext(CommandContext):
    id_instalacion: int | None = None
    op_id: UUID | None = None


def _build_context(
    x_op_id: str | None,
    x_usuario_id: str | None,
    x_sucursal_id: str | None,
    x_instalacion_id: str | None,
) -> FinancieroCommandContext:
    id_instalacion: int | None = None
    op_id: UUID | None = None

    if x_instalacion_id is not None:
        try:
            id_instalacion = int(x_instalacion_id)
        except ValueError:
            pass
    if x_op_id:
        try:
            op_id = UUID(x_op_id)
        except ValueError:
            pass

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

    return FinancieroCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )


@router.post(
    "/api/v1/financiero/relaciones-generadoras",
    status_code=201,
    response_model=RelacionGeneradoraResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_relacion_generadora(
    request: RelacionGeneradoraCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> RelacionGeneradoraResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)

    command = CreateRelacionGeneradoraCommand(
        context=context,
        tipo_origen=request.tipo_origen,
        id_origen=request.id_origen,
        descripcion=request.descripcion,
    )

    repository = FinancieroRepository(db)
    service = CreateRelacionGeneradoraService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if "TIPO_ORIGEN_INVALIDO" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="APPLICATION_ERROR",
                    error_message="tipo_origen debe ser VENTA o CONTRATO_ALQUILER.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "NOT_FOUND_ORIGEN" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="El origen indicado no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo crear la relación generadora.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return RelacionGeneradoraResponse(data=RelacionGeneradoraData(**result.data))


@router.get(
    "/api/v1/financiero/relaciones-generadoras/{id_relacion_generadora}",
    response_model=RelacionGeneradoraResponse,
    responses={
        404: {"model": ErrorResponse},
    },
)
def get_relacion_generadora(
    id_relacion_generadora: int,
    db: Session = Depends(get_db),
) -> RelacionGeneradoraResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = GetRelacionGeneradoraService(repository=repository)
    result = service.execute(id_relacion_generadora)

    if not result.success or result.data is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La relación generadora indicada no existe.",
            ).model_dump(),
        )

    return RelacionGeneradoraResponse(data=RelacionGeneradoraData(**result.data))


@router.get(
    "/api/v1/financiero/relaciones-generadoras",
    response_model=RelacionGeneradoraListResponse,
    responses={
        500: {"model": ErrorResponse},
    },
)
def list_relaciones_generadoras(
    tipo_origen: str | None = Query(default=None),
    id_origen: int | None = Query(default=None),
    vigente: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> RelacionGeneradoraListResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = ListRelacionesGeneradorasService(repository=repository)

    try:
        result = service.execute(
            tipo_origen=tipo_origen,
            id_origen=id_origen,
            vigente=vigente,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    return RelacionGeneradoraListResponse(
        data=RelacionGeneradoraListData(
            items=[RelacionGeneradoraData(**item) for item in result.data["items"]],
            total=result.data["total"],
        )
    )


@router.get(
    "/api/v1/financiero/deuda",
    response_model=DeudaListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_deuda_consolidada(
    id_relacion_generadora: int | None = Query(default=None),
    estado_obligacion: str | None = Query(default=None),
    fecha_vencimiento_desde: date | None = Query(default=None),
    fecha_vencimiento_hasta: date | None = Query(default=None),
    con_saldo: bool | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> DeudaListResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = ListDeudaConsolidadaService(repository=repository)

    try:
        result = service.execute(
            id_relacion_generadora=id_relacion_generadora,
            estado_obligacion=estado_obligacion,
            fecha_vencimiento_desde=fecha_vencimiento_desde,
            fecha_vencimiento_hasta=fecha_vencimiento_hasta,
            con_saldo=con_saldo,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="FECHA_RANGO_INVALIDO",
                error_message="fecha_vencimiento_hasta debe ser mayor o igual a fecha_vencimiento_desde.",
            ).model_dump(),
        )

    return DeudaListResponse(
        data=DeudaListData(
            items=[DeudaItem(**item) for item in result.data["items"]],
            total=result.data["total"],
        )
    )


@router.get(
    "/api/v1/financiero/estado-cuenta",
    response_model=EstadoCuentaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_estado_cuenta_financiero(
    id_relacion_generadora: int = Query(..., gt=0),
    incluir_canceladas: bool = Query(default=False),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> EstadoCuentaResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = GetEstadoCuentaFinancieroService(repository=repository)

    try:
        result = service.execute(
            id_relacion_generadora=id_relacion_generadora,
            incluir_canceladas=incluir_canceladas,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if "NOT_FOUND_RELACION" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="La relacion generadora indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "FECHA_RANGO_INVALIDO" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="FECHA_RANGO_INVALIDO",
                    error_message="fecha_hasta debe ser mayor o igual a fecha_desde.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo consultar el estado de cuenta.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return EstadoCuentaResponse(data=EstadoCuentaData(**result.data))


@router.get(
    "/api/v1/financiero/deuda/consolidado",
    response_model=DeudaConsolidadoResponse,
    responses={500: {"model": ErrorResponse}},
)
def get_deuda_consolidado(
    tipo_origen: str | None = Query(default=None),
    fecha_corte: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> DeudaConsolidadoResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = GetDeudaConsolidadoService(repository=repository)

    try:
        result = service.execute(tipo_origen=tipo_origen, fecha_corte=fecha_corte)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    data = result.data
    return DeudaConsolidadoResponse(
        data=DeudaConsolidadoData(
            fecha_corte=data["fecha_corte"],
            resumen=DeudaConsolidadoResumen(**data["resumen"]),
            por_tipo_origen={
                t: DeudaConsolidadoTipoOrigenResumen(**v)
                for t, v in data["por_tipo_origen"].items()
            },
            relaciones=[
                DeudaConsolidadoRelacionItem(**r) for r in data["relaciones"]
            ],
        )
    )


@router.get(
    "/api/v1/financiero/conceptos-financieros",
    response_model=ConceptoFinancieroListResponse,
    responses={500: {"model": ErrorResponse}},
)
def list_conceptos_financieros(
    estado: str | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ConceptoFinancieroListResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = ListConceptosFinancierosService(repository=repository)

    try:
        result = service.execute(estado=estado, limit=limit, offset=offset)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    return ConceptoFinancieroListResponse(
        data=ConceptoFinancieroListData(
            items=[ConceptoFinancieroData(**item) for item in result.data["items"]],
            total=result.data["total"],
        )
    )


@router.post(
    "/api/v1/financiero/imputaciones",
    status_code=201,
    response_model=ImputacionResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_imputacion_financiera(
    request: ImputacionCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ImputacionResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)

    command = CreateImputacionFinancieraCommand(
        context=context,
        id_obligacion_financiera=request.id_obligacion_financiera,
        monto=request.monto,
    )

    repository = FinancieroRepository(db)
    service = CreateImputacionFinancieraService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if "NOT_FOUND_OBLIGACION" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="La obligación financiera indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "MONTO_EXCEDE_SALDO" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="MONTO_EXCEDE_SALDO",
                    error_message="El monto excede el saldo pendiente de la obligación.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "ESTADO_NO_ACEPTA_IMPUTACION" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="ESTADO_INVALIDO",
                    error_message="El estado de la obligación no acepta imputaciones.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo registrar la imputación.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    data = result.data
    return ImputacionResponse(
        data=ImputacionData(
            id_obligacion_financiera=data["id_obligacion_financiera"],
            id_movimiento_financiero=data["id_movimiento_financiero"],
            monto_aplicado=data["monto_aplicado"],
            aplicaciones=[AplicacionItemData(**a) for a in data["aplicaciones"]],
        )
    )


@router.post(
    "/api/v1/financiero/mora/generar",
    response_model=MoraGenerarResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def generar_mora_financiera(
    request: MoraGenerarRequest | None = None,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> MoraGenerarResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    command = GenerarMoraFinancieraCommand(
        context=context,
        fecha_proceso=request.fecha_proceso if request is not None else None,
    )

    repository = FinancieroRepository(db)
    service = GenerarMoraFinancieraService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo generar la mora financiera.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return MoraGenerarResponse(data=MoraGenerarData(**result.data))


@router.post(
    "/api/v1/financiero/obligaciones",
    status_code=201,
    response_model=ObligacionFinancieraResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_obligacion_financiera(
    request: ObligacionFinancieraCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ObligacionFinancieraResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)

    command = CreateObligacionFinancieraCommand(
        context=context,
        id_relacion_generadora=request.id_relacion_generadora,
        fecha_vencimiento=request.fecha_vencimiento,
        composiciones=[
            ComposicionInput(
                codigo_concepto_financiero=c.codigo_concepto_financiero,
                importe_componente=c.importe_componente,
            )
            for c in request.composiciones
        ],
    )

    repository = FinancieroRepository(db)
    service = CreateObligacionFinancieraService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if any("NOT_FOUND_RELACION" in e for e in result.errors):
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="La relación generadora indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if any("NOT_FOUND_CONCEPTO" in e for e in result.errors):
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="El concepto financiero indicado no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo crear la obligación financiera.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return ObligacionFinancieraResponse(data=ObligacionFinancieraData(**result.data))


@router.get(
    "/api/v1/financiero/obligaciones/{id_obligacion_financiera}",
    response_model=ObligacionFinancieraResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_obligacion_financiera(
    id_obligacion_financiera: int,
    db: Session = Depends(get_db),
) -> ObligacionFinancieraResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = GetObligacionFinancieraService(repository=repository)
    result = service.execute(id_obligacion_financiera)

    if not result.success or result.data is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La obligación financiera indicada no existe.",
            ).model_dump(),
        )

    return ObligacionFinancieraResponse(
        data=ObligacionFinancieraData(**result.data)
    )


@router.get(
    "/api/v1/financiero/personas/{id_persona}/estado-cuenta",
    response_model=EstadoCuentaPersonaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_estado_cuenta_persona(
    id_persona: int,
    estado: str | None = Query(default=None),
    tipo_origen: str | None = Query(default=None),
    id_origen: int | None = Query(default=None),
    vencidas: bool | None = Query(default=None),
    fecha_vencimiento_desde: date | None = Query(default=None),
    fecha_vencimiento_hasta: date | None = Query(default=None),
    fecha_corte: date | None = Query(default=None),
    db: Session = Depends(get_db),
) -> EstadoCuentaPersonaResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = GetEstadoCuentaPersonaService(repository=repository)

    try:
        result = service.execute(
            id_persona=id_persona,
            estado=estado,
            tipo_origen=tipo_origen,
            id_origen=id_origen,
            vencidas=vencidas,
            fecha_vencimiento_desde=fecha_vencimiento_desde,
            fecha_vencimiento_hasta=fecha_vencimiento_hasta,
            fecha_corte=fecha_corte,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if "NOT_FOUND_PERSONA" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="La persona indicada no existe.",
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo consultar el estado de cuenta.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    data = result.data
    return EstadoCuentaPersonaResponse(
        data=EstadoCuentaPersonaData(
            id_persona=data["id_persona"],
            fecha_corte=data["fecha_corte"],
            resumen=EstadoCuentaPersonaResumen(**data["resumen"]),
            obligaciones=[
                EstadoCuentaPersonaObligacionItem(**ob)
                for ob in data["obligaciones"]
            ],
        )
    )


@router.post(
    "/api/v1/financiero/personas/{id_persona}/simular-pago",
    response_model=SimularPagoPersonaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def simular_pago_persona(
    id_persona: int,
    request: SimularPagoPersonaRequest,
    db: Session = Depends(get_db),
) -> SimularPagoPersonaResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = SimularPagoPersonaService(repository=repository)

    try:
        result = service.execute(
            id_persona=id_persona,
            monto=request.monto,
            fecha_corte=request.fecha_corte,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if "NOT_FOUND_PERSONA" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="La persona indicada no existe.",
                ).model_dump(),
            )
        if "MONTO_INVALIDO" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="MONTO_INVALIDO",
                    error_message="El monto debe ser mayor que cero.",
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo simular el pago.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    data = result.data
    return SimularPagoPersonaResponse(
        data=SimularPagoPersonaData(
            id_persona=data["id_persona"],
            fecha_corte=data["fecha_corte"],
            monto_ingresado=data["monto_ingresado"],
            monto_aplicado=data["monto_aplicado"],
            remanente=data["remanente"],
            total_deuda_considerada=data["total_deuda_considerada"],
            detalle=[SimularPagoObligacionItem(**d) for d in data["detalle"]],
        )
    )


@router.post(
    "/api/v1/financiero/pagos",
    status_code=201,
    response_model=RegistrarPagoPersonaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def registrar_pago_persona(
    id_persona: int = Query(..., gt=0),
    request: RegistrarPagoPersonaRequest = ...,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> RegistrarPagoPersonaResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    repository = FinancieroRepository(db)
    service = RegistrarPagoPersonaService(repository=repository)

    try:
        result = service.execute(
            id_persona=id_persona,
            monto=request.monto,
            fecha_pago=request.fecha_pago,
            context=context,
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if "NOT_FOUND_PERSONA" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="La persona indicada no existe.",
                ).model_dump(),
            )
        if "MONTO_INVALIDO" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="MONTO_INVALIDO",
                    error_message="El monto debe ser mayor que cero.",
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo registrar el pago.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    data = result.data
    return RegistrarPagoPersonaResponse(
        data=RegistrarPagoPersonaData(
            id_persona=data["id_persona"],
            fecha_pago=data["fecha_pago"],
            monto_ingresado=data["monto_ingresado"],
            monto_aplicado=data["monto_aplicado"],
            remanente=data["remanente"],
            obligaciones_pagadas=[
                PagoObligacionResultado(**ob) for ob in data["obligaciones_pagadas"]
            ],
        )
    )


@router.post("/api/v1/financiero/inbox", status_code=204)
def financiero_inbox(
    request: InboxEventRequest,
    db: Session = Depends(get_db),
) -> None:
    InboxEventDispatcher(db).dispatch(
        event_type=request.event_type,
        payload=request.payload,
    )
