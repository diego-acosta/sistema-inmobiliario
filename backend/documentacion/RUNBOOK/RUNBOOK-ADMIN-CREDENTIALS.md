# RUNBOOK — Credenciales administrativas locales

## Precondiciones

- PostgreSQL y el esquema vigente deben estar disponibles.
- `DATABASE_URL` y `LOCAL_INSTALLATION_CODE` deben identificar una instalación activa.
- Ejecutar desde `backend`, en una TTY. Pipes y stdin redirigido se rechazan antes de abrir DB.
- El usuario debe estar `ACTIVO`, no eliminado y sin fecha de baja.

## Operación

Genere una vez un UUID (`python -c "import uuid; print(uuid.uuid4())"`) y consérvelo en el registro operativo seguro, nunca junto con el secreto:

```bash
python -m app.cli.admin_credentials init --usuario CODIGO --op-id UUID
python -m app.cli.admin_credentials reset --usuario CODIGO --op-id UUID
```

La contraseña se solicita dos veces con `getpass`; no la copie en comandos, variables, archivos, logs o tickets. Tampoco registre el PHC. Debe tener 12–1024 caracteres y no puede coincidir exactamente con código o login.

## Reintentos y recuperación

Ante timeout incierto, reintente el mismo verbo, usuario, secreto y `op-id`. `REPLAY_IDEMPOTENTE` confirma que esa operación ya creó una fila; no autentica, reactiva ni modifica credenciales. No reutilice el UUID con otro usuario o secreto. Los conflictos requieren inspección operativa sanitizada; no altere filas manualmente. Los fallos revierten revocación e inserción juntas.

## Códigos de salida

| Código | Significado |
| --- | --- |
| 0 | completado o replay válido |
| 1 | error técnico/DB/hashing |
| 2 | entrada, TTY, UUID, EOF o contraseña inválida |
| 3 | usuario inexistente |
| 4 | usuario/instalación no elegible o precondición ausente |
| 5 | conflicto de estado o idempotencia |
| 130 | cancelación con Ctrl+C |

Esta herramienta administra credenciales estrictamente locales y no sincronizables. No crea sesiones, tokens, eventos ni outbox.

## Sincronización y respaldos (#455)

La credencial creada por `init`, `reset` o `replay` es exclusivamente local: el bootstrap no genera outbox. No copiar PHC, sesiones ni tokens a logs, Git, issues, PRs o artifacts. Todo backup que los contenga requiere cifrado; ante restore no confiable, invalidar sesiones y rotar credenciales.
