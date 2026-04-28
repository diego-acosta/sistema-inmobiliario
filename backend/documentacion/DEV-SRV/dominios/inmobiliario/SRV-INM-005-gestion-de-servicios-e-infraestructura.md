# SRV-INM-005 - Gestion de servicios e infraestructura

## Estado del servicio
- clasificacion: `PARCIAL`
- fuente de verdad implementada: SQL `servicio`, `inmueble_servicio`, `unidad_funcional_servicio`, `servicios_router.py`, `inmuebles_router.py`, tests de servicios y asociaciones
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

## Funcionalidad disponible
- CRUD basico de `servicio`
- asociacion de servicios a inmuebles y unidades funcionales
- control de duplicados activos en aplicacion y, para `inmueble_servicio`, tambien en DB

## Funcionalidad pendiente
- modelar `infraestructura` como entidad propia: `NO IMPLEMENTADO`
- catalogos especializados de cobertura o capacidad del servicio: `CONCEPTUAL`
- registrar factura de servicio emitida por proveedor externo: `SQL IMPLEMENTADO` / `API-BACKEND-EVENTO-CONSUMER NO IMPLEMENTADOS`
- disparar integracion con `financiero` para generar obligacion derivada de una factura de servicio externa: `NO IMPLEMENTADO`

## Registro de facturas externas de servicios (PENDIENTE)

### Clasificacion
- `servicio`: soporte transversal del activo inmobiliario.
- asociacion `inmueble_servicio` / `unidad_funcional_servicio`: soporte transversal.
- `factura_servicio`: tabla SQL estructural implementada, vinculada al servicio y al activo alcanzado; sin API/backend funcional vigente.
- obligacion financiera derivada: nucleo del dominio `financiero`.

### Definicion del concepto
`factura_servicio` representa el registro interno, implementado solo a nivel SQL estructural, de una factura emitida por un proveedor externo de servicios como agua, luz, gas u otros servicios asociados a un objeto inmobiliario.

El sistema no factura servicios. La tabla SQL permite estructurar el origen operativo recibido del proveedor, pero no existe API/backend para registrarlo funcionalmente ni circuito financiero implementado.

### Regla de ownership
El sistema no factura servicios. La factura es emitida por un proveedor externo.

El dominio inmobiliario solo registra el origen operativo de esa factura externa. Hoy ese soporte existe solo en SQL estructural; no existe API/backend para operar el registro. Ese registro no debe calcular deuda como fuente primaria, no debe emitir comprobantes y no debe reemplazar la obligacion financiera.

El dominio `financiero` es el responsable de crear la `relacion_generadora`, generar la `obligacion_financiera` y sus `composicion_obligacion` cuando reciba un origen compatible.

El dominio `operativo` no adquiere ownership sobre esta factura. Su alcance vigente sigue limitado a sucursales, instalaciones, caja operativa, movimientos de caja, cierre de caja y consultas operativas.

### Flujo conceptual
1. un proveedor externo emite una factura por un servicio asociado a un inmueble o unidad funcional.
2. el sistema registra la factura externa como origen operativo pendiente del dominio inmobiliario, vinculandola al `servicio` y al activo alcanzado.
3. ese registro publicaria el evento conceptual pendiente `factura_servicio_registrada`.
4. `financiero` valida el origen, crea o reutiliza la `relacion_generadora` que corresponda y genera la obligacion financiera derivada.
5. pagos, imputaciones, mora, ajustes, saldos y reportes financieros quedan fuera del dominio inmobiliario.

Representacion resumida:

`factura externa` -> `registro SQL estructural disponible / API pendiente` -> `factura_servicio_registrada` (evento NO IMPLEMENTADO) -> `financiero genera obligacion` (NO IMPLEMENTADO)

La integracion debe ser event-driven a nivel conceptual: `inmobiliario` publica el hecho de registro y `financiero` reacciona sin que `inmobiliario` cree obligaciones ni ejecute logica financiera.

El evento conceptual pendiente `factura_servicio_registrada` debe ser idempotente. La clave conceptual recomendada es `id_factura_servicio`; el consumidor financiero no debe crear obligaciones duplicadas ante reintentos del mismo evento.

### Estado de implementacion
- `factura_servicio` existe como tabla SQL estructural.
- no existe hoy API/backend inmobiliario para registrar facturas de servicio externas.
- no existe hoy evento implementado que represente el registro de factura externa; `factura_servicio_registrada` es solo un nombre conceptual pendiente de contrato/evento real.
- no existe consumer financiero para `factura_servicio_registrada`.
- no se genera `relacion_generadora` ni `obligacion_financiera` desde `factura_servicio`.
- la integracion con `financiero` queda pendiente hasta definir contrato, API/backend, evento y consumer.

### Relacion conceptual con financiero
- `factura_servicio` actua como origen conceptual de `SERVICIO_TRASLADADO`.
- decision recomendada: 1 servicio asociado a inmueble o unidad funcional -> 1 `relacion_generadora` en `financiero`.
- decision recomendada: esa `relacion_generadora` puede existir antes de la primera `factura_servicio`.
- decision recomendada: cada `factura_servicio` posterior -> 1 `obligacion_financiera` dentro de esa misma `relacion_generadora`.
- esta decision queda `PENDIENTE` de implementacion funcional y no implica API/backend, eventos, consumers ni generacion financiera existentes.

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
