# AGENTS — Reglas obligatorias del sistema

## 1. Propósito

Este archivo define las reglas que TODO agente (Codex / ChatGPT) debe respetar al trabajar en este repositorio.

Estas reglas son obligatorias y prevalecen sobre cualquier generación automática.

---

## 2. Fuente de verdad (arquitectura)

Debes respetar SIEMPRE:

- backend/documentacion/DEV-ARCH/DEV-ARCH-GEN-001.md
- backend/documentacion/DEV-ARCH/dominios/personas/DEV-ARCH-PER-001.md
- backend/documentacion/DEV-ARCH/dominios/comercial/DEV-ARCH-COM-001.md
- backend/documentacion/DEV-ARCH/dominios/operativo/DEV-ARCH-OPE-001.md
- backend/documentacion/DEV-ARCH/dominios/analitico/DEV-ARCH-ANA-001.md

Estos documentos definen el ownership semántico del sistema.

NO pueden ser contradichos.

---

## 3. Modelo de dominios

- personas → identidad base
- comercial → compraventa y cliente
- operativo → operación física
- analitico → lectura y agregación (read-only)

Cada dominio tiene ownership exclusivo.

---

## 4. Reglas críticas

NO puedes:

- mezclar dominios
- redefinir ownership
- mover lógica entre dominios
- usar estructuras transversales como núcleo
- expandir compatibilidad heredada como modelo principal
- inventar entidades o endpoints
- asumir que algo existe si no está en SQL, backend o tests

---

## 5. Clasificación obligatoria

Todo concepto debe ser:

- núcleo del dominio
- soporte transversal
- compatibilidad heredada

Si no se puede clasificar → NO generarlo.

---

## 6. Validación obligatoria

Antes de responder debes verificar:

- dominio correcto
- no invasión de otros dominios
- coherencia con DEV-SRV
- coherencia con DEV-API
- coherencia con SQL
- coherencia con endpoints existentes
- coherencia con tests existentes cuando correspondan

---

## 7. Casos sensibles

Controlar especialmente:

- cliente / cliente_comprador → comercial
- rol_participacion → soporte, no semántica
- relacion_persona_rol → soporte
- documento_logico → no invadir
- operativo vs financiero → separar
- analitico → siempre read-only

---

## 8. Relación con implementación

Validar contra:

- SQL
- routers
- schemas
- services
- repositories
- tests

Si no existe, marcar como:

- pendiente
- heredado
- no implementado
- no confirmado

---

## 9. Relación con tests

Cuando un cambio afecte comportamiento implementado, contratos de API, validaciones, persistencia o flujos de dominio, debes:

- revisar si existen tests relacionados en backend/tests/
- verificar si el cambio los contradice
- indicar si deberían ajustarse tests existentes
- evitar afirmar que algo está completo si el cambio deja tests desalineados

No debes inventar cobertura de tests inexistente.

---

## 10. Manejo de errores

Si detectas:

- inconsistencia
- violación de dominio
- ambigüedad
- contradicción con tests existentes

Debes:

1. detenerte
2. señalar el problema
3. corregir antes de continuar

---

## 11. Flujo de trabajo

Siempre:

1. analizar
2. generar
3. validar contra arquitectura
4. validar contra implementación
5. validar contra tests si aplica
6. corregir

---

## 12. Restricción clave

Este sistema NO permite diseño libre.

Todo debe respetar la arquitectura, la implementación real y la cobertura existente.

---

## 13. Regla final

Si una solución:

- rompe dominio
- invade otro dominio
- inventa algo inexistente
- contradice tests existentes sin explicitarlo

→ es inválida, aunque funcione técnicamente.
