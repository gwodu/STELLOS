import os
import time
import uuid
import random
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def simulate():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Set SUPABASE_URL and SUPABASE_KEY env vars")
        return
        
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Create a few fake tracks to use for routing if none exist
    tracks_res = supabase.table("tracks").select("id").limit(10).execute()
    tracks = [t["id"] for t in tracks_res.data]
    
    if len(tracks) < 5:
        print("Not enough tracks found. Creating fake tracks...")
        for i in range(5):
            tid = str(uuid.uuid4())
            supabase.table("tracks").insert({
                "id": tid,
                "title": f"Fake Track {i}",
                "artist_name": "Simulator",
                "audio_file_url": "http://fake",
                "status": "LIVE"
            }).execute()
            tracks.append(tid)
            
    print(f"Using {len(tracks)} tracks for simulation.")
    
    # 2. Simulate 3 sessions
    # Target graph:
    # A -> B -> C (happy path)
    # A -> D (skipped D)
    A, B, C, D = tracks[0], tracks[1], tracks[2], tracks[3]
    
    sessions = [
        # Session 1: A -> B -> C (all normal plays)
        [
            {"track_id": A, "type": "play_start", "delay": 0},
            {"track_id": A, "type": "play_10s", "delay": 1},
            {"track_id": B, "type": "play_start", "delay": 5},
            {"track_id": B, "type": "radio_next", "delay": 1},
            {"track_id": C, "type": "play_start", "delay": 1},
        ],
        # Session 2: A -> D (skipped D shortly after)
        [
            {"track_id": A, "type": "play_start", "delay": 0},
            {"track_id": D, "type": "play_start", "delay": 5},
            {"track_id": D, "type": "skip", "meta": {"elapsed_ms": 2000}, "delay": 2},
            {"track_id": B, "type": "play_start", "delay": 1},
        ]
    ]
    
    for s_idx, session in enumerate(sessions):
        sid = f"sim_session_{uuid.uuid4()}"
        print(f"\n--- Running Session {s_idx + 1} ({sid}) ---")
        
        for ev in session:
            time.sleep(ev["delay"]) # Keep realistic chronologic ordering minimally
            payload = {
                "session_id": sid,
                "track_id": ev["track_id"],
                "event_type": ev["type"],
                "meta": ev.get("meta", {})
            }
            res = supabase.table("events").insert(payload).execute()
            print(f"-> Inserted event: {ev['type']} on {ev['track_id']}")
            
    print("\nSimulated sessions recorded. Run `python backend/gravity_builder.py` to aggregate them.")

if __name__ == "__main__":
    simulate()
