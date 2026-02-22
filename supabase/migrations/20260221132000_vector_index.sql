CREATE INDEX ON public.tracks USING hnsw (embedding_vector vector_ip_ops);
