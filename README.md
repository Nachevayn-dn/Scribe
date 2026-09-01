# Healthcare AI Platform — Scribe Agent (Step 1)

An AI medical/dental scribe: record or upload a patient encounter, get a
real transcript (OpenAI Whisper) turned into a structured, entity-tagged
clinical note (Claude), edit it line-by-line, and sign it off. Built as the
first agent of a larger multi-agent healthcare platform (scribe today;
inbound/outbound call agents later) — see the product spec this was built
from for the full roadmap.

## Stack

- **Backend**: FastAPI (async), SQLAlchemy 2.0 + Alembic, PostgreSQL, JWT auth
- **Frontend**: React + TypeScript + Vite
- **AI**: OpenAI Whisper (transcription) → Claude (clinical extraction, via `anthropic` SDK)
- **Deploy**: Docker Compose (dev), + Caddy reverse proxy for automatic TLS (prod)

## Data model & roles

`Clinic` (practice) is the top-level tenant. Every `User` belongs to one
clinic with a role:

| Role | Can do |
|---|---|
| `SUPER_ADMIN` | Manage clinic users, assign assistants to providers, everything a provider can do, view audit log |
| `PROVIDER` | Doctor — owns their encounters, signs notes, manages their own templates/preferences |
| `ASSISTANT` | Assigned to one or more providers (many-to-many); can start recordings and edit draft notes for those providers, but cannot sign |

See `backend/app/core/permissions.py` for the exact permission matrix
enforced on every endpoint.

The core pipeline: `Encounter` (patient + provider) → audio uploaded →
`Transcript` (Whisper) → `ClinicalNote` + tagged `NoteEntity` rows (Claude),
organized by an optional `NoteTemplate` and steered by the provider's active
`DoctorPreference` rules. Entities are color-coded in the UI: Medications
(red), Procedures (teal), Diagnostics (yellow), Symptoms (green), Allergies
(mint).

## Running locally

**Requirements**: Docker + Docker Compose.

```bash
cp .env.example .env          # fill in OPENAI_API_KEY / ANTHROPIC_API_KEY (optional for now)
docker compose -f deploy/docker-compose.yml up
```

- Frontend: http://localhost:5173
- Backend API + docs: http://localhost:8000/docs
- Postgres: localhost:5432 (user/pass/db: `scribe`)

The backend runs `alembic upgrade head` on startup, seeding two global note
templates (Clinical Summary, Referral Letter). First visit
http://localhost:5173/signup to create a clinic + your Super Admin account.

Without `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` set, the pipeline still runs
end-to-end but the encounter cleanly ends in `FAILED` status with a clear
error message — useful for exercising everything except the actual AI
calls.

### Running without Docker

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # point DATABASE_URL at your own Postgres
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Tests

```bash
cd backend
source .venv/bin/activate
# Needs a Postgres reachable at DATABASE_URL's host with a `scribe_test` DB
# (JSONB/UUID behavior needs to be real Postgres, not SQLite):
createdb scribe_test
pytest
```

```bash
cd frontend
npm run lint   # tsc --noEmit
npm run build  # full production build
```

## Deploying

The same `docker-compose.yml` plus `docker-compose.prod.yml` gets you a
real HTTPS deployment on any VM with Docker installed — no cloud
vendor account required:

```bash
cp deploy/.env.prod.example deploy/.env.prod   # set DOMAIN, JWT_SECRET, API keys
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.prod.yml \
  --env-file deploy/.env.prod up -d --build
```

This adds a `caddy` service that automatically provisions and renews a
Let's Encrypt TLS certificate for `DOMAIN` (point its DNS A/AAAA record at
the VM first), builds the frontend into a static `nginx` image instead of
running the dev server, drops host-bound dev ports/bind-mounts, and sets
`restart: unless-stopped` on every service.

## Repo layout

```
backend/    FastAPI app (app/), Alembic migrations, pytest suite
frontend/   React + TypeScript app (src/)
deploy/     docker-compose.yml (dev), docker-compose.prod.yml + Caddyfile (prod)
```

See `backend/app/services/pipeline.py` for the audio→transcript→note
orchestration and `backend/app/core/permissions.py` for the role model —
those two files are the best starting point for understanding how the
system fits together.

## Security notes (MVP scope)

- Passwords hashed with bcrypt; JWT (HS256) auth, ~12h expiry.
- Every note view/edit/sign, audio upload, and admin action writes an
  append-only `AuditLog` row (no update/delete endpoint exists for it).
- TLS is terminated at Caddy in the prod compose file; local dev is
  plain HTTP.
- A signed `ClinicalNote` is immutable — no endpoint allows editing it.
- Secrets are all env vars; `.env` files are gitignored.

This is an MVP security posture, not a HIPAA/SOC2 compliance package —
see the product's GDPR/compliance framework doc for what a production
rollout would still need (DPAs, DPIAs, formal audits, etc).
