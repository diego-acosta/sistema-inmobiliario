from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.financiero import (
    AplicacionItemData,
    AjusteIndexacionData,
    AjusteIndexacionRequest,
    AjusteIndexacionResponse,
    AnularEgresoProveedorFacturaServicioData,
    AnularEgresoProveedorFacturaServicioRequest,
    AnularEgresoProveedorFacturaServicioResponse,
    AnularLiquidacionRecuperoData,
    AnularLiquidacionRecuperoRequest,
    AnularLiquidacionRecuperoResponse,
    BonificacionIndexacionData,
    BonificacionIndexacionRequest,
    BonificacionIndexacionResponse,
    ComprobanteImpuestoCreateRequest,
    ComprobanteImpuestoData,
    ComprobanteImpuestoListResponse,
    ComprobanteImpuestoResponse,
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
    EgresoProveedorFacturaServicioData,
    EgresosProveedorFacturaServicioData,
    EgresosProveedorFacturaServicioResponse,
    EgresoProveedorFacturaServicioRequest,
    EgresoProveedorFacturaServicioResponse,
    EgresoImpuestoEmpresaData,
    EgresoImpuestoEmpresaRequest,
    EgresoImpuestoEmpresaResponse,
    ErrorResponse,
    EstadoCuentaData,
    EstadoCuentaPersonaData,
    EstadoCuentaPersonaObligacionItem,
    EstadoCuentaPersonaResumen,
    EstadoCuentaPersonaResponse,
    EstadoCuentaResponse,
    PagoObligacionResultado,
    PagoExternoFacturaServicioData,
    PagoExternoFacturaServicioRequest,
    PagoExternoFacturaServicioResponse,
    PagoAgrupadoPersonaItem,
    PagoAgrupadoPersonaListResponse,
    PagoAgrupadoDetalleResponse,
    PagoReciboData,
    PagoReciboResponse,
    RegistrarPagoPersonaData,
    RegistrarPagoPersonaRequest,
    RegistrarPagoPersonaResponse,
    RevertirPagoAgrupadoData,
    RevertirPagoAgrupadoRequest,
    RevertirPagoAgrupadoResponse,
    SimularPagoObligacionItem,
    SimularPagoPersonaData,
    SimularPagoPersonaRequest,
    SimularPagoPersonaResponse,
    ImputacionCreateRequest,
    ImputacionData,
    ImputacionResponse,
    InboxEventRequest,
    LiquidacionRecuperoFacturaServicioData,
    LiquidacionRecuperoDetalleData,
    LiquidacionRecuperoDetalleResponse,
    LiquidacionRecuperoFacturaServicioRequest,
    LiquidacionRecuperoFacturaServicioResponse,
    LiquidacionesRecuperoFacturaServicioListData,
    LiquidacionesRecuperoFacturaServicioListResponse,
    LiquidacionRecuperoFacturaServicioListItem,
    MaterializarFacturaServicioData,
    MaterializarFacturaServicioResponse,
    RegenerarCronogramaData,
    RegenerarCronogramaRequest,
    RegenerarCronogramaResponse,
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
from app.application.financiero.commands.create_comprobante_impuesto import (
    CreateComprobanteImpuestoCommand,
)
from app.application.financiero.commands.generar_mora_financiera import (
    GenerarMoraFinancieraCommand,
)
from app.application.financiero.services.create_relacion_generadora_service import (
    CreateRelacionGeneradoraService,
)
from app.application.financiero.services.create_comprobante_impuesto_service import (
    CreateComprobanteImpuestoService,
)
from app.application.financiero.services.get_comprobante_impuesto_service import (
    GetComprobanteImpuestoService,
)
from app.application.financiero.services.list_comprobantes_impuesto_service import (
    ListComprobantesImpuestoService,
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
from app.application.financiero.services.aplicar_ajuste_indexacion_service import (
    AplicarAjusteIndexacionService,
)
from app.application.financiero.services.aplicar_bonificacion_indexacion_service import (
    AplicarBonificacionIndexacionService,
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
from app.application.financiero.services.list_pagos_agrupados_persona_service import (
    ListPagosAgrupadosPersonaService,
)
from app.application.financiero.services.get_pago_agrupado_por_codigo_service import (
    GetPagoAgrupadoPorCodigoService,
)
from app.application.financiero.services.get_recibo_pago_agrupado_service import (
    GetReciboPagoAgrupadoService,
)
from app.application.financiero.services.revertir_pago_agrupado_service import (
    RevertirPagoAgrupadoService,
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
from app.application.financiero.services.materializar_factura_servicio_service import (
    MaterializarFacturaServicioService,
)
from app.application.financiero.services.registrar_pago_externo_factura_servicio_service import (
    RegistrarPagoExternoFacturaServicioService,
)
from app.application.financiero.services.registrar_egreso_proveedor_factura_servicio_service import (
    RegistrarEgresoProveedorFacturaServicioService,
)
from app.application.financiero.services.registrar_egreso_impuesto_empresa_service import (
    RegistrarEgresoImpuestoEmpresaService,
)
from app.application.financiero.services.consultar_egresos_proveedor_factura_servicio_service import (
    ConsultarEgresosProveedorFacturaServicioService,
)
from app.application.financiero.services.anular_egreso_proveedor_factura_servicio_service import (
    AnularEgresoProveedorFacturaServicioService,
)
from app.application.financiero.services.anular_liquidacion_recupero_service import (
    AnularLiquidacionRecuperoService,
)
from app.application.financiero.services.liquidar_recupero_factura_servicio_service import (
    LiquidarRecuperoFacturaServicioService,
)
from app.application.financiero.services.get_liquidacion_recupero_service import (
    GetLiquidacionRecuperoService,
)
from app.application.financiero.services.list_liquidaciones_recupero_factura_servicio_service import (
    ListLiquidacionesRecuperoFacturaServicioService,
)
from app.application.financiero.services.regenerar_cronograma_locativo_service import (
    RegenerarCronogramaLocativoService,
)
from app.infrastructure.persistence.repositories.financiero_repository import (
    FinancieroRepository,
)
from app.infrastructure.persistence.repositories.locativo_repository import (
    LocativoRepository,
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
    "/api/v1/comprobantes-impuesto",
    status_code=201,
    response_model=ComprobanteImpuestoResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_comprobante_impuesto(
    request: ComprobanteImpuestoCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ComprobanteImpuestoResponse | JSONResponse:
    context = _build_context(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    command = CreateComprobanteImpuestoCommand(
        context=context,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        organismo=request.organismo,
        tipo_impuesto=request.tipo_impuesto,
        partida_nomenclatura=request.partida_nomenclatura,
        numero_comprobante=request.numero_comprobante,
        periodo_desde=request.periodo_desde,
        periodo_hasta=request.periodo_hasta,
        fecha_emision=request.fecha_emision,
        fecha_vencimiento=request.fecha_vencimiento,
        importe_total=Decimal(str(request.importe_total)),
        modalidad_gestion_impuesto=request.modalidad_gestion_impuesto,
        observaciones=request.observaciones,
    )
    service = CreateComprobanteImpuestoService(FinancieroRepository(db))

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(error in result.errors for error in ("NOT_FOUND_INMUEBLE", "NOT_FOUND_UNIDAD_FUNCIONAL")):
            error = ErrorResponse(
                error_code="NOT_FOUND_OBJETO_INMOBILIARIO",
                error_message="El inmueble o la unidad funcional indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())
        if "COMPROBANTE_IMPUESTO_DUPLICADO" in result.errors:
            error = ErrorResponse(
                error_code="COMPROBANTE_IMPUESTO_DUPLICADO",
                error_message="Ya existe un comprobante activo para el organismo y numero indicados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())
        error = ErrorResponse(
            error_code="COMPROBANTE_IMPUESTO_INVALIDO",
            error_message="No se pudo crear el comprobante de impuesto.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ComprobanteImpuestoResponse(data=ComprobanteImpuestoData(**result.data))


@router.get(
    "/api/v1/comprobantes-impuesto/{id_comprobante_impuesto}",
    response_model=ComprobanteImpuestoResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_comprobante_impuesto(
    id_comprobante_impuesto: int,
    db: Session = Depends(get_db),
) -> ComprobanteImpuestoResponse | JSONResponse:
    service = GetComprobanteImpuestoService(FinancieroRepository(db))
    try:
        result = service.execute(id_comprobante_impuesto)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND_COMPROBANTE_IMPUESTO",
            error_message="El comprobante de impuesto indicado no existe.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return ComprobanteImpuestoResponse(data=ComprobanteImpuestoData(**result.data))


@router.get(
    "/api/v1/comprobantes-impuesto",
    response_model=ComprobanteImpuestoListResponse,
    responses={400: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def list_comprobantes_impuesto(
    db: Session = Depends(get_db),
) -> ComprobanteImpuestoListResponse | JSONResponse:
    service = ListComprobantesImpuestoService(FinancieroRepository(db))
    try:
        result = service.execute()
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener los comprobantes de impuesto.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ComprobanteImpuestoListResponse(
        data=[ComprobanteImpuestoData(**item) for item in result.data]
    )


@router.post(
    "/api/v1/financiero/comprobantes-impuesto/{id_comprobante_impuesto}/egresos",
    status_code=201,
    response_model=EgresoImpuestoEmpresaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def registrar_egreso_impuesto_empresa(
    id_comprobante_impuesto: int,
    request: EgresoImpuestoEmpresaRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> EgresoImpuestoEmpresaResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    service = RegistrarEgresoImpuestoEmpresaService(FinancieroRepository(db))

    try:
        result = service.execute(
            id_comprobante_impuesto=id_comprobante_impuesto,
            id_cuenta_financiera_origen=request.id_cuenta_financiera_origen,
            fecha_pago=request.fecha_pago,
            importe_pagado=request.importe_pagado,
            medio_pago=request.medio_pago,
            referencia_comprobante=request.referencia_comprobante,
            observaciones=request.observaciones,
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
        not_found_errors = {
            "COMPROBANTE_IMPUESTO_NOT_FOUND",
            "CUENTA_FINANCIERA_NOT_FOUND",
        }
        for code in not_found_errors:
            if code in result.errors:
                return JSONResponse(
                    status_code=404,
                    content=ErrorResponse(
                        error_code=code,
                        error_message="No se pudo registrar el egreso de impuesto.",
                        details={"errors": result.errors},
                    ).model_dump(),
                )

        conflict_errors = {
            "COMPROBANTE_IMPUESTO_ANULADO",
            "EGRESO_IMPUESTO_NO_APLICA_MODALIDAD",
            "CUENTA_FINANCIERA_INACTIVA",
            "EGRESO_SUPERA_IMPORTE_COMPROBANTE",
            "IDEMPOTENCY_PAYLOAD_CONFLICT",
        }
        for code in conflict_errors:
            if code in result.errors:
                return JSONResponse(
                    status_code=409,
                    content=ErrorResponse(
                        error_code=code,
                        error_message="No se pudo registrar el egreso de impuesto.",
                        details={"errors": result.errors},
                    ).model_dump(),
                )

        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=result.errors[0] if result.errors else "APPLICATION_ERROR",
                error_message="No se pudo registrar el egreso de impuesto.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    response = EgresoImpuestoEmpresaResponse(
        data=EgresoImpuestoEmpresaData(**result.data)
    )
    if result.data.get("resultado") == "YA_REGISTRADO":
        return JSONResponse(status_code=200, content=response.model_dump(mode="json"))
    return response


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
                    error_message=(
                        "tipo_origen debe ser VENTA, CONTRATO_ALQUILER "
                        "FACTURA_SERVICIO o LIQUIDACION_RECUPERO."
                    ),
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


@router.post(
    "/api/v1/financiero/facturas-servicio/{id_factura_servicio}/materializar",
    status_code=201,
    response_model=MaterializarFacturaServicioResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def materializar_factura_servicio(
    id_factura_servicio: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> MaterializarFacturaServicioResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    repository = FinancieroRepository(db)
    service = MaterializarFacturaServicioService(repository=repository)

    try:
        result = service.execute(id_factura_servicio, context)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if "NOT_FOUND_FACTURA_SERVICIO" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="La factura de servicio indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "FACTURA_SERVICIO_NO_ACTIVA" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="FACTURA_SERVICIO_NO_ACTIVA",
                    error_message="La factura de servicio no esta activa.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        conflict_errors = {
            "OBLIGADO_NO_RESUELTO",
            "PERIODO_FACTURA_REQUERIDO",
            "RESPONSABLE_SERVICIO_AMBIGUO",
            "FACTURA_CRUZA_CAMBIO_RESPONSABLE",
        }
        for code in conflict_errors:
            if code in result.errors:
                return JSONResponse(
                    status_code=409,
                    content=ErrorResponse(
                        error_code=code,
                        error_message="No se pudo resolver el responsable del servicio trasladado.",
                        details={"errors": result.errors},
                    ).model_dump(),
                )
        for error in result.errors:
            if error.startswith("NOT_FOUND_CONCEPTO:"):
                return JSONResponse(
                    status_code=409,
                    content=ErrorResponse(
                        error_code="NOT_FOUND_CONCEPTO",
                        error_message="No existe el concepto financiero requerido.",
                        details={"errors": result.errors},
                    ).model_dump(),
                )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo materializar la factura de servicio.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    response = MaterializarFacturaServicioResponse(
        data=MaterializarFacturaServicioData(**result.data)
    )
    if result.data["resultado"] == "YA_MATERIALIZADA":
        return JSONResponse(status_code=200, content=response.model_dump(mode="json"))
    return response


@router.post(
    "/api/v1/financiero/facturas-servicio/{id_factura_servicio}/pago-externo",
    status_code=201,
    response_model=PagoExternoFacturaServicioResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def registrar_pago_externo_factura_servicio(
    id_factura_servicio: int,
    request: PagoExternoFacturaServicioRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> PagoExternoFacturaServicioResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    repository = FinancieroRepository(db)
    service = RegistrarPagoExternoFacturaServicioService(repository=repository)

    try:
        result = service.execute(
            id_factura_servicio=id_factura_servicio,
            fecha_pago=request.fecha_pago,
            importe_pagado=request.importe_pagado,
            referencia_pago=request.referencia_pago,
            medio_pago_externo=request.medio_pago_externo,
            observaciones=request.observaciones,
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
        if "NOT_FOUND_FACTURA_SERVICIO" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="La factura de servicio indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        conflict_errors = {
            "FACTURA_SERVICIO_NO_ACTIVA",
            "FACTURA_SERVICIO_NO_MATERIALIZADA",
            "IDEMPOTENCY_PAYLOAD_CONFLICT",
            "PAGO_EXTERNO_REQUIERE_RESPONSABLE_UNICO",
            "SIN_SALDO_APLICABLE",
        }
        for code in conflict_errors:
            if code in result.errors:
                return JSONResponse(
                    status_code=409,
                    content=ErrorResponse(
                        error_code=code,
                        error_message="No se pudo registrar el pago externo informado.",
                        details={"errors": result.errors},
                    ).model_dump(),
                )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=result.errors[0] if result.errors else "APPLICATION_ERROR",
                error_message="No se pudo registrar el pago externo informado.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    response = PagoExternoFacturaServicioResponse(
        data=PagoExternoFacturaServicioData(**result.data)
    )
    if result.data.get("resultado") == "YA_REGISTRADO":
        return JSONResponse(status_code=200, content=response.model_dump(mode="json"))
    return response


@router.post(
    "/api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor",
    status_code=201,
    response_model=EgresoProveedorFacturaServicioResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def registrar_egreso_proveedor_factura_servicio(
    id_factura_servicio: int,
    request: EgresoProveedorFacturaServicioRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> EgresoProveedorFacturaServicioResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    repository = FinancieroRepository(db)
    service = RegistrarEgresoProveedorFacturaServicioService(repository=repository)

    try:
        result = service.execute(
            id_factura_servicio=id_factura_servicio,
            id_cuenta_financiera_origen=request.id_cuenta_financiera_origen,
            fecha_pago=request.fecha_pago,
            importe_pagado=request.importe_pagado,
            medio_pago=request.medio_pago,
            referencia_comprobante=request.referencia_comprobante,
            observaciones=request.observaciones,
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
        not_found_errors = {"FACTURA_SERVICIO_NOT_FOUND", "CUENTA_FINANCIERA_NOT_FOUND"}
        for code in not_found_errors:
            if code in result.errors:
                return JSONResponse(
                    status_code=404,
                    content=ErrorResponse(
                        error_code=code,
                        error_message="No se pudo registrar el egreso proveedor.",
                        details={"errors": result.errors},
                    ).model_dump(),
                )

        conflict_errors = {
            "FACTURA_SERVICIO_ANULADA",
            "CUENTA_FINANCIERA_INACTIVA",
            "EGRESO_SUPERA_IMPORTE_FACTURA",
            "IDEMPOTENCY_PAYLOAD_CONFLICT",
        }
        for code in conflict_errors:
            if code in result.errors:
                return JSONResponse(
                    status_code=409,
                    content=ErrorResponse(
                        error_code=code,
                        error_message="No se pudo registrar el egreso proveedor.",
                        details={"errors": result.errors},
                    ).model_dump(),
                )

        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=result.errors[0] if result.errors else "APPLICATION_ERROR",
                error_message="No se pudo registrar el egreso proveedor.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    response = EgresoProveedorFacturaServicioResponse(
        data=EgresoProveedorFacturaServicioData(**result.data)
    )
    if result.data.get("resultado") == "YA_REGISTRADO":
        return JSONResponse(status_code=200, content=response.model_dump(mode="json"))
    return response


@router.get(
    "/api/v1/financiero/facturas-servicio/{id_factura_servicio}/egresos-proveedor",
    response_model=EgresosProveedorFacturaServicioResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_egresos_proveedor_factura_servicio(
    id_factura_servicio: int,
    db: Session = Depends(get_db),
) -> EgresosProveedorFacturaServicioResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = ConsultarEgresosProveedorFacturaServicioService(repository=repository)

    try:
        result = service.execute(id_factura_servicio=id_factura_servicio)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if "FACTURA_SERVICIO_NOT_FOUND" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="FACTURA_SERVICIO_NOT_FOUND",
                    error_message="La factura de servicio indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=result.errors[0] if result.errors else "APPLICATION_ERROR",
                error_message="No se pudieron consultar los egresos proveedor.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return EgresosProveedorFacturaServicioResponse(
        data=EgresosProveedorFacturaServicioData(**result.data)
    )


@router.get(
    "/api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}",
    response_model=LiquidacionRecuperoDetalleResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_liquidacion_recupero(
    id_liquidacion_recupero: int,
    db: Session = Depends(get_db),
) -> LiquidacionRecuperoDetalleResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = GetLiquidacionRecuperoService(repository=repository)

    try:
        result = service.execute(id_liquidacion_recupero)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="LIQUIDACION_RECUPERO_NOT_FOUND",
                error_message="La liquidacion de recupero indicada no existe.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return LiquidacionRecuperoDetalleResponse(
        data=LiquidacionRecuperoDetalleData(**result.data)
    )


@router.get(
    "/api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero",
    response_model=LiquidacionesRecuperoFacturaServicioListResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_liquidaciones_recupero_factura_servicio(
    id_factura_servicio: int,
    db: Session = Depends(get_db),
) -> LiquidacionesRecuperoFacturaServicioListResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = ListLiquidacionesRecuperoFacturaServicioService(repository=repository)

    try:
        result = service.execute(id_factura_servicio)
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="FACTURA_SERVICIO_NOT_FOUND",
                error_message="La factura de servicio indicada no existe.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    items = [LiquidacionRecuperoFacturaServicioListItem(**item) for item in result.data]
    return LiquidacionesRecuperoFacturaServicioListResponse(
        data=LiquidacionesRecuperoFacturaServicioListData(
            id_factura_servicio=id_factura_servicio,
            items=items,
            total=len(items),
        )
    )


@router.post(
    "/api/v1/financiero/facturas-servicio/{id_factura_servicio}/liquidaciones-recupero",
    status_code=201,
    response_model=LiquidacionRecuperoFacturaServicioResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def liquidar_recupero_factura_servicio(
    id_factura_servicio: int,
    request: LiquidacionRecuperoFacturaServicioRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> LiquidacionRecuperoFacturaServicioResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    repository = FinancieroRepository(db)
    service = LiquidarRecuperoFacturaServicioService(repository=repository)

    try:
        result = service.execute(
            id_factura_servicio=id_factura_servicio,
            fecha_liquidacion=request.fecha_liquidacion,
            fecha_vencimiento=request.fecha_vencimiento,
            importe_total_recuperar=request.importe_total_recuperar,
            responsables=[r.model_dump() for r in request.responsables],
            observaciones=request.observaciones,
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
        if "FACTURA_SERVICIO_NOT_FOUND" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="FACTURA_SERVICIO_NOT_FOUND",
                    error_message="La factura de servicio indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "RESPONSABLE_PERSONA_NOT_FOUND" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="RESPONSABLE_PERSONA_NOT_FOUND",
                    error_message="Una persona responsable indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        conflict_errors = {
            "FACTURA_SERVICIO_ANULADA",
            "EGRESO_PROVEEDOR_REQUERIDO",
            "SIN_MONTO_EGRESADO_DISPONIBLE",
            "IMPORTE_RECUPERO_SUPERA_EGRESADO",
            "CONCEPTO_SERVICIO_RECUPERADO_NO_EXISTE",
            "IDEMPOTENCY_PAYLOAD_CONFLICT",
        }
        for code in conflict_errors:
            if code in result.errors:
                return JSONResponse(
                    status_code=409,
                    content=ErrorResponse(
                        error_code=code,
                        error_message="No se pudo liquidar el recupero de servicio.",
                        details={"errors": result.errors},
                    ).model_dump(),
                )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=result.errors[0] if result.errors else "APPLICATION_ERROR",
                error_message="No se pudo liquidar el recupero de servicio.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    response = LiquidacionRecuperoFacturaServicioResponse(
        data=LiquidacionRecuperoFacturaServicioData(**result.data)
    )
    if result.data.get("resultado") == "YA_EMITIDA":
        return JSONResponse(status_code=200, content=response.model_dump(mode="json"))
    return response


@router.patch(
    "/api/v1/financiero/liquidaciones-recupero/{id_liquidacion_recupero}/anular",
    response_model=AnularLiquidacionRecuperoResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def anular_liquidacion_recupero(
    id_liquidacion_recupero: int,
    request: AnularLiquidacionRecuperoRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> AnularLiquidacionRecuperoResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    repository = FinancieroRepository(db)
    service = AnularLiquidacionRecuperoService(repository=repository)

    try:
        result = service.execute(
            id_liquidacion_recupero=id_liquidacion_recupero,
            motivo=request.motivo,
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
        if "LIQUIDACION_RECUPERO_NOT_FOUND" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="LIQUIDACION_RECUPERO_NOT_FOUND",
                    error_message="La liquidacion de recupero indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "LIQUIDACION_RECUPERO_TIENE_OPERACIONES" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="LIQUIDACION_RECUPERO_TIENE_OPERACIONES",
                    error_message=(
                        "La liquidacion de recupero tiene operaciones financieras activas."
                    ),
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=result.errors[0] if result.errors else "APPLICATION_ERROR",
                error_message="No se pudo anular la liquidacion de recupero.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return AnularLiquidacionRecuperoResponse(
        data=AnularLiquidacionRecuperoData(**result.data)
    )


@router.patch(
    "/api/v1/financiero/egresos-proveedor-factura-servicio/{id_egreso}/anular",
    response_model=AnularEgresoProveedorFacturaServicioResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def anular_egreso_proveedor_factura_servicio(
    id_egreso: int,
    request: AnularEgresoProveedorFacturaServicioRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> AnularEgresoProveedorFacturaServicioResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    repository = FinancieroRepository(db)
    service = AnularEgresoProveedorFacturaServicioService(repository=repository)

    try:
        result = service.execute(
            id_egreso=id_egreso,
            motivo=request.motivo,
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
        if "EGRESO_PROVEEDOR_NOT_FOUND" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="EGRESO_PROVEEDOR_NOT_FOUND",
                    error_message="El egreso proveedor indicado no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "EGRESO_PROVEEDOR_CON_LIQUIDACION_RECUPERO" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="EGRESO_PROVEEDOR_CON_LIQUIDACION_RECUPERO",
                    error_message=(
                        "El egreso proveedor ya fue usado por una liquidacion de recupero activa."
                    ),
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code=result.errors[0] if result.errors else "APPLICATION_ERROR",
                error_message="No se pudo anular el egreso proveedor.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return AnularEgresoProveedorFacturaServicioResponse(
        data=AnularEgresoProveedorFacturaServicioData(**result.data)
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


@router.post(
    "/api/v1/financiero/obligaciones/{id_obligacion_financiera}/ajuste-indexacion",
    status_code=201,
    response_model=AjusteIndexacionResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def aplicar_ajuste_indexacion(
    id_obligacion_financiera: int,
    request: AjusteIndexacionRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> AjusteIndexacionResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    repository = FinancieroRepository(db)
    service = AplicarAjusteIndexacionService(repository=repository)

    try:
        result = service.execute(
            id_obligacion_financiera=id_obligacion_financiera,
            importe_ajuste=request.importe_ajuste,
            motivo=request.motivo,
            fecha_ajuste=request.fecha_ajuste,
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
        if "NOT_FOUND_OBLIGACION" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="La obligación financiera indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "NOT_FOUND_CONCEPTO_AJUSTE_INDEXACION" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND_CONCEPTO",
                    error_message="El concepto AJUSTE_INDEXACION no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "AJUSTE_INDEXACION_DUPLICADO" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="AJUSTE_INDEXACION_DUPLICADO",
                    error_message=(
                        "La obligación ya tiene un AJUSTE_INDEXACION activo."
                    ),
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "OBLIGACION_SIN_PAGOS_APLICADOS" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="OBLIGACION_SIN_PAGOS_APLICADOS",
                    error_message=(
                        "La obligación no tiene pagos aplicados; debe corregirse por regeneración."
                    ),
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "ESTADO_NO_ACEPTA_AJUSTE" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="ESTADO_NO_ACEPTA_AJUSTE",
                    error_message="La obligación no acepta ajuste de indexación.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo aplicar el ajuste de indexación.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return AjusteIndexacionResponse(data=AjusteIndexacionData(**result.data))


@router.post(
    "/api/v1/financiero/obligaciones/{id_obligacion_financiera}/bonificacion-indexacion",
    status_code=201,
    response_model=BonificacionIndexacionResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def aplicar_bonificacion_indexacion(
    id_obligacion_financiera: int,
    request: BonificacionIndexacionRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> BonificacionIndexacionResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    repository = FinancieroRepository(db)
    service = AplicarBonificacionIndexacionService(repository=repository)

    try:
        result = service.execute(
            id_obligacion_financiera=id_obligacion_financiera,
            importe_bonificacion=request.importe_bonificacion,
            motivo=request.motivo,
            fecha_bonificacion=request.fecha_bonificacion,
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
        if "NOT_FOUND_OBLIGACION" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="La obligación financiera indicada no existe.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "SIN_SALDO_APLICABLE" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="SIN_SALDO_APLICABLE",
                    error_message=(
                        "La obligación no tiene saldo aplicable para bonificación."
                    ),
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "BONIFICACION_OP_ID_CONFLICT" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="BONIFICACION_OP_ID_CONFLICT",
                    error_message="El X-Op-Id ya fue utilizado en otra bonificación.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "OBLIGACION_SIN_PAGOS_APLICADOS" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="OBLIGACION_SIN_PAGOS_APLICADOS",
                    error_message=(
                        "La obligación no tiene pagos aplicados; debe corregirse por regeneración."
                    ),
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "ESTADO_NO_ACEPTA_BONIFICACION" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="ESTADO_NO_ACEPTA_BONIFICACION",
                    error_message="La obligación no acepta bonificación de indexación.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo aplicar la bonificación de indexación.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return BonificacionIndexacionResponse(
        data=BonificacionIndexacionData(**result.data)
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
            grupos_deuda=data["grupos_deuda"],
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
        409: {"model": ErrorResponse},
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
        if "IDEMPOTENCY_PAYLOAD_CONFLICT" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="IDEMPOTENCY_PAYLOAD_CONFLICT",
                    error_message="El X-Op-Id ya fue utilizado con un payload distinto.",
                    details={"errors": result.errors},
                ).model_dump(),
            )
        if "PAGO_YA_REVERTIDO" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="PAGO_YA_REVERTIDO",
                    error_message="El X-Op-Id corresponde a un pago ya revertido.",
                    details={"errors": result.errors},
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
            uid_pago_grupo=data.get("uid_pago_grupo"),
            codigo_pago_grupo=data.get("codigo_pago_grupo"),
            monto_ingresado=data["monto_ingresado"],
            monto_aplicado=data["monto_aplicado"],
            remanente=data["remanente"],
            obligaciones_pagadas=[
                PagoObligacionResultado(**ob) for ob in data["obligaciones_pagadas"]
            ],
        )
    )


@router.get(
    "/api/v1/financiero/personas/{id_persona}/pagos",
    response_model=PagoAgrupadoPersonaListResponse,
)
def list_pagos_agrupados_persona(
    id_persona: int,
    db: Session = Depends(get_db),
) -> PagoAgrupadoPersonaListResponse:
    repository = FinancieroRepository(db)
    service = ListPagosAgrupadosPersonaService(repository=repository)
    result = service.execute(id_persona=id_persona)
    return PagoAgrupadoPersonaListResponse(
        data=[PagoAgrupadoPersonaItem(**r) for r in (result.data or [])]
    )


@router.get(
    "/api/v1/financiero/pagos/{codigo_pago_grupo}",
    response_model=PagoAgrupadoDetalleResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_pago_agrupado_por_codigo(
    codigo_pago_grupo: str,
    db: Session = Depends(get_db),
) -> PagoAgrupadoDetalleResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = GetPagoAgrupadoPorCodigoService(repository=repository)
    result = service.execute(codigo_pago_grupo=codigo_pago_grupo)
    if not result.success or result.data is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="NOT_FOUND",
                error_message="No existe pago para el codigo_pago_grupo indicado.",
            ).model_dump(),
        )
    return PagoAgrupadoDetalleResponse(data=result.data)


@router.get(
    "/api/v1/financiero/pagos/{codigo_pago_grupo}/recibo",
    response_model=PagoReciboResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_recibo_pago_agrupado(
    codigo_pago_grupo: str,
    db: Session = Depends(get_db),
) -> PagoReciboResponse | JSONResponse:
    repository = FinancieroRepository(db)
    service = GetReciboPagoAgrupadoService(repository=repository)
    result = service.execute(codigo_pago_grupo=codigo_pago_grupo)
    if not result.success or result.data is None:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error_code="NOT_FOUND",
                error_message="No existe pago para el codigo_pago_grupo indicado.",
            ).model_dump(),
        )
    return PagoReciboResponse(data=PagoReciboData(**result.data))


@router.post(
    "/api/v1/financiero/pagos/{codigo_pago_grupo}/revertir",
    response_model=RevertirPagoAgrupadoResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def revertir_pago_agrupado(
    codigo_pago_grupo: str,
    request: RevertirPagoAgrupadoRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> RevertirPagoAgrupadoResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    repository = FinancieroRepository(db)
    service = RevertirPagoAgrupadoService(repository=repository)

    try:
        result = service.execute(
            codigo_pago_grupo=codigo_pago_grupo,
            motivo=request.motivo,
            context=context,
        )
    except ValueError as exc:
        if str(exc) == "NOT_FOUND_PAGO":
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="No existe pago para el codigo_pago_grupo indicado.",
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message=str(exc),
            ).model_dump(),
        )
    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error_code="INTERNAL_ERROR", error_message=str(exc)
            ).model_dump(),
        )

    if not result.success or result.data is None:
        if "NOT_FOUND_PAGO" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="No existe pago para el codigo_pago_grupo indicado.",
                ).model_dump(),
            )
        if "MOTIVO_REQUERIDO" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="MOTIVO_REQUERIDO",
                    error_message="El motivo de reversión es obligatorio.",
                ).model_dump(),
            )
        if "PAGO_TIENE_OPERACIONES_POSTERIORES" in result.errors:
            return JSONResponse(
                status_code=409,
                content=ErrorResponse(
                    error_code="PAGO_TIENE_OPERACIONES_POSTERIORES",
                    error_message=(
                        "El pago agrupado tiene operaciones posteriores activas "
                        "sobre sus obligaciones o composiciones."
                    ),
                    details={"errors": result.errors},
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo revertir el pago.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return RevertirPagoAgrupadoResponse(
        data=RevertirPagoAgrupadoData(**result.data)
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


@router.post(
    "/api/v1/financiero/contratos-alquiler/{id_contrato_alquiler}/regenerar-cronograma",
    response_model=RegenerarCronogramaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def regenerar_cronograma_locativo(
    id_contrato_alquiler: int,
    request: RegenerarCronogramaRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> RegenerarCronogramaResponse | JSONResponse:
    context = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)

    fin_repo = FinancieroRepository(db)
    loc_repo = LocativoRepository(db)
    service = RegenerarCronogramaLocativoService(
        locativo_repository=loc_repo,
        financiero_repository=fin_repo,
    )

    try:
        result = service.execute(
            id_contrato_alquiler=id_contrato_alquiler,
            fecha_corte=request.fecha_corte,
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
        if "NOT_FOUND_CONTRATO" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="El contrato de alquiler indicado no existe.",
                ).model_dump(),
            )
        if "NOT_FOUND_RELACION_GENERADORA" in result.errors:
            return JSONResponse(
                status_code=404,
                content=ErrorResponse(
                    error_code="NOT_FOUND",
                    error_message="No existe cronograma generado para este contrato.",
                ).model_dump(),
            )
        if "SIN_LOCATARIO_PRINCIPAL" in result.errors:
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error_code="SIN_LOCATARIO_PRINCIPAL",
                    error_message="El contrato no tiene locatario principal vigente.",
                ).model_dump(),
            )
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="No se pudo regenerar el cronograma.",
                details={"errors": result.errors},
            ).model_dump(),
        )

    return RegenerarCronogramaResponse(data=RegenerarCronogramaData(**result.data))
