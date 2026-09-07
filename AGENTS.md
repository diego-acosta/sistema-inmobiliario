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

## 10. Modos de actuación y manejo de errores

El modo se determina por el objetivo y el alcance autorizado, independientemente de la herramienta o del agente utilizado. Distinguir los siguientes tres modos; una consulta o auditoría no se convierte automáticamente en trabajo mutativo por detectar un problema.

Esta clasificación aclara cómo aplicar las obligaciones de detener, señalar y corregir; no cambia el orden de fuentes. `AGENTS.md` sigue siendo la fuente de mayor precedencia para los agentes del repositorio y prevalece sobre `CODEX-WORKFLOW.md`.

### 10.1 CONSULTA / ANÁLISIS NO MUTATIVO

Aplica al responder preguntas, explicar, resumir, comparar, analizar, interpretar, asesorar, recuperar información o revisar el repositorio sin modificarlo y sin un objetivo explícito de auditoría formal.

Ante inconsistencias, violaciones de dominio, contradicciones (incluidas las relativas a tests existentes) o ambigüedades relevantes:

1. señalar el problema;
2. usar la fuente de mayor precedencia cuando permita resolverlo;
3. explicitar los supuestos y las limitaciones que correspondan;
4. continuar la respuesta si puede darse con fiabilidad.

Sólo detener la respuesta cuando la ambigüedad o contradicción impida responder de forma fiable, indicando qué falta resolver.

Detectar un problema documental durante una consulta **no autoriza a modificar el repositorio**. Detectar una inconsistencia **no obliga automáticamente a corregir archivos antes de responder**.

### 10.2 AUDITORÍA / REVIEW FORMAL

Aplica cuando el objetivo explícito sea auditar o revisar formalmente un PR, una arquitectura, un contrato, una implementación, una invariante o documentación contractual.

Ante un problema detectado:

1. registrar el finding con su evidencia;
2. clasificarlo y evaluar su impacto/materialidad;
3. determinar si invalida el objeto auditado;
4. distinguir findings `BLOQUEANTE` y `NO_BLOQUEANTE` según los criterios del workflow vigente, subordinados a este archivo.

Un finding detectado **no implica automáticamente modificar el repositorio**. Una auditoría de alcance read-only puede concluir que algo debe corregirse sin ejecutar esa corrección. Si el finding invalida materialmente el objeto auditado, no declararlo listo ni correcto.

### 10.3 TRABAJO MUTATIVO

Aplica a modificaciones de código, SQL, documentación, tests, configuración, ramas, commits, PRs, issues o cualquier otro estado del repositorio.

Si una inconsistencia, violación de dominio, contradicción (incluidas las relativas a tests existentes) o ambigüedad afecta la corrección del cambio actual:

1. detener esa implementación;
2. señalar el problema;
3. corregirlo dentro del alcance autorizado o escalarlo antes de continuar.

Si la corrección necesaria excede el alcance autorizado, mantener detenida la implementación afectada hasta resolver el bloqueo y contar con autorización para cualquier ampliación necesaria. Escalar no equivale a dar el problema por resuelto.

Un problema fuera de alcance y no necesario para corregir el incremento **no autoriza la expansión automática del scope**: registrarlo, escalarlo y dejarlo fuera del incremento si corresponde, sin modificarlo sin autorización. Puede continuar el trabajo cuya corrección no dependa de ese problema.

### 10.4 Obligaciones comunes

Los tres modos preservan ownership de dominios, prohibición de diseño libre, restricciones arquitectónicas, validación contra SQL/runtime/tests, CORE-EF y reglas de autenticación. No permiten inventar implementación o cobertura ni declarar tests ejecutados si no se ejecutaron.

Si una tarea combina auditoría y corrección autorizada, aplicar las obligaciones de auditoría al dictamen y las de trabajo mutativo a las modificaciones. El modo no amplía los permisos ni el alcance de la tarea.

---

## 11. Flujo de trabajo

Aplicar este flujo según el modo definido en la sección 10: en consulta o auditoría read-only, generar y corregir se refiere a la respuesta o al informe; no obliga ni autoriza a modificar el repositorio.

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
2. **Si es write sincronizable:** usar helper común CORE-EF de headers (sin parseo manual) y exigir `X-Op-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`; exigir `If-Match-Version` cuando modifica entidad existente/versionada; preservar `ErrorResponse` estándar; no devolver `{"detail": "..."}` para errores de headers. Todo write nuevo o modificado que use autenticación Bearer debe derivar la identidad humana exclusivamente de `AuthenticatedPrincipal`; en esos commands `X-Usuario-Id` está prohibido como fuente de identidad y no se requiere, usa, compara ni parsea para identidad o autorización. Los endpoints heredados que aún dependan de `X-Usuario-Id` pueden conservar temporalmente su contrato histórico y deben migrarse incrementalmente mediante sus issues correspondientes, sin ampliar ese modelo heredado.
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
---

## 15. Reset PostgreSQL local / Codex Cloud

- Windows local: usar `backend/scripts/reset_db.bat`.
- Linux/Codex Cloud: usar `backend/scripts/reset_db.sh`.
- PostgreSQL debe estar activo antes de ejecutar cualquier reset.
- Los tests PostgreSQL no se consideran validados si el reset correspondiente no terminó correctamente.
