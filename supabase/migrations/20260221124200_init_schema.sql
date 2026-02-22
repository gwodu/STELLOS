CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE public.tracks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    artist_name TEXT,
    audio_file_url TEXT NOT NULL,
    preview_file_url TEXT,
    duration NUMERIC,
    upload_user_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    status TEXT NOT NULL DEFAULT 'UPLOADED',
    embedding_vector vector(512),
    map_x NUMERIC,
    map_y NUMERIC,
    tags JSONB
);
