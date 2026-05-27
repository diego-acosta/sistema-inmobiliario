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


---

## 14. CORE-EF obligatorio para endpoints write (checklist operativo)

Para todo endpoint write nuevo o modificado, el PR debe incluir decisión CORE-EF explícita (no se difiere a migración posterior).

1. **Clasificación obligatoria del endpoint:** `COMMAND_WRITE_NEGOCIO`, `COMMAND_WRITE_TECNICO`, `SIMULACION_READLIKE`, `PREVIEW_READLIKE`, `QUERY_READLIKE` o `NO_CONFIRMADO`.
2. **Si es write sincronizable:** usar helper común CORE-EF de headers (sin parseo manual) y exigir `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`; exigir `If-Match-Version` cuando modifica entidad existente/versionada; preservar `ErrorResponse` estándar; no devolver `{"detail": "..."}` para errores de headers.
3. **Todo command sincronizable debe declarar:**
   - idempotencia: aplica/no aplica, criterio de payload, `mismo op_id + mismo payload`, `mismo op_id + payload distinto`, retry post-error;
   - outbox: aplica/no aplica, evento y misma transacción que negocio;
   - lock lógico: aplica/no aplica, entidad bloqueada y operaciones incompatibles;
   - versionado: entidad versionada y uso esperado de `version_registro`;
   - rollback/transacción: frontera transaccional del caso de uso.
4. **Tests mínimos obligatorios en PR write:** headers faltantes/inválidos; happy path; `If-Match-Version` faltante/inválido si aplica; mismatch real de versión si aplica; idempotencia si aplica; rollback si es orquestador; outbox si aplica.
5. **Resumen obligatorio del PR:** sección "Decisión CORE-EF" con naturaleza del endpoint, headers, idempotencia, outbox, lock, versionado y tests ejecutados.
6. **Reglas de alcance:** no implementar caja operativa, recibos fiscales persistidos, documental real ni administrativo nuevo sin nacer con estas reglas.
7. **Read-like/simulación/preview:** dejar explícita la condición para no forzar headers write.
8. **Cuando una regla no aplique:** indicar `NO APLICA` con justificación breve.
9. **Prohibición de cumplimiento sin evidencia:** no declarar cumplimiento CORE-EF profundo sin respaldo verificable en router/service/repository/SQL/tests.
