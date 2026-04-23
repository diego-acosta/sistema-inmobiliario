from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.servicios import (
    ErrorResponse,
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
from app.application.servicios.commands.create_servicio import CreateServicioCommand
from app.application.servicios.commands.delete_servicio import DeleteServicioCommand
from app.application.servicios.commands.update_servicio import UpdateServicioCommand
from app.application.servicios.services.create_servicio_service import (
    CreateServicioService,
)
from app.application.servicios.services.delete_servicio_service import (
    DeleteServicioService,
)
from app.application.servicios.services.get_servicio_service import (
    GetServicioService,
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

    context = ServicioCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
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
