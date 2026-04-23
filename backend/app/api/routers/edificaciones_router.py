from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.edificaciones import (
    EdificacionBajaData,
    EdificacionBajaResponse,
    EdificacionCreateData,
    EdificacionCreateRequest,
    EdificacionCreateResponse,
    EdificacionDetailData,
    EdificacionDetailResponse,
    EdificacionListItem,
    EdificacionListResponse,
    EdificacionUpdateData,
    EdificacionUpdateRequest,
    EdificacionUpdateResponse,
    ErrorResponse,
)
from app.application.common.commands import CommandContext
from app.application.edificaciones.commands.create_edificacion import (
    CreateEdificacionCommand,
)
from app.application.edificaciones.commands.delete_edificacion import (
    DeleteEdificacionCommand,
)
from app.application.edificaciones.commands.update_edificacion import (
    UpdateEdificacionCommand,
)
from app.application.edificaciones.services.create_edificacion_service import (
    CreateEdificacionService,
)
from app.application.edificaciones.services.delete_edificacion_service import (
    DeleteEdificacionService,
)
from app.application.edificaciones.services.get_edificaciones_by_inmueble_service import (
    GetEdificacionesByInmuebleService,
)
from app.application.edificaciones.services.get_edificaciones_service import (
    GetEdificacionesService,
)
from app.application.edificaciones.services.get_edificaciones_by_unidad_funcional_service import (
    GetEdificacionesByUnidadFuncionalService,
)
from app.application.edificaciones.services.get_edificacion_service import (
    GetEdificacionService,
)
from app.application.edificaciones.services.update_edificacion_service import (
    UpdateEdificacionService,
)
from app.infrastructure.persistence.repositories.edificacion_repository import (
    EdificacionRepository,
)


router = APIRouter(tags=["Inmobiliario"])


class EdificacionCommandContext(CommandContext):
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
    "/api/v1/edificaciones",
    status_code=201,
    response_model=EdificacionCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_edificacion(
    request: EdificacionCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> EdificacionCreateResponse | JSONResponse:
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

    context = EdificacionCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreateEdificacionCommand(
        context=context,
        id_inmueble=request.id_inmueble,
        id_unidad_funcional=request.id_unidad_funcional,
        descripcion=request.descripcion,
        tipo_edificacion=request.tipo_edificacion,
        superficie=request.superficie,
        observaciones=request.observaciones,
    )

    repository = EdificacionRepository(db)
    service = CreateEdificacionService(repository=repository)

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

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear la edificacion.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return EdificacionCreateResponse(data=EdificacionCreateData(**result.data))


@router.get(
    "/api/v1/edificaciones/{id_edificacion}",
    response_model=EdificacionDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_edificacion(
    id_edificacion: int,
    db: Session = Depends(get_db),
) -> EdificacionDetailResponse | JSONResponse:
    repository = EdificacionRepository(db)
    service = GetEdificacionService(repository=repository)

    try:
        result = service.execute(id_edificacion)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error_code = "NOT_FOUND" if "NOT_FOUND" in result.errors else "APPLICATION_ERROR"
        error_message = (
            "La edificacion indicada no existe."
            if error_code == "NOT_FOUND"
            else "No se pudo obtener la edificacion."
        )
        status_code = 404 if error_code == "NOT_FOUND" else 400
        error = ErrorResponse(
            error_code=error_code,
            error_message=error_message,
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=status_code, content=error.model_dump())

    return EdificacionDetailResponse(data=EdificacionDetailData(**result.data))


@router.get(
    "/api/v1/edificaciones",
    response_model=EdificacionListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_edificaciones(
    db: Session = Depends(get_db),
) -> EdificacionListResponse | JSONResponse:
    repository = EdificacionRepository(db)
    service = GetEdificacionesService(repository=repository)

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
            error_message="No se pudieron obtener las edificaciones.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return EdificacionListResponse(
        data=[EdificacionListItem(**item) for item in result.data]
    )


@router.put(
    "/api/v1/edificaciones/{id_edificacion}",
    response_model=EdificacionUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_edificacion(
    id_edificacion: int,
    request: EdificacionUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> EdificacionUpdateResponse | JSONResponse:
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

    context = EdificacionCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdateEdificacionCommand(
        context=context,
        id_edificacion=id_edificacion,
        if_match_version=parsed_if_match_version,
        descripcion=request.descripcion,
        tipo_edificacion=request.tipo_edificacion,
        superficie=request.superficie,
        observaciones=request.observaciones,
    )

    repository = EdificacionRepository(db)
    service = UpdateEdificacionService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_EDIFICACION" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La edificacion indicada no existe.",
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
            error_message="No se pudo actualizar la edificacion.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return EdificacionUpdateResponse(data=EdificacionUpdateData(**result.data))


@router.patch(
    "/api/v1/edificaciones/{id_edificacion}/baja",
    response_model=EdificacionBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_edificacion(
    id_edificacion: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> EdificacionBajaResponse | JSONResponse:
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

    context = EdificacionCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeleteEdificacionCommand(
        context=context,
        id_edificacion=id_edificacion,
        if_match_version=parsed_if_match_version,
    )

    repository = EdificacionRepository(db)
    service = DeleteEdificacionService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_EDIFICACION" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La edificacion indicada no existe.",
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
            error_message="No se pudo dar de baja la edificacion.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return EdificacionBajaResponse(data=EdificacionBajaData(**result.data))


@router.get(
    "/api/v1/inmuebles/{id_inmueble}/edificaciones",
    response_model=EdificacionListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_edificaciones_by_inmueble(
    id_inmueble: int,
    db: Session = Depends(get_db),
) -> EdificacionListResponse | JSONResponse:
    repository = EdificacionRepository(db)
    service = GetEdificacionesByInmuebleService(repository=repository)

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
            error_message="No se pudieron obtener las edificaciones.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return EdificacionListResponse(
        data=[EdificacionListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/unidades-funcionales/{id_unidad_funcional}/edificaciones",
    response_model=EdificacionListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_edificaciones_by_unidad_funcional(
    id_unidad_funcional: int,
    db: Session = Depends(get_db),
) -> EdificacionListResponse | JSONResponse:
    repository = EdificacionRepository(db)
    service = GetEdificacionesByUnidadFuncionalService(repository=repository)

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
            error_message="No se pudieron obtener las edificaciones.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return EdificacionListResponse(
        data=[EdificacionListItem(**item) for item in result.data]
    )
