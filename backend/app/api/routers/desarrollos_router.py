from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.desarrollos import (
    DesarrolloBajaData,
    DesarrolloBajaResponse,
    DesarrolloCreateData,
    DesarrolloCreateRequest,
    DesarrolloCreateResponse,
    DesarrolloDetailData,
    DesarrolloDetailResponse,
    DesarrolloListItem,
    DesarrolloListResponse,
    DesarrolloUpdateData,
    DesarrolloUpdateRequest,
    DesarrolloUpdateResponse,
    ErrorResponse,
)
from app.application.common.commands import CommandContext
from app.application.desarrollos.commands.create_desarrollo import (
    CreateDesarrolloCommand,
)
from app.application.desarrollos.commands.delete_desarrollo import (
    DeleteDesarrolloCommand,
)
from app.application.desarrollos.commands.update_desarrollo import (
    UpdateDesarrolloCommand,
)
from app.application.desarrollos.services.create_desarrollo_service import (
    CreateDesarrolloService,
)
from app.application.desarrollos.services.delete_desarrollo_service import (
    DeleteDesarrolloService,
)
from app.application.desarrollos.services.get_desarrollo_service import (
    GetDesarrolloService,
)
from app.application.desarrollos.services.get_desarrollos_service import (
    GetDesarrollosService,
)
from app.application.desarrollos.services.update_desarrollo_service import (
    UpdateDesarrolloService,
)
from app.infrastructure.persistence.repositories.desarrollo_repository import (
    DesarrolloRepository,
)


router = APIRouter(tags=["Inmobiliario"])


class DesarrolloCommandContext(CommandContext):
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
    "/api/v1/desarrollos",
    status_code=201,
    response_model=DesarrolloCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_desarrollo(
    request: DesarrolloCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> DesarrolloCreateResponse | JSONResponse:
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

    context = DesarrolloCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreateDesarrolloCommand(
        context=context,
        codigo_desarrollo=request.codigo_desarrollo,
        nombre_desarrollo=request.nombre_desarrollo,
        descripcion=request.descripcion,
        estado_desarrollo=request.estado_desarrollo,
        observaciones=request.observaciones,
    )

    repository = DesarrolloRepository(db)
    service = CreateDesarrolloService(repository=repository)

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
            error_message="No se pudo crear el desarrollo.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DesarrolloCreateResponse(data=DesarrolloCreateData(**result.data))


@router.get(
    "/api/v1/desarrollos/{id_desarrollo}",
    response_model=DesarrolloDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_desarrollo(
    id_desarrollo: int,
    db: Session = Depends(get_db),
) -> DesarrolloDetailResponse | JSONResponse:
    repository = DesarrolloRepository(db)
    service = GetDesarrolloService(repository=repository)

    try:
        result = service.execute(id_desarrollo)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error_code = "NOT_FOUND" if "NOT_FOUND" in result.errors else "APPLICATION_ERROR"
        error_message = (
            "El desarrollo indicado no existe."
            if error_code == "NOT_FOUND"
            else "No se pudo obtener el desarrollo."
        )
        status_code = 404 if error_code == "NOT_FOUND" else 400
        error = ErrorResponse(
            error_code=error_code,
            error_message=error_message,
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=status_code, content=error.model_dump())

    return DesarrolloDetailResponse(data=DesarrolloDetailData(**result.data))


@router.get(
    "/api/v1/desarrollos",
    response_model=DesarrolloListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_desarrollos(
    db: Session = Depends(get_db),
) -> DesarrolloListResponse | JSONResponse:
    repository = DesarrolloRepository(db)
    service = GetDesarrollosService(repository=repository)

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
            error_message="No se pudieron obtener los desarrollos.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DesarrolloListResponse(
        data=[DesarrolloListItem(**item) for item in result.data]
    )


@router.put(
    "/api/v1/desarrollos/{id_desarrollo}",
    response_model=DesarrolloUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_desarrollo(
    id_desarrollo: int,
    request: DesarrolloUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> DesarrolloUpdateResponse | JSONResponse:
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

    context = DesarrolloCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdateDesarrolloCommand(
        context=context,
        id_desarrollo=id_desarrollo,
        if_match_version=parsed_if_match_version,
        codigo_desarrollo=request.codigo_desarrollo,
        nombre_desarrollo=request.nombre_desarrollo,
        descripcion=request.descripcion,
        estado_desarrollo=request.estado_desarrollo,
        observaciones=request.observaciones,
    )

    repository = DesarrolloRepository(db)
    service = UpdateDesarrolloService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_DESARROLLO" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El desarrollo indicado no existe.",
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
            error_message="No se pudo actualizar el desarrollo.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DesarrolloUpdateResponse(data=DesarrolloUpdateData(**result.data))


@router.patch(
    "/api/v1/desarrollos/{id_desarrollo}/baja",
    response_model=DesarrolloBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_desarrollo(
    id_desarrollo: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> DesarrolloBajaResponse | JSONResponse:
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

    context = DesarrolloCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeleteDesarrolloCommand(
        context=context,
        id_desarrollo=id_desarrollo,
        if_match_version=parsed_if_match_version,
    )

    repository = DesarrolloRepository(db)
    service = DeleteDesarrolloService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_DESARROLLO" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="El desarrollo indicado no existe.",
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
            error_message="No se pudo dar de baja el desarrollo.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return DesarrolloBajaResponse(data=DesarrolloBajaData(**result.data))
