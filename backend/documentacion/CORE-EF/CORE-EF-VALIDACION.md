# CORE-EF-VALIDACION — Checklist de validación transversal

## Objetivo
Validar que la arquitectura funcional, documental y técnica del sistema se encuentre alineada con CORE-EF-001 antes de pasar a DEV-API e implementación.

## Alcance
Aplica a todos los dominios del sistema y a toda operación write/read que participe en:
- persistencia
- sincronización
- auditoría
- versionado
- concurrencia
- idempotencia
- trazabilidad

## 0. Clasificación de entidades

### Definición
Una entidad sincronizable es toda entidad que:
- deba replicarse entre instalaciones
- participe en operaciones distribuidas
- afecte estado de negocio compartido

Una entidad no sincronizable es toda estructura cuyo alcance sea local, derivado o técnico sin necesidad de replicación distribuida.

### Ejemplos típicos
- persona
- inmueble
- contrato
- obligación
- documento

### No sincronizables
- logs internos
- datos temporales
- caches
- estructuras derivadas

### Checklist
- [ ] Cada dominio declara explícitamente qué entidades son sincronizables.
- [ ] Cada dominio distingue entidades de negocio de estructuras derivadas o locales.
- [ ] No se marcan como sincronizables datos efímeros o técnicos sin valor distribuido.
- [ ] Las entidades compartidas entre instalaciones están identificadas como sincronizables.

---

## 1. Identidad global

### Validaciones obligatorias
- Toda entidad sincronizable debe tener `uid_global`.
- `uid_global` debe ser inmutable.
- `uid_global` no debe reutilizarse.
- El sistema no debe usar ID local como identidad distribuida.
- Toda sincronización y comparación remota debe operar por `uid_global`.

### Checklist
- [ ] El dominio define identidad global para cada entidad sincronizable.
- [ ] Las entidades sincronizables tienen `uid_global` explícito.
- [ ] No hay operaciones distribuidas basadas en ID local.
- [ ] La trazabilidad remota referencia identidad global y no claves locales.

---

## 2. Versionado de registros

### Validaciones obligatorias
- Toda entidad sincronizable debe tener `version_registro`.
- Toda operación write debe validar versión esperada cuando aplique.
- Toda modificación válida debe incrementar `version_registro`.
- No debe existir overwrite silencioso.

### Checklist
- [ ] Las entidades sincronizables contemplan `version_registro`.
- [ ] Los writes críticos validan versión esperada.
- [ ] La política de incremento de versión está explicitada.
- [ ] Los errores de versión inválida están contemplados en catálogos.
- [ ] No hay mutaciones silenciosas sobre registros compartidos.

---

## 3. Timestamps y trazabilidad temporal

### Validaciones obligatorias
- Las entidades persistentes deben manejar timestamps consistentes.
- Debe poder distinguirse creación, modificación y baja lógica cuando aplique.
- Las lecturas históricas y a fecha deben apoyarse en trazabilidad temporal consistente.
- Los eventos derivados de operaciones write deben mantener orden lógico consistente.

### Checklist
- [ ] Los dominios contemplan timestamps mínimos consistentes.
- [ ] Existe criterio uniforme para creación, actualización y baja lógica.
- [ ] Las consultas históricas o a fecha tienen soporte temporal coherente.
- [ ] No se procesan eventos posteriores si falta aplicar un evento previo necesario para preservar consistencia temporal.
- [ ] No hay lecturas históricas apoyadas en datos sin trazabilidad temporal suficiente.

---

## 4. Clasificación de operaciones

### Tipos de operaciones

#### Write sincronizable
- requiere `uid_global`
- requiere `version_registro`
- requiere `op_id`
- genera outbox
- participa en trazabilidad distribuida

#### Write no sincronizable
- no requiere `op_id`
- no genera outbox
- su impacto es local
- no debe confundirse con mutación distribuida

### Regla obligatoria
Todo caso de uso write debe declarar explícitamente si es sincronizable o no sincronizable.

### Checklist
- [ ] Cada caso de uso write declara su tipo.
- [ ] No existen writes ambiguos respecto de sincronización.
- [ ] Los writes sincronizables exigen los artefactos transversales requeridos.
- [ ] Los writes no sincronizables están documentados como locales.
- [ ] La documentación distingue claramente write sincronizable de write no sincronizable.

---

## 5. op_id

### Validaciones obligatorias
- Toda operación write sincronizable debe usar `op_id`.
- `op_id` debe ser globalmente único por operación distribuida.
- Mismo `op_id` con distinto payload debe considerarse conflicto.
- `op_id` debe formar parte de la trazabilidad operativa.

### Checklist
- [ ] Los writes sincronizables exigen `op_id`.
- [ ] Los errores por `op_id` duplicado están contemplados.
- [ ] La auditoría y trazabilidad pueden enlazarse con `op_id`.
- [ ] No existen operaciones distribuidas relevantes sin identidad de operación.

---

## 6. Outbox / Inbox

### Validaciones obligatorias
- Todo write sincronizable debe generar outbox en la misma transacción.
- No debe existir write sincronizable sin outbox.
- Inbox y outbox deben permitir trazabilidad de emisión y recepción.
- La sincronización no debe depender de memoria o procesos efímeros.
- La generación de outbox debe ser atómica con el write principal.
- No debe existir persistencia de estado sin su correspondiente evento en outbox cuando la operación sea sincronizable.

### Checklist
- [ ] Los writes sincronizables declaran outbox.
- [ ] El sistema distingue operaciones con y sin sincronización.
- [ ] El dominio técnico contempla inbox y outbox.
- [ ] No hay eventos distribuibles fuera de una transacción consistente.
- [ ] La recepción remota cuenta con trazabilidad suficiente en inbox o estructura equivalente.
- [ ] La persistencia del write y la generación de outbox se validan como una única unidad transaccional.

---

## 7. Idempotencia

### Validaciones obligatorias
- Toda operación distribuida relevante debe ser idempotente.
- Mismo `op_id` + mismo payload = reintento válido.
- Mismo `op_id` + distinto payload = conflicto.
- La idempotencia debe estar contemplada en diseño, errores y validaciones.

### Checklist
- [ ] Los dominios críticos contemplan reintentos seguros.
- [ ] Existen errores de idempotencia normalizados.
- [ ] La documentación no deja writes sensibles sin estrategia idempotente.
- [ ] Los reintentos válidos no generan efectos duplicados.

---

## 8. Locks lógicos

### Validaciones obligatorias
- Las operaciones críticas deben definir si requieren lock lógico.
- El lock lógico debe impedir modificaciones concurrentes incompatibles.
- Debe existir error explícito para lock activo.
- No debe asumirse exclusividad implícita no documentada.
- El lock lógico debe aplicarse sobre la entidad o agregado afectado.
- El scope del lock debe ser explícito.

### Checklist
- [ ] Los writes críticos definen si usan lock.
- [ ] Existen errores por lock lógico activo.
- [ ] Los dominios sensibles tienen criterio explícito de lock.
- [ ] No hay mutaciones críticas que dependan de exclusividad implícita.
- [ ] El scope del lock lógico está definido explícitamente por entidad, agregado o recurso crítico.
- [ ] No se usan locks excesivamente amplios ni locks ambiguos.

---

## 9. Conflictos de sincronización

### Política mínima obligatoria
- conflictos de versión: error
- conflictos de `op_id` con mismo payload: idempotente
- conflictos de `op_id` con distinto payload: error
- conflictos de negocio críticos: resolución explícita
- no se permite `last write wins` por defecto

### Checklist
- [ ] Los conflictos de versión están tratados como error explícito.
- [ ] La política de `op_id` distingue repetición válida de conflicto real.
- [ ] Los conflictos de negocio críticos no se resuelven en silencio.
- [ ] No se usa `last write wins` sin definición formal y excepcional.
- [ ] Los errores y estados de conflicto están modelados en catálogos.

---

## 10. Borrado lógico

### Validaciones obligatorias
- La baja lógica debe preservar historia.
- No debe reemplazarse baja lógica por borrado físico en entidades de negocio.
- Debe existir criterio uniforme para reactivación cuando aplique.

### Checklist
- [ ] Los dominios usan baja lógica de forma consistente.
- [ ] No se destruye historia relevante.
- [ ] Reactivación y vigencia están definidas cuando corresponda.
- [ ] No hay borrado físico de entidades de negocio con valor histórico.

---

## 11. Separaciones conceptuales críticas

### Validaciones obligatorias
- No fusionar usuario con persona.
- No fusionar documento con entidad principal.
- No fusionar movimiento financiero con tesorería.
- No fusionar sucursal con instalación.
- No fusionar disponibilidad, ocupación y estado como si fueran lo mismo.

### Checklist
- [ ] Las separaciones conceptuales están preservadas.
- [ ] No hay colapso indebido entre dominios.
- [ ] Los catálogos de dominio respetan límites claros de responsabilidad.
- [ ] Los read models no redefinen entidades ni mezclan conceptos base del sistema.

---

## 12. Lecturas y cálculos

### Validaciones obligatorias
- Las operaciones read no generan efectos persistentes.
- Los cálculos dinámicos a fecha son válidos si no redefinen la lógica del dominio.
- Las consultas no deben producir side effects.
- Las lecturas no deben duplicar la lógica primaria del dominio fuente.

### Checklist
- [ ] Las operaciones read no persisten cambios ni generan outbox.
- [ ] No existen side effects en consultas o reportes.
- [ ] Los cálculos dinámicos a fecha se apoyan en reglas del dominio fuente.
- [ ] El cálculo financiero permanece centralizado en el dominio financiero.
- [ ] No hay lógica duplicada en lecturas analíticas o consolidadas.

---

## 13. Resultado de la auditoría

### Estado esperado
- Arquitectura funcional alineada con CORE-EF-001.
- Dominios con reglas compatibles con sincronización y concurrencia.
- Catálogos de errores, eventos y estados alineados con operaciones distribuidas.
- Separaciones conceptuales preservadas.
- Base lista para DEV-API.

### Pendientes a validar
- explicitar entidades sincronizables por dominio
- formalizar clasificación de writes por tipo
- formalizar política de versionado en writes
- explicitar `op_id` en operaciones sincronizables
- formalizar obligación de outbox transaccional
- explicitar criterio mínimo de locks lógicos
- explicitar política mínima de resolución de conflictos
- verificar soporte temporal uniforme para consultas históricas o a fecha

---

## 14. Conclusión

El sistema puede considerarse listo para pasar a DEV-API solo si:
- los dominios respetan las obligaciones transversales de CORE-EF,
- no quedan huecos críticos en versionado, `op_id`, outbox, idempotencia, locks y conflictos,
- cada write está clasificado correctamente,
- y la separación conceptual entre dominios se mantiene intacta.

## Notas
- Este documento no reemplaza CORE-EF-001.
- Funciona como checklist de validación arquitectónica.
- Debe usarse como referencia previa a DEV-API e implementación backend.
- Puede evolucionar como hoja de control de revisión técnica.
