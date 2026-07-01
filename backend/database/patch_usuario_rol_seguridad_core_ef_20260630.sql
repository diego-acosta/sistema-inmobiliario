-- Patch mínimo CORE-EF para asignación usuario-rol de seguridad administrativa.
-- Habilita idempotencia por op_id, versionado y baja lógica sincronizable.

ALTER TABLE public.usuario_rol_seguridad
    ADD COLUMN IF NOT EXISTS version_registro integer DEFAULT 1 NOT NULL,
    ADD COLUMN IF NOT EXISTS updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ADD COLUMN IF NOT EXISTS deleted_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS id_instalacion_origen bigint,
    ADD COLUMN IF NOT EXISTS id_instalacion_ultima_modificacion bigint,
    ADD COLUMN IF NOT EXISTS op_id_alta uuid,
    ADD COLUMN IF NOT EXISTS op_id_ultima_modificacion uuid;

CREATE UNIQUE INDEX IF NOT EXISTS ux_usuario_rol_seguridad_op_id_alta
    ON public.usuario_rol_seguridad (op_id_alta)
    WHERE op_id_alta IS NOT NULL;


CREATE UNIQUE INDEX IF NOT EXISTS ux_usuario_rol_seguridad_activo
    ON public.usuario_rol_seguridad (id_usuario, id_rol_seguridad)
    WHERE deleted_at IS NULL AND fecha_hasta IS NULL;
