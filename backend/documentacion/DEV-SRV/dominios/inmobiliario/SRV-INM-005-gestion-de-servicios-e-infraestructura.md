# SRV-INM-005 - Gestion de servicios e infraestructura

## Estado del servicio
- clasificacion: `PARCIAL`
- fuente de verdad implementada: SQL `servicio`, `inmueble_servicio`, `unidad_funcional_servicio`, `factura_servicio`, `asignacion_servicio_responsable`, `servicios_router.py`, `inmuebles_router.py`, `financiero_router.py`, tests de servicios, asociaciones, facturas de servicio y materializacion financiera
- nota: el termino `infraestructura` se conserva solo para referencia historica del documento

## Modelo implementado
- entidad gestionada: `servicio`
- relaciones implementadas:
  - `inmueble_servicio`
  - `unidad_funcional_servicio`
- operaciones disponibles:
  - `POST /api/v1/servicios`
  - `GET /api/v1/servicios/{id_servicio}`
  - `GET /api/v1/servicios`
  - `PUT /api/v1/servicios/{id_servicio}`
  - `PUT /api/v1/servicios/{id_servicio}/baja`
  - `POST /api/v1/inmuebles/{id_inmueble}/servicios`
  - `GET /api/v1/inmuebles/{id_inmueble}/servicios`
  - `GET /api/v1/servicios/{id_servicio}/inmuebles`
  - `POST /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios`
  - `GET /api/v1/unidades-funcionales/{id_unidad_funcional}/servicios`
  - `GET /api/v1/servicios/{id_servicio}/unidades-funcionales`
  - `POST /api/v1/facturas-servicio`
  - `GET /api/v1/facturas-servicio/{id_factura_servicio}`
  - `GET /api/v1/facturas-servicio`

## Funcionalidad disponible
- CRUD basico de `servicio`
- asociacion de servicios a inmuebles y unidades funcionales
- control de duplicados activos en aplicacion y, para `inmueble_servicio`, tambien en DB
- registro y consulta V1 de `factura_servicio` como factura externa de proveedor asociada a inmueble o unidad funcional
- materializacion financiera V1 explicita desde `factura_servicio` hacia `SERVICIO_TRASLADADO` en el dominio `financiero`

## Funcionalidad pendiente
- modelar `infraestructura` como entidad propia: `NO IMPLEMENTADO`
- catalogos especializados de cobertura o capacidad del servicio: `CONCEPTUAL`
- evento `factura_servicio_registrada`: `NO IMPLEMENTADO`
- consumer/evento automatico para generar obligacion derivada de una factura de servicio externa: `NO IMPLEMENTADO`
- flujo `EMPRESA_PAGA_Y_RECUPERA` para facturas comunes, compartidas,
  porcentuales o repartidas: `PENDIENTE`. Requiere diseno propio de recupero
  financiero/operativo; la automatizacion desde una factura pagada por la
  empresa no esta implementada.

## Registro de facturas externas de servicios (V1 IMPLEMENTADO)

### Clasificacion
- `servicio`: soporte transversal del activo inmobiliario.
- asociacion `inmueble_servicio` / `unidad_funcional_servicio`: soporte transversal.
- `factura_servicio`: nucleo del registro inmobiliario de factura externa recibida; implementado en SQL y API/backend V1.
- obligacion financiera derivada: nucleo del dominio `financiero`.

### Definicion del concepto
`factura_servicio` representa el registro interno de una factura emitida por un proveedor externo de servicios como agua, luz, gas u otros servicios asociados a un objeto inmobiliario.

El sistema no factura servicios. La API V1 registra el origen operativo recibido
del proveedor. La materializacion financiera es una operacion explicita del
dominio `financiero`; no es emision de factura ni logica financiera del dominio
inmobiliario.

La factura externa puede registrarse sin `periodo_desde` y/o `periodo_hasta`
como dato operativo/documental recibido. Ese registro no implica que sea
materializable financieramente.

### Decision operativa sobre pago directo y recupero

V1 distingue dos escenarios:

1. `DIRECTO_RESPONSABLE`
- aplica solo cuando la factura corresponde directamente a una persona
  responsable.
- en V1 debe interpretarse como responsabilidad 100% de una persona.
- el responsable puede pagar directamente al proveedor.
- financiero puede registrar `PAGO_EXTERNO_INFORMADO`.
- no impacta caja/tesoreria ni genera recibo interno.

2. `EMPRESA_PAGA_Y_RECUPERA`
- aplica cuando la factura es comun, compartida, porcentual o debe repartirse
  entre empresa e inquilino/comprador, o entre varias personas.
- la empresa/inmobiliaria paga al proveedor; ese pago pertenece al circuito de
  egreso, caja y tesoreria de la empresa.
- luego se genera una obligacion de recupero a los responsables por la parte
  correspondiente.
- la obligacion de recupero representa deuda con la empresa, no pago al
  proveedor.
- el concepto financiero de recupero queda pendiente de decision
  (`EXPENSA_TRASLADADA`, `SERVICIO_RECUPERADO`, `CARGO_COMUN` u otro).
- en V1 la generacion de recupero es manual/controlada; la automatizacion desde
  una factura pagada queda pendiente.

`porcentaje_responsabilidad` de `asignacion_servicio_responsable` no debe
interpretarse como porcentaje que cada persona paga directamente al proveedor.
Si una factura requiere reparto, no corresponde registrar
`PAGO_EXTERNO_INFORMADO` por cada persona.

### Regla de ownership
El sistema no factura servicios. La factura es emitida por un proveedor externo.

El dominio inmobiliario solo registra el origen operativo de esa factura externa. Ese registro no debe calcular deuda como fuente primaria, no debe emitir comprobantes y no debe reemplazar la obligacion financiera.

El dominio `financiero` es el responsable de crear la `relacion_generadora`, generar la `obligacion_financiera` y sus `composicion_obligacion` cuando reciba un origen compatible.

El dominio `operativo` no adquiere ownership sobre esta factura. Su alcance vigente sigue limitado a sucursales, instalaciones, caja operativa, movimientos de caja, cierre de caja y consultas operativas.

### Flujo conceptual
1. un proveedor externo emite una factura por un servicio asociado a un inmueble o unidad funcional.
2. el sistema registra la factura externa como origen operativo pendiente del dominio inmobiliario, vinculandola al `servicio` y al activo alcanzado.
3. V1 no publica evento.
4. `financiero`, mediante endpoint explicito, valida el origen, crea o reutiliza la `relacion_generadora` que corresponda y genera la obligacion financiera derivada.
5. pagos, imputaciones, mora, ajustes, saldos y reportes financieros quedan fuera del dominio inmobiliario.

Representacion resumida:

`factura externa` -> `POST /api/v1/facturas-servicio` -> `factura_servicio` registrada -> `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/materializar` -> `relacion_generadora FACTURA_SERVICIO` -> `obligacion_financiera SERVICIO_TRASLADADO`

La integracion debe ser event-driven a nivel conceptual futuro: `inmobiliario` publicaria el hecho de registro y `financiero` reaccionaria sin que `inmobiliario` cree obligaciones ni ejecute logica financiera.

El evento conceptual pendiente `factura_servicio_registrada` debe ser idempotente. La clave conceptual recomendada es `id_factura_servicio`; el consumidor financiero no debe crear obligaciones duplicadas ante reintentos del mismo evento.

### Estado de implementacion
- `factura_servicio` existe como tabla SQL estructural.
- existe API/backend inmobiliario V1 para registrar y consultar facturas de servicio externas.
- endpoints V1: `POST /api/v1/facturas-servicio`, `GET /api/v1/facturas-servicio/{id_factura_servicio}`, `GET /api/v1/facturas-servicio`.
- la API valida XOR entre `id_inmueble` e `id_unidad_funcional`, servicio activo asociado al activo, fechas, importe no negativo y duplicado activo por proveedor + numero.
- el registro operativo/documental permite `periodo_desde` y `periodo_hasta`
  nulos.
- no existe hoy evento implementado que represente el registro de factura externa; `factura_servicio_registrada` es solo un nombre conceptual pendiente de contrato/evento real.
- no existe consumer financiero para `factura_servicio_registrada`.
- la generacion automatica por evento/consumer sigue pendiente.
- existe materializacion financiera explicita: `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/materializar`.
- la materializacion crea o reutiliza `relacion_generadora FACTURA_SERVICIO` y crea `obligacion_financiera SERVICIO_TRASLADADO` con composicion y obligados resueltos desde `asignacion_servicio_responsable`.
- para materializar, financiero exige periodo completo en la factura
  (`periodo_desde` y `periodo_hasta`). Si falta alguno, devuelve
  `PERIODO_FACTURA_REQUERIDO` y no crea `relacion_generadora`,
  `obligacion_financiera`, `composicion_obligacion` ni `obligacion_obligado`.
- existe registro financiero de pago externo informado:
  `POST /api/v1/financiero/facturas-servicio/{id_factura_servicio}/pago-externo`.
  Este flujo corresponde solo al escenario `DIRECTO_RESPONSABLE`: una persona
  responsable al 100% paga directamente al proveedor y se informa para reducir
  o cancelar `SERVICIO_TRASLADADO`; no es cobro de la inmobiliaria, no genera
  caja, tesoreria ni constancia interna de cobro.
- el endpoint de pago externo valida que la obligacion materializada tenga
  exactamente un `obligacion_obligado` activo y que su
  `porcentaje_responsabilidad` sea 100. Si no se cumple, devuelve
  `PAGO_EXTERNO_REQUIERE_RESPONSABLE_UNICO`.
- no se permite `PAGO_EXTERNO_INFORMADO` cuando la factura sea comun,
  compartida, porcentual o tenga reparto entre varias personas. Esos casos
  corresponden a `EMPRESA_PAGA_Y_RECUPERA`.

## Asignacion de responsables de servicios trasladados (IMPLEMENTADO V1)

### Decision
Para V1, la resolucion del responsable de un servicio trasladado no se infiere rigidamente desde alquiler, venta u ocupacion, ni usa `relacion_persona_rol` como solucion final. Se define una entidad especifica del dominio inmobiliario:

`asignacion_servicio_responsable`

Su funcion es definir quien responde por un servicio trasladado sobre un inmueble o unidad funcional en una vigencia determinada.

### Modelo conceptual

`servicio`
-> `inmueble_servicio` / `unidad_funcional_servicio`
-> `asignacion_servicio_responsable`
-> `factura_servicio`
-> `relacion_generadora FACTURA_SERVICIO`
-> `obligacion_financiera SERVICIO_TRASLADADO`
-> `obligacion_obligado`

### Reglas V1
- La asignacion se vincula directamente por `id_servicio` + `id_inmueble` o `id_unidad_funcional`.
- No se vincula por FK directa a `inmueble_servicio` ni a `unidad_funcional_servicio`.
- Debe distinguir por XOR si aplica a inmueble o unidad funcional.
- `id_persona` es obligatorio.
- `porcentaje_responsabilidad` es obligatorio.
- La suma de porcentajes activos aplicables al mismo servicio + objeto + tramo vigente debe ser 100%.
- La suma 100% resuelve obligados para materializacion financiera, pero no
  significa que cada persona deba pagar directamente su porcentaje al proveedor.
- Si una `factura_servicio` no tiene responsable vigente aplicable, financiero debe devolver `OBLIGADO_NO_RESUELTO`.
- Si una `factura_servicio` no tiene periodo completo, financiero debe devolver
  `PERIODO_FACTURA_REQUERIDO` antes de resolver responsables y antes de crear
  filas financieras.
- Si existen responsables inconsistentes o porcentajes activos que no suman 100%, debe devolverse `RESPONSABLE_SERVICIO_AMBIGUO`.
- Si la factura cruza un cambio de responsable, debe devolverse `FACTURA_CRUZA_CAMBIO_RESPONSABLE`.
- V1 no prorratea por cambio de responsable dentro del periodo de factura.
- V1 no usa composiciones negativas ni saldos a favor para resolver cambios de responsable.
- Expensas e impuestos siguen fuera de alcance de este bloque.

### Endpoints V1
- `POST /api/v1/asignaciones-servicio-responsable`
- `GET /api/v1/asignaciones-servicio-responsable/{id_asignacion_servicio_responsable}`
- `GET /api/v1/asignaciones-servicio-responsable`
- `PUT /api/v1/asignaciones-servicio-responsable/{id_asignacion_servicio_responsable}`
- `PATCH /api/v1/asignaciones-servicio-responsable/{id_asignacion_servicio_responsable}/baja`

### Estado
- Implementado como SQL/API/backend V1.
- No genera por si misma `relacion_generadora`, `obligacion_financiera` ni `obligacion_obligado`.
- La materializacion financiera queda en el dominio `financiero`.

### Relacion conceptual con financiero
- `factura_servicio` actua como origen conceptual de `SERVICIO_TRASLADADO`.
- decision V1: cada `factura_servicio` registrada -> 1 `relacion_generadora` financiera propia.
- decision V1: `relacion_generadora.tipo_origen = FACTURA_SERVICIO`.
- decision V1: `relacion_generadora.id_origen = id_factura_servicio`.
- decision V1: la obligacion derivada usa el concepto financiero `SERVICIO_TRASLADADO`.
- motivo: idempotencia directa por factura, trazabilidad simple factura -> obligacion, sin entidad intermedia de servicio facturable y alineado con el modelo actual de `relacion_generadora`.
- la resolucion de responsables para V1 se apoya en la entidad especifica `asignacion_servicio_responsable`.
- si una persona responsable al 100% paga directamente al proveedor
  (`DIRECTO_RESPONSABLE`), financiero puede registrar
  `PAGO_EXTERNO_INFORMADO` contra la obligacion materializada; inmobiliario no
  registra pagos, caja ni recibos.
- si la factura es comun, compartida, porcentual o repartida, no corresponde
  usar `PAGO_EXTERNO_INFORMADO` por persona. La decision operativa es
  `EMPRESA_PAGA_Y_RECUPERA`: la empresa paga al proveedor y luego genera una
  obligacion de recupero por la parte correspondiente.
- expensas e impuestos no se implementan en este bloque.
- esta decision esta implementada mediante endpoint financiero explicito; la generacion automatica por evento/consumer sigue pendiente.

## Modelo conceptual futuro
- si el negocio necesita distinguir infraestructura fisica de servicio, debe aparecer como modelo nuevo y no como alias de `servicio`
- si el negocio necesita registrar facturas externas de servicios, debe incorporarse como registro de origen operativo vinculado al activo y al servicio, no como facturacion propia del sistema

## Fuera de alcance
- `infraestructura` como entidad tecnica transversal
- ownership sobre `instalacion`
- emision de facturas de servicio
- calculo de deuda, saldo, pago, imputacion, mora o ajuste financiero
- gestion semantica de proveedor como identidad base
- caja operativa o movimientos de caja

## Referencias
- [[SRV-INM-002-gestion-de-inmuebles]]
- [[SRV-INM-003-gestion-de-unidades-funcionales]]
