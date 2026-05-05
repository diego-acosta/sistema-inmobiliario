-- Patch idempotente: agrupador comun de movimientos de pago por persona.

ALTER TABLE public.movimiento_financiero
    ADD COLUMN IF NOT EXISTS uid_pago_grupo uuid;

ALTER TABLE public.movimiento_financiero
    ADD COLUMN IF NOT EXISTS codigo_pago_grupo character varying(50);

CREATE INDEX IF NOT EXISTS ix_movimiento_financiero_pago_grupo
    ON public.movimiento_financiero USING btree (uid_pago_grupo, codigo_pago_grupo);
