# DEV-ARCH-PER-001 — Freeze arquitectónico del dominio Personas

## 1. Objetivo
Congelar el criterio arquitectónico vigente del dominio `personas` para asegurar alineación entre `SYS-MAP-002`, `DEV-SRV`, `DEV-API-PER-001`, el SQL real del dominio y los ajustes recientes de `SRV-PER-004` y `SRV-PER-006`.

## 2. Alcance del dominio
El dominio `personas` incluye:
- persona base
- identidad y documentación
- domicilios
- contactos
- relaciones entre personas
- representación y poderes

Además, por compatibilidad con el modelo e implementación existentes, actualmente también incluye:
- participación contextual en operaciones de otros dominios
- `rol_participacion`
- `relacion_persona_rol`
- presencia de `cliente_comprador` en SQL

El dominio no debe interpretarse como dueño semántico de:
- compraventa
- locación
- condición funcional de cliente
- semántica de negocio externa derivada de roles contextuales

## 3. Responsabilidad del dominio
El dominio `personas` es responsable de definir al sujeto base del sistema y sus atributos propios.

Su responsabilidad incluye:
- identificar a la persona como referencia transversal
- mantener su documentación identificatoria
- mantener domicilios y contactos
- modelar relaciones estructurales entre personas
- modelar representación y poderes
- sostener asociaciones contextuales existentes cuando el modelo real ya las materializa

No le corresponde:
- definir lógica comercial
- definir lógica locativa
- definir la semántica de cliente como entidad de negocio
- absorber el dominio de usuario administrativo

## 4. Límites del dominio

### con comercial
`personas` provee el sujeto base y puede sostener asociaciones contextuales existentes como `relacion_persona_rol`.

`comercial` define la semántica de negocio de comprador, vendedor, cliente comprador y demás roles propios de compraventa.

La existencia de `cliente_comprador` en SQL no convierte a `personas` en dueño semántico del dominio comercial.
`personas` no debe resolver reglas de elegibilidad, condición comercial ni estado de relación comercial.

### con locativo
`personas` provee el sujeto base y puede participar en asociaciones contextuales utilizadas por contratos y operaciones locativas.

`locativo` define la semántica de negocio de locatario, garante y demás roles del circuito locativo.

Los roles contextuales locativos no deben interpretarse como atributos base de `persona`.

### con financiero
`personas` provee sujetos y referencias personales que pueden ser usadas por relaciones financieras, obligaciones o consultas.

`financiero` define la semántica de deuda, pago, imputación y estado financiero.

`personas` no determina elegibilidad financiera ni condición funcional por sí mismo.

### con administrativo
`personas` y `administrativo` están explícitamente separados.

`persona` es sujeto base del sistema.

`usuario` pertenece al dominio `administrativo` y no debe fusionarse con `personas`.

## 5. Modelo conceptual

### persona base
`persona` es el sujeto base del sistema y la referencia transversal para vínculos, participación y consulta.

Es el núcleo semántico estable del dominio.

### entidades asociadas
Entidades asociadas al dominio:
- `persona_documento`
- `persona_domicilio`
- `persona_contacto`
- `persona_relacion`
- `representacion_poder`
- `rol_participacion`
- `relacion_persona_rol`
- `cliente_comprador`

Las primeras cinco integran el núcleo propio del dominio. Las restantes se mantienen por compatibilidad técnica, contractual o física y no deben expandirse como semántica base de `personas`.

### representación
`representacion_poder` pertenece al dominio `personas` como modelado de representación entre sujetos y consulta de vigencia funcional.

Su semántica es propia del dominio porque representa una relación entre personas y no una operación de negocio ajena.

### participación contextual
`rol_participacion` y `relacion_persona_rol` se congelan como soporte transversal de asociación persona-contexto.

Su función es:
- vincular una persona con un contexto externo mediante `tipo_relacion` + `id_relacion`
- preservar trazabilidad
- soportar compatibilidad con implementación real

No definen por sí mismos la semántica de comprador, locatario, garante u otros roles contextuales, que pertenecen al dominio origen.
La existencia de estas asociaciones no habilita al dominio `personas` a gobernar semántica contextual de dominios externos.

## 6. Reglas de modelado

### persona base
- `persona` es el sujeto base del sistema.
- `usuario` no pertenece a `personas`.
- los atributos base de persona no deben contaminarse con semántica comercial, locativa o financiera.

### clasificaciones
- las clasificaciones o condiciones generales solo pueden leerse como soporte auxiliar o heredado.
- categorías como `cliente`, `proveedor`, `titular` o `garante` no deben consolidarse como identidad base de la persona.
- `SRV-PER-004` queda congelado como soporte auxiliar, no como definidor de esencia funcional del sujeto.

### roles de participación
- los roles como `comprador`, `locatario` o equivalentes son contextuales.
- no son atributos base de la persona.
- `rol_participacion` y `relacion_persona_rol` quedan congelados como soporte técnico/relacional y de trazabilidad.
- `personas` no debe asumir reglas de negocio del dominio que usa la asociación.

### cliente_comprador
- `cliente_comprador` se congela como compatibilidad heredada del modelo físico.
- no forma parte del núcleo del dominio `personas`.
- debe interpretarse como proyección funcional o especialización contextual, no como identidad base.

## 7. Decisiones congeladas
- `persona` es el sujeto base del sistema.
- `personas` es dominio transversal autónomo.
- `usuario` pertenece a `administrativo`, no a `personas`.
- `cliente` no es identidad base de la persona.
- `cliente_comprador` queda congelado como compatibilidad heredada, no como núcleo del dominio.
- los roles contextuales no son atributos base de `persona`.
- `rol_participacion` y `relacion_persona_rol` quedan congelados como soporte transversal de asociación y trazabilidad.
- `SRV-PER-004` y `SRV-PER-006` no deben expandirse con nueva semántica funcional ajena sin decisión arquitectónica explícita.

## 8. Criterio de evolución
Toda evolución futura del dominio debe:
- preservar el núcleo semántico de `persona` como sujeto base
- distinguir explícitamente entre núcleo del dominio, soporte transversal y semántica externa
- evitar incorporar nuevas categorías funcionales como identidad base
- evitar expandir asociaciones contextuales hacia lógica de negocio de `comercial`, `locativo` o `financiero`
- mantener compatibilidad con SQL e implementación existentes mientras no se decida una refactorización mayor

## 9. Notas
- Este documento congela el criterio arquitectónico vigente del dominio `personas`.
- No reemplaza `DEV-SRV`, `DEV-API` ni el modelo físico, pero fija el límite semántico del dominio.
- Debe mantenerse alineado con `SYS-MAP-002`, `DEV-SRV`, `DEV-API-PER-001` y con la materialización existente en SQL e implementación.
