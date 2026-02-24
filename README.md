---
title: STELLOS
emoji: 🌌
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
---

# STELLOS

STELLOS is a music discovery app with:
- FastAPI backend (`main.py`) on port `7860`
- Next.js frontend (`frontend/`) on port `3000`
- Supabase for database + storage

## 1. Prerequisites

- Linux/macOS shell
- Python 3.12+ (or 3.11 if you want full ML stack compatibility)
- Node.js 18+
- npm
- Supabase project URL + service role key

Optional:
- Stripe key for real payment intents
- XRPL seed for real XRPL testnet logging

## 2. Environment Setup

From repo root:

```bash
cp .env.example .env
```

Edit `.env`:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-service-role-key
STRIPE_API_KEY=
XRPL_SEED=
DEFAULT_TOKEN_BALANCE=100
NEXT_PUBLIC_API_URL=http://localhost:7860
```

Notes:
- `SUPABASE_KEY` must be the service role key for backend writes.
- You can leave `STRIPE_API_KEY` blank for local mock payments.
- You can leave `XRPL_SEED` blank for local mock XRPL logging.

## 3. Database Migrations

Apply migrations before running the app:

```bash
supabase db push
```

## 4. Backend Setup and Run

### Quick local path (works for API + upload/licensing)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m ensurepip --upgrade
python -m pip install --upgrade pip
pip install fastapi==0.110.0 "uvicorn[standard]==0.29.0" python-dotenv==1.0.1 supabase==2.4.3 python-multipart==0.0.9 requests==2.31.0 stripe
uvicorn main:app --host 0.0.0.0 --port 7860 --reload
```

Health check:

```bash
curl http://localhost:7860/
```

Expected:

```json
{"status":"ok","message":"STELLOS API"}
```

### Full dependency install (includes everything from `requirements.txt`)

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 7860 --reload
```

### Install ML dependencies (for vectorization worker)

```bash
pip install -r requirements_ml.txt
```

## 5. Frontend Setup and Run

In a second terminal:

```bash
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:7860 npm run dev
```

Open:

- `http://localhost:3000`

## 6. LAN Access (Other Devices)

If your laptop IP is `100.67.5.155`:

Backend:

```bash
uvicorn main:app --host 0.0.0.0 --port 7860
```

Frontend:

```bash
cd frontend
NEXT_PUBLIC_API_URL=http://100.67.5.155:7860 npm run dev -- -H 0.0.0.0 -p 3000
```

Open from another device:

- Frontend: `http://100.67.5.155:3000`
- Backend health: `http://100.67.5.155:7860/`

If needed, open firewall ports:

```bash
sudo ufw allow 3000
sudo ufw allow 7860
```

## 7. API Endpoints (Core)

- `GET /` health
- `POST /upload` upload audio
- `GET /tracks?status=LIVE`
- `GET /track/{track_id}`
- `POST /event`
- `POST /radio/start`
- `POST /radio/next`
- `GET /tokens/balance?session_id=...`
- `POST /tracks/{track_id}/vote`
- `GET /tracks/{track_id}/license-templates`
- `POST /tracks/{track_id}/license`

## 8. Seed Demo Audio

```bash
python scripts/seed_demo.py --path /path/to/audio --artist "Demo Artist" --api-url http://localhost:7860
```

## 9. Async Vectorization Worker

Use a separate worker process/service to vectorize uploaded tracks.

```bash
cd /path/to/STELLOS
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements_ml.txt
python scripts/ml_worker.py --interval 20 --batch-size 10
```

What it does:
- Polls tracks with status `UPLOADED` or `PREVIEW_READY`
- Marks track status as `EMBEDDING`
- Computes CLAP embedding
- Updates track with `embedding_vector`, map coordinates, and `status=LIVE`

Run once:

```bash
python scripts/ml_worker.py --once
```

## 10. Common Errors and Fixes

### `ModuleNotFoundError: No module named 'stripe'`

```bash
pip install stripe
```

### `Form data requires "python-multipart"`

```bash
pip install python-multipart==0.0.9
```

### `Supabase not configured`

- Ensure `.env` exists in repo root.
- Ensure `SUPABASE_URL` and `SUPABASE_KEY` are set.
- Restart backend after editing `.env`.

### Frontend loads but backend calls fail

- Confirm frontend env uses backend URL:
  - `NEXT_PUBLIC_API_URL=http://localhost:7860` (or LAN IP)
- Confirm backend is running on `0.0.0.0:7860`.
- Confirm port `7860` is reachable.

## 11. Docker (Optional)

Build and run:

```bash
docker build -t stellos-backend .
docker run --env-file .env -p 7860:7860 stellos-backend
```

## Security Notes

- Never commit `.env`.
- Treat `SUPABASE_KEY`, Stripe keys, and XRPL seed as secrets.
