ALTER TABLE public.tracks
ADD COLUMN vote_score INTEGER NOT NULL DEFAULT 0;

CREATE TABLE public.token_balances (
    session_id TEXT PRIMARY KEY,
    balance INTEGER NOT NULL DEFAULT 100,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE public.votes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    track_id UUID NOT NULL REFERENCES public.tracks(id),
    session_id TEXT NOT NULL,
    tokens_spent INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_votes_track_id ON public.votes(track_id);
CREATE INDEX idx_votes_session_id ON public.votes(session_id);
