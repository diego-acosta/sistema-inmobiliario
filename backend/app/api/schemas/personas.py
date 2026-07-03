from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PersonaCreateRequest(BaseModel):
    tipo_persona: str
    nombre: str
    apellido: str
    razon_social: str | None = None
    fecha_nacimiento: date | None = None
    estado_persona: str
    observaciones: str | None = None


class PersonaCreateData(BaseModel):
    id_persona: int
    uid_global: str
    version_registro: int
    estado_persona: str


class PersonaCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaCreateData


class RelacionPersonaRolCreateRequest(BaseModel):
    id_persona: int
    id_rol_participacion: int
    tipo_relacion: str
    id_relacion: int
    fecha_desde: date
    fecha_hasta: date | None = None
    observaciones: str | None = None


class RelacionPersonaRolCreateData(BaseModel):
    id_relacion_persona_rol: int
    id_persona: int
    id_rol_participacion: int
    tipo_relacion: str
    id_relacion: int
    version_registro: int
    fecha_desde: date
    fecha_hasta: date | None


class RelacionPersonaRolCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: RelacionPersonaRolCreateData


class RelacionPersonaRolUpdateRequest(BaseModel):
    id_persona: int
    id_rol_participacion: int
    tipo_relacion: str
    id_relacion: int
    fecha_desde: date
    fecha_hasta: date | None = None
    observaciones: str | None = None


class RelacionPersonaRolUpdateData(BaseModel):
    id_relacion_persona_rol: int
    id_persona: int
    id_rol_participacion: int
    tipo_relacion: str
    id_relacion: int
    version_registro: int
    fecha_desde: date
    fecha_hasta: date | None


class RelacionPersonaRolUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: RelacionPersonaRolUpdateData


class RelacionPersonaRolBajaData(BaseModel):
    id_relacion_persona_rol: int
    version_registro: int
    deleted: Literal[True] = True


class RelacionPersonaRolBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: RelacionPersonaRolBajaData


class PersonaParticipacionListItem(BaseModel):
    id_relacion_persona_rol: int
    id_persona: int
    id_rol_participacion: int
    tipo_relacion: str
    id_relacion: int
    fecha_desde: date
    fecha_hasta: date | None


class PersonaParticipacionListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[PersonaParticipacionListItem]


class RolParticipacionCatalogItem(BaseModel):
    id_rol_participacion: int
    codigo_rol: str
    nombre_rol: str
    deleted_at: datetime | None = None


class RolParticipacionCatalogResponse(BaseModel):
    ok: Literal[True] = True
    data: list[RolParticipacionCatalogItem]


class PersonaUpdateRequest(BaseModel):
    tipo_persona: str
    nombre: str | None
    apellido: str | None
    razon_social: str | None = None
    fecha_nacimiento: date | None = None
    estado_persona: str
    observaciones: str | None = None


class PersonaUpdateData(BaseModel):
    id_persona: int
    version_registro: int
    tipo_persona: str
    nombre: str | None
    apellido: str | None
    razon_social: str | None
    estado_persona: str


class PersonaUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaUpdateData


class PersonaBajaData(BaseModel):
    id_persona: int
    version_registro: int
    deleted: Literal[True] = True


class PersonaBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaBajaData


class PersonaDetailData(BaseModel):
    id_persona: int
    tipo_persona: str
    nombre: str | None
    apellido: str | None
    razon_social: str | None
    fecha_nacimiento: date | None
    estado_persona: str
    observaciones: str | None
    version_registro: int
    documentos: list["PersonaDocumentoListItem"]
    domicilios: list["PersonaDomicilioListItem"]
    contactos: list["PersonaContactoListItem"]
    relaciones: list["PersonaRelacionListItem"]
    representaciones_poder: list["RepresentacionPoderListItem"]


class PersonaDetailResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaDetailData


class PersonaDetalleIntegralParticipacionItem(BaseModel):
    id_relacion_persona_rol: int
    id_persona: int
    id_rol_participacion: int
    codigo_rol: str | None
    nombre_rol: str | None
    estado_rol: str | None
    tipo_relacion: str
    id_relacion: int
    fecha_desde: datetime
    fecha_hasta: datetime | None


class PersonaDetalleIntegralObligacionItem(BaseModel):
    id_obligacion_obligado: int
    id_obligacion_financiera: int
    id_relacion_generadora: int
    tipo_origen: str
    id_origen: int
    rol_obligado: str | None
    porcentaje_responsabilidad: float | None
    fecha_emision: date
    fecha_vencimiento: date | None
    estado_obligacion: str
    importe_total: float
    saldo_pendiente: float
    moneda: str
    monto_responsabilidad: float
    saldo_responsabilidad: float


class PersonaDetalleIntegralResumenFinanciero(BaseModel):
    cantidad_obligaciones: int
    importe_total: float
    saldo_pendiente_total: float
    importe_total_responsabilidad: float
    saldo_pendiente_responsabilidad: float


class PersonaUsoVentaItem(BaseModel):
    id_venta: int
    codigo_venta: str | None
    estado_venta: str | None
    monto_total: float | None
    moneda: str | None
    rol: str | None


class PersonaUsoContratoItem(BaseModel):
    id_contrato_alquiler: int
    codigo_contrato: str | None
    estado_contrato: str | None
    fecha_inicio: date | None
    fecha_fin: date | None
    rol: str | None


class PersonaUsoServicioResponsableItem(BaseModel):
    id_asignacion_servicio_responsable: int
    id_servicio: int
    id_inmueble: int | None
    id_unidad_funcional: int | None
    porcentaje_responsabilidad: float
    fecha_desde: date
    fecha_hasta: date | None
    estado_asignacion: str


class PersonaDetalleIntegralUsosTransversales(BaseModel):
    comprador_ventas: list[PersonaUsoVentaItem]
    contratos_locativos: list[PersonaUsoContratoItem]
    servicios_responsable: list[PersonaUsoServicioResponsableItem]
    obligado_financiero: PersonaDetalleIntegralResumenFinanciero


class PersonaDetalleIntegralData(PersonaDetailData):
    participaciones: list[PersonaDetalleIntegralParticipacionItem]
    obligaciones_financieras: list[PersonaDetalleIntegralObligacionItem]
    resumen_financiero: PersonaDetalleIntegralResumenFinanciero
    usos_transversales: PersonaDetalleIntegralUsosTransversales


class PersonaDetalleIntegralResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaDetalleIntegralData


class PersonaListDocumentoPrincipal(BaseModel):
    id_persona_documento: int
    tipo_documento_persona: str
    numero_documento: str
    pais_emision: str | None


class PersonaListContactoPrincipal(BaseModel):
    id_persona_contacto: int
    tipo_contacto: str | None
    valor_contacto: str


class PersonaListItem(BaseModel):
    id_persona: int
    tipo_persona: str
    nombre: str | None
    apellido: str | None
    razon_social: str | None
    display_name: str
    estado_persona: str
    cuit_cuil: str | None
    documento_principal: PersonaListDocumentoPrincipal | None
    contacto_principal: PersonaListContactoPrincipal | None


class PersonaListData(BaseModel):
    items: list[PersonaListItem]
    total: int
    limit: int
    offset: int


class PersonaListResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaListData


class PersonaDocumentoCreateRequest(BaseModel):
    tipo_documento: str
    numero_documento: str
    pais_emision: str | None = None
    es_principal: bool = False
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    observaciones: str | None = None


class PersonaDocumentoCreateData(BaseModel):
    id_persona_documento: int
    id_persona: int
    uid_global: str
    version_registro: int
    tipo_documento: str
    numero_documento: str
    es_principal: bool


class PersonaDocumentoCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaDocumentoCreateData


class PersonaDocumentoUpdateRequest(BaseModel):
    tipo_documento: str
    numero_documento: str
    pais_emision: str | None = None
    es_principal: bool = False
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    observaciones: str | None = None


class PersonaDocumentoUpdateData(BaseModel):
    id_persona_documento: int
    id_persona: int
    version_registro: int
    tipo_documento: str
    numero_documento: str
    pais_emision: str | None
    es_principal: bool


class PersonaDocumentoUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaDocumentoUpdateData


class PersonaDocumentoBajaData(BaseModel):
    id_persona_documento: int
    id_persona: int
    version_registro: int
    deleted: Literal[True] = True


class PersonaDocumentoBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaDocumentoBajaData


class PersonaDocumentoListItem(BaseModel):
    id_persona_documento: int
    tipo_documento: str
    numero_documento: str
    pais_emision: str | None
    es_principal: bool
    version_registro: int


class PersonaDocumentoListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[PersonaDocumentoListItem]


class PersonaDomicilioCreateRequest(BaseModel):
    tipo_domicilio: str | None = None
    direccion: str | None = None
    localidad: str | None = None
    provincia: str | None = None
    pais: str | None = None
    codigo_postal: str | None = None
    es_principal: bool = False
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    observaciones: str | None = None


class PersonaDomicilioCreateData(BaseModel):
    id_persona_domicilio: int
    id_persona: int
    uid_global: str
    version_registro: int
    tipo_domicilio: str | None
    direccion: str | None
    es_principal: bool


class PersonaDomicilioCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaDomicilioCreateData


class PersonaDomicilioUpdateRequest(BaseModel):
    tipo_domicilio: str | None = None
    direccion: str | None = None
    localidad: str | None = None
    provincia: str | None = None
    pais: str | None = None
    codigo_postal: str | None = None
    es_principal: bool = False
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    observaciones: str | None = None


class PersonaDomicilioUpdateData(BaseModel):
    id_persona_domicilio: int
    id_persona: int
    version_registro: int
    tipo_domicilio: str | None
    direccion: str | None
    localidad: str | None
    provincia: str | None
    pais: str | None
    codigo_postal: str | None
    es_principal: bool


class PersonaDomicilioUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaDomicilioUpdateData


class PersonaDomicilioBajaData(BaseModel):
    id_persona_domicilio: int
    id_persona: int
    version_registro: int
    deleted: Literal[True] = True


class PersonaDomicilioBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaDomicilioBajaData


class PersonaDomicilioListItem(BaseModel):
    id_persona_domicilio: int
    version_registro: int
    tipo_domicilio: str | None
    direccion: str | None
    localidad: str | None
    provincia: str | None
    pais: str | None
    codigo_postal: str | None
    es_principal: bool


class PersonaDomicilioListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[PersonaDomicilioListItem]


class PersonaContactoCreateRequest(BaseModel):
    tipo_contacto: str | None = None
    valor_contacto: str
    es_principal: bool = False
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    observaciones: str | None = None


class PersonaContactoCreateData(BaseModel):
    id_persona_contacto: int
    id_persona: int
    uid_global: str
    version_registro: int
    tipo_contacto: str | None
    valor_contacto: str
    es_principal: bool


class PersonaContactoCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaContactoCreateData


class PersonaRelacionCreateRequest(BaseModel):
    id_persona_destino: int
    tipo_relacion: str
    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None
    observaciones: str | None = None


class PersonaRelacionCreateData(BaseModel):
    id_persona_relacion: int
    id_persona_origen: int
    id_persona_destino: int
    uid_global: str
    version_registro: int
    tipo_relacion: str


class PersonaRelacionCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaRelacionCreateData


class PersonaRelacionListItem(BaseModel):
    id_persona_relacion: int
    id_persona_origen: int
    id_persona_destino: int
    tipo_relacion: str
    fecha_desde: datetime | None
    fecha_hasta: datetime | None


class PersonaRelacionListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[PersonaRelacionListItem]


class PersonaRelacionUpdateRequest(BaseModel):
    id_persona_destino: int
    tipo_relacion: str
    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None
    observaciones: str | None = None


class PersonaRelacionUpdateData(BaseModel):
    id_persona_relacion: int
    id_persona_origen: int
    id_persona_destino: int
    version_registro: int
    tipo_relacion: str
    fecha_desde: datetime | None
    fecha_hasta: datetime | None


class PersonaRelacionUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaRelacionUpdateData


class PersonaRelacionBajaData(BaseModel):
    id_persona_relacion: int
    id_persona_origen: int
    version_registro: int
    deleted: Literal[True] = True


class PersonaRelacionBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaRelacionBajaData


class RepresentacionPoderCreateRequest(BaseModel):
    id_persona_representante: int
    tipo_poder: str
    estado_representacion: str
    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None
    descripcion: str | None = None


class RepresentacionPoderCreateData(BaseModel):
    id_representacion_poder: int
    id_persona_representado: int
    id_persona_representante: int
    uid_global: str
    version_registro: int
    tipo_poder: str
    estado_representacion: str


class RepresentacionPoderCreateResponse(BaseModel):
    ok: Literal[True] = True
    data: RepresentacionPoderCreateData


class RepresentacionPoderListItem(BaseModel):
    id_representacion_poder: int
    id_persona_representado: int
    id_persona_representante: int
    tipo_poder: str
    estado_representacion: str
    fecha_desde: datetime | None
    fecha_hasta: datetime | None


class RepresentacionPoderListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[RepresentacionPoderListItem]


class RepresentacionPoderUpdateRequest(BaseModel):
    id_persona_representante: int
    tipo_poder: str
    estado_representacion: str
    fecha_desde: datetime | None = None
    fecha_hasta: datetime | None = None
    descripcion: str | None = None


class RepresentacionPoderUpdateData(BaseModel):
    id_representacion_poder: int
    id_persona_representado: int
    id_persona_representante: int
    version_registro: int
    tipo_poder: str
    estado_representacion: str
    fecha_desde: datetime | None
    fecha_hasta: datetime | None


class RepresentacionPoderUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: RepresentacionPoderUpdateData


class RepresentacionPoderBajaData(BaseModel):
    id_representacion_poder: int
    id_persona_representado: int
    version_registro: int
    deleted: Literal[True] = True


class RepresentacionPoderBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: RepresentacionPoderBajaData


class PersonaContactoUpdateRequest(BaseModel):
    tipo_contacto: str | None = None
    valor_contacto: str
    es_principal: bool = False
    fecha_desde: date | None = None
    fecha_hasta: date | None = None
    observaciones: str | None = None


class PersonaContactoUpdateData(BaseModel):
    id_persona_contacto: int
    id_persona: int
    version_registro: int
    tipo_contacto: str | None
    valor_contacto: str
    es_principal: bool


class PersonaContactoUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaContactoUpdateData


class PersonaContactoBajaData(BaseModel):
    id_persona_contacto: int
    id_persona: int
    version_registro: int
    deleted: Literal[True] = True


class PersonaContactoBajaResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaContactoBajaData


class PersonaContactoListItem(BaseModel):
    id_persona_contacto: int
    version_registro: int
    tipo_contacto: str | None
    valor_contacto: str
    es_principal: bool


class PersonaContactoListResponse(BaseModel):
    ok: Literal[True] = True
    data: list[PersonaContactoListItem]


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    error_code: str
    error_message: str
    details: dict[str, Any] = Field(default_factory=dict)

class DatosPrincipalesPersonaRequest(BaseModel):
    tipo_persona: str
    nombre: str | None
    apellido: str | None
    razon_social: str | None = None
    fecha_nacimiento: date | None = None
    estado_persona: str
    observaciones: str | None = None
    version_registro: int


class DatosPrincipalesDocumentoRequest(BaseModel):
    id_persona_documento: int | None = None
    tipo_documento: str
    numero_documento: str | None = None
    pais_emision: str | None = None
    es_principal: bool = False
    version_registro: int | None = None


class DatosPrincipalesUpdateRequest(BaseModel):
    persona: DatosPrincipalesPersonaRequest
    documento_identidad: DatosPrincipalesDocumentoRequest | None = None
    identificacion_fiscal: DatosPrincipalesDocumentoRequest | None = None


class DatosPrincipalesUpdateResponse(BaseModel):
    ok: Literal[True] = True
    data: PersonaDetailData
