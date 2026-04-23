# Convenciones documentales

## Objetivo
Definir las reglas de organización y escritura del DEV-SRV modular.

## Tipos de ID

| Tipo | Formato |
|-----|--------|
| Caso de uso | CU-XXX-001 |
| Regla | RN-XXX-001 |
| Servicio | SRV-XXX-001 |
| Error | ERR-XXX-001 |
| Evento | EVT-XXX-001 |
| Estado | EST-XXX-001 |
| API | API-XXX-001 |

## Reglas de organización

- Un archivo = una unidad documental.
- Un servicio = un archivo.
- No duplicar reglas dentro de servicios.
- No duplicar errores dentro de servicios.
- Las reglas transversales se referencian, no se reescriben.
- Todo write debe referenciar CORE-EF-001.
- Los servicios deben ser breves y referenciales.

## Estructura mínima de un servicio

1. Objetivo
2. Alcance
3. Agregado principal
4. Entidades relacionadas
5. Casos de uso
6. Reglas
7. Estados
8. Flujo de alto nivel
9. Validaciones clave
10. Efectos
11. Errores
12. Referencias

## Regla de links

- Usar links tipo wiki cuando aplique.
- Preferir nombres simples de archivo.
- No usar rutas largas dentro del texto si puede evitarse.

## Organización de carpetas

- `catalogos/` = catálogos globales
- `comunes/` = reglas transversales y patrones
- `dominios/` = servicios y catálogos por dominio
