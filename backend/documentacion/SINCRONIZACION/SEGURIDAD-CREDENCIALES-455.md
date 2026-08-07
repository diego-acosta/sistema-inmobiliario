# Contrato de exclusión de credenciales y sesiones (#455)

## Política runtime

`credencial_usuario` y la estructura histórica `sesion_usuario` son núcleo
Administrativo de seguridad **local por instalación y no sincronizable**. La
metadata CORE-EF (`uid_global`, versiones, instalaciones y op IDs) no concede
semántica de sincronización. El flujo transversal aplica la allowlist runtime
de `synchronization_policy.py` con default-deny antes de outbox y otra vez antes
de dispatch; tampoco son tipos válidos para conflictos remotos, inbox, paquetes,
import/export ni catálogos futuros. No existe builder ZIP/JSON runtime confirmado.

Las claves sensibles se buscan en profundidad y sin distinguir mayúsculas:
`password`, `password_hash`, `hash_credencial`, `token`, `token_sesion`,
`refresh_token`, `hash_token`, `authorization`, `cookie` y `cookies`. Una clave
`algoritmo_hash` sólo se rechaza bajo una estructura identificada como material
de credencial; no se prohíbe su uso legítimo aislado. Los errores persistidos se
reducen a códigos estables y nunca contienen payload, excepción del driver, SQL,
parámetros o URL de base de datos.

## Matriz física completa de `credencial_usuario`

Todas las columnas son locales y no sincronizables, sin excepción:

| Columna | Local | Sincronizable |
| --- | --- | --- |
| `id_credencial_usuario` | sí | no |
| `uid_global` | sí | no |
| `id_usuario` | sí | no |
| `tipo_credencial` | sí | no |
| `identificador_credencial` | sí | no |
| `hash_credencial` | sí | no |
| `algoritmo_hash` | sí | no |
| `estado_credencial` | sí | no |
| `es_credencial_principal` | sí | no |
| `fecha_alta` | sí | no |
| `fecha_activacion` | sí | no |
| `fecha_vencimiento` | sí | no |
| `fecha_revocacion` | sí | no |
| `motivo_revocacion` | sí | no |
| `obliga_rotacion` | sí | no |
| `ultimo_cambio_credencial` | sí | no |
| `intentos_fallidos_acumulados` | sí | no |
| `ultimo_intento_fallido` | sí | no |
| `bloqueo_hasta` | sí | no |
| `requiere_reset` | sí | no |
| `observaciones` | sí | no |
| `version_registro` | sí | no |
| `created_at` | sí | no |
| `updated_at` | sí | no |
| `deleted_at` | sí | no |
| `id_instalacion_origen` | sí | no |
| `id_instalacion_ultima_modificacion` | sí | no |
| `op_id_alta` | sí | no |
| `op_id_ultima_modificacion` | sí | no |

## `sesion_usuario` histórica

La estructura física existente no equivale a un runtime de sesión vigente;
#455 no lo implementa. Todos sus campos son locales y no sincronizables:
`id_sesion_usuario`, `id_usuario`, `id_credencial_usuario`,
`id_sucursal_operativa`, `id_instalacion_origen`, `token_sesion`,
`fecha_hora_inicio`, `fecha_hora_ultima_actividad`, `fecha_hora_cierre`,
`estado_sesion`, `motivo_cierre`, `origen_autenticacion`, `ip_origen`,
`nombre_equipo_origen`, `version_cliente`, `requiere_reautenticacion`,
`expira_en` y `observaciones`.

## Backups

Un respaldo que contenga `credencial_usuario`, `sesion_usuario` o
`historial_acceso` es material sensible. Se prohíbe publicarlo en Git, issues,
PRs o artifacts de CI, almacenarlo sin cifrado, o registrar un `DATABASE_URL`.
Tras restaurarlo en un entorno no confiable deben invalidarse sesiones y rotarse
las credenciales potencialmente expuestas. #455 no crea un sistema de backups.
