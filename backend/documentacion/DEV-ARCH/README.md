# Arquitectura del Sistema — Guía de referencia

## Propósito
Este documento centraliza las reglas arquitectónicas del sistema, define cómo deben respetarse los dominios y ayuda a evitar errores de semántica, ownership y mezcla de responsabilidades.

## Documentos de arquitectura (fuente de verdad)
Los documentos de arquitectura vigentes son:
- `DEV-ARCH-GEN-001.md`
- `dominios/personas/DEV-ARCH-PER-001.md`
- `dominios/comercial/DEV-ARCH-COM-001.md`
- `dominios/operativo/DEV-ARCH-OPE-001.md`
- `dominios/analitico/DEV-ARCH-ANA-001.md`

Estos documentos:
- son la fuente de verdad
- tienen prioridad sobre DEV-SRV, DEV-API o código
- no deben contradecirse

## Modelo de dominios
- `personas` → identidad base
- `comercial` → compraventa y cliente
- `operativo` → operación física (sucursal, caja, etc.)
- `analitico` → lectura y agregación (read-only)

Cada dominio tiene ownership semántico exclusivo.

Los dominios no deben mezclarse.

## Reglas fundamentales
- no mezclar dominios
- no redefinir ownership
- no expandir compatibilidad heredada como núcleo
- no inventar entidades o endpoints
- no trasladar lógica entre dominios

## Cómo trabajar con IA (Codex / ChatGPT)
- siempre validar contra DEV-ARCH
- nunca aceptar respuestas sin revisar dominio
- usar prompts de validación o checklist
- no confiar en generación automática sin control

## Flujo de trabajo recomendado
1. generar (IA)
2. validar (checklist)
3. corregir
4. recién después integrar

No se debe saltar la validación.

Los cambios deben evaluarse semánticamente.

## Checklist obligatorio
- ¿Este cambio pertenece al dominio correcto?
- ¿Estoy introduciendo lógica de otro dominio?
- ¿Estoy transformando algo heredado o transversal en núcleo del dominio?
- ¿El cambio es coherente con DEV-SRV, DEV-API, SQL y endpoints reales?
- ¿Se está inventando alguna entidad, endpoint o comportamiento que no existe?

## Notas
- este README no reemplaza los DEV-ARCH
- es una guía operativa
- debe mantenerse simple
- es el punto de entrada para nuevos desarrollos
