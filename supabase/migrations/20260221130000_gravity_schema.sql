CREATE TABLE public.events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    user_id UUID,
    track_id UUID REFERENCES public.tracks(id),
    event_type TEXT NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    context TEXT,
    meta JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_events_session_type ON public.events(session_id, event_type);
CREATE INDEX idx_events_track_id ON public.events(track_id);
CREATE INDEX idx_events_timestamp ON public.events(timestamp);

CREATE TABLE public.track_edges (
    from_track_id UUID REFERENCES public.tracks(id),
    to_track_id UUID REFERENCES public.tracks(id),
    weight NUMERIC NOT NULL DEFAULT 0.0,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (from_track_id, to_track_id)
);

CREATE INDEX idx_track_edges_from ON public.track_edges(from_track_id);
CREATE INDEX idx_track_edges_to ON public.track_edges(to_track_id);

CREATE TABLE public.gravity_cursor (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    last_processed_event_id UUID REFERENCES public.events(id),
    last_processed_timestamp TIMESTAMPTZ NOT NULL DEFAULT '1970-01-01 00:00:00Z',
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Initialize cursor with a single row
INSERT INTO public.gravity_cursor (last_processed_timestamp) VALUES ('1970-01-01 00:00:00Z');
