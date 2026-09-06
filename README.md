# Property Matcher

Upload property brochures, describe what a client wants in plain language, get a ranked shortlist with match reasons.

## Stack
FastAPI + asyncpg · Postgres/pgvector via Supabase · React + Vite (monochrome UI) · Gemini 3.5 Flash-Lite (or GPT-4o-mini fallback)

## Local setup

### Backend
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt   # includes test deps; use requirements.txt alone for production
cp .env.example .env                  # fill in Supabase + AI keys
```

### Database
Run `schema.sql` (and any later `alter table` migrations from this project's history) against your Supabase Postgres instance via the SQL Editor.

### Frontend
```bash
cd frontend
npm install
cp .env.local.example .env.local      # set VITE_API_URL
```

### Run locally
```bash
# backend
cd backend && uvicorn main:app --reload --port 8000

# frontend (separate terminal)
cd frontend && npm run dev
```

## Deploy

### Backend — Render
1. Push this repo to GitHub.
2. Render dashboard → **New → Blueprint** → connect the repo. Render reads `render.yaml` automatically.
3. Render will prompt for every env var marked `sync: false` — paste in your real `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_ANON_KEY`, `DATABASE_URL`, `GEMINI_API_KEY` (and `OPENAI_API_KEY` if using that fallback).
4. Leave `CORS_ORIGINS` blank for now — fill it in after the frontend is deployed (step below).
5. Deploy. Note the resulting URL, e.g. `https://property-matcher-api.onrender.com`.
6. Confirm: `curl https://property-matcher-api.onrender.com/health`.

### Frontend — Vercel
1. Vercel dashboard → **New Project** → import the same repo, set **root directory** to `frontend`.
2. Vercel auto-detects `vercel.json`. Add one env var: `VITE_API_URL` = your Render backend URL from above.
3. Deploy. Note the resulting URL, e.g. `https://property-matcher.vercel.app`.

### Close the loop — CORS
Go back to Render → your service → **Environment** → set `CORS_ORIGINS` to your Vercel URL (e.g. `https://property-matcher.vercel.app`), then **Manual Deploy → Clear cache & deploy** to pick up the change.

### Verify end-to-end
Visit your Vercel URL, upload a property, run a search — confirm requests reach the Render backend (check Render's logs) and results render correctly.

## Notes
- Free-tier Render services spin down after inactivity — first request after idle takes ~30-60s to wake up. Fine for a demo; worth knowing before showing it to someone live.
- Gemini free-tier rate limits apply in production too — see https://aistudio.google.com/rate-limit for your account's current limits.