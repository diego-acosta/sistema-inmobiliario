# PRE-COMMIT-CHECKLIST — Validación arquitectónica

## Objetivo
Este checklist se usa para evitar:
- romper límites de dominio
- introducir semántica incorrecta
- generar drift entre arquitectura, documentación y código

## Cuándo usar este checklist
- antes de cada commit
- antes de aceptar cambios generados por IA
- antes de modificar DEV-SRV o DEV-API
- antes de agregar endpoints o lógica de negocio

## Checklist obligatorio
- ¿Este cambio pertenece al dominio correcto?
- ¿Estoy introduciendo lógica de otro dominio?
- ¿Estoy transformando algo heredado o transversal en núcleo del dominio?
- ¿El cambio es coherente con DEV-SRV, DEV-API, SQL y endpoints reales?
- ¿Se está inventando alguna entidad, endpoint o comportamiento que no existe?

## Criterio de decisión
- Si todas las respuestas son correctas → se puede commitear
- Si alguna es dudosa → revisar antes de continuar
- Si alguna es incorrecta → NO commitear

## Uso con IA (Codex / ChatGPT)
Podés usar este checklist con IA pidiendo:

`Evaluá este cambio usando el PRE-COMMIT-CHECKLIST`

Para hacerlo bien:
- no se debe pegar todo el archivo
- solo el bloque modificado
- el objetivo es validar decisiones, no código completo

## Notas
- este checklist complementa DEV-ARCH
- no reemplaza testing ni validaciones técnicas
- se enfoca en semántica y arquitectura
- debe mantenerse simple y usable
