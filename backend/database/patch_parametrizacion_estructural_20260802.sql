-- #409: vocabulario estructural mínimo requerido antes de configurar #425.
-- No crea definiciones en parametro_sistema ni valores en valor_parametro.

BEGIN;

ALTER TABLE tipo_dato_parametro
    ADD COLUMN IF NOT EXISTS descripcion_tipo_dato text;

ALTER TABLE alcance_parametro
    ADD COLUMN IF NOT EXISTS descripcion_alcance text;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM tipo_dato_parametro
        WHERE upper(codigo_tipo_dato) IN ('ENTERO', 'NUMERO')
          AND (
              codigo_tipo_dato IS DISTINCT FROM 'ENTERO'
              OR nombre_tipo_dato IS DISTINCT FROM 'Entero'
              OR descripcion_tipo_dato IS DISTINCT FROM
                 'Valor numérico entero sin componente decimal.'
          )
    ) THEN
        RAISE EXCEPTION
            'tipo_dato_parametro incompatible con el dato estructural ENTERO';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM alcance_parametro
        WHERE upper(codigo_alcance) IN ('GLOBAL', 'GENERAL', 'LOCAL')
          AND (
              codigo_alcance IS DISTINCT FROM 'GLOBAL'
              OR nombre_alcance IS DISTINCT FROM 'Global'
              OR descripcion_alcance IS DISTINCT FROM
                 'Aplicable sin contexto de sucursal o instalación.'
          )
    ) THEN
        RAISE EXCEPTION
            'alcance_parametro incompatible con el dato estructural GLOBAL';
    END IF;

    IF (SELECT count(*) FROM tipo_dato_parametro
        WHERE codigo_tipo_dato = 'ENTERO') > 1 THEN
        RAISE EXCEPTION 'existe más de un tipo ENTERO';
    END IF;

    IF (SELECT count(*) FROM alcance_parametro
        WHERE codigo_alcance = 'GLOBAL') > 1 THEN
        RAISE EXCEPTION 'existe más de un alcance GLOBAL';
    END IF;
END;
$$;

INSERT INTO tipo_dato_parametro (
    codigo_tipo_dato,
    nombre_tipo_dato,
    descripcion_tipo_dato
)
SELECT
    'ENTERO',
    'Entero',
    'Valor numérico entero sin componente decimal.'
WHERE NOT EXISTS (
    SELECT 1
    FROM tipo_dato_parametro
    WHERE codigo_tipo_dato = 'ENTERO'
);

INSERT INTO alcance_parametro (
    codigo_alcance,
    nombre_alcance,
    descripcion_alcance
)
SELECT
    'GLOBAL',
    'Global',
    'Aplicable sin contexto de sucursal o instalación.'
WHERE NOT EXISTS (
    SELECT 1
    FROM alcance_parametro
    WHERE codigo_alcance = 'GLOBAL'
);

COMMIT;
