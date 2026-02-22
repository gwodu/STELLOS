import os
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from licensing import router as licensing_router

load_dotenv()

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
DEFAULT_TOKEN_BALANCE = int(os.environ.get("DEFAULT_TOKEN_BALANCE", "100"))
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Failed to initialize Supabase: {e}")
        supabase = None
else:
    supabase = None

@app.get("/")
def read_root():
    return {"status": "ok", "message": "STELLOS API"}

app.include_router(licensing_router)

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

    # Demo: auto-associate artist + enable licensing + create a default template
    try:
        artist_id = None
        artist_res = supabase.table("artists").select("id").eq("name", artist_name).limit(1).execute()
        if artist_res.data:
            artist_id = artist_res.data[0]["id"]
        else:
            a_insert = supabase.table("artists").insert({"name": artist_name}).execute()
            if a_insert.data:
                artist_id = a_insert.data[0]["id"]

        if artist_id:
            supabase.table("tracks").update({
                "artist_id": artist_id,
                "licensing_enabled": True
            }).eq("id", track_id).execute()

            tmpl_res = supabase.table("license_templates").select("id").eq("track_id", track_id).limit(1).execute()
            if not tmpl_res.data:
                supabase.table("license_templates").insert({
                    "track_id": track_id,
                    "name": "Standard License",
                    "description": "Demo license for web and social usage.",
                    "price_cents": 500,
                    "usage_terms_text": "Non-exclusive license for digital use. Demo terms."
                }).execute()
    except Exception as e:
        print(f"Warning: Failed to setup demo licensing: {e}")
        
    from process import make_preview, make_embedding
    background_tasks.add_task(make_preview, track_id, full_url)
    background_tasks.add_task(make_embedding, track_id, full_url)
    
    return {"track_id": track_id, "status": "UPLOADED", "url": full_url}

@app.get("/tracks")
def get_tracks(bbox: str = None, status: str = "LIVE"):
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
def get_track(track_id: str):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    try:
        res = supabase.table("tracks").select("*").eq("id", track_id).execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Track not found")
        return {"track": res.data[0]}
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

class VoteRequest(BaseModel):
    session_id: str
    tokens_spent: int = 1

@app.post("/radio/start")
def start_radio():
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

@app.get("/tokens/balance")
def get_token_balance(session_id: str):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id required")

    try:
        res = supabase.table("token_balances").select("*").eq("session_id", session_id).execute()
        if res.data:
            return {"session_id": session_id, "balance": res.data[0]["balance"]}

        insert_res = supabase.table("token_balances").insert({
            "session_id": session_id,
            "balance": DEFAULT_TOKEN_BALANCE
        }).execute()
        balance = insert_res.data[0]["balance"] if insert_res.data else DEFAULT_TOKEN_BALANCE
        return {"session_id": session_id, "balance": balance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tracks/{track_id}/vote")
def vote_track(track_id: str, req: VoteRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    if req.tokens_spent <= 0:
        raise HTTPException(status_code=400, detail="tokens_spent must be > 0")

    try:
        track_res = supabase.table("tracks").select("id, vote_score").eq("id", track_id).execute()
        if not track_res.data:
            raise HTTPException(status_code=404, detail="Track not found")
    except Exception as e:
        if isinstance(e, HTTPException): raise
        raise HTTPException(status_code=500, detail=str(e))

    try:
        bal_res = supabase.table("token_balances").select("*").eq("session_id", req.session_id).execute()
        if not bal_res.data:
            bal_insert = supabase.table("token_balances").insert({
                "session_id": req.session_id,
                "balance": DEFAULT_TOKEN_BALANCE
            }).execute()
            balance = bal_insert.data[0]["balance"] if bal_insert.data else DEFAULT_TOKEN_BALANCE
        else:
            balance = bal_res.data[0]["balance"]

        if balance < req.tokens_spent:
            raise HTTPException(status_code=400, detail="Insufficient tokens")

        new_balance = balance - req.tokens_spent
        supabase.table("token_balances").update({
            "balance": new_balance,
            "updated_at": datetime.utcnow().isoformat()
        }).eq("session_id", req.session_id).execute()

        supabase.table("votes").insert({
            "track_id": track_id,
            "session_id": req.session_id,
            "tokens_spent": req.tokens_spent
        }).execute()

        new_score = (track_res.data[0].get("vote_score") or 0) + req.tokens_spent
        supabase.table("tracks").update({"vote_score": new_score}).eq("id", track_id).execute()

        return {"track_id": track_id, "vote_score": new_score, "balance": new_balance}
    except Exception as e:
        if isinstance(e, HTTPException): raise
        raise HTTPException(status_code=500, detail=str(e))
