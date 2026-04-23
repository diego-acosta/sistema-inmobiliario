from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.api.schemas.personas import (
    ErrorResponse,
    PersonaCreateData,
    PersonaCreateRequest,
    PersonaCreateResponse,
    PersonaDetailData,
    PersonaDetailResponse,
    PersonaBajaData,
    PersonaBajaResponse,
    RelacionPersonaRolCreateData,
    RelacionPersonaRolCreateRequest,
    RelacionPersonaRolCreateResponse,
    RelacionPersonaRolBajaData,
    RelacionPersonaRolBajaResponse,
    RelacionPersonaRolUpdateData,
    RelacionPersonaRolUpdateRequest,
    RelacionPersonaRolUpdateResponse,
    PersonaParticipacionListItem,
    PersonaParticipacionListResponse,
    PersonaUpdateData,
    PersonaUpdateRequest,
    PersonaUpdateResponse,
    PersonaContactoCreateData,
    PersonaContactoCreateRequest,
    PersonaContactoCreateResponse,
    PersonaRelacionCreateData,
    PersonaRelacionCreateRequest,
    PersonaRelacionCreateResponse,
    PersonaRelacionListItem,
    PersonaRelacionListResponse,
    PersonaRelacionUpdateData,
    PersonaRelacionUpdateRequest,
    PersonaRelacionUpdateResponse,
    PersonaRelacionBajaData,
    PersonaRelacionBajaResponse,
    RepresentacionPoderCreateData,
    RepresentacionPoderCreateRequest,
    RepresentacionPoderCreateResponse,
    RepresentacionPoderListItem,
    RepresentacionPoderListResponse,
    RepresentacionPoderUpdateData,
    RepresentacionPoderUpdateRequest,
    RepresentacionPoderUpdateResponse,
    RepresentacionPoderBajaData,
    RepresentacionPoderBajaResponse,
    PersonaContactoBajaData,
    PersonaContactoBajaResponse,
    PersonaContactoListItem,
    PersonaContactoListResponse,
    PersonaContactoUpdateData,
    PersonaContactoUpdateRequest,
    PersonaContactoUpdateResponse,
    PersonaDomicilioBajaData,
    PersonaDomicilioBajaResponse,
    PersonaDomicilioCreateData,
    PersonaDomicilioCreateRequest,
    PersonaDomicilioCreateResponse,
    PersonaDomicilioListItem,
    PersonaDomicilioListResponse,
    PersonaDomicilioUpdateData,
    PersonaDomicilioUpdateRequest,
    PersonaDomicilioUpdateResponse,
    PersonaDocumentoBajaData,
    PersonaDocumentoBajaResponse,
    PersonaDocumentoCreateData,
    PersonaDocumentoCreateRequest,
    PersonaDocumentoCreateResponse,
    PersonaDocumentoListItem,
    PersonaDocumentoListResponse,
    PersonaDocumentoUpdateData,
    PersonaDocumentoUpdateRequest,
    PersonaDocumentoUpdateResponse,
)
from app.application.common.commands import CommandContext
from app.application.personas.commands.create_persona import CreatePersonaCommand
from app.application.personas.commands.create_relacion_persona_rol import (
    CreateRelacionPersonaRolCommand,
)
from app.application.personas.commands.delete_relacion_persona_rol import (
    DeleteRelacionPersonaRolCommand,
)
from app.application.personas.commands.update_relacion_persona_rol import (
    UpdateRelacionPersonaRolCommand,
)
from app.application.personas.commands.delete_persona import DeletePersonaCommand
from app.application.personas.commands.update_persona import UpdatePersonaCommand
from app.application.personas.commands.create_persona_contacto import (
    CreatePersonaContactoCommand,
)
from app.application.personas.commands.create_persona_relacion import (
    CreatePersonaRelacionCommand,
)
from app.application.personas.commands.update_persona_relacion import (
    UpdatePersonaRelacionCommand,
)
from app.application.personas.commands.delete_persona_relacion import (
    DeletePersonaRelacionCommand,
)
from app.application.personas.commands.create_representacion_poder import (
    CreateRepresentacionPoderCommand,
)
from app.application.personas.commands.update_representacion_poder import (
    UpdateRepresentacionPoderCommand,
)
from app.application.personas.commands.delete_representacion_poder import (
    DeleteRepresentacionPoderCommand,
)
from app.application.personas.commands.create_persona_domicilio import (
    CreatePersonaDomicilioCommand,
)
from app.application.personas.commands.create_persona_documento import (
    CreatePersonaDocumentoCommand,
)
from app.application.personas.commands.delete_persona_contacto import (
    DeletePersonaContactoCommand,
)
from app.application.personas.commands.delete_persona_documento import (
    DeletePersonaDocumentoCommand,
)
from app.application.personas.commands.delete_persona_domicilio import (
    DeletePersonaDomicilioCommand,
)
from app.application.personas.commands.update_persona_documento import (
    UpdatePersonaDocumentoCommand,
)
from app.application.personas.commands.update_persona_domicilio import (
    UpdatePersonaDomicilioCommand,
)
from app.application.personas.commands.update_persona_contacto import (
    UpdatePersonaContactoCommand,
)
from app.application.personas.services.create_persona_contacto_service import (
    CreatePersonaContactoService,
)
from app.application.personas.services.create_persona_relacion_service import (
    CreatePersonaRelacionService,
)
from app.application.personas.services.update_persona_relacion_service import (
    UpdatePersonaRelacionService,
)
from app.application.personas.services.delete_persona_relacion_service import (
    DeletePersonaRelacionService,
)
from app.application.personas.services.create_representacion_poder_service import (
    CreateRepresentacionPoderService,
)
from app.application.personas.services.get_representacion_poder_service import (
    GetRepresentacionPoderService,
)
from app.application.personas.services.update_representacion_poder_service import (
    UpdateRepresentacionPoderService,
)
from app.application.personas.services.delete_representacion_poder_service import (
    DeleteRepresentacionPoderService,
)
from app.application.personas.services.delete_persona_contacto_service import (
    DeletePersonaContactoService,
)
from app.application.personas.services.delete_persona_documento_service import (
    DeletePersonaDocumentoService,
)
from app.application.personas.services.delete_persona_domicilio_service import (
    DeletePersonaDomicilioService,
)
from app.application.personas.services.create_persona_domicilio_service import (
    CreatePersonaDomicilioService,
)
from app.application.personas.services.get_persona_documentos_service import (
    GetPersonaDocumentosService,
)
from app.application.personas.services.update_persona_documento_service import (
    UpdatePersonaDocumentoService,
)
from app.application.personas.services.update_persona_service import (
    UpdatePersonaService,
)
from app.application.personas.services.delete_persona_service import (
    DeletePersonaService,
)
from app.application.personas.services.create_relacion_persona_rol_service import (
    CreateRelacionPersonaRolService,
)
from app.application.personas.services.delete_relacion_persona_rol_service import (
    DeleteRelacionPersonaRolService,
)
from app.application.personas.services.update_relacion_persona_rol_service import (
    UpdateRelacionPersonaRolService,
)
from app.application.personas.services.get_persona_participaciones_service import (
    GetPersonaParticipacionesService,
)
from app.application.personas.services.get_persona_service import GetPersonaService
from app.application.personas.services.get_persona_domicilios_service import (
    GetPersonaDomiciliosService,
)
from app.application.personas.services.get_persona_contactos_service import (
    GetPersonaContactosService,
)
from app.application.personas.services.get_persona_relaciones_service import (
    GetPersonaRelacionesService,
)
from app.application.personas.services.update_persona_domicilio_service import (
    UpdatePersonaDomicilioService,
)
from app.application.personas.services.update_persona_contacto_service import (
    UpdatePersonaContactoService,
)
from app.application.personas.services.create_persona_service import CreatePersonaService
from app.application.personas.services.create_persona_documento_service import (
    CreatePersonaDocumentoService,
)
from app.infrastructure.persistence.repositories.persona_repository import (
    PersonaRepository,
)


router = APIRouter(tags=["Personas"])


class PersonaCommandContext(CommandContext):
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
    "/api/v1/personas",
    status_code=201,
    response_model=PersonaCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_persona(
    request: PersonaCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> PersonaCreateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreatePersonaCommand(
        context=context,
        tipo_persona=request.tipo_persona,
        nombre=request.nombre,
        apellido=request.apellido,
        razon_social=request.razon_social,
        fecha_nacimiento=request.fecha_nacimiento,
        estado_persona=request.estado_persona,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = CreatePersonaService(repository=repository)

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
            error_message="No se pudo crear la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaCreateResponse(data=PersonaCreateData(**result.data))


@router.post(
    "/api/v1/personas/{id_persona}/documentos",
    status_code=201,
    response_model=PersonaDocumentoCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_persona_documento(
    id_persona: int,
    request: PersonaDocumentoCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> PersonaDocumentoCreateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreatePersonaDocumentoCommand(
        context=context,
        id_persona=id_persona,
        tipo_documento=request.tipo_documento,
        numero_documento=request.numero_documento,
        pais_emision=request.pais_emision,
        es_principal=request.es_principal,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = CreatePersonaDocumentoService(repository=repository)

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
            error_message="No se pudo crear el documento de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaDocumentoCreateResponse(
        data=PersonaDocumentoCreateData(**result.data)
    )


@router.post(
    "/api/v1/personas/{id_persona}/domicilios",
    status_code=201,
    response_model=PersonaDomicilioCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_persona_domicilio(
    id_persona: int,
    request: PersonaDomicilioCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> PersonaDomicilioCreateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreatePersonaDomicilioCommand(
        context=context,
        id_persona=id_persona,
        tipo_domicilio=request.tipo_domicilio,
        direccion=request.direccion,
        localidad=request.localidad,
        provincia=request.provincia,
        pais=request.pais,
        codigo_postal=request.codigo_postal,
        es_principal=request.es_principal,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = CreatePersonaDomicilioService(repository=repository)

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
            error_message="No se pudo crear el domicilio de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaDomicilioCreateResponse(
        data=PersonaDomicilioCreateData(**result.data)
    )


@router.post(
    "/api/v1/personas/{id_persona}/contactos",
    status_code=201,
    response_model=PersonaContactoCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_persona_contacto(
    id_persona: int,
    request: PersonaContactoCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> PersonaContactoCreateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreatePersonaContactoCommand(
        context=context,
        id_persona=id_persona,
        tipo_contacto=request.tipo_contacto,
        valor_contacto=request.valor_contacto,
        es_principal=request.es_principal,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = CreatePersonaContactoService(repository=repository)

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
            error_message="No se pudo crear el contacto de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaContactoCreateResponse(
        data=PersonaContactoCreateData(**result.data)
    )


@router.post(
    "/api/v1/personas/{id_persona}/relaciones",
    status_code=201,
    response_model=PersonaRelacionCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_persona_relacion(
    id_persona: int,
    request: PersonaRelacionCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> PersonaRelacionCreateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreatePersonaRelacionCommand(
        context=context,
        id_persona_origen=id_persona,
        id_persona_destino=request.id_persona_destino,
        tipo_relacion=request.tipo_relacion,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = CreatePersonaRelacionService(repository=repository)

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
            error_message="No se pudo crear la relacion de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaRelacionCreateResponse(
        data=PersonaRelacionCreateData(**result.data)
    )


@router.post(
    "/api/v1/personas/{id_persona}/representaciones-poder",
    status_code=201,
    response_model=RepresentacionPoderCreateResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_representacion_poder(
    id_persona: int,
    request: RepresentacionPoderCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> RepresentacionPoderCreateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreateRepresentacionPoderCommand(
        context=context,
        id_persona_representado=id_persona,
        id_persona_representante=request.id_persona_representante,
        tipo_poder=request.tipo_poder,
        estado_representacion=request.estado_representacion,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        descripcion=request.descripcion,
    )

    repository = PersonaRepository(db)
    service = CreateRepresentacionPoderService(repository=repository)

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
            error_message="No se pudo crear la representacion de poder.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return RepresentacionPoderCreateResponse(
        data=RepresentacionPoderCreateData(**result.data)
    )


@router.post(
    "/api/v1/roles-participacion",
    include_in_schema=False,
    status_code=201,
    response_model=RelacionPersonaRolCreateResponse,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@router.post(
    "/api/v1/relaciones-persona-rol",
    status_code=201,
    response_model=RelacionPersonaRolCreateResponse,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def create_relacion_persona_rol(
    request: RelacionPersonaRolCreateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
) -> RelacionPersonaRolCreateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = CreateRelacionPersonaRolCommand(
        context=context,
        id_persona=request.id_persona,
        id_rol_participacion=request.id_rol_participacion,
        tipo_relacion=request.tipo_relacion,
        id_relacion=request.id_relacion,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = CreateRelacionPersonaRolService(repository=repository)

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
            for error in ("NOT_FOUND_PERSONA", "NOT_FOUND_ROL_PARTICIPACION")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o el rol de participacion indicado no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudo crear la relacion persona rol.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return RelacionPersonaRolCreateResponse(
        data=RelacionPersonaRolCreateData(**result.data)
    )


@router.put(
    "/api/v1/roles-participacion/{id_relacion_persona_rol}",
    include_in_schema=False,
    response_model=RelacionPersonaRolUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@router.put(
    "/api/v1/relaciones-persona-rol/{id_relacion_persona_rol}",
    response_model=RelacionPersonaRolUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_relacion_persona_rol(
    id_relacion_persona_rol: int,
    request: RelacionPersonaRolUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> RelacionPersonaRolUpdateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdateRelacionPersonaRolCommand(
        context=context,
        id_relacion_persona_rol=id_relacion_persona_rol,
        if_match_version=parsed_if_match_version,
        id_persona=request.id_persona,
        id_rol_participacion=request.id_rol_participacion,
        tipo_relacion=request.tipo_relacion,
        id_relacion=request.id_relacion,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = UpdateRelacionPersonaRolService(repository=repository)

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
                "NOT_FOUND_RELACION_PERSONA_ROL",
                "NOT_FOUND_PERSONA",
                "NOT_FOUND_ROL_PARTICIPACION",
            )
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La relacion, la persona o el rol de participacion indicado no existe.",
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
            error_message="No se pudo actualizar la relacion persona rol.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return RelacionPersonaRolUpdateResponse(
        data=RelacionPersonaRolUpdateData(**result.data)
    )


@router.patch(
    "/api/v1/roles-participacion/{id_relacion_persona_rol}/baja",
    include_in_schema=False,
    response_model=RelacionPersonaRolBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
@router.patch(
    "/api/v1/relaciones-persona-rol/{id_relacion_persona_rol}/baja",
    response_model=RelacionPersonaRolBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_relacion_persona_rol(
    id_relacion_persona_rol: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> RelacionPersonaRolBajaResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeleteRelacionPersonaRolCommand(
        context=context,
        id_relacion_persona_rol=id_relacion_persona_rol,
        if_match_version=parsed_if_match_version,
    )

    repository = PersonaRepository(db)
    service = DeleteRelacionPersonaRolService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_RELACION_PERSONA_ROL" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La relacion persona rol indicada no existe.",
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
            error_message="No se pudo dar de baja la relacion persona rol.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return RelacionPersonaRolBajaResponse(
        data=RelacionPersonaRolBajaData(**result.data)
    )


@router.patch(
    "/api/v1/personas/{id_persona}/baja",
    response_model=PersonaBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_persona(
    id_persona: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> PersonaBajaResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeletePersonaCommand(
        context=context,
        id_persona=id_persona,
        if_match_version=parsed_if_match_version,
    )

    repository = PersonaRepository(db)
    service = DeletePersonaService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_PERSONA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona indicada no existe.",
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
            error_message="No se pudo dar de baja la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaBajaResponse(data=PersonaBajaData(**result.data))


@router.put(
    "/api/v1/personas/{id_persona}",
    response_model=PersonaUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_persona(
    id_persona: int,
    request: PersonaUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> PersonaUpdateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdatePersonaCommand(
        context=context,
        id_persona=id_persona,
        if_match_version=parsed_if_match_version,
        tipo_persona=request.tipo_persona,
        nombre=request.nombre,
        apellido=request.apellido,
        razon_social=request.razon_social,
        fecha_nacimiento=request.fecha_nacimiento,
        estado_persona=request.estado_persona,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = UpdatePersonaService(repository=repository)

    try:
        result = service.execute(command)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "NOT_FOUND_PERSONA" in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona indicada no existe.",
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
            error_message="No se pudo actualizar la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaUpdateResponse(data=PersonaUpdateData(**result.data))


@router.put(
    "/api/v1/personas/{id_persona}/documentos/{id_persona_documento}",
    response_model=PersonaDocumentoUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_persona_documento(
    id_persona: int,
    id_persona_documento: int,
    request: PersonaDocumentoUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> PersonaDocumentoUpdateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdatePersonaDocumentoCommand(
        context=context,
        id_persona=id_persona,
        id_persona_documento=id_persona_documento,
        if_match_version=parsed_if_match_version,
        tipo_documento=request.tipo_documento,
        numero_documento=request.numero_documento,
        pais_emision=request.pais_emision,
        es_principal=request.es_principal,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = UpdatePersonaDocumentoService(repository=repository)

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
            for error in ("NOT_FOUND_PERSONA", "NOT_FOUND_DOCUMENTO")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o el documento indicado no existe.",
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
            error_message="No se pudo actualizar el documento de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaDocumentoUpdateResponse(
        data=PersonaDocumentoUpdateData(**result.data)
    )


@router.patch(
    "/api/v1/personas/{id_persona}/representaciones-poder/{id_representacion_poder}/baja",
    response_model=RepresentacionPoderBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_representacion_poder(
    id_persona: int,
    id_representacion_poder: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> RepresentacionPoderBajaResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeleteRepresentacionPoderCommand(
        context=context,
        id_persona_representado=id_persona,
        id_representacion_poder=id_representacion_poder,
        if_match_version=parsed_if_match_version,
    )

    repository = PersonaRepository(db)
    service = DeleteRepresentacionPoderService(repository=repository)

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
            for error in ("NOT_FOUND_PERSONA", "NOT_FOUND_REPRESENTACION_PODER")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o la representacion de poder indicada no existe.",
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
            error_message="No se pudo dar de baja la representacion de poder.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return RepresentacionPoderBajaResponse(
        data=RepresentacionPoderBajaData(**result.data)
    )


@router.patch(
    "/api/v1/personas/{id_persona}/relaciones/{id_persona_relacion}/baja",
    response_model=PersonaRelacionBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_persona_relacion(
    id_persona: int,
    id_persona_relacion: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> PersonaRelacionBajaResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeletePersonaRelacionCommand(
        context=context,
        id_persona_origen=id_persona,
        id_persona_relacion=id_persona_relacion,
        if_match_version=parsed_if_match_version,
    )

    repository = PersonaRepository(db)
    service = DeletePersonaRelacionService(repository=repository)

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
            for error in ("NOT_FOUND_PERSONA", "NOT_FOUND_RELACION")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o la relacion indicada no existe.",
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
            error_message="No se pudo dar de baja la relacion de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaRelacionBajaResponse(
        data=PersonaRelacionBajaData(**result.data)
    )


@router.patch(
    "/api/v1/personas/{id_persona}/documentos/{id_persona_documento}/baja",
    response_model=PersonaDocumentoBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_persona_documento(
    id_persona: int,
    id_persona_documento: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> PersonaDocumentoBajaResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeletePersonaDocumentoCommand(
        context=context,
        id_persona=id_persona,
        id_persona_documento=id_persona_documento,
        if_match_version=parsed_if_match_version,
    )

    repository = PersonaRepository(db)
    service = DeletePersonaDocumentoService(repository=repository)

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
            for error in ("NOT_FOUND_PERSONA", "NOT_FOUND_DOCUMENTO")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o el documento indicado no existe.",
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
            error_message="No se pudo dar de baja el documento de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaDocumentoBajaResponse(
        data=PersonaDocumentoBajaData(**result.data)
    )


@router.patch(
    "/api/v1/personas/{id_persona}/contactos/{id_persona_contacto}/baja",
    response_model=PersonaContactoBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_persona_contacto(
    id_persona: int,
    id_persona_contacto: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> PersonaContactoBajaResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeletePersonaContactoCommand(
        context=context,
        id_persona=id_persona,
        id_persona_contacto=id_persona_contacto,
        if_match_version=parsed_if_match_version,
    )

    repository = PersonaRepository(db)
    service = DeletePersonaContactoService(repository=repository)

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
            for error in ("NOT_FOUND_PERSONA", "NOT_FOUND_CONTACTO")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o el contacto indicado no existe.",
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
            error_message="No se pudo dar de baja el contacto de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaContactoBajaResponse(
        data=PersonaContactoBajaData(**result.data)
    )


@router.patch(
    "/api/v1/personas/{id_persona}/domicilios/{id_persona_domicilio}/baja",
    response_model=PersonaDomicilioBajaResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def delete_persona_domicilio(
    id_persona: int,
    id_persona_domicilio: int,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> PersonaDomicilioBajaResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = DeletePersonaDomicilioCommand(
        context=context,
        id_persona=id_persona,
        id_persona_domicilio=id_persona_domicilio,
        if_match_version=parsed_if_match_version,
    )

    repository = PersonaRepository(db)
    service = DeletePersonaDomicilioService(repository=repository)

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
            for error in ("NOT_FOUND_PERSONA", "NOT_FOUND_DOMICILIO")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o el domicilio indicado no existe.",
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
            error_message="No se pudo dar de baja el domicilio de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaDomicilioBajaResponse(
        data=PersonaDomicilioBajaData(**result.data)
    )


@router.put(
    "/api/v1/personas/{id_persona}/domicilios/{id_persona_domicilio}",
    response_model=PersonaDomicilioUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_persona_domicilio(
    id_persona: int,
    id_persona_domicilio: int,
    request: PersonaDomicilioUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> PersonaDomicilioUpdateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdatePersonaDomicilioCommand(
        context=context,
        id_persona=id_persona,
        id_persona_domicilio=id_persona_domicilio,
        if_match_version=parsed_if_match_version,
        tipo_domicilio=request.tipo_domicilio,
        direccion=request.direccion,
        localidad=request.localidad,
        provincia=request.provincia,
        pais=request.pais,
        codigo_postal=request.codigo_postal,
        es_principal=request.es_principal,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = UpdatePersonaDomicilioService(repository=repository)

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
            for error in ("NOT_FOUND_PERSONA", "NOT_FOUND_DOMICILIO")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o el domicilio indicado no existe.",
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
            error_message="No se pudo actualizar el domicilio de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaDomicilioUpdateResponse(
        data=PersonaDomicilioUpdateData(**result.data)
    )


@router.put(
    "/api/v1/personas/{id_persona}/representaciones-poder/{id_representacion_poder}",
    response_model=RepresentacionPoderUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_representacion_poder(
    id_persona: int,
    id_representacion_poder: int,
    request: RepresentacionPoderUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> RepresentacionPoderUpdateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdateRepresentacionPoderCommand(
        context=context,
        id_persona_representado=id_persona,
        id_representacion_poder=id_representacion_poder,
        if_match_version=parsed_if_match_version,
        id_persona_representante=request.id_persona_representante,
        tipo_poder=request.tipo_poder,
        estado_representacion=request.estado_representacion,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        descripcion=request.descripcion,
    )

    repository = PersonaRepository(db)
    service = UpdateRepresentacionPoderService(repository=repository)

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
                "NOT_FOUND_PERSONA",
                "NOT_FOUND_REPRESENTACION_PODER",
                "NOT_FOUND_PERSONA_REPRESENTANTE",
            )
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o la representacion de poder indicada no existe.",
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
            error_message="No se pudo actualizar la representacion de poder.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return RepresentacionPoderUpdateResponse(
        data=RepresentacionPoderUpdateData(**result.data)
    )


@router.put(
    "/api/v1/personas/{id_persona}/relaciones/{id_persona_relacion}",
    response_model=PersonaRelacionUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_persona_relacion(
    id_persona: int,
    id_persona_relacion: int,
    request: PersonaRelacionUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> PersonaRelacionUpdateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdatePersonaRelacionCommand(
        context=context,
        id_persona_origen=id_persona,
        id_persona_relacion=id_persona_relacion,
        if_match_version=parsed_if_match_version,
        id_persona_destino=request.id_persona_destino,
        tipo_relacion=request.tipo_relacion,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = UpdatePersonaRelacionService(repository=repository)

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
                "NOT_FOUND_PERSONA",
                "NOT_FOUND_RELACION",
                "NOT_FOUND_PERSONA_DESTINO",
            )
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o la relacion indicada no existe.",
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
            error_message="No se pudo actualizar la relacion de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaRelacionUpdateResponse(
        data=PersonaRelacionUpdateData(**result.data)
    )


@router.put(
    "/api/v1/personas/{id_persona}/contactos/{id_persona_contacto}",
    response_model=PersonaContactoUpdateResponse,
    responses={
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def update_persona_contacto(
    id_persona: int,
    id_persona_contacto: int,
    request: PersonaContactoUpdateRequest,
    db: Session = Depends(get_db),
    x_op_id: str | None = Header(default=None, alias="X-Op-Id"),
    x_usuario_id: str | None = Header(default=None, alias="X-Usuario-Id"),
    x_sucursal_id: str | None = Header(default=None, alias="X-Sucursal-Id"),
    x_instalacion_id: str | None = Header(default=None, alias="X-Instalacion-Id"),
    if_match_version: str | None = Header(default=None, alias="If-Match-Version"),
) -> PersonaContactoUpdateResponse | JSONResponse:
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

    context = PersonaCommandContext(
        id_instalacion=id_instalacion,
        op_id=op_id,
        **context_kwargs,
    )

    command = UpdatePersonaContactoCommand(
        context=context,
        id_persona=id_persona,
        id_persona_contacto=id_persona_contacto,
        if_match_version=parsed_if_match_version,
        tipo_contacto=request.tipo_contacto,
        valor_contacto=request.valor_contacto,
        es_principal=request.es_principal,
        fecha_desde=request.fecha_desde,
        fecha_hasta=request.fecha_hasta,
        observaciones=request.observaciones,
    )

    repository = PersonaRepository(db)
    service = UpdatePersonaContactoService(repository=repository)

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
            for error in ("NOT_FOUND_PERSONA", "NOT_FOUND_CONTACTO")
        ):
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona o el contacto indicado no existe.",
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
            error_message="No se pudo actualizar el contacto de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaContactoUpdateResponse(
        data=PersonaContactoUpdateData(**result.data)
    )


@router.get(
    "/api/v1/personas/{id_persona}",
    response_model=PersonaDetailResponse,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_persona(
    id_persona: int,
    db: Session = Depends(get_db),
) -> PersonaDetailResponse | JSONResponse:
    repository = PersonaRepository(db)
    service = GetPersonaService(repository=repository)

    try:
        result = service.execute(id_persona)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error_code = "NOT_FOUND" if "NOT_FOUND" in result.errors else "APPLICATION_ERROR"
        error_message = (
            "La persona indicada no existe."
            if error_code == "NOT_FOUND"
            else "No se pudo obtener la persona."
        )
        status_code = 404 if error_code == "NOT_FOUND" else 400
        error = ErrorResponse(
            error_code=error_code,
            error_message=error_message,
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=status_code, content=error.model_dump())

    return PersonaDetailResponse(data=PersonaDetailData(**result.data))


@router.get(
    "/api/v1/personas/{id_persona}/documentos",
    response_model=PersonaDocumentoListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_persona_documentos(
    id_persona: int,
    db: Session = Depends(get_db),
) -> PersonaDocumentoListResponse | JSONResponse:
    repository = PersonaRepository(db)
    service = GetPersonaDocumentosService(repository=repository)

    try:
        result = service.execute(id_persona)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener los documentos de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaDocumentoListResponse(
        data=[PersonaDocumentoListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/personas/{id_persona}/participaciones",
    response_model=PersonaParticipacionListResponse,
    responses={
        404: {"model": ErrorResponse},
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_persona_participaciones(
    id_persona: int,
    db: Session = Depends(get_db),
) -> PersonaParticipacionListResponse | JSONResponse:
    repository = PersonaRepository(db)
    service = GetPersonaParticipacionesService(repository=repository)

    try:
        result = service.execute(id_persona)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        if "La persona indicada no existe." in result.errors:
            error = ErrorResponse(
                error_code="NOT_FOUND",
                error_message="La persona indicada no existe.",
                details={"errors": result.errors},
            )
            return JSONResponse(status_code=404, content=error.model_dump())

        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las participaciones de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaParticipacionListResponse(
        data=[PersonaParticipacionListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/personas/{id_persona}/domicilios",
    response_model=PersonaDomicilioListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_persona_domicilios(
    id_persona: int,
    db: Session = Depends(get_db),
) -> PersonaDomicilioListResponse | JSONResponse:
    repository = PersonaRepository(db)
    service = GetPersonaDomiciliosService(repository=repository)

    try:
        result = service.execute(id_persona)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener los domicilios de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaDomicilioListResponse(
        data=[PersonaDomicilioListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/personas/{id_persona}/contactos",
    response_model=PersonaContactoListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_persona_contactos(
    id_persona: int,
    db: Session = Depends(get_db),
) -> PersonaContactoListResponse | JSONResponse:
    repository = PersonaRepository(db)
    service = GetPersonaContactosService(repository=repository)

    try:
        result = service.execute(id_persona)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener los contactos de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaContactoListResponse(
        data=[PersonaContactoListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/personas/{id_persona}/relaciones",
    response_model=PersonaRelacionListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_persona_relaciones(
    id_persona: int,
    db: Session = Depends(get_db),
) -> PersonaRelacionListResponse | JSONResponse:
    repository = PersonaRepository(db)
    service = GetPersonaRelacionesService(repository=repository)

    try:
        result = service.execute(id_persona)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las relaciones de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return PersonaRelacionListResponse(
        data=[PersonaRelacionListItem(**item) for item in result.data]
    )


@router.get(
    "/api/v1/personas/{id_persona}/representaciones-poder",
    response_model=RepresentacionPoderListResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse},
    },
)
def get_representaciones_poder(
    id_persona: int,
    db: Session = Depends(get_db),
) -> RepresentacionPoderListResponse | JSONResponse:
    repository = PersonaRepository(db)
    service = GetRepresentacionPoderService(repository=repository)

    try:
        result = service.execute(id_persona)
    except Exception as exc:
        error = ErrorResponse(
            error_code="INTERNAL_ERROR",
            error_message=str(exc),
        )
        return JSONResponse(status_code=500, content=error.model_dump())

    if not result.success or result.data is None:
        error = ErrorResponse(
            error_code="APPLICATION_ERROR",
            error_message="No se pudieron obtener las representaciones de poder de la persona.",
            details={"errors": result.errors},
        )
        return JSONResponse(status_code=400, content=error.model_dump())

    return RepresentacionPoderListResponse(
        data=[RepresentacionPoderListItem(**item) for item in result.data]
    )
