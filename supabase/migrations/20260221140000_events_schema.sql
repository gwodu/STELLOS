CREATE TABLE public.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID,
    session_id TEXT NOT NULL,
    track_id UUID NOT NULL REFERENCES public.tracks(id),
    event_type TEXT NOT NULL,
    context TEXT,
    meta JSONB,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
