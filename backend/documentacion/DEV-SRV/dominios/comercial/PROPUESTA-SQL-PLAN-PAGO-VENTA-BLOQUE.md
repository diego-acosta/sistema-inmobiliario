# PROPUESTA-SQL-PLAN-PAGO-VENTA-BLOQUE - SQL minimo para bloques de plan de pago de venta

## Estado posterior

Esta propuesta ya fue materializada por `backend/database/patch_plan_pago_venta_bloques_v2_20260515.sql`. Se conserva como trazabilidad de decision. Para el estado vigente, considerar:

- `plan_pago_venta_bloque` existe en SQL y pertenece al dominio `comercial`;
- `obligacion_financiera.id_plan_pago_venta_bloque` existe como trazabilidad de origen hacia el bloque;
- `id_plan_pago_venta_bloque` no es idempotencia financiera;
- `clave_funcional_origen` sigue siendo la clave idempotente de `obligacion_financiera`;
- el endpoint unificado `POST /api/v1/ventas/{id_venta}/plan-pago-v2/generar` sigue futuro/no implementado.

## 1. Diagnostico

Issue: #27 — Disenar SQL minimo para `plan_pago_venta_bloque`.

Clasificacion arquitectonica:

- `plan_pago_venta`: nucleo comercial, cabecera/regla del plan.
- `plan_pago_venta_bloque`: nucleo comercial, estructura de negociacion del plan.
- `obligacion_financiera`: nucleo financiero, deuda/proyeccion/exigibilidad.
- `composicion_obligacion`: soporte financiero del desglose.
- `obligacion_obligado`: soporte financiero de responsables.
- `venta_plan_cuota`: compatibilidad heredada V1 para `CUOTAS_FIJAS`.

El SQL vigente separa la cabecera comercial `plan_pago_venta`, los bloques comerciales `plan_pago_venta_bloque`, la corrida tecnica `generacion_cronograma_financiero` y los items financieros V2 en `obligacion_financiera`. Esta separacion no crea cuotas comerciales ni tramos separados, y no mueve deuda, saldos, pagos, mora, caja, recibos o imputaciones al dominio comercial.

La tabla de bloques persiste reglas comerciales ordenadas que pueden expandirse a obligaciones financieras mediante la generacion vigente. Los endpoints especificos actuales ya la usan; el backend unificado por bloques todavia no esta implementado.

## 2. Respuestas de diseno

### 2.1 Columnas minimas de `plan_pago_venta_bloque`

Columnas recomendadas para el primer SQL:

| Columna | Nulabilidad | Rol |
| --- | --- | --- |
| `id_plan_pago_venta_bloque` | `NOT NULL` | PK tecnica. |
| metadatos CORE-EF | segun patron vigente | Auditoria tecnica (`uid_global`, version, fechas, instalacion, operaciones). |
| `id_plan_pago_venta` | `NOT NULL` | FK a cabecera comercial. |
| `numero_bloque` | `NOT NULL` | Orden funcional dentro del plan. |
| `tipo_bloque` | `NOT NULL` | Tipo controlado de regla comercial. |
| `etiqueta_bloque` | nullable | Texto estable para UI/reportes; no participa de idempotencia. |
| `clave_bloque` | `NOT NULL` | Identificador estable del bloque dentro del plan. |
| `moneda` | `NOT NULL DEFAULT 'ARS'` | Moneda pactada del bloque. |
| `importe_total_bloque` | nullable | Monto comercial total del bloque; no es saldo financiero. |
| `cantidad_cuotas` | nullable | Solo aplica a `TRAMO_CUOTAS`. |
| `importe_cuota` | nullable | Parametro comercial de cuota uniforme; no es obligacion. |
| `fecha_vencimiento` | nullable | Fecha para bloques de obligacion unica. |
| `fecha_primer_vencimiento` | nullable | Primera fecha del tramo. |
| `periodicidad` | nullable | Periodicidad del tramo. |
| `regla_redondeo` | nullable | Regla de distribucion/redondeo del tramo. |
| `concepto_financiero_codigo` | nullable | Pista de composicion financiera existente; no crea catalogo. |
| `observaciones` | nullable | Texto libre no normativo. |

No se recomienda incluir en el SQL inicial `hito_vencimiento`, `indice_referencia`, `tasa_interes`, frecuencia de indexacion ni sistema de interes. Esos campos pertenecen a decisiones futuras y agregarlos ahora aumenta ambiguedad sin soporte de backend ni catalogos.

### 2.2 Tipos de bloque del primer SQL

El primer SQL debe aceptar exactamente:

- `CONTADO`
- `ANTICIPO`
- `TRAMO_CUOTAS`
- `REFUERZO`
- `SALDO`

`TRAMO_INDEXADO` y `TRAMO_INTERES` quedan fuera del primer patch porque requieren reglas financieras, conceptos, calculos y regeneracion que todavia no estan implementados.

### 2.3 Campos comunes de todo bloque

Todo bloque activo debe tener:

- metadatos CORE-EF;
- `id_plan_pago_venta`;
- `numero_bloque`;
- `tipo_bloque`;
- `clave_bloque`;
- `moneda`;
- `deleted_at` controlado por soft-delete;
- opcionalmente `etiqueta_bloque` y `observaciones`.

`importe_total_bloque` es comun como columna fisica, pero no debe ser `NOT NULL` global porque `TRAMO_CUOTAS` puede definirse por `cantidad_cuotas * importe_cuota` y porque una regla de `SALDO` remanente podria requerir diseno posterior. En este primer SQL, si se permite `SALDO`, conviene exigir monto o dejar explicitamente pendiente una regla de saldo remanente en backend; para SQL minimo se recomienda exigir monto en `SALDO` hasta que exista `hito_vencimiento`/regla remanente formal.

### 2.4 Campos especificos nullable segun tipo

| Tipo | Campos obligatorios por check | Campos que deben quedar `NULL` para no mezclar semanticas |
| --- | --- | --- |
| `CONTADO` | `importe_total_bloque`, `fecha_vencimiento` | `cantidad_cuotas`, `importe_cuota`, `fecha_primer_vencimiento`, `periodicidad`, `regla_redondeo` |
| `ANTICIPO` | `importe_total_bloque`, `fecha_vencimiento` | `cantidad_cuotas`, `importe_cuota`, `fecha_primer_vencimiento`, `periodicidad`, `regla_redondeo` |
| `TRAMO_CUOTAS` | `cantidad_cuotas`, `fecha_primer_vencimiento`, `periodicidad`; y al menos uno entre `importe_cuota` o `importe_total_bloque` | `fecha_vencimiento` |
| `REFUERZO` | `importe_total_bloque`, `fecha_vencimiento` | `cantidad_cuotas`, `importe_cuota`, `fecha_primer_vencimiento`, `periodicidad`, `regla_redondeo` |
| `SALDO` | `importe_total_bloque`, `fecha_vencimiento` | `cantidad_cuotas`, `importe_cuota`, `fecha_primer_vencimiento`, `periodicidad`, `regla_redondeo` |

### 2.5 Checks implementables hoy

Checks recomendados sin sobrecomplicar:

1. `deleted_at IS NULL OR deleted_at >= created_at`.
2. `numero_bloque > 0`.
3. `tipo_bloque IN ('CONTADO', 'ANTICIPO', 'TRAMO_CUOTAS', 'REFUERZO', 'SALDO')`.
4. `importe_total_bloque IS NULL OR importe_total_bloque > 0`.
5. `importe_cuota IS NULL OR importe_cuota > 0`.
6. `cantidad_cuotas IS NULL OR cantidad_cuotas > 0`.
7. `periodicidad IS NULL OR periodicidad IN ('MENSUAL')` para alinearse al V2 inicial; ampliar luego si existe backend.
8. `regla_redondeo IS NULL OR regla_redondeo IN ('ULTIMA_CUOTA')` para no prometer reglas sin implementacion.
9. Check por tipo para campos requeridos y campos incompatibles.
10. `clave_bloque <> ''` y, si se desea, `btrim(clave_bloque) = clave_bloque` para evitar claves con espacios accidentales.

No se recomienda un check SQL que fuerce `importe_total_bloque = cantidad_cuotas * importe_cuota`, porque redondeo, centavos y distribucion pertenecen a la logica de generacion. SQL solo debe asegurar parametros no ambiguos.

### 2.6 Como evitar que el bloque se convierta en tabla de cuotas

Protecciones de diseno:

- No crear `plan_pago_venta_cuota` ni `plan_pago_venta_tramo`.
- Modelar `TRAMO_CUOTAS` como una sola fila con `cantidad_cuotas` e `importe_cuota` o `importe_total_bloque`.
- No agregar `numero_cuota`, `saldo_pendiente`, `importe_cancelado`, `estado_pago`, `id_movimiento_financiero`, `id_aplicacion_financiera`, recibos, caja, mora ni punitorios.
- Documentar el comentario de tabla indicando que es regla comercial y no deuda.
- Mantener `clave_funcional_origen` por obligacion generada en `obligacion_financiera`; la clave del bloque no reemplaza la clave por item financiero.
- Si un usuario carga 12 cuotas regulares, debe existir 1 bloque `TRAMO_CUOTAS`, no 12 bloques. Si carga 12 hitos distintos no homogeneos, deben evaluarse como acuerdos comerciales singulares o como endpoint futuro, no como cuotas financieras encubiertas.

### 2.7 Unique por plan + numero_bloque

Si. Debe existir unique parcial:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_ppvb_plan_numero_activo
ON public.plan_pago_venta_bloque (id_plan_pago_venta, numero_bloque)
WHERE deleted_at IS NULL;
```

Motivo: el orden comercial del plan debe ser deterministico y no puede tener dos bloques activos con el mismo numero.

### 2.8 `clave_bloque` estable

Si. Debe existir `clave_bloque` estable y unique parcial por plan:

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_ppvb_plan_clave_activa
ON public.plan_pago_venta_bloque (id_plan_pago_venta, clave_bloque)
WHERE deleted_at IS NULL;
```

Convencion recomendada:

```text
BLOQUE:{numero_bloque}:{tipo_bloque}
```

Ejemplos:

```text
BLOQUE:1:ANTICIPO
BLOQUE:2:TRAMO_CUOTAS
BLOQUE:3:REFUERZO
BLOQUE:4:SALDO
```

La clave del bloque sirve para trazabilidad comercial y estabilidad ante ediciones menores de etiqueta, importe o fecha. No debe reemplazar `obligacion_financiera.clave_funcional_origen`, que sigue siendo la clave idempotente por item financiero generado.

### 2.9 FK opcional en `obligacion_financiera`

Conviene agregar en el mismo patch:

```sql
ALTER TABLE public.obligacion_financiera
ADD COLUMN IF NOT EXISTS id_plan_pago_venta_bloque bigint;
```

con FK opcional:

```sql
ALTER TABLE public.obligacion_financiera
ADD CONSTRAINT fk_obl_plan_pago_venta_bloque
FOREIGN KEY (id_plan_pago_venta_bloque)
REFERENCES public.plan_pago_venta_bloque(id_plan_pago_venta_bloque)
ON DELETE RESTRICT;
```

Indice sugerido:

```sql
CREATE INDEX IF NOT EXISTS idx_obl_plan_pago_venta_bloque
ON public.obligacion_financiera (id_plan_pago_venta_bloque)
WHERE deleted_at IS NULL;
```

Criterio: esta FK es de trazabilidad/consulta, no de idempotencia. La idempotencia sigue en `clave_funcional_origen` y el orden financiero sigue en `numero_obligacion`.

### 2.10 Convivencia con endpoints especificos actuales

El patch SQL no debe cambiar endpoints ni servicios. Los endpoints actuales de V2 especificos deben seguir funcionando:

- `/api/v1/ventas/{id_venta}/plan-pago-v2/cuotas-iguales-simple`
- `/api/v1/ventas/{id_venta}/plan-pago-v2/anticipo-mas-cuotas-iguales`

Estrategia de compatibilidad:

1. Crear la tabla sin exigir que los endpoints existentes la usen.
2. No hacer `NOT NULL` en `obligacion_financiera.id_plan_pago_venta_bloque`, porque las obligaciones V2 actuales ya pueden existir sin bloque.
3. No alterar `plan_pago_venta.metodo_plan_pago` en este patch salvo decision explicita posterior para un metodo `PLAN_POR_BLOQUES`.
4. Mantener `CUOTAS_IGUALES_SIMPLE` y `ANTICIPO_MAS_CUOTAS_IGUALES` como flujos V2 vigentes hasta que exista endpoint unificado.
5. Si luego se implementa backend de bloques, debe crear bloques y expandirlos a obligaciones, pero no reinterpretar automaticamente planes V2 historicos.

### 2.11 Proteccion de `venta_plan_cuota` legacy

`venta_plan_cuota` debe permanecer intacta:

- no eliminarla;
- no migrarla automaticamente en el patch de bloques;
- no agregar nuevos tipos de plan sobre esa tabla;
- no usarla como fuente de `TRAMO_CUOTAS` V2;
- no crear FK desde `plan_pago_venta_bloque` a `venta_plan_cuota`;
- conservar tests V1 que verifican `CUOTAS_FIJAS`.

La proteccion principal es documental y de tests: el test de humo debe seguir afirmando que `venta_plan_cuota` existe y que no existen `plan_pago_venta_cuota` ni `plan_pago_venta_tramo`.

### 2.12 Test de humo de schema sugerido

Actualizar `backend/tests/test_schema_cronograma_v2.py` con:

- nuevo set `PLAN_PAGO_VENTA_BLOQUE_COLUMNS`;
- assert de existencia de `plan_pago_venta_bloque`;
- assert de no existencia de `plan_pago_venta_cuota` y `plan_pago_venta_tramo` ya presente;
- constraints esperadas:
  - `fk_ppvb_plan_pago_venta`;
  - `chk_ppvb_deleted_at`;
  - `chk_ppvb_numero`;
  - `chk_ppvb_tipo`;
  - `chk_ppvb_importe_total`;
  - `chk_ppvb_importe_cuota`;
  - `chk_ppvb_cantidad_cuotas`;
  - `chk_ppvb_periodicidad`;
  - `chk_ppvb_regla_redondeo`;
  - `chk_ppvb_tipo_campos`;
  - `fk_obl_plan_pago_venta_bloque` si se agrega la FK en `obligacion_financiera`.
- indices esperados:
  - `idx_ppvb_uid_global`;
  - `idx_ppvb_plan_pago_venta`;
  - `uq_ppvb_plan_numero_activo`;
  - `uq_ppvb_plan_clave_activa`;
  - `idx_obl_plan_pago_venta_bloque` si se agrega la FK.
- triggers esperados:
  - `trg_bi_ppvb_core_ef`;
  - `trg_bu_ppvb_core_ef`.

No agregar tests de endpoint ni de generacion en este issue porque el alcance es SQL/schema, no backend productivo.

## 3. SQL minimo propuesto

> Este bloque es una propuesta de diseno. No debe aplicarse como patch hasta que se pida explicitamente la implementacion.

```sql
CREATE TABLE IF NOT EXISTS public.plan_pago_venta_bloque (
    id_plan_pago_venta_bloque bigserial PRIMARY KEY,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_plan_pago_venta bigint NOT NULL,
    numero_bloque integer NOT NULL,
    tipo_bloque character varying(30) NOT NULL,
    etiqueta_bloque character varying(120),
    clave_bloque character varying(120) NOT NULL,
    moneda character varying(10) DEFAULT 'ARS' NOT NULL,
    importe_total_bloque numeric(14,2),
    cantidad_cuotas integer,
    importe_cuota numeric(14,2),
    fecha_vencimiento date,
    fecha_primer_vencimiento date,
    periodicidad character varying(30),
    regla_redondeo character varying(30),
    concepto_financiero_codigo character varying(80),
    observaciones text
);
```

Constraints sugeridas:

```sql
ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT fk_ppvb_plan_pago_venta
FOREIGN KEY (id_plan_pago_venta)
REFERENCES public.plan_pago_venta(id_plan_pago_venta)
ON DELETE RESTRICT;

ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT chk_ppvb_deleted_at
CHECK (deleted_at IS NULL OR deleted_at >= created_at);

ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT chk_ppvb_numero
CHECK (numero_bloque > 0);

ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT chk_ppvb_tipo
CHECK (tipo_bloque IN ('CONTADO', 'ANTICIPO', 'TRAMO_CUOTAS', 'REFUERZO', 'SALDO'));

ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT chk_ppvb_importe_total
CHECK (importe_total_bloque IS NULL OR importe_total_bloque > 0);

ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT chk_ppvb_importe_cuota
CHECK (importe_cuota IS NULL OR importe_cuota > 0);

ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT chk_ppvb_cantidad_cuotas
CHECK (cantidad_cuotas IS NULL OR cantidad_cuotas > 0);

ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT chk_ppvb_periodicidad
CHECK (periodicidad IS NULL OR periodicidad IN ('MENSUAL'));

ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT chk_ppvb_regla_redondeo
CHECK (regla_redondeo IS NULL OR regla_redondeo IN ('ULTIMA_CUOTA'));

ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT chk_ppvb_clave_bloque
CHECK (btrim(clave_bloque) <> '' AND btrim(clave_bloque) = clave_bloque);

ALTER TABLE public.plan_pago_venta_bloque
ADD CONSTRAINT chk_ppvb_tipo_campos
CHECK (
    (
        tipo_bloque IN ('CONTADO', 'ANTICIPO', 'REFUERZO', 'SALDO')
        AND importe_total_bloque IS NOT NULL
        AND fecha_vencimiento IS NOT NULL
        AND cantidad_cuotas IS NULL
        AND importe_cuota IS NULL
        AND fecha_primer_vencimiento IS NULL
        AND periodicidad IS NULL
        AND regla_redondeo IS NULL
    )
    OR
    (
        tipo_bloque = 'TRAMO_CUOTAS'
        AND cantidad_cuotas IS NOT NULL
        AND fecha_primer_vencimiento IS NOT NULL
        AND periodicidad IS NOT NULL
        AND (importe_cuota IS NOT NULL OR importe_total_bloque IS NOT NULL)
        AND fecha_vencimiento IS NULL
    )
);
```

Indices:

```sql
CREATE INDEX IF NOT EXISTS idx_ppvb_uid_global
ON public.plan_pago_venta_bloque (uid_global);

CREATE INDEX IF NOT EXISTS idx_ppvb_plan_pago_venta
ON public.plan_pago_venta_bloque (id_plan_pago_venta)
WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_ppvb_plan_numero_activo
ON public.plan_pago_venta_bloque (id_plan_pago_venta, numero_bloque)
WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_ppvb_plan_clave_activa
ON public.plan_pago_venta_bloque (id_plan_pago_venta, clave_bloque)
WHERE deleted_at IS NULL;
```

Triggers CORE-EF:

```sql
CREATE TRIGGER trg_bi_ppvb_core_ef
BEFORE INSERT ON public.plan_pago_venta_bloque
FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();

CREATE TRIGGER trg_bu_ppvb_core_ef
BEFORE UPDATE ON public.plan_pago_venta_bloque
FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
```

Comentarios sugeridos:

```sql
COMMENT ON TABLE public.plan_pago_venta_bloque IS
'Bloque comercial ordenado de plan de pago de venta. Es regla/estructura comercial; no es deuda, cuota financiera, saldo ni reemplazo de obligacion_financiera.';

COMMENT ON COLUMN public.plan_pago_venta_bloque.importe_total_bloque IS
'Parametro comercial del bloque. No representa saldo financiero ni importe cancelado.';

COMMENT ON COLUMN public.plan_pago_venta_bloque.clave_bloque IS
'Clave estable del bloque dentro del plan. No reemplaza obligacion_financiera.clave_funcional_origen.';
```

FK opcional en obligaciones:

```sql
ALTER TABLE public.obligacion_financiera
ADD COLUMN IF NOT EXISTS id_plan_pago_venta_bloque bigint;

ALTER TABLE public.obligacion_financiera
ADD CONSTRAINT fk_obl_plan_pago_venta_bloque
FOREIGN KEY (id_plan_pago_venta_bloque)
REFERENCES public.plan_pago_venta_bloque(id_plan_pago_venta_bloque)
ON DELETE RESTRICT;

CREATE INDEX IF NOT EXISTS idx_obl_plan_pago_venta_bloque
ON public.obligacion_financiera (id_plan_pago_venta_bloque)
WHERE deleted_at IS NULL;

COMMENT ON COLUMN public.obligacion_financiera.id_plan_pago_venta_bloque IS
'Bloque comercial de origen del item de cronograma. Trazabilidad/consulta; la idempotencia sigue en clave_funcional_origen.';
```

## 4. Idempotencia y trazabilidad

- `plan_pago_venta_bloque.clave_bloque` identifica establemente el bloque comercial dentro del plan.
- `obligacion_financiera.clave_funcional_origen` sigue identificando cada item financiero generado.
- `obligacion_financiera.id_plan_pago_venta_bloque` permite consultar bloque -> obligaciones sin parsear strings.
- `generacion_cronograma_financiero.id_plan_pago_venta` sigue agrupando la corrida tecnica.

Convencion recomendada para obligaciones generadas:

```text
PLAN_PAGO_VENTA:{id_plan_pago_venta}:BLOQUE:{numero_bloque}:{tipo_item}:{n}
```

Donde `n` es `1` para `ANTICIPO`, `REFUERZO`, `SALDO` y `CONTADO` materializado como `SALDO`; y es el numero interno de cuota para `TRAMO_CUOTAS`.

## 5. Validacion contra arquitectura e implementacion

- Dominio correcto: `plan_pago_venta_bloque` pertenece a `comercial` como regla pactada de compraventa.
- No invade financiero: no guarda deuda, saldos, pagos, mora, caja, recibos, imputaciones ni obligados finales.
- Coherencia con SQL vigente: referencia `plan_pago_venta`; no altera `venta_plan_cuota`; agrega FK nullable en `obligacion_financiera` solo para trazabilidad.
- Coherencia con endpoints existentes: no requiere cambios de backend ni contratos actuales.
- Coherencia con tests: requiere solo test de humo de schema; no debe afirmar cobertura funcional de generacion por bloques.

## 6. Prompt recomendado para implementar el patch SQL

```text
Implementar el patch SQL minimo para plan_pago_venta_bloque segun
backend/documentacion/DEV-SRV/dominios/comercial/PROPUESTA-SQL-PLAN-PAGO-VENTA-BLOQUE.md.

Alcance estricto:
- Crear backend/database/patch_plan_pago_venta_bloque_YYYYMMDD.sql.
- Agregar tabla public.plan_pago_venta_bloque con metadatos CORE-EF.
- Agregar constraints, indices, comentarios y triggers CORE-EF definidos en la propuesta.
- Agregar obligacion_financiera.id_plan_pago_venta_bloque nullable con FK e indice.
- Actualizar backend/tests/test_schema_cronograma_v2.py con humo de schema.

Restricciones:
- No implementar backend, endpoints, servicios, schemas ni UI.
- No tocar pagos/caja/recibos.
- No eliminar ni modificar venta_plan_cuota salvo tests de proteccion existentes.
- No crear plan_pago_venta_cuota ni plan_pago_venta_tramo.
- No romper CUOTAS_IGUALES_SIMPLE V2 ni ANTICIPO_MAS_CUOTAS_IGUALES V2.
- Mantener clave_funcional_origen como idempotencia de obligaciones.
```
