-- #262 Administrativo: alcance operativo por sucursal/instalación.
-- Completa metadata CORE-EF para usuario_sucursal y agrega unicidad idempotente/activa.

ALTER TABLE public.usuario_sucursal
    ADD COLUMN IF NOT EXISTS uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    ADD COLUMN IF NOT EXISTS version_registro integer DEFAULT 1 NOT NULL,
    ADD COLUMN IF NOT EXISTS created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ADD COLUMN IF NOT EXISTS updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ADD COLUMN IF NOT EXISTS deleted_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS id_instalacion_origen bigint,
    ADD COLUMN IF NOT EXISTS id_instalacion_ultima_modificacion bigint,
    ADD COLUMN IF NOT EXISTS op_id_alta uuid,
    ADD COLUMN IF NOT EXISTS op_id_ultima_modificacion uuid;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'chk_usuario_sucursal_deleted_at'
    ) THEN
        ALTER TABLE public.usuario_sucursal
            ADD CONSTRAINT chk_usuario_sucursal_deleted_at
            CHECK ((deleted_at IS NULL) OR (deleted_at >= created_at)) NOT VALID;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ux_usuario_sucursal_op_id_alta
    ON public.usuario_sucursal (op_id_alta)
    WHERE op_id_alta IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_usuario_sucursal_activa
    ON public.usuario_sucursal (id_usuario, id_sucursal)
    WHERE deleted_at IS NULL AND estado_vinculo = 'ACTIVO' AND fecha_hasta IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS ux_usuario_sucursal_predeterminada_activa
    ON public.usuario_sucursal (id_usuario)
    WHERE deleted_at IS NULL AND estado_vinculo = 'ACTIVO' AND fecha_hasta IS NULL AND es_sucursal_predeterminada = true;
