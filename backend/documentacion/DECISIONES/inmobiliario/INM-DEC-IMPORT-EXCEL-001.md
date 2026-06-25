# INM-DEC-IMPORT-EXCEL-001 — Ownership inmobiliario del importador Excel de inmuebles/lotes

## Estado

Aceptada.

## Contexto

La documentación del importador Excel reusable preparada para #205 define una infraestructura técnica/frontend reusable para leer planillas, mapear columnas, generar preview, validar estructura y confirmar posteriormente mediante contratos del dominio dueño.

Esa documentación mencionaba los inmuebles/lotes con una formulación ambigua entre inmobiliario y operativo. Antes de implementar #212, se deja asentado que el importador específico de inmuebles/lotes pertenece al Dominio Inmobiliario.

El Dominio Inmobiliario es dueño del activo inmobiliario y de su estructura base. En la implementación/documentación vigente esto incluye, entre otros conceptos, `desarrollo`, `inmueble`, `unidad_funcional`, disponibilidad inmobiliaria y datos propios del activo cuando estén implementados o se documenten como pendientes del dominio.

El importador puede consumir contexto de ejecución compuesto por usuario autenticado, sucursal, instalación, headers CORE-EF, `op_id` y trazabilidad técnica. Ese contexto no transfiere ownership al Dominio Operativo: usuario/autorización pertenecen al dominio administrativo o a infraestructura de seguridad; CORE-EF/trazabilidad técnica pertenecen a infraestructura transversal; auditoría institucional pertenece al dominio administrativo/auditoría cuando corresponda; sucursal/instalación actúan como contexto global/técnico-operativo. Operativo no es dueño del activo inmobiliario ni de los writes inmobiliarios.

## Decisión

El importador Excel de inmuebles/lotes (#212) se clasifica como una **especialización técnica del importador Excel reusable**, orientada al Dominio Inmobiliario.

Como proceso de importación, conserva naturaleza técnica/transversal: lectura de archivo, detección de hojas y columnas, normalización, mapping, preview, validación estructural, orquestación de confirmación y reporte final.

Como operación de negocio, no es dueño de las reglas inmobiliarias ni de la persistencia del activo. La confirmación real debe delegar los writes en contratos, endpoints, commands o servicios del Dominio Inmobiliario.

En consecuencia, la infraestructura del importador puede ser técnica/reusable, pero los efectos persistentes sobre inmuebles, unidades funcionales, datos catastrales/registrales y disponibilidad inmobiliaria pertenecen al Dominio Inmobiliario.

La confirmación real de #212 deberá resolverse mediante contratos, endpoints, commands y servicios del Dominio Inmobiliario para:

- desarrollos, cuando corresponda resolver o asociar contexto existente;
- inmuebles, incluyendo aquellos que funcionalmente se identifiquen como lotes;
- unidades funcionales, si el caso futuro las incluye;
- datos catastrales/registrales del inmueble, incluyendo manzana, lote, parcela, nomenclatura, partida o matrícula cuando correspondan;
- disponibilidad inmobiliaria inicial, si correspondiera.

`lote` no se documenta como entidad persistente separada. En #212, lote es una denominación funcional o dato identificatorio/catastral de un inmueble, salvo que una decisión futura cree formalmente una entidad distinta.

La base Excel reusable de #205 permanece clasificada como **soporte transversal técnico/frontend reusable**: puede aportar lectura, normalización, mapping, preview estructural, reporte técnico y componentes UI, pero no define reglas de negocio ni ownership del activo inmobiliario.

Operativo puede participar como consumidor o aportante de contexto de ejecución o información operativa, pero no debe recibir ownership de los writes inmobiliarios, ni ownership de autenticación/autorización, auditoría institucional o trazabilidad CORE-EF.

## Consecuencias

- #212 debe documentar su mapping, validaciones de negocio y confirmación real dentro del Dominio Inmobiliario.
- Cualquier endpoint/command nuevo o modificado para confirmar #212 debe quedar documentado en DEV-SRV/DEV-API inmobiliario antes o junto con la implementación.
- La UI puede reutilizar el importador Excel común, pero debe confirmar contra contratos inmobiliarios vigentes o futuros debidamente documentados.
- No se debe crear un importador operativo que persista desarrollos, inmuebles, unidades funcionales o disponibilidad inmobiliaria como si fueran ownership operativo.
- No se debe promover `lote` como entidad write separada: la información de lote/manzana/parcela debe viajar como dato del inmueble o como dato catastral/registral asociado, según contratos vigentes.
- Si la importación necesita usuario autenticado, sucursal, instalación, headers CORE-EF, `op_id`, auditoría institucional o trazabilidad técnica, esos datos viajan como contexto del caso de uso sin cambiar el dominio dueño del write y sin asignar auth/audit/CORE-EF al Dominio Operativo.

## Relación con #205 y #212

- #205: esta decisión corrige y precisa la documentación del importador Excel reusable. No cambia su naturaleza de soporte transversal técnico/frontend.
- #212: esta decisión prepara la implementación del importador específico de inmuebles/lotes y fija que sus efectos persistentes sobre activos inmobiliarios pertenecen al Dominio Inmobiliario.

Esta decisión no cierra #205 ni #212.

## Regla CORE-EF

- Lectura local de archivo Excel: `QUERY_READLIKE`; CORE-EF **NO APLICA** porque no persiste ni modifica entidades.
- Preview estructural o preview backend sin persistencia: `PREVIEW_READLIKE`; CORE-EF **NO APLICA** porque no crea ni modifica entidades.
- Confirmación real de #212: `COMMAND_WRITE_NEGOCIO`; CORE-EF **APLICA** por writes sincronizables del Dominio Inmobiliario.
- Headers para confirmación real sincronizable: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`; `If-Match-Version` cuando modifique una entidad existente/versionada.
- Idempotencia: deberá definirse en el PR de implementación de #212 con criterio explícito por lote/fila/payload; no se puede implementar confirmación real sin esa decisión.
- Outbox: aplica solo si el command inmobiliario emite eventos; deberá compartir transacción con el cambio de negocio.
- Lock lógico: aplica según entidad inmobiliaria afectada y operaciones incompatibles.
- Versionado: aplica sobre entidades inmobiliarias versionadas y deberá respetar `version_registro`.
- Rollback/transacción: deberá declarar si la confirmación es all-or-nothing o parcial por fila, y reportar errores por fila si corresponde.

## Fuera de alcance

Esta decisión no implementa ni define ownership para:

- ventas;
- precios o listas comerciales;
- servicios;
- geometría/plano;
- endpoints nuevos;
- SQL nuevo;
- código frontend o backend.

## Validación documental

- DEV-SRV técnico: el importador reusable queda como soporte transversal técnico/frontend.
- DEV-SRV inmobiliario: los activos inmobiliarios permanecen bajo Dominio Inmobiliario.
- DEV-API inmobiliario: la confirmación real deberá usar contratos inmobiliarios vigentes o futuros documentados; no se declara un endpoint nuevo en esta decisión.
- SQL/backend/tests: no se tocan en esta decisión documental.
