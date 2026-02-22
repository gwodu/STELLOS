# STELLOS Gravity Layer Integration Guide

The Gravity Layer provides an interaction-driven similarity graph that improves the Live Radio sequence over time by observing how users traverse tracks.

## 1. Frontend Integration

### Emitting Events
The frontend must report user track interactions to the `POST /event` endpoint.
```json
// POST /event payload
{
  "session_id": "string (required, unique per active session)",
  "track_id": "uuid (required, the track being interacted with)",
  "event_type": "string (play_start | play_10s | skip | radio_next | like)",
  "user_id": "uuid (optional)",
  "timestamp": "iso8601 (optional, server defaults to now)",
  "context": "string (optional, e.g., 'radio', 'map', 'direct')",
  "meta": {
    "elapsed_ms": 1234 // needed for skip penalties
  }
}
```

**Event Types to hook up:**
- `play_start`: Fired when a track begins playing.
- `play_10s`: Fired when a track has played for 10 seconds.
- `radio_next`: Fired explicitly when the radio system selects the next track.
- `skip`: Fired when a user skips a track early. (Include `elapsed_ms` in `meta`).

### Fetching Neighbors for UI (Warp Lanes)
To show connected tracks on the 2D map:
```http
GET /tracks/{id}/gravity_neighbors?limit=10
```
Returns a list of tracks with weights and a `normalized_score` between 0 and 1.

## 2. Radio Service Integration

In the radio queue generation logic, when selecting the next track from candidate embeddings, use the `rank_candidates` function in `gravity.py`:

```python
from backend.gravity import rank_candidates

# 1. You have a pool of next-track candidates
candidate_ids = ["uuid-1", "uuid-2", ...]

# 2. You have embedding scores (cosine similarity from map)
emb_scores = {"uuid-1": 0.9, "uuid-2": 0.85}

# 3. Call the gravity ranker
ranked = rank_candidates(
    current_track_id=current_playing_id,
    candidate_track_ids=candidate_ids,
    embeddings_scores=emb_scores,
    session_history=history_of_played_track_ids  # prevents repeats
)

# Pick the best
next_track_id = ranked[0]["track_id"]
```

## 3. Running the Batch Job
The graph isn't built synchronously to avoid blocking the DB. You must run the `gravity_builder.py` script periodically (e.g. via cron, Celery Beat, or an external worker like Railway/Heroku scheduler).

```bash
# Run locally to process recent events and update the TrackEdges table
python backend/gravity_builder.py
```
This script resumes from its last processed event by reading the `gravity_cursor` table.

## 4. Simulation
You can populate fake data and edges to test the system:
1. Start the API (`uvicorn main:app --reload`).
2. Run `python backend/simulate_sessions.py` to post fake events.
3. Run `python backend/gravity_builder.py` to aggregate them.
4. Try fetching `GET /tracks/{mocked_id}/gravity_neighbors`.
