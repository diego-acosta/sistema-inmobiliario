# INM-DEC-IMPORT-EXCEL-001 — Ownership inmobiliario del importador Excel de inmuebles/lotes

## Estado

Aceptada.

## Contexto

La documentación del importador Excel reusable preparada para #205 define una infraestructura técnica/frontend reusable para leer planillas, mapear columnas, generar preview, validar estructura y confirmar posteriormente mediante contratos del dominio dueño.

Esa documentación mencionaba los inmuebles/lotes con una formulación ambigua entre inmobiliario y operativo. Antes de implementar #212, se deja asentado que el importador específico de inmuebles/lotes pertenece al Dominio Inmobiliario.

El Dominio Inmobiliario es dueño del activo inmobiliario y de su estructura base. En la implementación/documentación vigente esto incluye, entre otros conceptos, `desarrollo`, `inmueble`, `unidad_funcional`, disponibilidad inmobiliaria y datos propios del activo cuando estén implementados o se documenten como pendientes del dominio.

El Dominio Operativo conserva ownership de contexto operativo como usuario, sucursal, instalación, ejecución del proceso, auditoría operativa, trazabilidad técnica y contexto de importación, pero no del activo inmobiliario.

## Decisión

El importador específico de inmuebles/lotes de #212 se clasifica como **núcleo del Dominio Inmobiliario** para los writes principales que creen o modifiquen activos inmobiliarios.

La confirmación real de #212 deberá resolverse mediante contratos, endpoints, commands y servicios del Dominio Inmobiliario para:

- desarrollos;
- inmuebles;
- lotes;
- unidades funcionales;
- datos catastrales/registrales, cuando existan contratos vigentes o se documenten como pendientes inmobiliarios;
- disponibilidad inmobiliaria inicial, si correspondiera.

La base Excel reusable de #205 permanece clasificada como **soporte transversal técnico/frontend reusable**: puede aportar lectura, normalización, mapping, preview estructural, reporte técnico y componentes UI, pero no define reglas de negocio ni ownership del activo inmobiliario.

Operativo puede intervenir únicamente como **soporte/contexto de ejecución y trazabilidad**. No debe definir los campos semánticos del activo inmobiliario ni ejecutar como dueño los writes principales del importador de inmuebles/lotes.

## Consecuencias

- #212 debe documentar su mapping, validaciones de negocio y confirmación real dentro del Dominio Inmobiliario.
- Cualquier endpoint/command nuevo o modificado para confirmar #212 debe quedar documentado en DEV-SRV/DEV-API inmobiliario antes o junto con la implementación.
- La UI puede reutilizar el importador Excel común, pero debe confirmar contra contratos inmobiliarios vigentes o futuros debidamente documentados.
- No se debe crear un importador operativo que persista desarrollos, inmuebles, lotes, unidades funcionales o disponibilidad inmobiliaria como si fueran ownership operativo.
- Si la importación necesita usuario, sucursal, instalación, ejecución, auditoría o trazabilidad técnica, esos datos pueden viajar como contexto CORE-EF o trazabilidad, sin cambiar el dominio dueño del write.

## Relación con #205 y #212

- #205: esta decisión corrige y precisa la documentación del importador Excel reusable. No cambia su naturaleza de soporte transversal técnico/frontend.
- #212: esta decisión prepara la implementación del importador específico de inmuebles/lotes y fija su ownership en el Dominio Inmobiliario.

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
