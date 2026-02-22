#!/usr/bin/env python3
import argparse
import os
import sys
import requests

SUPPORTED_EXT = {".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"}

def find_audio_files(path: str):
    files = []
    if os.path.isdir(path):
        for root, _, names in os.walk(path):
            for n in names:
                ext = os.path.splitext(n)[1].lower()
                if ext in SUPPORTED_EXT:
                    files.append(os.path.join(root, n))
    elif os.path.isfile(path):
        ext = os.path.splitext(path)[1].lower()
        if ext in SUPPORTED_EXT:
            files.append(path)
    return files

def upload_file(api_url: str, file_path: str, title: str, artist: str):
    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f)}
        data = {
            "title": title,
            "artist_name": artist
        }
        res = requests.post(f"{api_url}/upload", files=files, data=data, timeout=120)
        if not res.ok:
            raise RuntimeError(f"Upload failed: {res.status_code} {res.text}")
        return res.json()

def main():
    parser = argparse.ArgumentParser(description="Seed demo tracks via API upload.")
    parser.add_argument("--api-url", default=os.environ.get("API_URL", "http://localhost:7860"))
    parser.add_argument("--path", required=True, help="File or directory containing audio files")
    parser.add_argument("--artist", default="Demo Artist", help="Artist name for all uploads")
    parser.add_argument("--title-prefix", default="", help="Prefix for titles")
    args = parser.parse_args()

    files = find_audio_files(args.path)
    if not files:
        print("No audio files found.")
        return 1

    print(f"Uploading {len(files)} file(s) to {args.api_url}")
    for i, fp in enumerate(files, start=1):
        title = f"{args.title_prefix}{os.path.splitext(os.path.basename(fp))[0]}"
        print(f"[{i}/{len(files)}] {fp}")
        try:
            resp = upload_file(args.api_url, fp, title, args.artist)
            print(f"  -> track_id={resp.get('track_id')} status={resp.get('status')}")
        except Exception as e:
            print(f"  -> failed: {e}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
