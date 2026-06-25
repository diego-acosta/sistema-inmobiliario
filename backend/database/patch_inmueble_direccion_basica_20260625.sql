ALTER TABLE public.inmueble
    ADD COLUMN IF NOT EXISTS calle character varying(150),
    ADD COLUMN IF NOT EXISTS altura character varying(50);
