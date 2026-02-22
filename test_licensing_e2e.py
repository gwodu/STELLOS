import asyncio
import os
import uuid
from datetime import datetime

# Set dummy keys if they are not set to avoid immediate crashes when not running with them
# Note: For an actual test against Stripe/XRPL, these should be set in the environment before run.
if not os.environ.get("STRIPE_API_KEY"):
    os.environ["STRIPE_API_KEY"] = "sk_test_mocked123"
from xrpl.wallet import Wallet
if not os.environ.get("XRPL_SEED"):
    # Create a random valid testnet seed for demonstration purposes
    w = Wallet.create()
    os.environ["XRPL_SEED"] = w.seed

from licensing import \
    router, LicensePurchaseRequest, process_stripe_payment, xrpl_record_license

class MockBackgroundTasks:
    def __init__(self):
        self.tasks = []
    
    def add_task(self, func, *args, **kwargs):
        self.tasks.append((func, args, kwargs))

async def test_licensing_e2e():
    from licensing import supabase
    if not supabase:
        print("Skipping E2E test. Supabase is not configured locally.")
        return

    print("--- Starting Licensing E2E Test ---")
    
    # Setup test data
    test_artist_id = str(uuid.uuid4())
    test_track_id = str(uuid.uuid4())
    test_template_id = str(uuid.uuid4())
    
    print(f"1. Creating Mock Artist ({test_artist_id})...")
    supabase.table("artists").insert({
        "id": test_artist_id,
        "name": "Test SDK Artist",
        "balance_cents": 0
    }).execute()
    
    print(f"2. Creating Mock Track ({test_track_id})...")
    supabase.table("tracks").insert({
        "id": test_track_id,
        "title": "E2E SDK Test Track",
        "audio_file_url": "http://mock.com/raw/test.mp3",
        "licensing_enabled": True,
        "license_revenue_cents": 0,
        "artist_id": test_artist_id
    }).execute()
    
    print(f"3. Creating Mock License Template ({test_template_id})...")
    supabase.table("license_templates").insert({
        "id": test_template_id,
        "track_id": test_track_id,
        "name": "Premium License",
        "price_cents": 5000,
        "usage_terms_text": "Unlimited streaming."
    }).execute()

    print("\n--- Running Purchase Flow ---")
    req = LicensePurchaseRequest(
        license_template_id=test_template_id,
        user_id=str(uuid.uuid4())
    )
    
    bg_tasks = MockBackgroundTasks()
    
    try:
        # Import the endpoint function directly for testing
        from licensing import purchase_license
        resp = await purchase_license(test_track_id, req, bg_tasks)
        print(f"Purchase Successful! License ID: {resp.id}")
        print(f"License Hash: {resp.license_hash}")
        
    except Exception as e:
        print(f"Purchase failed: {e}")
        return
        
    print("\n--- Running Background XRPL Logging ---")
    if bg_tasks.tasks:
        func, args, kwargs = bg_tasks.tasks[0]
        print(f"Executing: {func.__name__} with args {args}")
        await func(*args, **kwargs)
    else:
        print("No background tasks were enqueued.")
        
    print("\n--- Verifying Database State ---")
    l_res = supabase.table("licenses").select("*").eq("id", resp.id).execute()
    license_record = l_res.data[0]
    print(f"License Record Found. XRPL Tx Hash: {license_record.get('xrpl_tx_hash')}")
    print(f"Stripe Payment ID: {license_record.get('stripe_payment_id')}")

    a_res = supabase.table("artists").select("balance_cents").eq("id", test_artist_id).execute()
    print(f"Artist Balance: {a_res.data[0]['balance_cents']} cents")
    
    print("\n--- E2E Test Completed ---")

if __name__ == "__main__":
    asyncio.run(test_licensing_e2e())
