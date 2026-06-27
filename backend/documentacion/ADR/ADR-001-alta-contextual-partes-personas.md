# ADR-001 — Alta contextual de Partes/Personas

## Estado

Aceptada

## Fecha

2026-06-27

## Contexto

El sistema ya cuenta con `persona` como maestro único de identidad y como sujeto base transversal. La arquitectura vigente del dominio `personas` establece que `persona` concentra los atributos propios de identidad, documentación, domicilios, contactos, relaciones entre personas, representación y poderes, sin absorber la semántica comercial, locativa, financiera o administrativa de los contextos donde ese sujeto participa.

También existen ficha de Parte, búsqueda/listado operativo de personas y endpoints de alta de persona base. Sin embargo, luego de la auditoría realizada en el issue #275 y de la alineación aplicada al tablero en el issue #285, se decide que el alta aislada de Persona/Parte desde la UI operativa no debe ser el flujo operativo normal. Ese flujo permite generar personas sin motivo funcional verificable y debilita la trazabilidad del sujeto respecto del caso de uso que justificó su existencia.

La decisión preserva la compatibilidad técnica existente, pero fija una regla funcional para la evolución de la UI y de los flujos operativos: una persona puede ser creada durante la resolución de un contexto concreto que necesita un sujeto, no como un fin en sí mismo.

## Problema

Una persona cargada sin relación funcional genera:

- fichas vacías o poco útiles;
- duplicados;
- falta de trazabilidad;
- confusión entre persona, cliente, comprador, locatario, garante y obligado financiero;
- mezcla entre identidad base y roles contextuales.

El problema no es la existencia del maestro `persona`, sino el uso operativo de un alta aislada que no explicita por qué esa identidad ingresa al sistema ni con qué operación, relación o autorización queda vinculada.

## Decisión

`persona` sigue siendo el maestro único de identidad y el núcleo semántico del dominio `personas`.

La UI operativa no debe permitir crear una Persona/Parte como fin en sí mismo. Toda creación funcional debe originarse desde un contexto concreto que requiera resolver un sujeto participante.

La operación funcional debe primero intentar reutilizar una persona existente. Si la persona ya existe, se reutiliza y se vincula al contexto correspondiente. Si no existe, puede crearse únicamente cuando quede vinculada al contexto en la misma operación funcional.

No deben quedar personas nuevas sin vínculo contextual, salvo importación histórica autorizada o regularización administrativa autorizada.

Esta ADR no redefine el ownership semántico de los roles contextuales: `personas` conserva la identidad base; el dominio que origina el caso de uso conserva la semántica del rol funcional. Las estructuras de vinculación o participación contextual se interpretan como soporte transversal o compatibilidad heredada cuando corresponda, no como núcleo semántico de `persona`.

## Regla funcional

```text
No se permite alta aislada de Persona/Parte en la UI operativa.

Toda creación funcional de persona debe originarse desde un contexto concreto que justifique su existencia.

Si la persona ya existe, debe reutilizarse.
Si no existe, puede crearse solo si queda vinculada al contexto en la misma operación funcional.

No deben quedar personas nuevas sin vínculo contextual, salvo importación histórica autorizada o regularización administrativa autorizada.
```

## Contextos válidos iniciales

Los contextos válidos iniciales para resolver alta/reutilización de Persona/Parte son:

- comprador en venta;
- comprador/interesado en reserva de venta;
- locatario en contrato de alquiler;
- garante;
- locador;
- representante/apoderado;
- relación entre personas;
- obligado financiero;
- usuario vinculado;
- importación histórica autorizada;
- regularización administrativa autorizada.

Esta lista define el punto de partida de la decisión. La incorporación de nuevos contextos debe documentar el dominio dueño, el caso de uso que justifica el alta o reutilización, la forma de vinculación contextual y la compatibilidad con la arquitectura vigente.

## Clasificación arquitectónica

- `persona`: núcleo del dominio `personas`; maestro único de identidad.
- atributos propios de identidad, documentos, domicilios y contactos: núcleo del dominio `personas`.
- relaciones entre personas y representación/apoderamiento: núcleo del dominio `personas` cuando modelan vínculos entre sujetos.
- comprador en venta o reserva de venta: rol contextual del dominio `comercial`.
- locatario, garante y locador: roles contextuales del circuito locativo correspondiente; no son atributos base de `persona`.
- obligado financiero: rol contextual del dominio `financiero`; no es identidad base.
- usuario vinculado: vínculo con el dominio `administrativo`; `usuario` no pertenece a `personas`.
- estructuras de participación o vinculación contextual existentes: soporte transversal o compatibilidad heredada según su materialización real; no trasladan ownership semántico del contexto al dominio `personas`.
- importación histórica autorizada y regularización administrativa autorizada: excepciones controladas, no flujo operativo normal.

## Alcance de UI y operación

La UI operativa debe orientar el alta desde el caso de uso que necesita al sujeto. En vez de ofrecer una acción general de “crear Parte/Persona” sin propósito funcional, debe ofrecer resolución contextual de parte/persona dentro del flujo correspondiente.

El patrón esperado es:

1. buscar persona existente por datos identificatorios o criterios disponibles;
2. seleccionar y reutilizar si existe;
3. si no existe, capturar los datos mínimos necesarios de identidad;
4. crear la persona y su vínculo contextual en la misma operación funcional;
5. dejar trazabilidad del contexto que justificó la creación.

## Excepciones autorizadas

Se admiten personas sin vínculo funcional operativo inmediato únicamente en estos casos:

- importación histórica autorizada, para preservar o migrar información previa;
- regularización administrativa autorizada, para corregir datos existentes o completar información bajo control institucional.

Estas excepciones deben quedar identificadas como tales y no habilitan un flujo operativo general de alta aislada.

## Consecuencias

- La ficha de Parte/Persona debe ser principalmente una vista de identidad, consulta, enriquecimiento y trazabilidad, no el punto normal de alta funcional aislada.
- Los flujos comerciales, locativos, financieros o administrativos deben resolver sujetos desde su propio contexto funcional sin redefinir la identidad base.
- La búsqueda/reutilización de personas se vuelve obligatoria antes de crear una nueva persona desde un flujo contextual.
- Los duplicados se reducen al hacer explícito el paso de búsqueda y reutilización.
- La trazabilidad mejora porque cada nueva persona funcional queda asociada al motivo que justificó su alta.
- Las excepciones de importación histórica y regularización administrativa deben tratarse como flujos autorizados y auditables.

## Compatibilidad con implementación vigente

La decisión no elimina por sí misma endpoints existentes ni modifica contratos de API en este ADR. En particular, si existe alta técnica de persona base, queda como capacidad técnica o heredada cuya exposición en UI operativa debe alinearse con esta decisión.

Cualquier cambio posterior que modifique endpoints write, contratos de API, persistencia o flujos implementados deberá aplicar las reglas CORE-EF vigentes, revisar tests relacionados y documentar explícitamente headers, idempotencia, outbox, lock lógico, versionado, rollback/transacción y cobertura aplicable.

## Validación contra arquitectura

- Coherente con `DEV-ARCH-GEN-001`: mantiene ownership semántico único y clasifica estructuras compartidas.
- Coherente con `DEV-ARCH-PER-001`: preserva a `persona` como sujeto base y evita convertir roles contextuales en atributos base.
- Coherente con `DEV-ARCH-COM-001`: comprador, cliente comprador y otros roles comerciales permanecen contextuales al dominio comercial.
- Coherente con `DEV-ARCH-OPE-001`: no incorpora lógica de caja operativa ni redefine el dominio operativo.
- Coherente con `DEV-ARCH-ANA-001`: no asigna operaciones write ni ownership funcional al dominio analítico, que permanece read-only.

## Decisión CORE-EF

- Naturaleza del cambio: ADR documental; no crea ni modifica endpoints.
- Clasificación de endpoint: NO APLICA, porque este PR no introduce cambios de API ni operaciones write.
- Headers CORE-EF: NO APLICA, porque no hay endpoint write nuevo o modificado.
- Idempotencia: NO APLICA, porque no se implementa command sincronizable.
- Outbox: NO APLICA, porque no se implementa persistencia ni eventos.
- Lock lógico: NO APLICA, porque no se modifica ninguna entidad versionada ni operación concurrente.
- Versionado: NO APLICA, porque no se modifica persistencia ni contrato de actualización.
- Rollback/transacción: NO APLICA, porque no hay caso de uso implementado en este cambio.
- Tests: NO APLICA ejecución funcional; se validó el contenido documental y el estado del repositorio.
