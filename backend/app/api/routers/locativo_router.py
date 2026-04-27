from dataclasses import dataclass
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.locativo import (
    ReservaLocativaCreateRequest,
    ReservaLocativaData,
    ReservaLocativaResponse,
    ContratoAlquilerActivateData,
    ContratoAlquilerActivateResponse,
    ContratoAlquilerBajaData,
    ContratoAlquilerBajaResponse,
    ContratoAlquilerCancelData,
    ContratoAlquilerCancelResponse,
    ContratoAlquilerCreateData,
    ContratoAlquilerCreateRequest,
    ContratoAlquilerCreateResponse,
    ContratoAlquilerFinalizeData,
    ContratoAlquilerFinalizeResponse,
    ContratoAlquilerGetData,
    ContratoAlquilerGetResponse,
    ContratoAlquilerListData,
    ContratoAlquilerListItemData,
    ContratoAlquilerListResponse,
    CondicionEconomicaAlquilerCreateRequest,
    CondicionEconomicaAlquilerCerrarVigenciaRequest,
    CondicionEconomicaAlquilerData,
    CondicionEconomicaAlquilerCreateResponse,
    CondicionEconomicaAlquilerListData,
    CondicionEconomicaAlquilerListResponse,
    ErrorResponse,
)
from app.application.common.commands import CommandContext
from app.application.locativo.commands.create_contrato_alquiler import (
    CreateContratoAlquilerCommand,
    CreateContratoAlquilerObjetoCommand,
)
from app.application.locativo.commands.update_contrato_alquiler import (
    UpdateContratoAlquilerCommand,
    UpdateContratoAlquilerObjetoCommand,
)
from app.application.locativo.services.update_contrato_alquiler_service import (
    UpdateContratoAlquilerService,
)
from app.application.locativo.services.create_contrato_alquiler_service import (
    CreateContratoAlquilerService,
)
from app.application.locativo.services.get_contrato_alquiler_service import (
    GetContratoAlquilerService,
)
from app.application.locativo.services.activate_contrato_alquiler_service import (
    ActivateContratoAlquilerService,
)
from app.application.locativo.commands.activate_contrato_alquiler import (
    ActivateContratoAlquilerCommand,
)
from app.application.locativo.services.list_contratos_alquiler_service import (
    ListContratosAlquilerService,
)
from app.application.locativo.commands.create_reserva_locativa import (
    CreateReservaLocativaCommand,
    CreateReservaLocativaObjetoCommand,
)
from app.application.locativo.services.create_reserva_locativa_service import (
    CreateReservaLocativaService,
)
from app.application.locativo.services.get_reserva_locativa_service import (
    GetReservaLocativaService,
)
from app.application.locativo.commands.confirmar_reserva_locativa import (
    ConfirmarReservaLocativaCommand,
)
from app.application.locativo.services.confirmar_reserva_locativa_service import (
    ConfirmarReservaLocativaService,
)
from app.application.locativo.commands.cancel_reserva_locativa import (
    CancelReservaLocativaCommand,
)
from app.application.locativo.services.cancel_reserva_locativa_service import (
    CancelReservaLocativaService,
)
from app.application.locativo.commands.create_condicion_economica_alquiler import (
    CreateCondicionEconomicaAlquilerCommand,
)
from app.application.locativo.services.create_condicion_economica_alquiler_service import (
    CreateCondicionEconomicaAlquilerService,
)
from app.application.locativo.services.list_condiciones_economicas_alquiler_service import (
    ListCondicionesEconomicasAlquilerService,
)
from app.application.locativo.commands.cerrar_vigencia_condicion_economica_alquiler import (
    CerrarVigenciaCondicionEconomicaAlquilerCommand,
)
from app.application.locativo.services.cerrar_vigencia_condicion_economica_alquiler_service import (
    CerrarVigenciaCondicionEconomicaAlquilerService,
)
from app.application.locativo.commands.cancel_contrato_alquiler import (
    CancelContratoAlquilerCommand,
)
from app.application.locativo.services.cancel_contrato_alquiler_service import (
    CancelContratoAlquilerService,
)
from app.application.locativo.commands.finalize_contrato_alquiler import (
    FinalizeContratoAlquilerCommand,
)
from app.application.locativo.services.finalize_contrato_alquiler_service import (
    FinalizeContratoAlquilerService,
)
from app.application.locativo.commands.delete_contrato_alquiler import (
    DeleteContratoAlquilerCommand,
)
from app.application.locativo.services.delete_contrato_alquiler_service import (
    DeleteContratoAlquilerService,
)
from app.infrastructure.persistence.repositories.locativo_repository import (
    LocativoRepository,
)


router = APIRouter(tags=["Locativo"])


@dataclass(slots=True)
class LocativoCommandContext(CommandContext):
    id_instalacion: int | None = None
    op_id: UUID | None = None


@router.post(
    "/api/v1/contratos-alquiler",
    status_code=201,
    response_model=ContratoAlquilerCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_contrato_alquiler(
    request: ContratoAlquilerCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ContratoAlquilerCreateResponse | JSONResponse:
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

    context = LocativoCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreateContratoAlquilerCommand(
        context=context,
        codigo_contrato=request.codigo_contrato,
        fecha_inicio=request.fecha_inicio,
        fecha_fin=request.fecha_fin,
        observaciones=request.observaciones,
        objetos=[
            CreateContratoAlquilerObjetoCommand(
                id_inmueble=item.id_inmueble,
                id_unidad_funcional=item.id_unidad_funcional,
                observaciones=item.observaciones,
            )
            for item in request.objetos
        ],
    )

    repository = LocativoRepository(db)
    service = CreateContratoAlquilerService(repository=repository)

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
            )
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El objeto inmobiliario indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear el contrato de alquiler.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ContratoAlquilerCreateResponse(data=ContratoAlquilerCreateData(**result.data))


@router.get(
    "/api/v1/contratos-alquiler/{id_contrato_alquiler}",
    response_model=ContratoAlquilerGetResponse,
    responses={
        404: {"model": ErrorResponse},
    },
)
def get_contrato_alquiler(
    id_contrato_alquiler: int,
    db: Session = Depends(get_db),
) -> ContratoAlquilerGetResponse | JSONResponse:
    repository = LocativoRepository(db)
    service = GetContratoAlquilerService(repository=repository)
    result = service.execute(id_contrato_alquiler)

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="El contrato de alquiler indicado no existe.",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return ContratoAlquilerGetResponse(data=ContratoAlquilerGetData(**result.data))


@router.put(
    "/api/v1/contratos-alquiler/{id_contrato_alquiler}",
    response_model=ContratoAlquilerCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_contrato_alquiler(
    id_contrato_alquiler: int,
    request: ContratoAlquilerCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ContratoAlquilerCreateResponse | JSONResponse:
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
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = LocativoCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdateContratoAlquilerCommand(
        context=context,
        id_contrato_alquiler=id_contrato_alquiler,
        if_match_version=parsed_if_match_version,
        codigo_contrato=request.codigo_contrato,
        fecha_inicio=request.fecha_inicio,
        fecha_fin=request.fecha_fin,
        observaciones=request.observaciones,
        objetos=[
            UpdateContratoAlquilerObjetoCommand(
                id_inmueble=item.id_inmueble,
                id_unidad_funcional=item.id_unidad_funcional,
                observaciones=item.observaciones,
            )
            for item in request.objetos
        ],
    )

    repository = LocativoRepository(db)
    service = UpdateContratoAlquilerService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_CONTRATO_ALQUILER" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El contrato de alquiler indicado no existe.",
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

        if "INVALID_CONTRATO_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo un contrato en estado borrador puede modificarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        if any(
            e in result.errors
            for e in ("NOT_FOUND_INMUEBLE", "NOT_FOUND_UNIDAD_FUNCIONAL")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El objeto inmobiliario indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo modificar el contrato de alquiler.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ContratoAlquilerCreateResponse(data=ContratoAlquilerCreateData(**result.data))


@router.get(
    "/api/v1/contratos-alquiler",
    response_model=ContratoAlquilerListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_contratos_alquiler(
    codigo_contrato: str | None = Query(default=None),
    estado_contrato: str | None = Query(default=None),
    id_inmueble: int | None = Query(default=None),
    id_unidad_funcional: int | None = Query(default=None),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    limit: int = Query(default=50, ge=0, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ContratoAlquilerListResponse | JSONResponse:
    repository = LocativoRepository(db)
    service = ListContratosAlquilerService(repository=repository)

    try:
        result = service.execute(
            codigo_contrato=codigo_contrato,
            estado_contrato=estado_contrato,
            id_inmueble=id_inmueble,
            id_unidad_funcional=id_unidad_funcional,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
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
            error_message="No se pudieron obtener los contratos de alquiler.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ContratoAlquilerListResponse(
        data=ContratoAlquilerListData(
            items=[ContratoAlquilerListItemData(**item) for item in result.data["items"]],
            total=result.data["total"],
        )
    )


@router.post(
    "/api/v1/contratos-alquiler/{id_contrato_alquiler}/condiciones-economicas-alquiler",
    status_code=201,
    response_model=CondicionEconomicaAlquilerCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_condicion_economica_alquiler(
    id_contrato_alquiler: int,
    request: CondicionEconomicaAlquilerCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> CondicionEconomicaAlquilerCreateResponse | JSONResponse:
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

    context = LocativoCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreateCondicionEconomicaAlquilerCommand(
        context=context,
        id_contrato_alquiler=id_contrato_alquiler,
        monto_base=request.monto_base,
        periodicidad=request.periodicidad,
        moneda=request.moneda,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = LocativoRepository(db)
    service = CreateCondicionEconomicaAlquilerService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_CONTRATO_ALQUILER" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El contrato de alquiler indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear la condicion economica.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return CondicionEconomicaAlquilerCreateResponse(
        data=CondicionEconomicaAlquilerData(**result.data)
    )


@router.get(
    "/api/v1/contratos-alquiler/{id_contrato_alquiler}/condiciones-economicas-alquiler",
    response_model=CondicionEconomicaAlquilerListResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def list_condiciones_economicas_alquiler(
    id_contrato_alquiler: int,
    vigente: bool | None = Query(default=None),
    fecha_desde: date | None = Query(default=None),
    fecha_hasta: date | None = Query(default=None),
    moneda: str | None = Query(default=None),
    periodicidad: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> CondicionEconomicaAlquilerListResponse | JSONResponse:
    repository = LocativoRepository(db)
    service = ListCondicionesEconomicasAlquilerService(repository=repository)

    try:
        result = service.execute(
            id_contrato_alquiler=id_contrato_alquiler,
            vigente=vigente,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta,
            moneda=moneda,
            periodicidad=periodicidad,
        )
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_CONTRATO_ALQUILER" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El contrato de alquiler indicado no existe.",
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las condiciones economicas.",
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    return CondicionEconomicaAlquilerListResponse(
        data=CondicionEconomicaAlquilerListData(
            items=[CondicionEconomicaAlquilerData(**item) for item in result.data["items"]],
            total=result.data["total"],
        )
    )


@router.patch(
    "/api/v1/contratos-alquiler/{id_contrato_alquiler}/condiciones-economicas-alquiler/{id_condicion_economica}/cerrar-vigencia",
    response_model=CondicionEconomicaAlquilerCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def cerrar_vigencia_condicion_economica_alquiler(
    id_contrato_alquiler: int,
    id_condicion_economica: int,
    request: CondicionEconomicaAlquilerCerrarVigenciaRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> CondicionEconomicaAlquilerCreateResponse | JSONResponse:
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
        },
    }
    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = LocativoCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CerrarVigenciaCondicionEconomicaAlquilerCommand(
        context=context,
        id_contrato_alquiler=id_contrato_alquiler,
        id_condicion_economica=id_condicion_economica,
        if_match_version=parsed_if_match_version,
        fecha_hasta=request.fecha_hasta,
    )

    repository = LocativoRepository(db)
    service = CerrarVigenciaCondicionEconomicaAlquilerService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_CONTRATO_ALQUILER" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El contrato de alquiler indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        if "NOT_FOUND_CONDICION_ECONOMICA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La condicion economica indicada no existe.",
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
            error_message="No se pudo cerrar la vigencia de la condicion economica.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return CondicionEconomicaAlquilerCreateResponse(
        data=CondicionEconomicaAlquilerData(**result.data)
    )


@router.patch(
    "/api/v1/contratos-alquiler/{id_contrato_alquiler}/activar",
    response_model=ContratoAlquilerActivateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def activate_contrato_alquiler(
    id_contrato_alquiler: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ContratoAlquilerActivateResponse | JSONResponse:
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
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = LocativoCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = ActivateContratoAlquilerCommand(
        context=context,
        id_contrato_alquiler=id_contrato_alquiler,
        if_match_version=parsed_if_match_version,
    )

    repository = LocativoRepository(db)
    service = ActivateContratoAlquilerService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_CONTRATO_ALQUILER" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El contrato de alquiler indicado no existe.",
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

        if "INVALID_CONTRATO_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo un contrato en estado borrador puede activarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo activar el contrato de alquiler.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ContratoAlquilerActivateResponse(
        data=ContratoAlquilerActivateData(**result.data)
    )


@router.patch(
    "/api/v1/contratos-alquiler/{id_contrato_alquiler}/finalizar",
    response_model=ContratoAlquilerFinalizeResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def finalize_contrato_alquiler(
    id_contrato_alquiler: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ContratoAlquilerFinalizeResponse | JSONResponse:
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
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = LocativoCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = FinalizeContratoAlquilerCommand(
        context=context,
        id_contrato_alquiler=id_contrato_alquiler,
        if_match_version=parsed_if_match_version,
    )

    repository = LocativoRepository(db)
    service = FinalizeContratoAlquilerService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_CONTRATO_ALQUILER" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El contrato de alquiler indicado no existe.",
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

        if "INVALID_CONTRATO_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo un contrato en estado activo puede finalizarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo finalizar el contrato de alquiler.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ContratoAlquilerFinalizeResponse(
        data=ContratoAlquilerFinalizeData(**result.data)
    )


@router.patch(
    "/api/v1/contratos-alquiler/{id_contrato_alquiler}/cancelar",
    response_model=ContratoAlquilerCancelResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def cancel_contrato_alquiler(
    id_contrato_alquiler: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ContratoAlquilerCancelResponse | JSONResponse:
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
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = LocativoCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CancelContratoAlquilerCommand(
        context=context,
        id_contrato_alquiler=id_contrato_alquiler,
        if_match_version=parsed_if_match_version,
    )

    repository = LocativoRepository(db)
    service = CancelContratoAlquilerService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_CONTRATO_ALQUILER" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El contrato de alquiler indicado no existe.",
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

        if "INVALID_CONTRATO_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo un contrato en estado borrador puede cancelarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo cancelar el contrato de alquiler.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ContratoAlquilerCancelResponse(
        data=ContratoAlquilerCancelData(**result.data)
    )


@router.patch(
    "/api/v1/contratos-alquiler/{id_contrato_alquiler}/baja",
    response_model=ContratoAlquilerBajaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_contrato_alquiler(
    id_contrato_alquiler: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ContratoAlquilerBajaResponse | JSONResponse:
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
        },
    }

    if op_id is not None:
        context_kwargs["request_id"] = op_id

    context = LocativoCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeleteContratoAlquilerCommand(
        context=context,
        id_contrato_alquiler=id_contrato_alquiler,
        if_match_version=parsed_if_match_version,
    )

    repository = LocativoRepository(db)
    service = DeleteContratoAlquilerService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_CONTRATO_ALQUILER" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El contrato de alquiler indicado no existe.",
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

        if "INVALID_CONTRATO_STATE" in result.errors:
            error = ErrorResponse(
                error_code="APPLICATION_ERROR",
                error_message="Solo un contrato en estado borrador puede darse de baja.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo dar de baja el contrato de alquiler.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ContratoAlquilerBajaResponse(
        data=ContratoAlquilerBajaData(**result.data)
    )


# ── reservas_locativas ────────────────────────────────────────────────────────

def _build_context(
    x_op_id: str | None,
    x_usuario_id: str | None,
    x_sucursal_id: str | None,
    x_instalacion_id: str | None,
) -> tuple[LocativoCommandContext, UUID | None, int | None]:
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
    context_kwargs: dict = {
        "actor_id": x_usuario_id,
        "metadata": {
            "x_op_id": x_op_id,
            "x_sucursal_id": x_sucursal_id,
            "x_instalacion_id": x_instalacion_id,
        },
    }
    if op_id is not None:
        context_kwargs["request_id"] = op_id
    ctx = LocativoCommandContext(id_instalacion=id_instalacion, op_id=op_id, **context_kwargs)
    return ctx, op_id, id_instalacion


@router.post(
    "/api/v1/reservas-locativas",
    status_code=201,
    response_model=ReservaLocativaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_reserva_locativa(
    request: ReservaLocativaCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> ReservaLocativaResponse | JSONResponse:
    context, _, _ = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)

    command = CreateReservaLocativaCommand(
        context=context,
        codigo_reserva=request.codigo_reserva,
        fecha_reserva=request.fecha_reserva,
        fecha_vencimiento=request.fecha_vencimiento,
        observaciones=request.observaciones,
        objetos=[
            CreateReservaLocativaObjetoCommand(
                id_inmueble=o.id_inmueble,
                id_unidad_funcional=o.id_unidad_funcional,
                observaciones=o.observaciones,
            )
            for o in request.objetos
        ],
    )

    repository = LocativoRepository(db)
    service = CreateReservaLocativaService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if any(e in result.errors for e in ("NOT_FOUND_INMUEBLE", "NOT_FOUND_UNIDAD_FUNCIONAL")):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El objeto inmobiliario indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear la reserva locativa.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ReservaLocativaResponse(data=ReservaLocativaData(**result.data))


@router.get(
    "/api/v1/reservas-locativas/{id_reserva_locativa}",
    response_model=ReservaLocativaResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_reserva_locativa(
    id_reserva_locativa: int,
    db: Session = Depends(get_db),
) -> ReservaLocativaResponse | JSONResponse:
    repository = LocativoRepository(db)
    service = GetReservaLocativaService(repository=repository)
    result = service.execute(id_reserva_locativa)

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="NOT_FOUND",
            error_message="La reserva locativa indicada no existe.",
        )
        return JSONResponse(status_code=404, content=error.model_dump())

    return ReservaLocativaResponse(data=ReservaLocativaData(**result.data))


@router.patch(
    "/api/v1/reservas-locativas/{id_reserva_locativa}/confirmar",
    response_model=ReservaLocativaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def confirmar_reserva_locativa(
    id_reserva_locativa: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ReservaLocativaResponse | JSONResponse:
    context, _, _ = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    parsed_version: int | None = None
    if if_match_version is not None:
        try:
            parsed_version = int(if_match_version)
        except ValueError:
            pass

    command = ConfirmarReservaLocativaCommand(
        context=context,
        id_reserva_locativa=id_reserva_locativa,
        if_match_version=parsed_version,
    )

    repository = LocativoRepository(db)
    service = ConfirmarReservaLocativaService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_RESERVA_LOCATIVA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La reserva locativa indicada no existe.",
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
                error_message="Solo una reserva en estado pendiente puede confirmarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo confirmar la reserva locativa.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ReservaLocativaResponse(data=ReservaLocativaData(**result.data))


@router.patch(
    "/api/v1/reservas-locativas/{id_reserva_locativa}/cancelar",
    response_model=ReservaLocativaResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def cancel_reserva_locativa(
    id_reserva_locativa: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> ReservaLocativaResponse | JSONResponse:
    context, _, _ = _build_context(x_op_id, x_usuario_id, x_sucursal_id, x_instalacion_id)
    parsed_version: int | None = None
    if if_match_version is not None:
        try:
            parsed_version = int(if_match_version)
        except ValueError:
            pass

    command = CancelReservaLocativaCommand(
        context=context,
        id_reserva_locativa=id_reserva_locativa,
        if_match_version=parsed_version,
    )

    repository = LocativoRepository(db)
    service = CancelReservaLocativaService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(error_code="INTERNAL_ERROR", error_message=str(exc))
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_RESERVA_LOCATIVA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La reserva locativa indicada no existe.",
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
                error_message="Solo una reserva en estado activo puede cancelarse.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=400, content=error.model_dump())
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo cancelar la reserva locativa.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return ReservaLocativaResponse(data=ReservaLocativaData(**result.data))

