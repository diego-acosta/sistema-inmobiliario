# DEV-ARCH-GEN-001 — Convenciones generales de arquitectura

## 1. Objetivo
Definir convenciones generales de arquitectura para todos los dominios del sistema, con foco en ownership semántico, delimitación de dominios y clasificación de entidades y estructuras.

## 2. Alcance
Este documento establece criterios transversales aplicables a los dominios del sistema para:
- delimitar responsabilidad semántica
- distinguir tipos de elementos dentro de un dominio
- evitar ambigüedad en estructuras compartidas
- ordenar la evolución del modelo sin alterar freezes específicos ya definidos

## 3. Principios generales
- Cada dominio debe tener una responsabilidad principal explícita.
- Cada concepto relevante debe tener un único dominio dueño en términos semánticos.
- La existencia física de una estructura no define por sí misma el ownership semántico.
- La semántica del dato y la semántica de la estructura no son necesariamente equivalentes.
- Un dominio puede consumir, referenciar o asociar información de otros dominios sin convertirse en dueño del concepto consumido.
- La delimitación entre dominios debe priorizar claridad semántica antes que conveniencia técnica.

## 4. Tipos de elementos dentro de un dominio

### núcleo del dominio
El núcleo del dominio:
- define la semántica propia y estable del dominio
- representa la responsabilidad principal del dominio
- no depende semánticamente de otros dominios para justificar su significado
- debe mantenerse como referencia principal al modelar casos de uso, reglas, estados y eventos

### soporte transversal
El soporte transversal:
- comprende estructuras de asociación, trazabilidad o vinculación
- puede conectar o referenciar información entre dominios
- no define por sí mismo semántica de negocio
- no traslada ownership semántico entre dominios
- debe interpretarse como soporte de integración o relación, no como núcleo

### compatibilidad heredada
La compatibilidad heredada:
- comprende estructuras existentes por SQL, API o decisiones previas
- se preserva para sostener compatibilidad del sistema
- no redefine el ownership semántico vigente
- no debe expandirse como núcleo del dominio
- debe quedar explícitamente identificada cuando exista

## 5. Reglas de ownership semántico
- Cada concepto debe tener un único dominio dueño.
- El dominio dueño define:
  - significado
  - reglas
  - comportamiento
- Los demás dominios solo pueden consumir, referenciar, asociar o proyectar ese concepto.
- La presencia de un concepto en más de un dominio no implica ownership compartido.
- Un dominio no debe asumir ownership semántico sobre un concepto solo porque:
  - lo persiste
  - lo referencia
  - lo expone
  - lo integra técnicamente

## 6. Reglas de límites entre dominios
- Un dominio no debe redefinir reglas de otro dominio.
- Un dominio no debe recalcular lógica primaria de otro dominio como si fuera fuente de verdad.
- Un dominio no debe absorber semántica externa como parte de su núcleo.
- Los roles deben interpretarse siempre como contextuales al dominio que define su significado.
- Las referencias entre dominios deben explicitar si se trata de:
  - consumo
  - asociación
  - trazabilidad
  - dependencia funcional

## 7. Reglas sobre entidades compartidas
- La existencia técnica de una entidad o estructura en más de un contexto no implica ownership compartido.
- Toda entidad o estructura compartida debe clasificarse explícitamente como:
  - núcleo del dominio
  - soporte transversal
  - compatibilidad heredada
- La clasificación debe hacerse por semántica y responsabilidad, no por conveniencia de implementación.
- Cuando una estructura soporte un concepto de otro dominio, debe dejarse explícito que la estructura no redefine el ownership del concepto.

## 8. Reglas sobre evolución del modelo
- No expandir compatibilidad heredada como si fuera núcleo del dominio.
- No mover conceptos entre dominios sin decisión arquitectónica explícita.
- Toda evolución debe validarse contra:
  - `SYS-MAP-002`
  - `DEV-SRV`
  - `DEV-ARCH` existentes
- Las decisiones nuevas deben preservar consistencia entre ownership semántico, límites de dominio y clasificación de estructuras.
- Si una estructura existente genera ambigüedad, primero debe aclararse su clasificación antes de expandirla funcionalmente.

## 9. Notas
- Este documento actúa como referencia transversal de arquitectura para todos los dominios del sistema.
- No reemplaza freezes específicos por dominio, pero fija criterios comunes para interpretarlos y mantenerlos consistentes.
- Debe utilizarse como guía al revisar ownership, límites de dominio y tratamiento de estructuras heredadas o compartidas.
