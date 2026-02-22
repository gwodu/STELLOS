import os
import uuid
import hashlib
import asyncio
from datetime import datetime
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Database
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"Failed to initialize Supabase in licensing: {e}")
        supabase = None

# Router
router = APIRouter(tags=["Licensing"])

# --- Stripe & XRPL ---
import stripe
try:
    from xrpl.clients import JsonRpcClient
    from xrpl.wallet import Wallet
    from xrpl.models.transactions import Payment, Memo
    from xrpl.transaction import submit_and_wait
    XRPL_IMPORT_OK = True
except Exception as e:
    print(f"Warning: XRPL import failed, falling back to mock XRPL logging: {e}")
    XRPL_IMPORT_OK = False

stripe.api_key = os.environ.get("STRIPE_API_KEY", "")
XRPL_SEED = os.environ.get("XRPL_SEED", "")
XRPL_CLIENT = JsonRpcClient("https://s.altnet.rippletest.net:51234/") if XRPL_IMPORT_OK else None
if XRPL_IMPORT_OK and XRPL_SEED:
    xrpl_wallet = Wallet.from_seed(XRPL_SEED)
else:
    xrpl_wallet = None

# --- Models ---

class LicenseTemplateResponse(BaseModel):
    id: str
    track_id: str
    name: str
    description: Optional[str] = None
    price_cents: int
    usage_terms_text: str
    created_at: str

class LicensePurchaseRequest(BaseModel):
    license_template_id: str
    user_id: Optional[str] = None

class LicenseResponse(BaseModel):
    id: str
    license_hash: str
    status: str
    message: str

class DashboardResponse(BaseModel):
    total_license_revenue_cents: int
    total_licenses: int
    recent_licenses: List[Dict[str, Any]]

class LicenseTemplateListResponse(BaseModel):
    templates: List[LicenseTemplateResponse]

class LicenseTemplateCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    price_cents: int
    usage_terms_text: str

# --- External Services ---

def process_stripe_payment(amount_cents: int) -> str:
    """Creates a Stripe PaymentIntent for the given amount."""
    if not stripe.api_key:
        print("Warning: STRIPE_API_KEY not set. Falling back to mock payment.")
        return f"pi_mock_{uuid.uuid4().hex[:16]}"
        
    try:
        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency="usd",
            automatic_payment_methods={"enabled": True},
        )
        return intent.id
    except Exception as e:
        print(f"Stripe Error: {e}")
        raise HTTPException(status_code=400, detail="Payment processing failed")
        
async def xrpl_record_license(license_id: str, license_hash: str):
    """Submits a license hash to the XRPL Testnet as a memo."""
    print(f"XRPL Background: Preparing to log license_id={license_id}, hash={license_hash}")
    
    if not xrpl_wallet:
        print("Warning: XRPL unavailable or XRPL_SEED not set. Simulating XRPL logging.")
        await asyncio.sleep(2)
        mock_tx_hash = f"xrpl_mock_{uuid.uuid4().hex}"
        _update_license_xrpl(license_id, mock_tx_hash)
        return
        
    try:
        # A simple Payment transaction to self with the license hash as a memo
        memo = Memo(
            memo_data=license_hash.encode("utf-8").hex(),
            memo_type="license_hash".encode("utf-8").hex()
        )
        tx = Payment(
            account=xrpl_wallet.address,
            amount="1", # minimal drop amount
            destination=xrpl_wallet.address,
            memos=[memo]
        )
        
        reply = await asyncio.to_thread(submit_and_wait, tx, XRPL_CLIENT, xrpl_wallet)
        tx_hash = reply.result.get("hash")
        print(f"XRPL Background: Logged successfully. tx_hash={tx_hash}")
        _update_license_xrpl(license_id, tx_hash)
    except Exception as e:
        print(f"XRPL Background error: {e}")

def _update_license_xrpl(license_id: str, tx_hash: str):
    if supabase:
        try:
            supabase.table("licenses").update({"xrpl_tx_hash": tx_hash}).eq("id", license_id).execute()
        except Exception as e:
            print(f"XRPL Background error updating Supabase: {e}")

# --- Endpoints ---

@router.post("/tracks/{track_id}/license", response_model=LicenseResponse)
async def purchase_license(track_id: str, req: LicensePurchaseRequest, background_tasks: BackgroundTasks):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    # 1. Validate track & licensing enabled
    try:
        track_res = supabase.table("tracks").select("id, licensing_enabled, artist_id").eq("id", track_id).execute()
        if not track_res.data:
            raise HTTPException(status_code=404, detail="Track not found")
        track_info = track_res.data[0]
        if not track_info.get("licensing_enabled"):
            raise HTTPException(status_code=400, detail="Licensing is not enabled for this track")
    except Exception as e:
        if isinstance(e, HTTPException): raise
        raise HTTPException(status_code=500, detail=str(e))
        
    # 2. Validate selected template
    try:
        template_res = supabase.table("license_templates").select("*").eq("id", req.license_template_id).eq("track_id", track_id).execute()
        if not template_res.data:
            raise HTTPException(status_code=404, detail="License template not found for this track")
        template_info = template_res.data[0]
    except Exception as e:
        if isinstance(e, HTTPException): raise
        raise HTTPException(status_code=500, detail=str(e))

    # 3. Process Stripe Payment
    payment_id = process_stripe_payment(template_info["price_cents"])

    # 4. On success: create DB records, generate hash
    timestamp = datetime.utcnow().isoformat()
    track_hash = hashlib.sha256(track_id.encode()).hexdigest()
    user_str = req.user_id if req.user_id else "anonymous"
    
    hash_input = f"{track_hash}:{template_info['id']}:{user_str}:{timestamp}"
    license_hash = hashlib.sha256(hash_input.encode()).hexdigest()

    license_id = str(uuid.uuid4())
    license_record = {
        "id": license_id,
        "track_id": track_id,
        "license_template_id": template_info["id"],
        "price_cents": template_info["price_cents"],
        "stripe_payment_id": payment_id,
        "license_hash": license_hash,
    }
    if req.user_id:
        license_record["user_id"] = req.user_id

    try:
        supabase.table("licenses").insert(license_record).execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error during purchase: {e}")
        
    # Queue XRPL task
    background_tasks.add_task(xrpl_record_license, license_id, license_hash)
    
    # Update revenue/balance
    try:
        t_res = supabase.table("tracks").select("license_revenue_cents").eq("id", track_id).execute()
        if t_res.data:
            new_rev = t_res.data[0].get("license_revenue_cents", 0) + template_info["price_cents"]
            supabase.table("tracks").update({"license_revenue_cents": new_rev}).eq("id", track_id).execute()
            
        artist_id = track_info.get("artist_id")
        if artist_id:
            a_res = supabase.table("artists").select("balance_cents").eq("id", artist_id).execute()
            if a_res.data:
                new_bal = a_res.data[0].get("balance_cents", 0) + template_info["price_cents"]
                supabase.table("artists").update({"balance_cents": new_bal}).eq("id", artist_id).execute()
    except Exception as e:
        print(f"Warning: Failed to update revenue/balance: {e}")

    return LicenseResponse(
        id=license_id,
        license_hash=license_hash,
        status="success",
        message="License purchased successfully"
    )

@router.get("/tracks/{track_id}/license-templates", response_model=LicenseTemplateListResponse)
def list_license_templates(track_id: str):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        res = supabase.table("license_templates").select("*").eq("track_id", track_id).execute()
        return {"templates": res.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/tracks/{track_id}/license-templates", response_model=LicenseTemplateResponse)
def create_license_template(track_id: str, req: LicenseTemplateCreateRequest):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")

    try:
        track_res = supabase.table("tracks").select("id").eq("id", track_id).execute()
        if not track_res.data:
            raise HTTPException(status_code=404, detail="Track not found")

        insert_res = supabase.table("license_templates").insert({
            "track_id": track_id,
            "name": req.name,
            "description": req.description,
            "price_cents": req.price_cents,
            "usage_terms_text": req.usage_terms_text
        }).execute()
        if not insert_res.data:
            raise HTTPException(status_code=500, detail="Failed to create template")
        return insert_res.data[0]
    except Exception as e:
        if isinstance(e, HTTPException): raise
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/artists/{artist_id}/licensing-dashboard", response_model=DashboardResponse)
def get_dashboard(artist_id: str):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase not configured")
        
    try:
        # Check artist exists
        artist_res = supabase.table("artists").select("balance_cents").eq("id", artist_id).execute()
        if not artist_res.data:
            raise HTTPException(status_code=404, detail="Artist not found")
        
        # We query tracks by artist_id, then get total revenue
        tracks_res = supabase.table("tracks").select("id, license_revenue_cents").eq("artist_id", artist_id).execute()
        total_revenue = sum(t.get("license_revenue_cents", 0) for t in tracks_res.data)
        
        track_ids = [t["id"] for t in tracks_res.data]
        if track_ids:
            licenses_res = supabase.table("licenses").select("*").in_("track_id", track_ids).order("created_at", desc=True).limit(10).execute()
            recent_licenses = licenses_res.data
            
            # Use query count logic 
            count_res = supabase.table("licenses").select("id", count="exact").in_("track_id", track_ids).execute()
            total_licenses = count_res.count if count_res.count is not None else len(count_res.data)
        else:
            recent_licenses = []
            total_licenses = 0
            
        return DashboardResponse(
            total_license_revenue_cents=total_revenue,
            total_licenses=total_licenses,
            recent_licenses=recent_licenses
        )
            
    except Exception as e:
        if isinstance(e, HTTPException): raise
        raise HTTPException(status_code=500, detail=str(e))
