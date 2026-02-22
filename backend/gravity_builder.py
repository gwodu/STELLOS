import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

def process_events(limit: int = 1000):
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Missing Supabase credentials")
        return

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # 1. Fetch cursor
    cursor_res = supabase.table("gravity_cursor").select("*").limit(1).execute()
    if not cursor_res.data:
        print("No cursor found. Migration may not have run properly.")
        return
        
    cursor_id = cursor_res.data[0]["id"]
    last_timestamp = cursor_res.data[0]["last_processed_timestamp"]
    
    print(f"Fetching events after {last_timestamp}")
    
    # 2. Fetch new events ordered by timestamp
    events_res = supabase.table("events")\
        .select("*")\
        .gt("timestamp", last_timestamp)\
        .order("timestamp")\
        .limit(limit)\
        .execute()
        
    events = events_res.data
    if not events:
        print("No new events to process.")
        return
        
    print(f"Processing {len(events)} events...")
    
    # We will process events by session to form edges
    # For a simple MVP, we just look at adjacent plays in the SAME session
    # A true robust system would load session history, but we'll try to process chronologically
    # and maybe keep a small memory cache of "last track played per session"
    
    session_state = {}
    edges_to_update = {}  # (from_id, to_id) -> weight_delta
    
    for event in events:
        sid = event["session_id"]
        tid = event["track_id"]
        etype = event["event_type"]
        ts = event["timestamp"]
        
        # Initialize session state if not exist
        if sid not in session_state:
            session_state[sid] = {"last_play": None, "last_play_ts": None}
            
        state = session_state[sid]
        
        if etype in ["play_start", "play_10s", "radio_next"]:
            if state["last_play"] and state["last_play"] != tid:
                from_id = state["last_play"]
                to_id = tid
                edge = (from_id, to_id)
                
                weight_add = 0.0
                if etype == "play_start" or etype == "play_10s":
                    # within session: +1.0
                    weight_add = 1.0
                elif etype == "radio_next":
                    # explicitly nexted by radio: +2.0
                    weight_add = 2.0
                    
                if edge not in edges_to_update:
                    edges_to_update[edge] = 0.0
                edges_to_update[edge] += weight_add
                
            state["last_play"] = tid
            state["last_play_ts"] = ts
            
        elif etype == "skip":
            # Penalty: -0.5 on the edge from the mostly recently played to this skipped one, OR
            # from this skipped one to the next one? The instructions say:
            # "If skip on A with elapsed_ms < 5000: apply penalty: decrease outgoing from A to the next track, or create negative edge."
            # Actually, if we skip A, the very NEXT track played will be B. So we should penalize A -> B.
            # We will mark "A" as a skipped track context.
            state["last_play"] = tid
            state["last_play_ts"] = ts
            state["skip_active_for"] = tid
            
            # We don't know B yet, we'll apply it when the next track starts.
            # So let's tweak the play handler:
            
        # Refined rule application:
        # Re-evaluating etype handling to apply skip penalty
        # Wait, if we just handled play_start, we didn't check skip_active_for.
        # Let's rewrite the logic inside the loop to be cleaner.

def process_events_v2(limit: int = 1000):
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    cursor_res = supabase.table("gravity_cursor").select("*").limit(1).execute()
    if not cursor_res.data:
        return
    
    cursor = cursor_res.data[0]
    events_res = supabase.table("events").select("*").gt("timestamp", cursor["last_processed_timestamp"]).order("timestamp").limit(limit).execute()
    events = events_res.data
    
    if not events:
        return
        
    session_state = {}
    edges_to_update = {}
    
    for ev in events:
        sid = ev["session_id"]
        tid = ev["track_id"]
        etype = ev["event_type"]
        meta = ev.get("meta") or {}
        
        if sid not in session_state:
            session_state[sid] = {"prev_track": None, "skipped_prev": False}
        
        st = session_state[sid]
        
        if etype == "play_start" or etype == "radio_next":
            if st["prev_track"] and st["prev_track"] != tid:
                edge = (st["prev_track"], tid)
                if edge not in edges_to_update:
                    edges_to_update[edge] = 0.0
                
                if st["skipped_prev"]:
                    edges_to_update[edge] += -0.5
                elif etype == "radio_next":
                    edges_to_update[edge] += 2.0
                else:
                    edges_to_update[edge] += 1.0
                    
            st["prev_track"] = tid
            st["skipped_prev"] = False
            
        elif etype == "skip":
            elapsed = meta.get("elapsed_ms", 0)
            if elapsed < 5000:
                st["skipped_prev"] = True
                
        elif etype in ["like"]:
            # Optional: bidirectional +0.5 to all tracks in session
            pass
            
    # Apply updates
    for (from_id, to_id), weight_delta in edges_to_update.items():
        if weight_delta == 0: continue
        # Upsert logic
        # We need to fetch existing weight or use conflict resolution
        res = supabase.table("track_edges").select("weight").eq("from_track_id", from_id).eq("to_track_id", to_id).execute()
        existing_weight = res.data[0]["weight"] if res.data else 0.0
        
        new_weight = existing_weight + weight_delta
        
        supabase.table("track_edges").upsert({
            "from_track_id": from_id,
            "to_track_id": to_id,
            "weight": new_weight
        }).execute()
        
    # Update cursor
    latest_ts = events[-1]["timestamp"]
    supabase.table("gravity_cursor").update({
        "last_processed_timestamp": latest_ts,
        "last_processed_event_id": events[-1]["id"]
    }).eq("id", cursor["id"]).execute()
    
    print(f"Processed {len(events)} events, latest TS: {latest_ts}")

if __name__ == "__main__":
    process_events_v2()
