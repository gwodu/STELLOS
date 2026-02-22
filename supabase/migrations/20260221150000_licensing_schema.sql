CREATE TABLE public.artists (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    balance_cents BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE public.tracks
ADD COLUMN licensing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN license_revenue_cents BIGINT NOT NULL DEFAULT 0,
ADD COLUMN artist_id UUID REFERENCES public.artists(id);

CREATE TABLE public.license_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id UUID NOT NULL REFERENCES public.tracks(id),
    name TEXT NOT NULL,
    description TEXT,
    price_cents BIGINT NOT NULL,
    usage_terms_text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.licenses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    track_id UUID NOT NULL REFERENCES public.tracks(id),
    license_template_id UUID NOT NULL REFERENCES public.license_templates(id),
    price_cents BIGINT NOT NULL,
    stripe_payment_id TEXT NOT NULL,
    license_hash TEXT NOT NULL,
    xrpl_tx_hash TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
