# Runbook — identidad canónica de instalación local

## Alcance

`LOCAL_INSTALLATION_CODE` identifica la instalación física de este deployment para futuros commands técnicos CORE-EF. La resolución es read-only, exacta y default-deny; no crea credenciales ni implementa autenticación o sincronización.

## Consultar y elegir el código

Usar una sesión administrativa segura de PostgreSQL, sin imprimir `DATABASE_URL`:

```sql
SELECT codigo_instalacion, nombre_instalacion, estado_instalacion,
       fecha_baja, deleted_at
FROM public.instalacion
ORDER BY codigo_instalacion;
```

Elegir explícitamente el código exacto de la instalación física correcta. Confirmar `estado_instalacion = 'ACTIVA'`, `fecha_baja IS NULL` y `deleted_at IS NULL`. No elegir por ID `1`, primera/única fila, nombre, sucursal o `es_principal`; `permite_sincronizacion` tampoco determina esta identidad.

## Configurar, validar y cambiar

1. Definir en el entorno de deployment `LOCAL_INSTALLATION_CODE=<codigo exacto>`, respetando case y Unicode, sin espacios exteriores.
2. Reiniciar la aplicación de forma controlada.
3. Verificar mediante el check interno sanitizado del deployment que la resolución termina correctamente. No registrar el `DATABASE_URL`, SQL, credenciales ni parámetros completos.
4. Para cambiar de instalación, reemplazar explícitamente la variable, reiniciar y repetir la validación. No existe fallback al seed ni a otra fila.

Una variable ausente o sintácticamente inválida impide construir `Settings`. Un código inexistente, eliminado, inactivo, dado de baja o estructuralmente inconsistente impide resolver la identidad antes de cualquier write del futuro consumidor. Producción no dispone de panel ni bootstrap automático para este valor.
