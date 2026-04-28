# INT-FIN-002 - Resolucion de obligado financiero

## 1. Alcance

Este documento define la resolucion conceptual del obligado financiero para obligaciones originadas por:

1. venta
2. contrato locativo
3. servicios trasladados
4. expensas trasladadas
5. impuestos trasladados
6. cargos extraordinarios
7. liquidaciones finales

No implementa codigo, SQL, endpoints, consumers ni contratos tecnicos.

## 2. Principio rector

`financiero` genera la obligacion.

`financiero` no inventa el obligado.

El obligado debe resolverse desde dominios origen y soportes documentados:

1. `comercial`
2. `locativo`
3. `inmobiliario`
4. `personas`

El dominio financiero conserva ownership sobre:

1. `relacion_generadora`
2. `obligacion_financiera`
3. `composicion_obligacion`
4. `obligacion_obligado`

Pero no debe crear sujetos ni roles funcionales fuera de las fuentes de verdad de los dominios origen.

## 3. Entidad destino

La resolucion del obligado impacta en:

1. `obligacion_obligado`

Toda obligacion exigible debe tener al menos un obligado valido, salvo estado excepcional documentado.

Estado excepcional sugerido:

1. `PENDIENTE_RESOLUCION_OBLIGADO`

Ese estado queda `CONCEPTUAL` / `PENDIENTE` / `NO IMPLEMENTADO` hasta que exista soporte fisico, catalogo y contrato de servicio.

## 4. Regla general

Flujo conceptual:

```text
origen financiero
  -> relacion_generadora
  -> objeto / contrato / venta
  -> sujeto responsable
  -> obligacion_obligado
```

La `relacion_generadora` identifica el origen financiero formal.

La resolucion del sujeto responsable debe mirar el dominio origen y no reconstruirse por inferencia financiera aislada.

## 5. Fuentes de resolucion

### 5.1 Venta

Regla conceptual:

1. obligado = comprador / compradores asociados a la venta

Fuentes documentadas:

1. `venta`
2. `cliente_comprador`
3. `relacion_persona_rol`
4. `rol_participacion`

Notas:

1. `cliente_comprador` pertenece semanticamente a `comercial`, aunque exista referencia a `persona`.
2. `relacion_persona_rol` y `rol_participacion` son soporte transversal de asociacion y trazabilidad.
3. Si una venta tiene multiples compradores, la obligacion puede requerir multiples filas conceptuales en `obligacion_obligado`, segun regla financiera a formalizar.

### 5.2 Contrato locativo

Regla conceptual:

1. obligado = locatario / locatarios vigentes

Fuentes documentadas:

1. `contrato_alquiler`
2. `relacion_persona_rol`
3. `rol_participacion`

Obligados complementarios posibles:

1. garante
2. codeudor
3. fiador

Notas:

1. Los intervinientes del contrato locativo se resuelven por asociaciones contextuales, no como atributos base de `persona`.
2. Los roles de locatario, garante u otros roles locativos pertenecen semanticamente al dominio `locativo`.
3. La participacion de garante, codeudor o fiador como obligado financiero efectivo queda `PENDIENTE` de reglas financieras especificas.

### 5.3 Factura de servicio trasladado

Para `factura_servicio` bajo tipo_origen conceptual `SERVICIO_TRASLADADO`, la regla recomendada es:

1. si existe contrato locativo vigente sobre el objeto y periodo:
   obligado = locatario
2. si no existe contrato locativo vigente pero existe ocupacion vigente:
   obligado = ocupante responsable
3. si no existe ocupacion vigente:
   obligado = propietario / responsable operativo definido
4. si no puede resolverse:
   no generar obligacion exigible automaticamente
   dejar estado pendiente de resolucion

Estado sugerido:

1. `PENDIENTE_RESOLUCION_OBLIGADO`

Esta regla queda `CONCEPTUAL` / `PENDIENTE` / `NO IMPLEMENTADO` hasta que exista implementacion, contrato de integracion, entidad `factura_servicio`, evento `factura_servicio_registrada` y reglas fisicas para propietario / responsable operativo.

## 6. Resolucion por periodo

Para obligaciones asociadas a periodo, la resolucion debe considerar:

1. `fecha_emision`
2. `fecha_vencimiento`
3. `periodo_desde`
4. `periodo_hasta`

No alcanza con mirar solo el estado actual del inmueble o unidad funcional.

La resolucion debe evaluar el sujeto responsable durante el periodo alcanzado por la obligacion.

Si el periodo cruza cambios de contrato, ocupacion o responsable, la politica de prorrateo o seleccion de obligado queda `PENDIENTE`.

## 7. Prioridad de resolucion

Orden recomendado:

1. contrato vigente
2. ocupacion vigente
3. responsable operativo explicito
4. propietario
5. pendiente de resolucion

Este orden es conceptual y debe validarse contra contratos reales, SQL y reglas de dominio antes de implementarse.

## 8. Casos especiales

### 8.1 Varios obligados

Una obligacion puede requerir mas de un obligado cuando el origen tenga multiples sujetos responsables.

La politica de solidaridad, porcentaje, orden de cobro o responsabilidad proporcional queda `PENDIENTE`.

### 8.2 Locatarios solidarios

Cuando existan varios locatarios vigentes, pueden requerirse multiples obligados financieros.

La solidaridad locativa como efecto financiero queda `PENDIENTE` de formalizacion.

### 8.3 Compradores multiples

Cuando una venta tenga multiples compradores, la obligacion puede asociarse a todos ellos o a una regla de distribucion futura.

La distribucion exacta queda `PENDIENTE`.

### 8.4 Garantes

Garantes, codeudores o fiadores pueden actuar como obligados complementarios.

Su inclusion automatica como `obligacion_obligado` queda `PENDIENTE` de regla financiera explicita.

### 8.5 Obligado no resoluble

Si el obligado no puede resolverse con fuentes documentadas, no debe generarse deuda exigible automaticamente.

Estado sugerido:

1. `PENDIENTE_RESOLUCION_OBLIGADO`

Este estado queda `CONCEPTUAL` / `NO IMPLEMENTADO`.

### 8.6 Inmueble libre

Si el inmueble o unidad funcional esta libre y no existe contrato locativo ni ocupacion vigente, la resolucion debe intentar propietario / responsable operativo definido.

Si esa fuente no esta formalizada, la obligacion debe quedar pendiente de resolucion y no exigible automaticamente.

## 9. Integracion con factura_servicio

Flujo conceptual:

```text
factura_servicio
  -> SERVICIO_TRASLADADO
  -> relacion_generadora
  -> obligacion_financiera
  -> obligacion_obligado
```

La factura no define por si sola quien paga.

El obligado se resuelve cruzando:

1. objeto afectado
2. periodo
3. contrato
4. ocupacion
5. responsable operativo / propietario

`factura_servicio` y el evento conceptual `factura_servicio_registrada` quedan `PENDIENTE` / `NO IMPLEMENTADO`.

## 10. Responsabilidades por dominio

### 10.1 Inmobiliario

`inmobiliario` aporta:

1. objeto afectado
2. servicio asociado
3. factura registrada, cuando exista `factura_servicio`
4. disponibilidad
5. ocupacion

`inmobiliario` no decide deuda.

`inmobiliario` no crea `obligacion_financiera`.

### 10.2 Locativo

`locativo` aporta:

1. contrato vigente
2. locatarios
3. garantes
4. vigencia contractual
5. entrega / restitucion

`locativo` no calcula deuda financiera primaria.

### 10.3 Comercial

`comercial` aporta:

1. venta
2. compradores
3. participacion comercial

`comercial` no crea `obligacion_financiera` como fuente primaria del motor financiero.

### 10.4 Personas

`personas` aporta:

1. persona
2. roles de participacion
3. relaciones

`personas` no define por si mismo la semantica de comprador, locatario, garante u otros roles contextuales. Esa semantica pertenece al dominio origen.

### 10.5 Financiero

`financiero` crea:

1. `relacion_generadora`
2. `obligacion_financiera`
3. `composicion_obligacion`
4. `obligacion_obligado`

`financiero` no inventa sujetos fuera de dominios origen.

Si no puede resolver o recibir un obligado valido, no debe generar una obligacion exigible automatica.

## 11. Idempotencia

La resolucion debe ser deterministica para el mismo origen y periodo.

Para `factura_servicio`, la clave conceptual recomendada es:

1. `id_factura_servicio`

No debe generarse mas de una obligacion activa para la misma factura.

La idempotencia de `factura_servicio_registrada` queda `CONCEPTUAL` / `PENDIENTE` / `NO IMPLEMENTADO` hasta que exista contrato de evento real.

## 12. Estado de implementacion

Este documento es conceptual.

Queda `PENDIENTE`:

1. servicio formal de resolucion de obligado
2. contrato de integracion
3. endpoint o consumer
4. tabla `factura_servicio`
5. evento `factura_servicio_registrada`
6. reglas fisicas para propietario / responsable operativo
7. catalogo o estado fisico para `PENDIENTE_RESOLUCION_OBLIGADO`
8. politica de multiples obligados, solidaridad, porcentajes y prorrateo

## 13. Base documental

Esta decision se apoya en documentacion existente del workspace:

1. `DER-FINANCIERO`
2. `DER-COMERCIAL`
3. `DER-LOCATIVO`
4. `DEV-ARCH-PER-001`
5. `RN-FIN`
6. `RN-INM`
7. `RN-LOC`
8. `SRV-FIN-001`
9. `SRV-FIN-003`
10. `SRV-INM-005`
11. `SYS-MAP-002`

## 14. Contradicciones y limites

1. `factura_servicio` no existe como tabla formal documentada e implementada en el workspace.
2. `factura_servicio_registrada` no existe como evento implementado.
3. `propietario` / `responsable operativo` para este circuito no tiene regla fisica final documentada.
4. `PENDIENTE_RESOLUCION_OBLIGADO` es un estado sugerido conceptual, no un estado implementado.
5. Este documento no modifica ownership de ningun dominio.
