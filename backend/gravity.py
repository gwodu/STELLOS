import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# We keep a simple in-memory LRU or just fetch on demand for MVP
def get_gravity_edges(current_track_id: str):
    """Fetch outward edges for the given track."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {}
        
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    res = supabase.table("track_edges").select("to_track_id, weight").eq("from_track_id", current_track_id).execute()
    
    edges = {}
    for row in res.data:
        edges[row["to_track_id"]] = float(row["weight"])
        
    return edges

def rank_candidates(current_track_id: str, candidate_track_ids: list, embeddings_scores: dict = None, session_history: list = None):
    """
    Ranks candidates based on embedding similarity and gravity score.
    
    score(c) = 0.7 * embedding_similarity + 0.3 * gravity_score - repeat_penalty
    
    candidates: list of track_id strings we are considering.
    embeddings_scores: dict of track_id -> similarity_score [0, 1]. If None, assumed 0.
    session_history: list of recently played track_ids to apply repeat penalty.
    """
    embeddings_scores = embeddings_scores or {}
    session_history = session_history or []
    
    gravity_edges = get_gravity_edges(current_track_id)
    
    # Normalize gravity weights to [0, 1] relative to the max weight for this track
    max_weight = max(gravity_edges.values()) if gravity_edges else 0.0
    
    ranked = []
    for cid in candidate_track_ids:
        # Embedding part
        emb_score = embeddings_scores.get(cid, 0.0)
        
        # Gravity part
        raw_gravity = gravity_edges.get(cid, 0.0)
        norm_gravity = (raw_gravity / max_weight) if max_weight > 0 else 0.0
        
        # Penalty part
        repeat_penalty = 0.0
        if cid in session_history:
            # Simple penalty for MVP: e.g. -1.0 so it never repeats unless forced
            repeat_penalty = 1.0
            
        final_score = (0.7 * emb_score) + (0.3 * norm_gravity) - repeat_penalty
        
        ranked.append({
            "track_id": cid,
            "score": final_score,
            "embedding_score": emb_score,
            "gravity_score": norm_gravity,
            "raw_gravity": raw_gravity
        })
        
    # Sort descending by final score
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked
