import os
import uuid
import hashlib
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from stripe_service import process_support_payment
from xrpl_service import xrpl_record_support

class EventPayload(BaseModel):
    user_id: Optional[str] = None
    anonymous_session_id: Optional[str] = None
    session_id: str
    track_id: str
    event_type: str
    timestamp: Optional[datetime] = None
    context: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
app = FastAPI(title="STELLOS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
# In MVP, we might fail gracefully if missing
if SUPABASE_URL and SUPABASE_KEY:
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    supabase = None

@app.get("/")
def read_root():
    return {"status": "ok", "message": "STELLOS API"}

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks

@app.post("/upload")
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...), 
    title: str = "Unknown Title", 
    artist_name: str = "Unknown Artist"
):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    track_id = str(uuid.uuid4())
    file_ext = file.filename.split('.')[-1]
    storage_path = f"raw/{track_id}.{file_ext}"
    
    contents = await file.read()
    
    try:
        supabase.storage.from_("audio").upload(
            path=storage_path, 
            file=contents, 
            file_options={"content-type": file.content_type}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    full_url = f"{SUPABASE_URL}/storage/v1/object/public/audio/{storage_path}"
    
    track_data = {
        "id": track_id,
        "title": title,
        "artist_name": artist_name,
        "audio_file_url": full_url,
        "status": "UPLOADED"
    }
    
    try:
        supabase.table("tracks").insert(track_data).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
        
    # Enqueue Background Tasks for Preview and Embedding (No Celery/Redis)
    from process import make_preview, make_embedding
    background_tasks.add_task(make_preview, track_id, full_url)
    background_tasks.add_task(make_embedding, track_id, full_url)
    
    return {"track_id": track_id, "status": "UPLOADED", "url": full_url}

@app.get("/tracks")
def get_tracks(bbox: str = None, status: str = "LIVE"):
    """
    bbox format: x1,y1,x2,y2
    """
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    query = supabase.table("tracks").select("*")
    if status != "ALL":
        query = query.eq("status", status)
        
    if bbox:
        try:
            x1, y1, x2, y2 = map(float, bbox.split(","))
            query = query.gte("map_x", x1).lte("map_x", x2).gte("map_y", y1).lte("map_y", y2)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid bbox format. Expects x1,y1,x2,y2")
            
    try:
        res = query.execute()
        return {"tracks": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/track/{track_id}")
def get_track(track_id: str, user_id: Optional[str] = None):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    try:
        res = supabase.table("tracks").select("*").eq("id", track_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Track not found")
        
        track_data = res.data[0]
        track_data["is_supporter"] = False
        if user_id:
            sup_res = supabase.table("supports").select("id").eq("track_id", track_id).eq("user_id", user_id).limit(1).execute()
            if sup_res.data:
                track_data["is_supporter"] = True
                
        return {"track": track_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/event")
async def track_event(payload: EventPayload):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    event_data = {
        "session_id": payload.session_id,
        "track_id": payload.track_id,
        "event_type": payload.event_type,
        "context": payload.context,
        "meta": payload.meta or {},
    }
    
    if payload.user_id:
        # Assuming user_id can be cast to UUID in Supabase if valid, otherwise it might fail.
        # MVP: try inserting it, if not a valid UUID Supabase will reject.
        event_data["user_id"] = payload.user_id
        
    if payload.timestamp:
        event_data["timestamp"] = payload.timestamp.isoformat()
        
    try:
        supabase.table("events").insert(event_data).execute()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

@app.get("/tracks/{track_id}/gravity_neighbors")
def get_gravity_neighbors(track_id: str, limit: int = 50):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    try:
        # Fetch outbound edges sorted by weight descending
        res = supabase.table("track_edges")\
            .select("to_track_id, weight")\
            .eq("from_track_id", track_id)\
            .order("weight", desc=True)\
            .limit(limit)\
            .execute()
            
        edges = res.data
        if not edges:
            return {"neighbors": []}
            
        max_weight = max(e["weight"] for e in edges) if edges else 1.0
        
        neighbors = []
        for e in edges:
            neighbors.append({
                "track_id": e["to_track_id"],
                "weight": e["weight"],
                "normalized_score": e["weight"] / max_weight if max_weight > 0 else 0
            })
            
        return {"neighbors": neighbors}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class RadioNextRequest(BaseModel):
    session_id: str
    last_track_id: str
    prompt_text: Optional[str] = None

@app.post("/radio/start")
def start_radio():
    # MVP: pick a random track that is LIVE
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    try:
        res = supabase.table("tracks").select("*").eq("status", "LIVE").limit(50).execute()
        if not res.data:
            return {"track": None, "message": "No live tracks found."}
            
        import random
        return {"track": random.choice(res.data), "session_id": str(uuid.uuid4())}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/radio/next")
def next_radio_track(req: RadioNextRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    try:
        if req.prompt_text:
            print(f"Radio Steer Request: '{req.prompt_text}' -> Text Embedding Vector Search (Deferred MVP Hack)")
            
        res = supabase.table("tracks").select("*").eq("status", "LIVE").limit(50).execute()
        if not res.data:
            return {"track": None}
            
        import random
        candidates = [t for t in res.data if t["id"] != req.last_track_id]
        if not candidates:
            return {"track": res.data[0]}
            
        return {"track": random.choice(candidates)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SupportRequest(BaseModel):
    user_id: str
    amount_cents: int
    stripe_source: str

@app.post("/tracks/{track_id}/support")
async def support_track(
    track_id: str,
    req: SupportRequest,
    background_tasks: BackgroundTasks
):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    track_res = supabase.table("tracks").select("*").eq("id", track_id).execute()
    if not track_res.data:
        raise HTTPException(status_code=404, detail="Track not found")
    track = track_res.data[0]

    if not track.get("support_enabled", True):
        raise HTTPException(status_code=400, detail="Support is not enabled for this track")

    try:
        charge = process_support_payment(req.amount_cents, req.stripe_source)
        payment_id = charge.get("id")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Payment failed: {str(e)}")

    timestamp = datetime.utcnow().isoformat()
    raw_hash = f"{track_id}{req.user_id}{req.amount_cents}{timestamp}"
    support_hash = hashlib.sha256(raw_hash.encode()).hexdigest()

    support_id = str(uuid.uuid4())
    support_data = {
        "id": support_id,
        "user_id": req.user_id,
        "track_id": track_id,
        "amount_cents": req.amount_cents,
        "stripe_payment_id": payment_id,
        "support_hash": support_hash,
    }
    
    try:
        supabase.table("supports").insert(support_data).execute()
        
        new_count = track.get("support_count", 0) + 1
        supabase.table("tracks").update({"support_count": new_count}).eq("id", track_id).execute()

        artist_id = track.get("artist_id")
        if artist_id:
             artist_res = supabase.table("artists").select("balance_cents").eq("id", artist_id).execute()
             if artist_res.data:
                 new_balance = artist_res.data[0].get("balance_cents", 0) + req.amount_cents
                 supabase.table("artists").update({"balance_cents": new_balance}).eq("id", artist_id).execute()

        background_tasks.add_task(xrpl_record_support, support_id, support_hash)

        return {"status": "success", "support_id": support_id, "support_hash": support_hash}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")

@app.get("/tracks/{track_id}/supporters")
def get_track_supporters(track_id: str):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        res = supabase.table("supports").select("*").eq("track_id", track_id).order("created_at", desc=True).execute()
        return {"supporters": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/users/{user_id}/supported-tracks")
def get_user_supported_tracks(user_id: str):
    if not supabase:
         raise HTTPException(status_code=500, detail="Supabase not configured")
    try:
        res = supabase.table("supports").select("track_id, amount_cents, created_at").eq("user_id", user_id).order("created_at", desc=True).execute()
        return {"supported_tracks": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/artists/{artist_id}/support-dashboard")
def get_artist_support_dashboard(artist_id: str):
    if not supabase:
         raise HTTPException(status_code=500, detail="Supabase not configured")
    
    try:
        tracks_res = supabase.table("tracks").select("id, support_count, support_enabled").eq("artist_id", artist_id).execute()
        tracks = tracks_res.data
        track_ids = [t["id"] for t in tracks]

        total_support_revenue = 0
        total_supporters = 0
        recent_activity = []

        if track_ids:
            supports_res = supabase.table("supports").select("*").in_("track_id", track_ids).order("created_at", desc=True).execute()
            supports = supports_res.data

            total_support_revenue = sum(s.get("amount_cents", 0) for s in supports)
            total_supporters = len(set(s.get("user_id") for s in supports))
            recent_activity = supports[:10]

        return {
            "total_support_revenue": total_support_revenue,
            "total_supporters": total_supporters,
            "recent_support_activity": recent_activity
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

