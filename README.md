<p align="center"><img src="docs/brand/safarnama-logo.png" alt="Safarnama logo" width="320" /></p>

<p align="center">
  <a href="https://safarnama-ai-flame.vercel.app"><img src="https://img.shields.io/badge/Live-Demo-4F46E5?style=for-the-badge&logo=vercel&logoColor=white" alt="Live demo" /></a>
  <a href="https://github.com/mr-gaurav-kumar/safarnama-ai"><img src="https://img.shields.io/badge/GitHub-Code-181717?style=for-the-badge&logo=github&logoColor=white" alt="GitHub" /></a>
  <a href="https://safarnama-api-oi2a.onrender.com/docs"><img src="https://img.shields.io/badge/API%20docs-Swagger-85EA2D?style=for-the-badge&logo=swagger&logoColor=black" alt="API docs" /></a>
</p>

<p align="center">
  <a href="https://github.com/mr-gaurav-kumar/safarnama-ai/actions/workflows/ci.yml"><img src="https://github.com/mr-gaurav-kumar/safarnama-ai/actions/workflows/ci.yml/badge.svg" alt="CI" /></a>
</p>

- **Live:** https://safarnama-ai-flame.vercel.app
- **GitHub:** https://github.com/mr-gaurav-kumar/safarnama-ai
- **API docs:** https://safarnama-api-oi2a.onrender.com/docs (Swagger)

<sub>Free hosting: the first request after a quiet spell can take about 50 seconds while the server wakes up.</sub>

# Safarnama: AI Travel Planner

*Your Next Adventure, Perfectly Planned.*

An AI trip planner for India with personal memory. Every finished trip is
embedded with Gemini and stored in Postgres (pgvector); a new request retrieves
the traveller's most similar past trips (RAG) and Gemini writes a day-by-day plan
shaped by them, checked by guardrails before anyone sees it.

React + TypeScript · FastAPI · PostgreSQL + pgvector (Supabase) · Gemini 2.5 Flash + gemini-embedding-001 · scikit-learn · Celery/Redis (optional)

## AI at a glance

| Part | What it does | Measured |
| --- | --- | --- |
| **RAG memory** | Gemini embeddings of past trips in pgvector (HNSW, cosine); top matches go into the prompt and are shown as "Shaped by your past trips" | **83% Hit@1** finding a past trip to a *similar* place (Manali → Shimla) vs 17% for a lexical baseline (= random) |
| **LLM planner** | Gemini 2.5 Flash, JSON output, with Think-on-the-Plan notes and official tourism figures in the prompt | **100% valid plans**, 0% fallback, all within budget (8-request eval) |
| **Guardrails** | Schema, day-count and budget checks; one retry with the problems spelled out; local outline as last resort; user text sanitised and declared data-not-instructions | Prompt-injection attempt **blocked**; 6 unit tests |
| **Season model** | Random Forest on location + cyclical month → ideal / pleasant / hot / rainy / cold | **93.3%** on unseen destinations vs 65.9% month-only |
| **Budget recommender** | Scores every destination on budget fit, season, open months and style | 76% fully within budget vs 58% style-only |
| **Fraud scoring** | Rules + Isolation Forest over account activity | 84.6% recall, 0 false positives (simulated) |
| **Cost** | Per AI plan | **~$0.01** (~4.7k tokens), p50 latency 19.5 s |

Full numbers, method and caveats: [Metrics](#metrics).

## Features

- **Plan with AI** — day-by-day itinerary with map, budget breakdown and "why this plan"; live progress while it is written
- **Save my own plan** — write the days yourself (no AI), with autocomplete for places, sights, activities and packing items; edit any plan; **plan it again** on new dates
- **Travel Assistant** — "₹20,000, 3 days, mountains in December" → places with a rough budget and the weather, in English, Hindi or Hinglish
- **Where to go** — budget recommender from your home city, weekday/weekend pricing
- **Packing list** — weather-aware suggestions, tick going/returning, admin defaults
- **PDF export** — branded plan with tickets, packing checklist and a different good-luck note on every download
- **My documents** — Aadhaar, PAN, DL, passport, encrypted at rest (Fernet), OCR reads the number in the browser
- **My tickets** — trains (PNR), flights, buses, hotels booked anywhere, in one place
- **Groups** — invite friends; the plan balances everyone's preferences; trip rooms and feedback
- **Book travel** — hand-off to flight, hotel, train and bus sites with the trip pre-filled
- **Help chat** — page-specific help on every page, including login and signup
- **Admin** — merchants, packages, fraud flags, packing defaults, audit log
- **Security** — JWT access tokens + rotating refresh cookies, rate limits, encrypted documents, EXIF stripped from photos

---

## Quick start (Windows)

Double-click **`start.bat`**.

It checks for Python 3.10+ and Node.js, installs everything, sets up the
database, starts both servers in their own windows and opens the app in your
browser. The first run takes a few minutes; after that it starts in seconds.
Close the two server windows to stop the app.

Needs [Python 3.10+](https://www.python.org/downloads/) (tick "Add python.exe to
PATH" when installing) and [Node.js LTS](https://nodejs.org/). If either is
missing, `start.bat` says so and where to get it.

The manual steps below do the same thing one command at a time.

## Current state

All features above are built and tested (333 tests). Runs on Supabase
(Postgres + pgvector) with Gemini. Still to come: public deployment.

### Pages

**Traveller** — 9 screens, all built:

| Route | What it does |
| --- | --- |
| `/` | Landing page; the Help chat widget rides along on every page once you are logged in |
| `/login` | Log in or sign up (one screen, two tabs) |
| `/verify` | Confirms the email link, with a resend if it expired |
| `/dashboard` | Your trips, pending group invites, a nudge to rate finished trips |
| `/trips/new` | Destination, dates, budget, travellers, style tags, and the "use my past trips" toggle that turns RAG on |
| `/trips/:id` | Day-by-day plan, map, budget breakdown, "why this was suggested", PDF and email. Live progress arrives over the WebSocket while it is still planning |
| `/trips/:id/room` | Shared room for a group trip: members, each person's own style tags, live discussion |
| `/join` | Accept or decline an invitation |
| `/recommend` | "Where to go": budget, days, travellers, month and styles in; ranked places out, each with its reasons and a "Plan this trip" button that pre-fills `/trips/new` |
| `/insights` | Official tourism statistics, with sources. Public |

**Admin** — 8 screens under `/admin`, every one guarded server-side:

| Route | What it does |
| --- | --- |
| `/admin` | Overview: users, signups this week, trips planning now, and the two queues that need a person — open fraud flags and open escalations |
| `/admin/users` | Search, block/unblock, force-verify, delete, create accounts. Roles are not editable — see "The admin account" below |
| `/admin/trips` | Every trip, filtered by status. A trip stuck in `processing` because a worker died can be marked failed so its owner can replan it |
| `/admin/fraud` | The review queue, highest risk first. Each flag shows the rule that fired and the counts behind it; a decision is dismiss, confirm, or confirm and block |
| `/admin/escalations` | Chats the bot handed over, with the message that triggered it and a link to the full conversation |
| `/admin/feedback` | Ratings and comments, low ones highlighted |
| `/admin/chat-logs` | Every support message with its intent and sentiment, searchable by text or by person |
| `/admin/audit` | Every admin change, written by the server and not editable from the UI |

The admin nav badges the two queues with their live counts, from the same
`/admin/stats` query the overview uses — the number in the sidebar and the
number on the page can never disagree.

Still placeholders: `/book/flights` and `/book/hotels`.

### The admin account

There is exactly one admin: the address in `ADMIN_EMAIL` in `.env`. Sign up
(or log in) with it and confirm the email — it becomes admin by itself, no
command needed. Every `/admin` request checks all three: role, a verified
email, and that the email is `ADMIN_EMAIL`. Anyone else who somehow has the
admin role is turned back into a normal user at their next login, the admin
API has no way to change roles, and `python -m app.cli make-admin` refuses
any other address. Leave `ADMIN_EMAIL` empty and there is no admin at all.

The admin cannot block or delete their own account from the dashboard.

### API

| Endpoint | Method | Does |
| --- | --- | --- |
| `/auth/signup` `/auth/login` | POST | Create an account (sends a verification email) / get a token |
| `/auth/me` | GET | The current user |
| `/auth/refresh` | POST | New access token from the refresh cookie (needs `X-Requested-With`) |
| `/auth/logout` | POST | End this session on the server |
| `/auth/verify` `/auth/resend-verification` | POST | Confirm an email / send a fresh link |
| `/trips` | GET / POST | List your trips / accept a new one (202, planned in the background) |
| `/trips/{id}` | GET / DELETE | One trip with its itinerary / remove it and its memory |
| `/trips/{id}/replan` | POST | Plan it again |
| `/trips/{id}/pdf` | GET | The itinerary as a PDF |
| `/trips/{id}/email` | POST | Email the PDF to your (verified) address |
| `/trips/{id}/invite` `/join` `/decline` `/leave` | POST | Group trip membership |
| `/trips/{id}/matches` | GET | Other travellers going the same way on the same dates |
| `/trips/{id}/feedback` | GET / PUT | Your rating for a finished trip |
| `/ws/trips/{id}` | WebSocket | Live planning progress |
| `/ws/trips/{id}/room` | WebSocket | Group trip room |
| `/ws/chat` | WebSocket | Support chat |
| `/chat/history` | GET | Your chat history |
| `/insights` | GET | Official tourism statistics, with sources (public) |
| `/admin/stats` | GET | The overview numbers |
| `/admin/users` | GET / POST / PUT / DELETE | Manage accounts |
| `/admin/trips` | GET / PUT / DELETE | Manage trips |
| `/admin/fraud-flags` | GET / PUT | The review queue and its decisions |
| `/admin/escalations` | GET / PUT | Handed-over chats |
| `/admin/feedback` | GET / DELETE | Ratings |
| `/admin/chat-logs` `/admin/audit` | GET | Support messages / the admin action log |

**Risk scoring** — `backend/app/fraud/`. Five named rules, each with a window, a
threshold and a fixed score, and the flag records exactly what was counted:

| Rule | Fires on | Risk |
| --- | --- | --- |
| `trip_burst` | 5+ trips created in 10 minutes | 0.80 |
| `invite_burst` | 10+ invitations sent in an hour | 0.70 |
| `many_accounts_one_ip` | 3+ signups from one IP in 24h | 0.70 |
| `login_failures` | 5+ failed logins in 15 minutes | 0.60 |
| `ip_hopping` | logins from 4+ IPs in an hour | 0.60 |

An Isolation Forest (`anomalous_activity`) catches what the rules miss, once
there are enough users to say what "usual" looks like. Nothing here blocks
anyone on its own — a flag is a prompt for a person to look, because a false
positive that locks out a real traveller is worse than a review queue.

**Chat** — `backend/app/chat/`:

- `classify.py` — intent and sentiment; understands English and Hinglish
- `context.py` — your recent trips, stuck or failed ones, the past trips most
  like your question (the same pgvector memory the planner uses), and the
  recent conversation. Only ever your own data.
- `reply.py` — with `GEMINI_API_KEY`, one model call returns intent, sentiment
  and the reply; without it, templates that still use your real trips. The bot
  explains where to do things; it never claims to have changed anything.
- `escalation.py` — negative sentiment or a repeated issue opens a
  `support_escalations` row (one open per person) and emails `ADMIN_EMAIL`
  (defaults to `SMTP_USER`). `/admin/escalations` is where they land.

Messages are limited to 10 a minute per person and 1,000 characters.

Earlier phases — memory (`app/rag/`), background jobs (`app/tasks/`), live
progress (`app/realtime/`), email (`app/notify/`), maps (`app/geo/`), PDF
(`app/export/`) and tourism data (`app/data/`) — work as before.

**Sessions** — you stay logged in across reloads and new tabs for 14 days.
The short-lived access token (30 min) lives only in memory; a refresh token in
an httpOnly, SameSite=Strict cookie (unreadable by page scripts) renews it
silently when it expires. Refresh tokens are stored only as SHA-256 hashes and
rotate on every use; replaying an old one ends that whole session (with a 30 s
grace for two tabs refreshing at once). Logging out revokes it on the server.
For a deployed HTTPS site set `REFRESH_COOKIE_SECURE=true`.

### Phase 8 — the two models (`backend/app/ml/`)

Both learn from `destination_features` — 68 Indian destinations with
location, altitude, coast, typical on-ground cost per person per day and a
0–1 score for each trip style. **This data is curated by hand, not official**
(`app/data/destinations.py`); the table is seeded from it on first use and
rows you edit in the database stay edited.

**Budget Recommender** (`budget_recommender.py`, `POST /recommend/budget`).
Scores every destination:

    score = 0.55 × style match + 0.25 × budget fit + 0.20 × season

- *style* — cosine similarity between the styles you picked and the place's.
  Your rated trips nudge it: a 5★ trip pulls its styles up, a 1★ pushes them
  down (same memory the planner uses). Places you have been to are marked
  and moved down.
- *budget* — a quarter of the budget is set aside for getting there; the rest
  per person per day is compared with the place's typical cost. Under 70% of
  what a place needs, it is left out rather than ranked low.
- *season* — the season model below. National-park core zones closed that
  month are left out.

**Think on the Plan** (`season.py`, `think.py`). A new step in every trip's
generation, between memory retrieval and writing the plan:

1. Where is it? Matched by name or alias; else the nearest known place on the
   map (when geocoding is on); else a place in the same state — and it says so.
2. What is it like then? A **Random Forest** (scikit-learn) trained on
   latitude, longitude, altitude, coast and month → ideal / pleasant / hot /
   rainy / cold, with a confidence. Leave-one-destination-out accuracy is about
   93% (a test checks it beats month-only guessing by a wide margin).
3. How busy? Ministry of Tourism monthly arrival figures, plus Christmas–New
   Year and the summer school holidays for hill stations.
4. Does the money work? tight / workable / comfortable / generous.
5. Does it suit them? Chosen styles the place is weak at.

You watch it think — the reasoning streams over the trip's WebSocket as the
"Thinking it through" step — and it goes into the planner's prompt as
concrete instructions ("monsoon: give each day an indoor backup…"). It is
saved with the itinerary and shown as **How we thought about it**.
`POST /recommend/think` previews it without planning. If it ever fails, the
plan is still made without it.

## Two settings that decide whether the demo is real

Both have working stand-ins, so the app runs without them and nothing looks
broken. That is exactly why they are easy to miss.

| Setting | Stand-in if unset | What you lose |
| --- | --- | --- |
| `DATABASE_URL` on SQLite | SQLite, no pgvector | Similarity search falls back to loading rows and comparing in Python. Fine for tests, not the thing to demo or to put on a CV |
| `GEMINI_API_KEY` empty | hashed character n-grams | Retrieval matches shared words, not meaning. "Hill station in winter" will not find the Manali trip |

Set both before recording a demo. The Supabase steps below take about five
minutes; the Gemini key is free at
[aistudio.google.com](https://aistudio.google.com/apikey).

## Setup (Windows)

Run each block in PowerShell from this folder.

### 1. Configuration

```powershell
copy .env.example .env
```

Open `.env` and set at minimum:

- `DATABASE_URL` — your local Postgres user, password and port
- `JWT_SECRET_KEY` — generate one:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### 2. Database — Supabase

Postgres is a server, not a pip package, and pgvector does not ship with the
Windows build of Postgres — it has to be compiled with Visual Studio. Supabase
gives you Postgres with pgvector already available, with nothing to install, and
it is the same platform the deploy plan uses in production.

1. Sign up at [supabase.com](https://supabase.com) and create a new project.
   Pick the region closest to you (`ap-south-1`, Mumbai) and save the database
   password it asks you to set — it is shown once.
2. Wait for the project to finish provisioning (about two minutes).
3. Click **Connect** at the top of the dashboard, choose **Session pooler**, and
   copy the URI. It looks like:

   ```
   postgresql://postgres.abcdefgh:YOUR-PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
   ```

   Use the **Session pooler**, not the direct connection: the direct connection
   is IPv6-only on the free tier and most home and office networks are IPv4.

4. Put it in `.env` as `DATABASE_URL` (the `postgresql://` link works as it is;
   replace `[YOUR-PASSWORD]` with your password, without the brackets):

   ```
   DATABASE_URL=postgresql://postgres.abcdefgh:YOUR-PASSWORD@aws-0-ap-south-1.pooler.supabase.com:5432/postgres
   ```

   Already have data in local SQLite? Put the link in `.env` as
   `SUPABASE_DATABASE_URL` instead, run `python -m app.cli move-to-postgres`
   from `backend/`, then switch `DATABASE_URL` to it.

`alembic upgrade head` in the next step enables the pgvector extension itself —
there is nothing to click in the dashboard.

### 3. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

API at http://localhost:8000 · interactive docs at http://localhost:8000/docs

### 4. Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

App at http://localhost:5173. The home page shows `Backend: ok` when the two are
talking to each other.

---

## Layout

```
backend/
  app/
    core/        config (settings), database session
    routers/     one module per domain, all mounted in main.py
    models/      SQLAlchemy tables
    schemas/     Pydantic request/response models
    tasks/       Celery jobs
    rag/         embeddings + retrieval (the RAG pipeline)
    fraud/       risk rules + Isolation Forest scorer
    chat/        intent, sentiment, context, escalation
    ml/          Phase 8: budget recommender, season model, Think on the Plan
    data/        tourism statistics (official) + destinations (curated)
  alembic/       migrations
frontend/
  src/
    lib/         api client, auth context
    components/  app shell, route guards
    features/    one folder per feature area
      admin/     ui.tsx (tables, badges, paging) + one page per admin screen
```

## Conventions

- Settings are read in `app/core/config.py` and nowhere else.
- The frontend never calls axios directly — it imports `api` from `src/lib/api.ts`.
- The JWT lives in memory, not `localStorage`.
- Admin access is checked **server-side on every request**; the `AdminRoute`
  guard is only for the UI.
- `app/rag/embeddings.py` is the single swap point for the embedding provider.
- Admin screens are built from `features/admin/ui.tsx` -- tables, badges, paging
  and confirm buttons live there, so the eight screens stay thin and look alike.
- Every admin mutation invalidates the whole `['admin']` query key, so a block or
  a resolve refreshes the sidebar counts as well as the table it happened in.

## Health endpoints

| Endpoint | Checks |
| --- | --- |
| `GET /health` | process is up (no DB call) |
| `GET /health/db` | Postgres answers and pgvector is installed |

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pytest
```

333 tests, no database, no Redis and no network needed — the suite runs against in-memory
SQLite. They cover password hashing (including the bcrypt 72-byte trap), JWT round-trips
and tampering, every auth route — including that a wrong password and an unknown
email return an identical response — the trip routes, including that one user
cannot read or delete another user's trip, and the memory: similar trips are
recalled and ranked above unrelated ones, memory never crosses users, deleting a
trip removes it from memory, and the Postgres vector query compiles.

## Metrics

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m benchmarks.run_metrics
```

Offline and seeded, so it prints the same numbers every time. Each benchmark's
docstring says what it measures and what it does not — read it before quoting.

| What | Result | Baseline |
| --- | --- | --- |
| Memory recall (Hit@1, 150 synthetic queries, offline embedder) | 99.3% | 10.7% most-recent trip |
| Feedback: loved trip ranked above disliked (150 cases) | 99.3% | 48.0% similarity only |
| Season model, unseen destinations (816 samples, curated labels) | 93.3% acc, 0.93 macro-F1 | 65.9% / 0.53 month only |
| Recommender picks in a good season (1,728 requests) | 74.7% | 53.6% style only |
| Recommender picks fully within budget | 76.2% | 57.6% style only |
| Recommender style match (cosine, the trade-off) | 0.72 | 0.78 style only |
| Fraud recall, simulated 352 users / 52 abusers | 84.6%, 0 false positives | 61.5% rules only |
| Login burst: 100 wrong passwords in a minute | 90 blocked | 0 without limits |
| Recommender latency p50 | 2.3 ms | 399 ms before batching + caching |

### AI evaluation (real Gemini)

Needs `GEMINI_API_KEY` and internet; paced for the free tier (about 7 minutes):

```powershell
python -m benchmarks.ai_eval
```

Results are saved to `backend/benchmarks/results/ai_eval.json`.

**Memory retrieval** — 30 synthetic travellers × 6 past trips, each in a
different climate region. *Same place*: the request names a place they have been.
*Similar place*: a different place in the same region (past Manali, now Shimla),
so the right memory shares no words with the request. Random Hit@1 = 17%.

| Task | Gemini Hit@1 | Hit@3 | MRR | Lexical (hashed n-gram) Hit@1 | Hit@3 | MRR |
| --- | --- | --- | --- | --- | --- | --- |
| Same place | 100% | 100% | 1.00 | 60% | 97% | 0.79 |
| Similar place | **83%** | 90% | 0.89 | 17% | 53% | 0.43 |

**Itinerary quality** — gemini-2.5-flash, 7 trips plus one prompt-injection
attempt, through the real pipeline (notes, tourism context, guardrails).

| Metric | Result |
| --- | --- |
| Valid on first try / after one retry | 100% / 100% |
| Fell back to the local outline | 0% |
| Right number of days · within budget | 100% · 100% |
| Places matched to our curated sights | 62% (a lower bound: the list is short) |
| Prompt injection | Held |
| Latency p50 / max | 19.5 s / 26.3 s |
| Cost per plan | ~$0.011 (~4.7k tokens) |

Caveats: the itinerary eval is 8 requests (free-tier limits), so read 100% as
8 of 8, not a guarantee; season labels and fraud data are curated/simulated.

## License

MIT, see [LICENSE](LICENSE).
