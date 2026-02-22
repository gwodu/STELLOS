INSERT INTO storage.buckets (id, name, public)
VALUES ('audio', 'audio', TRUE)
ON CONFLICT (id) DO NOTHING;
