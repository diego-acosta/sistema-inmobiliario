from contextlib import AbstractContextManager
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from app.application.comercial.commands.confirm_venta import ConfirmVentaCommand
from app.application.comercial.commands.confirm_venta_directa_completa import (
    ConfirmVentaDirectaCompletaCommand,
)
from app.application.comercial.commands.define_condiciones_comerciales_venta import (
    DefineCondicionesComercialesVentaCommand,
    DefineCondicionesComercialesVentaCuotaCommand,
    DefineCondicionesComercialesVentaObjetoCommand,
)
from app.application.comercial.commands.generate_plan_pago_venta_v2_por_bloques import (
    CuotaRefuerzoInput,
    GeneratePlanPagoVentaV2PorBloquesCommand,
    PlanPagoVentaBloqueInput,
)
from app.application.comercial.services.confirm_venta_service import ConfirmVentaService
from app.application.comercial.services.define_condiciones_comerciales_venta_service import (
    DefineCondicionesComercialesVentaService,
)
from app.application.comercial.services.generate_plan_pago_venta_v2_por_bloques_service import (
    GeneratePlanPagoVentaV2PorBloquesService,
)
from app.application.comercial.services.build_plan_pago_venta_v2_por_bloques_preview_service import (
    BuildPlanPagoVentaV2PorBloquesPreviewService,
)
from app.application.comercial.services.prevalidate_venta_historica_indexacion_service import (
    ERROR_FECHA_CORTE_REQUERIDA_VENTA_HISTORICA,
    ERROR_VENTA_HISTORICA_INDEXACION_NO_RESUELTA,
    PrevalidateVentaHistoricaIndexacionInput,
    PrevalidateVentaHistoricaIndexacionService,
    detalle_bloqueo_prevalidacion,
    resumen_confirmacion_prevalidacion,
)
from app.application.common.results import AppResult
from app.application.personas.duplicados import TipoDuplicadoPersona


class _TransactionalComercialRepository:
    def __init__(self, repository: Any) -> None:
        self._repository = repository

    def __getattr__(self, name: str) -> Any:
        return getattr(self._repository, name)

    @property
    def db(self) -> Any:
        return self._repository.db

    def define_condiciones_comerciales_venta(
        self,
        payload: Any,
        objetos: list[Any],
        cuotas: list[Any],
    ) -> dict[str, Any]:
        return self._repository._define_condiciones_comerciales_venta_tx(
            payload,
            objetos,
            cuotas,
        )

    def confirm_venta(
        self,
        payload: Any,
        *,
        outbox_event: Any | None = None,
    ) -> dict[str, Any]:
        return self._repository._confirm_venta_tx(
            payload,
            outbox_event=outbox_event,
        )


class _StageFailed(Exception):
    def __init__(self, error: str) -> None:
        super().__init__(error)
        self.error = error


class ConfirmVentaDirectaCompletaService:
    def __init__(
        self,
        *,
        comercial_repository: Any,
        plan_pago_v2_service: GeneratePlanPagoVentaV2PorBloquesService,
        uuid_generator=None,
    ) -> None:
        self.comercial_repository = comercial_repository
        self.plan_pago_v2_service = plan_pago_v2_service
        self.uuid_generator = uuid_generator or uuid4
        self.db = comercial_repository.db

    def execute(
        self, command: ConfirmVentaDirectaCompletaCommand
    ) -> AppResult[dict[str, Any]]:
        id_instalacion = getattr(command.context, "id_instalacion", None)
        if id_instalacion is None:
            return AppResult.fail("X-Instalacion-Id es requerido.")

        total_derivado_result = self._normalizar_precios_y_total(command)
        if not total_derivado_result.success or total_derivado_result.data is None:
            return AppResult.fail(total_derivado_result.errors[0])

        total_derivado = total_derivado_result.data
        if total_derivado != command.plan_pago_v2.monto_total_plan:
            return AppResult.fail("MONTO_TOTAL_PLAN_MISMATCH")

        compradores_error = self._validate_compradores(command)
        if compradores_error is not None:
            return AppResult.fail(compradores_error)

        prevalidacion_historica: dict[str, Any] | None = None
        fecha_venta_date = command.generar_venta.fecha_venta.date()
        if command.fecha_corte is None and self._requiere_fecha_corte_historica(command):
            return AppResult.fail_with_details(
                ERROR_FECHA_CORTE_REQUERIDA_VENTA_HISTORICA,
                {
                    "fecha_venta": fecha_venta_date.isoformat(),
                    "fecha_operativa_confirmacion": date.today().isoformat(),
                    "motivo": "VENTA_INDEXADA_ANTERIOR_A_FECHA_OPERATIVA",
                },
            )
        if command.fecha_corte is not None:
            if fecha_venta_date > command.fecha_corte:
                return AppResult.fail("FECHA_VENTA_POSTERIOR_FECHA_CORTE")
            preview_command = self._plan_pago_v2_command(command, id_venta=None)
            preview_result = BuildPlanPagoVentaV2PorBloquesPreviewService(
                indice_financiero_query=self.plan_pago_v2_service.repository
            ).execute(preview_command)
            if not preview_result.success or preview_result.data is None:
                return AppResult.fail(preview_result.errors[0])
            prevalidacion_historica = PrevalidateVentaHistoricaIndexacionService(
                self.plan_pago_v2_service.repository
            ).execute(
                PrevalidateVentaHistoricaIndexacionInput(
                    fecha_venta=fecha_venta_date,
                    fecha_corte=command.fecha_corte,
                    command=preview_command,
                    preview=preview_result.data,
                )
            )
            if not prevalidacion_historica["puede_confirmar"]:
                return AppResult.fail_with_details(
                    ERROR_VENTA_HISTORICA_INDEXACION_NO_RESUELTA,
                    detalle_bloqueo_prevalidacion(prevalidacion_historica),
                )

        tx_repository = _TransactionalComercialRepository(self.comercial_repository)

        try:
            with self._transaction():
                resolve_error = self._resolve_compradores_contextuales(
                    command, id_instalacion=id_instalacion
                )
                if resolve_error is not None:
                    raise _StageFailed(resolve_error)

                generated = self.comercial_repository._create_venta_directa_tx(
                    self._venta_payload(command, id_instalacion=id_instalacion),
                    self._objetos_payload(command, id_instalacion=id_instalacion),
                    self._compradores_payload(command, id_instalacion=id_instalacion),
                )
                if generated.get("status") != "OK" or generated.get("data") is None:
                    raise _StageFailed(generated.get("status", "APPLICATION_ERROR"))

                id_venta = generated["data"]["id_venta"]
                condiciones = DefineCondicionesComercialesVentaService(
                    tx_repository
                ).execute(
                    DefineCondicionesComercialesVentaCommand(
                        context=command.context,
                        id_venta=id_venta,
                        if_match_version=generated["data"]["version_registro"],
                        monto_total=self._total_objetos(command),
                        tipo_plan_financiero=command.condiciones_comerciales.tipo_plan_financiero,
                        moneda=command.condiciones_comerciales.moneda,
                        importe_anticipo=command.condiciones_comerciales.importe_anticipo,
                        fecha_vencimiento_anticipo=command.condiciones_comerciales.fecha_vencimiento_anticipo,
                        importe_saldo=command.condiciones_comerciales.importe_saldo,
                        fecha_vencimiento_saldo=command.condiciones_comerciales.fecha_vencimiento_saldo,
                        cuotas=[
                            DefineCondicionesComercialesVentaCuotaCommand(
                                numero_cuota=cuota.numero_cuota,
                                importe_cuota=cuota.importe_cuota,
                                fecha_vencimiento=cuota.fecha_vencimiento,
                                moneda=cuota.moneda,
                                observaciones=cuota.observaciones,
                            )
                            for cuota in command.condiciones_comerciales.cuotas
                        ],
                        objetos=[
                            DefineCondicionesComercialesVentaObjetoCommand(
                                id_inmueble=objeto.id_inmueble,
                                id_unidad_funcional=objeto.id_unidad_funcional,
                                precio_asignado=objeto.precio_asignado,
                            )
                            for objeto in command.objetos
                        ],
                    )
                )
                if not condiciones.success or condiciones.data is None:
                    raise _StageFailed(condiciones.errors[0])

                plan = self.plan_pago_v2_service.execute_in_existing_transaction(
                    self._plan_pago_v2_command(command, id_venta=id_venta)
                )
                if not plan.success or plan.data is None:
                    raise _StageFailed(plan.errors[0])

                confirmed = ConfirmVentaService(tx_repository).execute(
                    ConfirmVentaCommand(
                        context=command.context,
                        id_venta=id_venta,
                        if_match_version=condiciones.data["version_registro"],
                        observaciones=command.confirmacion.observaciones,
                    )
                )
                if not confirmed.success or confirmed.data is None:
                    raise _StageFailed(confirmed.errors[0])

                return AppResult.ok(
                    {
                        "ok": True,
                        "data": {
                            "venta": {
                                "id_venta": confirmed.data["id_venta"],
                                "estado_venta": confirmed.data["estado_venta"],
                                "version_registro": confirmed.data["version_registro"],
                            },
                            "plan_pago_v2": {
                                "id_plan_pago_venta": plan.data["plan_pago_venta"][
                                    "id_plan_pago_venta"
                                ],
                                "estado_plan_pago": plan.data["plan_pago_venta"][
                                    "estado_plan_pago"
                                ],
                            },
                            "generacion_cronograma_financiero": {
                                "id_generacion_cronograma_financiero": plan.data[
                                    "generacion_cronograma_financiero"
                                ]["id_generacion_cronograma_financiero"],
                                "estado_generacion": plan.data[
                                    "generacion_cronograma_financiero"
                                ]["estado_generacion"],
                            },
                            "obligaciones": {
                                "cantidad": len(plan.data["obligaciones"]),
                                "ids": [
                                    obligacion["id_obligacion_financiera"]
                                    for obligacion in plan.data["obligaciones"]
                                ],
                            },
                            "es_venta_historica": (
                                prevalidacion_historica["es_venta_historica"]
                                if prevalidacion_historica is not None
                                else None
                            ),
                            "fecha_corte": command.fecha_corte,
                            "prevalidacion_historica": (
                                resumen_confirmacion_prevalidacion(prevalidacion_historica)
                                if prevalidacion_historica is not None
                                else None
                            ),
                        },
                    }
                )
        except _StageFailed as exc:
            return AppResult.fail(exc.error)

    def _normalizar_precios_y_total(
        self, command: ConfirmVentaDirectaCompletaCommand
    ) -> AppResult[Decimal]:
        if not command.objetos:
            return AppResult.fail("VENTA_WITHOUT_OBJECTS")

        monto_redundante = command.generar_venta.monto_total
        if monto_redundante is None:
            monto_redundante = command.condiciones_comerciales.monto_total
        precios: list[Decimal] = []
        seen_objects: set[tuple[str, int]] = set()
        ids_inmueble_payload: set[int] = set()
        ids_unidad_funcional_payload: set[int] = set()
        for objeto in command.objetos:
            if (objeto.id_inmueble is None) == (objeto.id_unidad_funcional is None):
                return AppResult.fail("INVALID_VENTA_OBJECTS")
            object_key = (
                ("inmueble", objeto.id_inmueble)
                if objeto.id_inmueble is not None
                else ("unidad_funcional", objeto.id_unidad_funcional)
            )
            if object_key in seen_objects:
                return AppResult.fail("OBJETO_VENTA_DUPLICADO")
            seen_objects.add(object_key)
            if objeto.id_inmueble is not None:
                ids_inmueble_payload.add(objeto.id_inmueble)
            elif objeto.id_unidad_funcional is not None:
                ids_unidad_funcional_payload.add(objeto.id_unidad_funcional)

        if self._hay_solapamiento_jerarquico_objetos(
            ids_inmueble_payload, ids_unidad_funcional_payload
        ):
            return AppResult.fail("OBJETO_VENTA_JERARQUIA_SOLAPADA")

        for objeto in command.objetos:
            precio = objeto.precio_asignado
            if precio is None:
                if len(command.objetos) == 1 and monto_redundante is not None:
                    precio = Decimal(str(monto_redundante))
                    objeto.precio_asignado = precio
                else:
                    return AppResult.fail("VALOR_ASIGNADO_OBJETO_REQUERIDO")

            precio_decimal = Decimal(str(precio))
            if precio_decimal <= 0:
                return AppResult.fail("VALOR_ASIGNADO_OBJETO_INVALIDO")
            objeto.precio_asignado = precio_decimal
            precios.append(precio_decimal)

        total_derivado = sum(precios, Decimal("0"))
        montos_redundantes = [
            command.generar_venta.monto_total,
            command.condiciones_comerciales.monto_total,
        ]
        for monto in montos_redundantes:
            if monto is not None and Decimal(str(monto)) != total_derivado:
                return AppResult.fail("SUMA_VALORES_OBJETOS_NO_COINCIDE_MONTO_VENTA")

        command.generar_venta.monto_total = total_derivado
        command.condiciones_comerciales.monto_total = total_derivado
        return AppResult.ok(total_derivado)

    def _hay_solapamiento_jerarquico_objetos(
        self,
        ids_inmueble_payload: set[int],
        ids_unidad_funcional_payload: set[int],
    ) -> bool:
        if not ids_inmueble_payload or not ids_unidad_funcional_payload:
            return False

        for id_unidad_funcional in ids_unidad_funcional_payload:
            id_inmueble_padre = (
                self.comercial_repository.get_id_inmueble_by_unidad_funcional(
                    id_unidad_funcional
                )
            )
            if id_inmueble_padre in ids_inmueble_payload:
                return True
        return False

    @staticmethod
    def _requiere_fecha_corte_historica(
        command: ConfirmVentaDirectaCompletaCommand,
    ) -> bool:
        fecha_venta = command.generar_venta.fecha_venta.date()
        tiene_bloque_indexado = any(
            (bloque.metodo_liquidacion or "").strip().upper() == "INDEXACION"
            for bloque in command.plan_pago_v2.bloques
        )
        # El sistema no cuenta aún con una fecha operativa persistida o enviada por
        # CORE-EF. Para este contrato, la fecha operativa de confirmación es el día
        # de ejecución de la aplicación; se usa exclusivamente para detectar una
        # venta histórica y nunca como sustituto de fecha_corte.
        return tiene_bloque_indexado and fecha_venta < date.today()

    def _plan_pago_v2_command(
        self, command: ConfirmVentaDirectaCompletaCommand, *, id_venta: int | None
    ) -> GeneratePlanPagoVentaV2PorBloquesCommand:
        return GeneratePlanPagoVentaV2PorBloquesCommand(
            context=command.context,
            id_venta=id_venta,
            tipo_pago=command.plan_pago_v2.tipo_pago,
            monto_total_plan=command.plan_pago_v2.monto_total_plan,
            moneda=command.plan_pago_v2.moneda,
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
                    cuotas_refuerzo=[
                        CuotaRefuerzoInput(
                            numero_cuota=cuota_refuerzo.numero_cuota,
                            etiqueta=cuota_refuerzo.etiqueta,
                            unidades_refuerzo=cuota_refuerzo.unidades_refuerzo,
                        )
                        for cuota_refuerzo in (bloque.cuotas_refuerzo or [])
                    ] or None,
                    observaciones=bloque.observaciones,
                )
                for bloque in command.plan_pago_v2.bloques
            ],
            observaciones=command.plan_pago_v2.observaciones,
        )

    @staticmethod
    def _total_objetos(command: ConfirmVentaDirectaCompletaCommand) -> Decimal:
        return sum(
            (Decimal(str(objeto.precio_asignado)) for objeto in command.objetos),
            Decimal("0"),
        )

    def _transaction(self) -> AbstractContextManager[Any]:
        if self.db.in_transaction():
            return self.db.begin_nested()
        return self.db.begin()

    def _venta_payload(
        self,
        command: ConfirmVentaDirectaCompletaCommand,
        *,
        id_instalacion: int,
    ) -> dict[str, Any]:
        now = datetime.now(UTC)
        op_id = self._op_id(command)
        return {
            "uid_global": str(self.uuid_generator()),
            "version_registro": 1,
            "created_at": now,
            "updated_at": now,
            "id_instalacion_origen": id_instalacion,
            "id_instalacion_ultima_modificacion": id_instalacion,
            "op_id_alta": op_id,
            "op_id_ultima_modificacion": op_id,
            "codigo_venta": command.generar_venta.codigo_venta,
            "fecha_venta": command.generar_venta.fecha_venta,
            "estado_venta": "borrador",
            "monto_total": self._total_objetos(command),
            "observaciones": command.generar_venta.observaciones,
        }

    def _objetos_payload(
        self,
        command: ConfirmVentaDirectaCompletaCommand,
        *,
        id_instalacion: int,
    ) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        op_id = self._op_id(command)
        return [
            {
                "uid_global": str(self.uuid_generator()),
                "version_registro": 1,
                "created_at": now,
                "updated_at": now,
                "id_instalacion_origen": id_instalacion,
                "id_instalacion_ultima_modificacion": id_instalacion,
                "op_id_alta": op_id,
                "op_id_ultima_modificacion": op_id,
                "id_inmueble": objeto.id_inmueble,
                "id_unidad_funcional": objeto.id_unidad_funcional,
                "precio_asignado": objeto.precio_asignado,
                "observaciones": objeto.observaciones,
            }
            for objeto in command.objetos
        ]

    def _compradores_payload(
        self,
        command: ConfirmVentaDirectaCompletaCommand,
        *,
        id_instalacion: int,
    ) -> list[dict[str, Any]]:
        now = datetime.now(UTC)
        op_id = self._op_id(command)
        return [
            {
                "uid_global": str(self.uuid_generator()),
                "version_registro": 1,
                "created_at": now,
                "updated_at": now,
                "id_instalacion_origen": id_instalacion,
                "id_instalacion_ultima_modificacion": id_instalacion,
                "op_id_alta": op_id,
                "op_id_ultima_modificacion": op_id,
                "id_persona": comprador.id_persona,
                "id_rol_participacion": comprador.id_rol_participacion,
                "porcentaje_responsabilidad": self._normalize_porcentaje_comprador(
                    comprador.porcentaje_responsabilidad,
                    total_compradores=len(command.compradores),
                ),
                "fecha_desde": comprador.fecha_desde or date.today(),
                "fecha_hasta": comprador.fecha_hasta,
                "observaciones": comprador.observaciones,
            }
            for comprador in command.compradores
        ]

    def _resolve_compradores_contextuales(
        self,
        command: ConfirmVentaDirectaCompletaCommand,
        *,
        id_instalacion: int,
    ) -> str | None:
        now = datetime.now(UTC)
        op_id = self._op_id(command)
        for comprador in command.compradores:
            if comprador.id_persona is not None:
                continue
            datos = comprador.datos_persona
            if datos is None:
                return "COMPRADOR_SIN_PERSONA"
            duplicado = self.comercial_repository.find_persona_duplicate_candidate(
                tipo_persona=datos.tipo_persona,
                nombre=datos.nombre,
                apellido=datos.apellido,
                razon_social=datos.razon_social,
                cuit_cuil=datos.cuit_cuil,
                documento=(
                    {
                        "tipo_documento": datos.documento_principal.tipo_documento,
                        "numero_documento": datos.documento_principal.numero_documento,
                    }
                    if datos.documento_principal is not None
                    else None
                ),
            )
            if duplicado is not None:
                tipo_duplicado = duplicado.get("tipo_duplicado")
                if tipo_duplicado == TipoDuplicadoPersona.FUERTE.value:
                    if self._same_op_id(duplicado.get("op_id_alta"), op_id):
                        comprador.id_persona = duplicado["id_persona"]
                        continue
                    return "PERSONA_DUPLICADA_REUTILIZAR_EXISTENTE"
                # El contrato actual de confirmación no tiene canal de warnings
                # no bloqueantes; los posibles duplicados quedan detectados en el
                # helper/repository sin impedir el alta contextual ni reutilizar
                # automáticamente una persona existente.

            persona = self.comercial_repository.create_persona_contextual_tx(
                {
                    "uid_global": str(self.uuid_generator()),
                    "version_registro": 1,
                    "tipo_persona": datos.tipo_persona.strip().upper(),
                    "nombre": datos.nombre.strip() if datos.nombre else None,
                    "apellido": datos.apellido.strip() if datos.apellido else None,
                    "razon_social": datos.razon_social.strip() if datos.razon_social else None,
                    "cuit_cuil": datos.cuit_cuil.strip() if datos.cuit_cuil else None,
                    "fecha_nacimiento_constitucion": None,
                    "estado_persona": "ACTIVA",
                    "fecha_alta": now,
                    "observaciones": "Alta contextual desde venta directa",
                    "created_at": now,
                    "updated_at": now,
                    "id_instalacion_origen": id_instalacion,
                    "id_instalacion_ultima_modificacion": id_instalacion,
                    "op_id_alta": op_id,
                    "op_id_ultima_modificacion": op_id,
                }
            )
            comprador.id_persona = persona["id_persona"]
            if datos.documento_principal is not None:
                self.comercial_repository.create_persona_documento_contextual_tx(
                    {
                        "uid_global": str(self.uuid_generator()),
                        "version_registro": 1,
                        "created_at": now,
                        "updated_at": now,
                        "id_instalacion_origen": id_instalacion,
                        "id_instalacion_ultima_modificacion": id_instalacion,
                        "op_id_alta": op_id,
                        "op_id_ultima_modificacion": op_id,
                        "id_persona": comprador.id_persona,
                        "tipo_documento": datos.documento_principal.tipo_documento.strip().upper(),
                        "numero_documento": datos.documento_principal.numero_documento.strip(),
                        "pais_emision": None,
                        "es_principal": True,
                        "fecha_desde": date.today(),
                        "fecha_hasta": None,
                        "observaciones": "Documento principal alta contextual venta",
                    }
                )
        return None

    def _validate_compradores(
        self, command: ConfirmVentaDirectaCompletaCommand
    ) -> str | None:
        if not command.compradores:
            return "COMPRADORES_REQUERIDOS"

        ids_persona: set[int] = set()
        porcentajes: list[Decimal] = []
        total_compradores = len(command.compradores)

        for comprador in command.compradores:
            if (comprador.id_persona is None) == (comprador.datos_persona is None):
                return "COMPRADOR_DEBE_INFORMAR_ID_O_DATOS_PERSONA"
            if comprador.datos_persona is not None:
                datos_error = self._validate_datos_persona_contextual(comprador.datos_persona)
                if datos_error is not None:
                    return datos_error
            if comprador.id_persona is not None and comprador.id_persona in ids_persona:
                return "COMPRADOR_DUPLICADO"
            if comprador.id_persona is not None:
                ids_persona.add(comprador.id_persona)

            porcentaje = self._normalize_porcentaje_comprador(
                comprador.porcentaje_responsabilidad,
                total_compradores=total_compradores,
            )
            if porcentaje is None:
                return "PORCENTAJE_COMPRADORES_NO_DEFINIDO"
            if porcentaje <= Decimal("0.00") or porcentaje > Decimal("100.00"):
                return "PORCENTAJE_COMPRADOR_INVALIDO"
            porcentajes.append(porcentaje)

        total = sum(porcentajes, Decimal("0.00")).quantize(Decimal("0.01"))
        if total != Decimal("100.00"):
            return "PORCENTAJE_COMPRADORES_NO_SUMA_100"
        return None

    @staticmethod
    def _validate_datos_persona_contextual(datos: Any) -> str | None:
        tipo = (datos.tipo_persona or "").strip().upper()
        if tipo == "FISICA":
            if not (datos.nombre or "").strip() or not (datos.apellido or "").strip():
                return "PERSONA_FISICA_NOMBRE_APELLIDO_REQUERIDOS"
        elif tipo == "JURIDICA":
            if not (datos.razon_social or "").strip():
                return "PERSONA_JURIDICA_RAZON_SOCIAL_REQUERIDA"
        else:
            return "TIPO_PERSONA_INVALIDO"
        if datos.documento_principal is not None:
            if not (datos.documento_principal.tipo_documento or "").strip():
                return "TIPO_DOCUMENTO_REQUERIDO"
            if not (datos.documento_principal.numero_documento or "").strip():
                return "NUMERO_DOCUMENTO_REQUERIDO"
        if not (datos.cuit_cuil or "").strip() and datos.documento_principal is None:
            return "IDENTIFICACION_PERSONA_REQUERIDA"
        return None

    @staticmethod
    def _normalize_porcentaje_comprador(
        porcentaje: Decimal | None, *, total_compradores: int
    ) -> Decimal | None:
        if porcentaje is None:
            if total_compradores == 1:
                return Decimal("100.00")
            return None
        return Decimal(str(porcentaje)).quantize(Decimal("0.01"))

    def _op_id(self, command: ConfirmVentaDirectaCompletaCommand) -> UUID | None:
        return getattr(command.context, "op_id", None)

    @staticmethod
    def _same_op_id(candidate_op_id: Any, current_op_id: UUID | None) -> bool:
        if candidate_op_id is None or current_op_id is None:
            return False
        return str(candidate_op_id) == str(current_op_id)
