from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.servicios import (
    AsignacionServicioResponsableBajaData,
    AsignacionServicioResponsableBajaResponse,
    AsignacionServicioResponsableData,
    AsignacionServicioResponsableListResponse,
    AsignacionServicioResponsableRequest,
    AsignacionServicioResponsableResponse,
    ErrorResponse,
    FacturaServicioCreateRequest,
    FacturaServicioCreateResponse,
    FacturaServicioData,
    FacturaServicioDetailResponse,
    FacturaServicioListResponse,
    ServicioBajaData,
    ServicioBajaResponse,
    ServicioCreateData,
    ServicioCreateRequest,
    ServicioCreateResponse,
    ServicioDetailData,
    ServicioDetailResponse,
    ServicioInmuebleListItem,
    ServicioInmuebleListResponse,
    ServicioListItem,
    ServicioListResponse,
    ServicioUnidadFuncionalListItem,
    ServicioUnidadFuncionalListResponse,
    ServicioUpdateData,
    ServicioUpdateRequest,
    ServicioUpdateResponse,
)
from app.application.common.commands import CommandContext
from app.application.servicios.commands.asignacion_servicio_responsable import (
    CreateAsignacionServicioResponsableCommand,
    DeleteAsignacionServicioResponsableCommand,
    UpdateAsignacionServicioResponsableCommand,
)
from app.application.servicios.commands.create_factura_servicio import (
    CreateFacturaServicioCommand,
)
from app.application.servicios.commands.create_servicio import CreateServicioCommand
from app.application.servicios.commands.delete_servicio import DeleteServicioCommand
from app.application.servicios.commands.update_servicio import UpdateServicioCommand
from app.application.servicios.services.create_factura_servicio_service import (
    CreateFacturaServicioService,
)
from app.application.servicios.services.asignacion_servicio_responsable_service import (
    CreateAsignacionServicioResponsableService,
    DeleteAsignacionServicioResponsableService,
    GetAsignacionServicioResponsableService,
    GetAsignacionesServicioResponsableService,
    UpdateAsignacionServicioResponsableService,
)
from app.application.servicios.services.create_servicio_service import (
    CreateServicioService,
)
from app.application.servicios.services.delete_servicio_service import (
    DeleteServicioService,
)
from app.application.servicios.services.get_servicio_service import (
    GetServicioService,
)
from app.application.servicios.services.get_factura_servicio_service import (
    GetFacturaServicioService,
)
from app.application.servicios.services.get_facturas_servicio_service import (
    GetFacturasServicioService,
)
from app.application.servicios.services.get_servicio_inmuebles_service import (
    GetServicioInmueblesService,
)
from app.application.servicios.services.get_servicio_unidades_funcionales_service import (
    GetServicioUnidadesFuncionalesService,
)
from app.application.servicios.services.get_servicios_service import (
    GetServiciosService,
)
from app.application.servicios.services.update_servicio_service import (
    UpdateServicioService,
)
from app.infrastructure.persistence.repositories.servicio_repository import (
    ServicioRepository,
)


router = APIRouter(tags=["Inmobiliario"])


class ServicioCommandContext(CommandContext):
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


def _build_servicio_context(
    *,
    x_op_id: str | None,
    x_usuario_id: str | None,
    x_sucursal_id: str | None,
    x_instalacion_id: str | None,
) -> ServicioCommandContext:
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

    return ServicioCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )


@router.post(
    "/api/v1/servicios",
    status_code=201,
    response_model=ServicioCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_servicio(
    request: ServicioCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ServicioCreateResponse | JSONResponse:
    context = _build_servicio_context(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )

    command = CreateServicioCommand(
        context=context,
        codigo_servicio=request.codigo_servicio,
        nombre_servicio=request.nombre_servicio,
        descripcion=request.descripcion,
        estado_servicio=request.estado_servicio,
    )

    repository = ServicioRepository(db)
    service = CreateServicioService(repository=repository)

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
            error_message="No se pudo crear el servicio.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ServicioCreateResponse(data=ServicioCreateData(**result.data))


@router.post(
    "/api/v1/facturas-servicio",
    status_code=201,
    response_model=FacturaServicioCreateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_factura_servicio(
    request: FacturaServicioCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> FacturaServicioCreateResponse | JSONResponse:
    context = _build_servicio_context(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    command = CreateFacturaServicioCommand(
        context=context,
        id_servicio=request.id_servicio,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        proveedor=request.proveedor,
        numero_factura=request.numero_factura,
        fecha_emision=request.fecha_emision,
        fecha_vencimiento=request.fecha_vencimiento,
        periodo_desde=request.periodo_desde,
        periodo_hasta=request.periodo_hasta,
        importe_total=request.importe_total,
        observaciones=request.observaciones,
    )

    repository = ServicioRepository(db)
    service = CreateFacturaServicioService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_SERVICIO" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND_SERVICIO",
                error_message="El servicio indicado no existe o no esta activo.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "SERVICIO_NO_ASOCIADO" in result.errors:
            error = ErrorResponse(
                error_code="SERVICIO_NO_ASOCIADO",
                error_message="El servicio no esta asociado al inmueble o unidad funcional indicada.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        if "FACTURA_SERVICIO_DUPLICADA" in result.errors:
            error = ErrorResponse(
                error_code="FACTURA_SERVICIO_DUPLICADA",
                error_message="Ya existe una factura activa para el proveedor y numero indicados.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=409, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear la factura de servicio.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return FacturaServicioCreateResponse(data=FacturaServicioData(**result.data))


@router.get(
    "/api/v1/facturas-servicio/{id_factura_servicio}",
    response_model=FacturaServicioDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_factura_servicio(
    id_factura_servicio: int,
    db: Session = Depends(get_db),
) -> FacturaServicioDetailResponse | JSONResponse:
    repository = ServicioRepository(db)
    service = GetFacturaServicioService(repository=repository)

    try:
        result = service.execute(id_factura_servicio)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND_FACTURA_SERVICIO",
            error_message="La factura de servicio indicada no existe.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return FacturaServicioDetailResponse(data=FacturaServicioData(**result.data))


@router.get(
    "/api/v1/facturas-servicio",
    response_model=FacturaServicioListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_facturas_servicio(
    db: Session = Depends(get_db),
) -> FacturaServicioListResponse | JSONResponse:
    repository = ServicioRepository(db)
    service = GetFacturasServicioService(repository=repository)

    try:
        result = service.execute()
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las facturas de servicio.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return FacturaServicioListResponse(
        data=[FacturaServicioData(**item) for item in result.data]
    )


def _asignacion_error_response(result_errors: list[str]) -> JSONResponse:
    if any(error in result_errors for error in ("NOT_FOUND_SERVICIO", "NOT_FOUND_PERSONA")):
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="El servicio o la persona indicada no existe o no esta activa.",
            details={"errors": result_errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    if "NOT_FOUND_ASIGNACION_SERVICIO_RESPONSABLE" in result_errors:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="La asignacion indicada no existe.",
            details={"errors": result_errors},
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    if "CONCURRENCY_ERROR" in result_errors:
        error = ErrorResponse(
            error_code="CONCURRENCY_ERROR",
            error_message="If-Match-Version es requerido y debe coincidir con version_registro.",
            details={"errors": result_errors},
        )
        return JSONResponse(status_code=409, content=error.model_dump())

    if any(error in result_errors for error in ("SERVICIO_NO_ASOCIADO", "RESPONSABLE_SERVICIO_AMBIGUO")):
        error = ErrorResponse(
            error_code=result_errors[0],
            error_message="La asignacion de responsable de servicio es inconsistente.",
            details={"errors": result_errors},
        )
        return JSONResponse(status_code=409, content=error.model_dump())

    error = ErrorResponse(
        error_code="APPLICATION_ERROR",
        error_message="No se pudo procesar la asignacion de responsable de servicio.",
        details={"errors": result_errors},
    )
    return JSONResponse(status_code=400, content=error.model_dump())


@router.post(
    "/api/v1/asignaciones-servicio-responsable",
    status_code=201,
    response_model=AsignacionServicioResponsableResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def create_asignacion_servicio_responsable(
    request: AsignacionServicioResponsableRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> AsignacionServicioResponsableResponse | JSONResponse:
    context = _build_servicio_context(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    command = CreateAsignacionServicioResponsableCommand(
        context=context,
        id_servicio=request.id_servicio,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        id_persona=request.id_persona,
        porcentaje_responsabilidad=request.porcentaje_responsabilidad,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        estado_asignacion=request.estado_asignacion,
        observaciones=request.observaciones,
    )
    service = CreateAsignacionServicioResponsableService(repository=ServicioRepository(db))
    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())
    if not result.success or result.data is None:
        return _asignacion_error_response(result.errors)
    return AsignacionServicioResponsableResponse(data=AsignacionServicioResponsableData(**result.data))


@router.get(
    "/api/v1/asignaciones-servicio-responsable/{id_asignacion_servicio_responsable}",
    response_model=AsignacionServicioResponsableResponse,
    responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def get_asignacion_servicio_responsable(
    id_asignacion_servicio_responsable: int,
    db: Session = Depends(get_db),
) -> AsignacionServicioResponsableResponse | JSONResponse:
    service = GetAsignacionServicioResponsableService(repository=ServicioRepository(db))
    try:
        result = service.execute(id_asignacion_servicio_responsable)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())
    if not result.success or result.data is None:
        return _asignacion_error_response(result.errors)
    return AsignacionServicioResponsableResponse(data=AsignacionServicioResponsableData(**result.data))


@router.get(
    "/api/v1/asignaciones-servicio-responsable",
    response_model=AsignacionServicioResponsableListResponse,
    responses={500: {"model": ErrorResponse}},
)
def get_asignaciones_servicio_responsable(
    db: Session = Depends(get_db),
) -> AsignacionServicioResponsableListResponse | JSONResponse:
    service = GetAsignacionesServicioResponsableService(repository=ServicioRepository(db))
    try:
        result = service.execute()
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())
    return AsignacionServicioResponsableListResponse(
        data=[AsignacionServicioResponsableData(**item) for item in (result.data or [])]
    )


@router.put(
    "/api/v1/asignaciones-servicio-responsable/{id_asignacion_servicio_responsable}",
    response_model=AsignacionServicioResponsableResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def update_asignacion_servicio_responsable(
    id_asignacion_servicio_responsable: int,
    request: AsignacionServicioResponsableRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> AsignacionServicioResponsableResponse | JSONResponse:
    try:
        parsed_version = int(if_match_version) if if_match_version is not None else None
    except ValueError:
        parsed_version = None
    context = _build_servicio_context(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    command = UpdateAsignacionServicioResponsableCommand(
        context=context,
        id_asignacion_servicio_responsable=id_asignacion_servicio_responsable,
        if_match_version=parsed_version,
        id_servicio=request.id_servicio,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        id_persona=request.id_persona,
        porcentaje_responsabilidad=request.porcentaje_responsabilidad,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        estado_asignacion=request.estado_asignacion,
        observaciones=request.observaciones,
    )
    service = UpdateAsignacionServicioResponsableService(repository=ServicioRepository(db))
    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())
    if not result.success or result.data is None:
        return _asignacion_error_response(result.errors)
    return AsignacionServicioResponsableResponse(data=AsignacionServicioResponsableData(**result.data))


@router.patch(
    "/api/v1/asignaciones-servicio-responsable/{id_asignacion_servicio_responsable}/baja",
    response_model=AsignacionServicioResponsableBajaResponse,
    responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
)
def delete_asignacion_servicio_responsable(
    id_asignacion_servicio_responsable: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> AsignacionServicioResponsableBajaResponse | JSONResponse:
    try:
        parsed_version = int(if_match_version) if if_match_version is not None else None
    except ValueError:
        parsed_version = None
    context = _build_servicio_context(
        x_op_id=x_op_id,
        x_usuario_id=x_usuario_id,
        x_sucursal_id=x_sucursal_id,
        x_instalacion_id=x_instalacion_id,
    )
    command = DeleteAsignacionServicioResponsableCommand(
        context=context,
        id_asignacion_servicio_responsable=id_asignacion_servicio_responsable,
        if_match_version=parsed_version,
    )
    service = DeleteAsignacionServicioResponsableService(repository=ServicioRepository(db))
    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())
    if not result.success or result.data is None:
        return _asignacion_error_response(result.errors)
    return AsignacionServicioResponsableBajaResponse(
        data=AsignacionServicioResponsableBajaData(**result.data)
    )


@router.get(
    "/api/v1/servicios/{id_servicio}",
    response_model=ServicioDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_servicio(
    id_servicio: int,
    db: Session = Depends(get_db),
) -> ServicioDetailResponse | JSONResponse:
    repository = ServicioRepository(db)
    service = GetServicioService(repository=repository)

    try:
        result = service.execute(id_servicio)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error_code = "NOT_FOUND" if "NOT_FOUND" in result.errors else "APPLICATION_ERROR"
        error_message = (
            "El servicio indicado no existe."
            if error_code == "NOT_FOUND"
            else "No se pudo obtener el servicio."
        )
        status_code = 404 if error_code == "NOT_FOUND" else 400
        error = ErrorResponse(
            error_code=error_code,
            error_message=error_message,
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=status_code, content=error.model_dump())

    return ServicioDetailResponse(data=ServicioDetailData(**result.data))


@router.get(
    "/api/v1/servicios",
    response_model=ServicioListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_servicios(
    db: Session = Depends(get_db),
) -> ServicioListResponse | JSONResponse:
    repository = ServicioRepository(db)
    service = GetServiciosService(repository=repository)

    try:
        result = service.execute()
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener los servicios.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ServicioListResponse(data=[ServicioListItem(**item) for item in result.data])


@router.get(
    "/api/v1/servicios/{id_servicio}/inmuebles",
    response_model=ServicioInmuebleListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_servicio_inmuebles(
    id_servicio: int,
    db: Session = Depends(get_db),
) -> ServicioInmuebleListResponse | JSONResponse:
    repository = ServicioRepository(db)
    service = GetServicioInmueblesService(repository=repository)

    try:
        result = service.execute(id_servicio)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener los inmuebles del servicio.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ServicioInmuebleListResponse(
        data=[ServicioInmuebleListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/servicios/{id_servicio}/unidades-funcionales",
    response_model=ServicioUnidadFuncionalListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_servicio_unidades_funcionales(
    id_servicio: int,
    db: Session = Depends(get_db),
) -> ServicioUnidadFuncionalListResponse | JSONResponse:
    repository = ServicioRepository(db)
    service = GetServicioUnidadesFuncionalesService(repository=repository)

    try:
        result = service.execute(id_servicio)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las unidades funcionales del servicio.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ServicioUnidadFuncionalListResponse(
        data=[ServicioUnidadFuncionalListItem(**item) for item in result.data]
    )


@router.put(
    "/api/v1/servicios/{id_servicio}",
    response_model=ServicioUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_servicio(
    id_servicio: int,
    request: ServicioUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ServicioUpdateResponse | JSONResponse:
    id_instalacion: int | None = None
    op_id: UUID | None = None
    parsed_if_match_version: int | None = None

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

    if if_match_version is not None:
        try:
            parsed_if_match_version = int(if_match_version)
        except ValueError:
            parsed_if_match_version = None

    context_kwargs = {
        "actor_id": x_usuario_id,
        "metadata": {
            "x_op_id": x_op_id,
            "x_sucursal_id": x_sucursal_id,
            "x_instalacion_id": x_instalacion_id,
            "if_match_version": if_match_version,
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = ServicioCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdateServicioCommand(
        context=context,
        id_servicio=id_servicio,
        if_match_version=parsed_if_match_version,
        codigo_servicio=request.codigo_servicio,
        nombre_servicio=request.nombre_servicio,
        descripcion=request.descripcion,
        estado_servicio=request.estado_servicio,
    )

    repository = ServicioRepository(db)
    service = UpdateServicioService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_SERVICIO" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El servicio indicado no existe.",
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
            error_message="No se pudo actualizar el servicio.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ServicioUpdateResponse(data=ServicioUpdateData(**result.data))


@router.patch(
    "/api/v1/servicios/{id_servicio}/baja",
    response_model=ServicioBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_servicio(
    id_servicio: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ServicioBajaResponse | JSONResponse:
    id_instalacion: int | None = None
    op_id: UUID | None = None
    parsed_if_match_version: int | None = None

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

    if if_match_version is not None:
        try:
            parsed_if_match_version = int(if_match_version)
        except ValueError:
            parsed_if_match_version = None

    context_kwargs = {
        "actor_id": x_usuario_id,
        "metadata": {
            "x_op_id": x_op_id,
            "x_sucursal_id": x_sucursal_id,
            "x_instalacion_id": x_instalacion_id,
            "if_match_version": if_match_version,
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = ServicioCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeleteServicioCommand(
        context=context,
        id_servicio=id_servicio,
        if_match_version=parsed_if_match_version,
    )

    repository = ServicioRepository(db)
    service = DeleteServicioService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_SERVICIO" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El servicio indicado no existe.",
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
            error_message="No se pudo dar de baja el servicio.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ServicioBajaResponse(data=ServicioBajaData(**result.data))
