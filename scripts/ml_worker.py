#!/usr/bin/env python3
import argparse
import os
import sys
import time

from dotenv import load_dotenv
from supabase import Client, create_client

# Reuse embedding pipeline logic from backend.
from process import make_embedding


def init_supabase() -> Client:
    load_dotenv()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(url, key)


def fetch_pending_tracks(supabase: Client, batch_size: int):
    pending = []
    for status in ("UPLOADED", "PREVIEW_READY"):
        try:
            res = (
                supabase.table("tracks")
                .select("id,audio_file_url,status")
                .eq("status", status)
                .limit(batch_size)
                .execute()
            )
            pending.extend(res.data or [])
            if len(pending) >= batch_size:
                break
        except Exception as exc:
            print(f"[worker] failed to fetch {status} tracks: {exc}")
    return pending[:batch_size]


def process_batch(supabase: Client, batch_size: int):
    tracks = fetch_pending_tracks(supabase, batch_size)
    if not tracks:
        print("[worker] no pending tracks")
        return 0

    processed = 0
    for track in tracks:
        track_id = track.get("id")
        audio_url = track.get("audio_file_url")
        if not track_id or not audio_url:
            continue

        print(f"[worker] embedding track {track_id} ({track.get('status')})")
        # Best effort lock to reduce duplicate processing if multiple workers run.
        try:
            supabase.table("tracks").update({"status": "EMBEDDING"}).eq("id", track_id).execute()
        except Exception as exc:
            print(f"[worker] could not set EMBEDDING for {track_id}: {exc}")

        make_embedding(track_id, audio_url)
        processed += 1

    return processed


def main():
    parser = argparse.ArgumentParser(description="STELLOS async ML embedding worker")
    parser.add_argument("--interval", type=int, default=20, help="poll interval in seconds")
    parser.add_argument("--batch-size", type=int, default=10, help="tracks per poll")
    parser.add_argument("--once", action="store_true", help="run one batch and exit")
    args = parser.parse_args()

    try:
        supabase = init_supabase()
    except Exception as exc:
        print(f"[worker] startup error: {exc}")
        return 1

    print("[worker] started")
    if args.once:
        process_batch(supabase, args.batch_size)
        return 0

    while True:
        try:
            process_batch(supabase, args.batch_size)
        except KeyboardInterrupt:
            print("[worker] stopped")
            return 0
        except Exception as exc:
            print(f"[worker] loop error: {exc}")
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
